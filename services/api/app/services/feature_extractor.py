"""Granular biometric feature extraction, template construction, and comparison.

Implements the full feature extraction pipeline described in the system
specification, covering eyes, nose, lips, eyebrows, jawline, face geometry,
skin texture analysis, dark-circle detection, and mole/mark constellation
mapping.  All computations use NumPy for performance.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

import numpy as np

# ── MediaPipe 468-landmark index groups ──────────────────────────────────
# Eye landmarks (6-point EAR model)
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# Extended eye contour for detailed geometry
LEFT_EYE_CONTOUR = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
RIGHT_EYE_CONTOUR = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]

# Iris landmarks (MediaPipe Face Mesh with iris)
LEFT_IRIS = [468, 469, 470, 471, 472]
RIGHT_IRIS = [473, 474, 475, 476, 477]

# Eyebrows
LEFT_BROW = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
RIGHT_BROW = [336, 296, 334, 293, 300, 285, 295, 282, 283, 276]

# Nose
NOSE_BRIDGE = [6, 197, 195, 5, 4]
NOSE_TIP = [1]
NOSE_BASE = [2, 98, 327]
NOSE_WINGS = [129, 358]  # Alar base
NOSTRILS = [48, 278]

# Lips / Mouth
UPPER_LIP_TOP = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291]
UPPER_LIP_BOTTOM = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308]
LOWER_LIP_TOP = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308]
LOWER_LIP_BOTTOM = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291]
MOUTH_CORNERS = [61, 291]
MOUTH_TOP_BOTTOM = [13, 14]

# Jawline contour
JAWLINE = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
           397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
           172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]

# Cheeks
LEFT_CHEEK = 234
RIGHT_CHEEK = 454

# Forehead / Chin
FOREHEAD = 10
CHIN = 152

# Face oval for boundary analysis
FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
             397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
             172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]

# Key indices for embedding computation (32 strategically chosen landmarks)
KEY_INDICES = [
    10, 33, 46, 52, 61, 70, 84, 91, 105, 127, 133, 145, 152, 159, 172, 195,
    199, 205, 234, 263, 291, 300, 308, 317, 334, 356, 362, 374, 386, 454, 468, 473,
]

# ── Skin analysis regions (approximate bounding boxes as landmark index groups)
SKIN_REGIONS = {
    "forehead": [10, 67, 109, 338, 297, 21, 54, 103],
    "left_cheek": [234, 132, 93, 127, 162, 116, 117, 118, 119, 120, 100],
    "right_cheek": [454, 361, 323, 356, 389, 345, 346, 347, 348, 349, 329],
    "nose": [6, 197, 195, 5, 4, 1, 2, 98, 327],
    "chin": [152, 148, 176, 149, 150, 136, 172, 377, 400, 378, 379],
    "periorbital_left": [33, 7, 163, 144, 145, 153, 154, 155, 133],
    "periorbital_right": [362, 382, 381, 380, 374, 373, 390, 249, 263],
}


# ─────────────────────────────────────────────────────────────────────────
# Low-level helpers
# ─────────────────────────────────────────────────────────────────────────

def _array(landmarks: list[list[float]]) -> np.ndarray:
    """Convert landmark list to Nx3 float32 array."""
    if not landmarks:
        return np.zeros((0, 3), dtype=np.float32)
    pts = np.array(landmarks, dtype=np.float32)
    if pts.ndim == 1:
        pts = pts.reshape(1, -1)
    if pts.shape[1] == 2:
        pts = np.column_stack([pts, np.zeros(pts.shape[0], dtype=np.float32)])
    return pts


def _dist(a: np.ndarray, b: np.ndarray) -> float:
    """Euclidean distance between two points."""
    return float(np.linalg.norm(a - b))


def _angle_between(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Angle at vertex b formed by vectors ba and bc, in degrees."""
    ba = a - b
    bc = c - b
    cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    return float(np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0))))


def _ear(pts: np.ndarray, idx: list[int]) -> float:
    """Eye Aspect Ratio for a 6-point eye model."""
    p1, p2, p3, p4, p5, p6 = [pts[i] for i in idx]
    vert = _dist(p2, p6) + _dist(p3, p5)
    horiz = 2.0 * max(_dist(p1, p4), 1e-6)
    return vert / horiz


def _centroid(pts: np.ndarray, indices: list[int]) -> np.ndarray:
    """Average position of a set of indexed landmarks."""
    return pts[indices].mean(axis=0)


def _classify_shape(ratio: float, ranges: list[tuple[float, float, str]]) -> str:
    """Classify a numeric ratio into a named category."""
    for lo, hi, label in ranges:
        if lo <= ratio < hi:
            return label
    return ranges[-1][2]


# ─────────────────────────────────────────────────────────────────────────
# Eye feature extraction
# ─────────────────────────────────────────────────────────────────────────

def _extract_eye_features(pts: np.ndarray) -> dict[str, float | str]:
    """Extract comprehensive eye biometric features."""
    feats: dict[str, Any] = {}

    # Eye Aspect Ratios
    ear_l = _ear(pts, LEFT_EYE)
    ear_r = _ear(pts, RIGHT_EYE)
    feats["ear_left"] = round(ear_l, 5)
    feats["ear_right"] = round(ear_r, 5)
    feats["ear_average"] = round((ear_l + ear_r) / 2, 5)
    feats["eye_symmetry_score"] = round(1.0 - abs(ear_l - ear_r) / max(ear_l, ear_r, 1e-6), 4)

    # Eye midpoints
    left_eye_mid = _centroid(pts, LEFT_EYE)
    right_eye_mid = _centroid(pts, RIGHT_EYE)

    # Inter-pupillary distance (normalised by face width)
    ipd = _dist(left_eye_mid, right_eye_mid)
    feats["inter_pupillary_distance"] = round(ipd, 5)

    # Palpebral fissure (eye opening dimensions)
    feats["left_eye_width"] = round(_dist(pts[LEFT_EYE[0]], pts[LEFT_EYE[3]]), 5)
    feats["left_eye_height"] = round(
        (_dist(pts[LEFT_EYE[1]], pts[LEFT_EYE[5]]) + _dist(pts[LEFT_EYE[2]], pts[LEFT_EYE[4]])) / 2, 5
    )
    feats["right_eye_width"] = round(_dist(pts[RIGHT_EYE[0]], pts[RIGHT_EYE[3]]), 5)
    feats["right_eye_height"] = round(
        (_dist(pts[RIGHT_EYE[1]], pts[RIGHT_EYE[5]]) + _dist(pts[RIGHT_EYE[2]], pts[RIGHT_EYE[4]])) / 2, 5
    )

    # Eye corner angles (medial and lateral canthus)
    feats["left_eye_medial_angle"] = round(
        _angle_between(pts[LEFT_EYE[1]], pts[LEFT_EYE[0]], pts[LEFT_EYE[5]]), 2
    )
    feats["right_eye_medial_angle"] = round(
        _angle_between(pts[RIGHT_EYE[1]], pts[RIGHT_EYE[0]], pts[RIGHT_EYE[5]]), 2
    )

    # Iris/gaze features (if iris landmarks available)
    if len(pts) > 473:
        left_iris_center = _centroid(pts, LEFT_IRIS)
        right_iris_center = _centroid(pts, RIGHT_IRIS)
        feats["gaze_horizontal"] = round(
            ((left_iris_center[0] - left_eye_mid[0]) + (right_iris_center[0] - right_eye_mid[0])) / 2, 5
        )
        feats["gaze_vertical"] = round(
            ((left_iris_center[1] - left_eye_mid[1]) + (right_iris_center[1] - right_eye_mid[1])) / 2, 5
        )
        # Iris-to-eye ratio (estimate of iris size relative to eye opening)
        left_iris_radius = np.mean([_dist(left_iris_center, pts[i]) for i in LEFT_IRIS[1:]])
        right_iris_radius = np.mean([_dist(right_iris_center, pts[i]) for i in RIGHT_IRIS[1:]])
        feats["left_iris_ratio"] = round(left_iris_radius / max(feats["left_eye_width"], 1e-6), 4)
        feats["right_iris_ratio"] = round(right_iris_radius / max(feats["right_eye_width"], 1e-6), 4)

    return feats


# ─────────────────────────────────────────────────────────────────────────
# Eyebrow feature extraction
# ─────────────────────────────────────────────────────────────────────────

def _extract_brow_features(pts: np.ndarray) -> dict[str, float | str]:
    feats: dict[str, Any] = {}

    left_brow_mid = _centroid(pts, LEFT_BROW)
    right_brow_mid = _centroid(pts, RIGHT_BROW)
    left_eye_mid = _centroid(pts, LEFT_EYE)
    right_eye_mid = _centroid(pts, RIGHT_EYE)
    face_height = _dist(pts[FOREHEAD], pts[CHIN])

    # Brow-to-eye distance (normalised)
    feats["left_brow_eye_dist"] = round(_dist(left_brow_mid, left_eye_mid) / max(face_height, 1e-6), 5)
    feats["right_brow_eye_dist"] = round(_dist(right_brow_mid, right_eye_mid) / max(face_height, 1e-6), 5)
    feats["brow_raise_score"] = round(
        ((feats["left_brow_eye_dist"] + feats["right_brow_eye_dist"]) / 2) * 9, 4
    )

    # Inter-eyebrow distance (glabella width)
    feats["inter_brow_distance"] = round(_dist(pts[LEFT_BROW[0]], pts[RIGHT_BROW[0]]), 5)

    # Brow arch height (highest point relative to inner/outer endpoints)
    left_inner = pts[LEFT_BROW[0]]
    left_outer = pts[LEFT_BROW[-1]]
    left_arch = pts[LEFT_BROW[2]]  # arch point
    baseline_left = (left_inner[1] + left_outer[1]) / 2
    feats["left_brow_arch"] = round(abs(left_arch[1] - baseline_left) / max(face_height, 1e-6), 5)

    right_inner = pts[RIGHT_BROW[0]]
    right_outer = pts[RIGHT_BROW[-1]]
    right_arch = pts[RIGHT_BROW[2]]
    baseline_right = (right_inner[1] + right_outer[1]) / 2
    feats["right_brow_arch"] = round(abs(right_arch[1] - baseline_right) / max(face_height, 1e-6), 5)

    # Brow length
    feats["left_brow_length"] = round(_dist(left_inner, left_outer), 5)
    feats["right_brow_length"] = round(_dist(right_inner, right_outer), 5)
    feats["brow_symmetry_score"] = round(
        1.0 - abs(feats["left_brow_length"] - feats["right_brow_length"]) /
        max(feats["left_brow_length"], feats["right_brow_length"], 1e-6), 4
    )

    return feats


# ─────────────────────────────────────────────────────────────────────────
# Nose feature extraction
# ─────────────────────────────────────────────────────────────────────────

def _extract_nose_features(pts: np.ndarray) -> dict[str, float | str]:
    feats: dict[str, Any] = {}
    face_height = _dist(pts[FOREHEAD], pts[CHIN])

    # Nose length (nasion to tip)
    nasion = pts[NOSE_BRIDGE[0]]
    tip = pts[NOSE_TIP[0]]
    feats["nose_length"] = round(_dist(nasion, tip) / max(face_height, 1e-6), 5)

    # Nose bridge width at different points
    bridge_mid = pts[NOSE_BRIDGE[2]]
    feats["nose_bridge_width"] = round(abs(pts[NOSE_WINGS[0]][0] - pts[NOSE_WINGS[1]][0]) * 0.5, 5)

    # Alar base width (widest point)
    alar_width = _dist(pts[NOSE_WINGS[0]], pts[NOSE_WINGS[1]])
    feats["alar_base_width"] = round(alar_width, 5)

    # Nose tip to base distance
    subnasale = pts[NOSE_BASE[0]]
    feats["columella_length"] = round(_dist(tip, subnasale), 5)

    # Nasolabial angle estimate (angle between columella and upper lip plane)
    upper_lip_center = pts[MOUTH_TOP_BOTTOM[0]]
    feats["nasolabial_angle"] = round(_angle_between(tip, subnasale, upper_lip_center), 2)

    # Nose bridge straightness (deviation from straight line)
    bridge_pts = pts[NOSE_BRIDGE]
    line_start = bridge_pts[0]
    line_end = bridge_pts[-1]
    line_vec = line_end - line_start
    line_len = np.linalg.norm(line_vec) + 1e-8
    deviations = []
    for p in bridge_pts[1:-1]:
        t = np.dot(p - line_start, line_vec) / (line_len ** 2)
        proj = line_start + t * line_vec
        deviations.append(_dist(p, proj))
    feats["nose_bridge_deviation"] = round(np.mean(deviations) / max(face_height, 1e-6), 6)

    # Nose asymmetry (compare left and right nostril positions relative to tip)
    tip_x = tip[0]
    left_nostril_offset = abs(pts[NOSTRILS[0]][0] - tip_x)
    right_nostril_offset = abs(pts[NOSTRILS[1]][0] - tip_x)
    feats["nose_asymmetry"] = round(
        abs(left_nostril_offset - right_nostril_offset) / max(alar_width, 1e-6), 4
    )

    return feats


# ─────────────────────────────────────────────────────────────────────────
# Lip and mouth feature extraction
# ─────────────────────────────────────────────────────────────────────────

def _extract_lip_features(pts: np.ndarray) -> dict[str, float | str]:
    feats: dict[str, Any] = {}
    face_height = _dist(pts[FOREHEAD], pts[CHIN])
    face_width = _dist(pts[LEFT_CHEEK], pts[RIGHT_CHEEK])

    mouth_left = pts[MOUTH_CORNERS[0]]
    mouth_right = pts[MOUTH_CORNERS[1]]
    mouth_top = pts[MOUTH_TOP_BOTTOM[0]]
    mouth_bottom = pts[MOUTH_TOP_BOTTOM[1]]

    mouth_width = _dist(mouth_left, mouth_right)
    mouth_height = _dist(mouth_top, mouth_bottom)

    feats["mouth_width"] = round(mouth_width, 5)
    feats["mouth_height"] = round(mouth_height, 5)
    feats["mar"] = round(mouth_height / max(mouth_width, 1e-6), 5)  # Mouth Aspect Ratio
    feats["smile_score"] = round((mouth_width / max(face_width, 1e-6)) * 2.2, 4)

    # Upper lip height (mid-point)
    upper_lip_top_mid = pts[0]  # Center of upper lip top
    upper_lip_bottom_mid = pts[13]  # Center of upper lip bottom
    feats["upper_lip_height"] = round(_dist(upper_lip_top_mid, upper_lip_bottom_mid), 5)

    # Lower lip height
    lower_lip_top_mid = pts[14]
    lower_lip_bottom_mid = pts[17]
    feats["lower_lip_height"] = round(_dist(lower_lip_top_mid, lower_lip_bottom_mid), 5)

    # Lip volume ratio (upper vs lower)
    feats["lip_volume_ratio"] = round(
        feats["upper_lip_height"] / max(feats["lower_lip_height"], 1e-6), 4
    )

    # Cupid's bow analysis
    cupid_left = pts[37]
    cupid_right = pts[267]
    cupid_center = pts[0]
    feats["cupid_bow_width"] = round(_dist(cupid_left, cupid_right), 5)
    feats["cupid_bow_depth"] = round(
        abs(cupid_center[1] - (cupid_left[1] + cupid_right[1]) / 2), 5
    )

    # Lip symmetry
    left_half_width = _dist(mouth_left, cupid_center)
    right_half_width = _dist(cupid_center, mouth_right)
    feats["lip_symmetry_score"] = round(
        1.0 - abs(left_half_width - right_half_width) / max(mouth_width, 1e-6), 4
    )

    # Mouth corner angle (relative to horizontal)
    angle = np.degrees(np.arctan2(
        mouth_right[1] - mouth_left[1], mouth_right[0] - mouth_left[0]
    ))
    feats["mouth_corner_angle"] = round(float(angle), 2)

    # Lip to chin distance
    feats["lip_to_chin"] = round(_dist(mouth_bottom, pts[CHIN]) / max(face_height, 1e-6), 5)

    # Philtrum width
    feats["philtrum_width"] = round(
        _dist(pts[164], pts[165]) if max(164, 165) < len(pts) else 0.0, 5
    )

    return feats


# ─────────────────────────────────────────────────────────────────────────
# Jawline and face shape
# ─────────────────────────────────────────────────────────────────────────

def _extract_jawline_features(pts: np.ndarray) -> dict[str, float | str]:
    feats: dict[str, Any] = {}
    face_width = _dist(pts[LEFT_CHEEK], pts[RIGHT_CHEEK])
    face_height = _dist(pts[FOREHEAD], pts[CHIN])

    # Face width-to-height ratio
    fwhr = face_width / max(face_height, 1e-6)
    feats["face_width"] = round(face_width, 5)
    feats["face_height"] = round(face_height, 5)
    feats["face_whr"] = round(fwhr, 4)

    # Face shape classification
    forehead_width = _dist(pts[JAWLINE[0]], pts[JAWLINE[-1]])
    jaw_width = _dist(pts[JAWLINE[8]], pts[JAWLINE[26]])
    mid_face_width = face_width

    fw_ratio = forehead_width / max(mid_face_width, 1e-6)
    jw_ratio = jaw_width / max(mid_face_width, 1e-6)

    if fwhr > 0.85:
        shape = "round" if fw_ratio > 0.9 and jw_ratio > 0.9 else "square"
    elif fwhr < 0.65:
        shape = "oblong"
    elif fw_ratio > jw_ratio + 0.1:
        shape = "heart"
    elif jw_ratio > fw_ratio + 0.1:
        shape = "diamond"
    else:
        shape = "oval"
    feats["face_shape"] = shape

    # Facial thirds ratio (forehead : nose : lower face)
    forehead_top = pts[FOREHEAD]
    brow_line = _centroid(pts, [LEFT_BROW[0], RIGHT_BROW[0]])
    nose_base = pts[NOSE_BASE[0]]
    chin_pt = pts[CHIN]
    third_upper = _dist(forehead_top, brow_line)
    third_middle = _dist(brow_line, nose_base)
    third_lower = _dist(nose_base, chin_pt)
    total_thirds = third_upper + third_middle + third_lower + 1e-8
    feats["facial_third_upper"] = round(third_upper / total_thirds, 4)
    feats["facial_third_middle"] = round(third_middle / total_thirds, 4)
    feats["facial_third_lower"] = round(third_lower / total_thirds, 4)

    # Facial asymmetry index
    left_jawline = pts[[JAWLINE[i] for i in range(0, len(JAWLINE) // 2)]]
    right_jawline = pts[[JAWLINE[i] for i in range(len(JAWLINE) // 2, len(JAWLINE))]]
    center_x = pts[CHIN][0]
    left_dists = np.abs(left_jawline[:, 0] - center_x)
    right_dists = np.abs(right_jawline[:, 0] - center_x)
    min_len = min(len(left_dists), len(right_dists))
    asymmetry = np.mean(np.abs(left_dists[:min_len] - right_dists[:min_len])) / max(face_width, 1e-6)
    feats["facial_asymmetry_index"] = round(float(asymmetry), 5)

    # Chin shape estimate
    chin_angle = _angle_between(pts[JAWLINE[16]], pts[CHIN], pts[JAWLINE[20]])
    if chin_angle > 130:
        feats["chin_shape"] = "round"
    elif chin_angle > 100:
        feats["chin_shape"] = "square"
    else:
        feats["chin_shape"] = "pointed"

    # Chin to forehead distance
    feats["chin_to_forehead"] = round(face_height, 5)

    # Face convexity angle (glabella → subnasale → chin)
    glabella = pts[NOSE_BRIDGE[0]]
    subnasale = pts[NOSE_BASE[0]]
    feats["face_convexity_angle"] = round(_angle_between(glabella, subnasale, chin_pt), 2)

    return feats


# ─────────────────────────────────────────────────────────────────────────
# Pose estimation
# ─────────────────────────────────────────────────────────────────────────

def _extract_pose(pts: np.ndarray) -> dict[str, float]:
    feats: dict[str, float] = {}
    left_eye_mid = _centroid(pts, LEFT_EYE)
    right_eye_mid = _centroid(pts, RIGHT_EYE)
    face_width = _dist(pts[LEFT_CHEEK], pts[RIGHT_CHEEK])
    face_height = _dist(pts[FOREHEAD], pts[CHIN])
    nose = pts[NOSE_TIP[0]]
    cheek_l, cheek_r = pts[LEFT_CHEEK], pts[RIGHT_CHEEK]
    mouth_top = pts[MOUTH_TOP_BOTTOM[0]]
    eye_mid = (left_eye_mid + right_eye_mid) / 2

    roll = np.degrees(np.arctan2(
        right_eye_mid[1] - left_eye_mid[1],
        right_eye_mid[0] - left_eye_mid[0]
    ))
    yaw = ((nose[0] - (cheek_l[0] + cheek_r[0]) / 2) / max(face_width, 1e-6)) * 180
    pitch = ((nose[1] - (eye_mid[1] + mouth_top[1]) / 2) / max(face_height, 1e-6)) * 180

    feats["yaw"] = round(float(yaw), 2)
    feats["pitch"] = round(float(pitch), 2)
    feats["roll"] = round(float(roll), 2)
    feats["face_size_ratio"] = round(float(face_width * face_height), 5)

    return feats


# ─────────────────────────────────────────────────────────────────────────
# Image-based feature extraction (skin texture, color, moles)
# ─────────────────────────────────────────────────────────────────────────

def _lbp_histogram(gray_patch: np.ndarray, radius: int = 1, bins: int = 26) -> list[float]:
    """Compute simplified Local Binary Pattern histogram for a grayscale patch."""
    if gray_patch.size < 9:
        return [0.0] * bins
    h, w = gray_patch.shape
    if h < 3 or w < 3:
        return [0.0] * bins
    center = gray_patch[radius:h - radius, radius:w - radius]
    offsets = [(-radius, 0), (-radius, radius), (0, radius), (radius, radius),
               (radius, 0), (radius, -radius), (0, -radius), (-radius, -radius)]
    lbp = np.zeros_like(center, dtype=np.uint8)
    for bit, (dy, dx) in enumerate(offsets):
        neighbor = gray_patch[radius + dy:h - radius + dy, radius + dx:w - radius + dx]
        lbp |= ((neighbor >= center).astype(np.uint8) << bit)
    hist, _ = np.histogram(lbp, bins=bins, range=(0, 256))
    total = hist.sum() + 1e-8
    return (hist / total).round(5).tolist()


def extract_skin_features(image: np.ndarray | None, pts: np.ndarray) -> dict[str, Any]:
    """Extract skin texture and color features from image using landmark regions."""
    feats: dict[str, Any] = {}
    if image is None or pts.size == 0:
        feats["skin_analysis_available"] = False
        return feats

    feats["skin_analysis_available"] = True
    h, w = image.shape[:2]
    gray = image.mean(axis=2) if image.ndim == 3 else image

    # Extract LBP histograms for each facial region
    lbp_features: dict[str, list[float]] = {}
    for region_name, region_indices in SKIN_REGIONS.items():
        valid_idx = [i for i in region_indices if i < len(pts)]
        if not valid_idx:
            continue
        region_pts = pts[valid_idx]
        xs = (region_pts[:, 0] * w).astype(int).clip(0, w - 1)
        ys = (region_pts[:, 1] * h).astype(int).clip(0, h - 1)
        x_min, x_max = max(xs.min(), 0), min(xs.max(), w - 1)
        y_min, y_max = max(ys.min(), 0), min(ys.max(), h - 1)
        if x_max - x_min < 4 or y_max - y_min < 4:
            continue
        patch = gray[y_min:y_max, x_min:x_max]
        lbp_features[region_name] = _lbp_histogram(patch, radius=1)

    feats["lbp_texture"] = lbp_features

    # Skin color analysis per region (mean RGB values)
    if image.ndim == 3:
        color_features: dict[str, dict[str, float]] = {}
        for region_name, region_indices in SKIN_REGIONS.items():
            valid_idx = [i for i in region_indices if i < len(pts)]
            if not valid_idx:
                continue
            region_pts = pts[valid_idx]
            xs = (region_pts[:, 0] * w).astype(int).clip(0, w - 1)
            ys = (region_pts[:, 1] * h).astype(int).clip(0, h - 1)
            x_min, x_max = max(xs.min(), 0), min(xs.max(), w - 1)
            y_min, y_max = max(ys.min(), 0), min(ys.max(), h - 1)
            if x_max - x_min < 2 or y_max - y_min < 2:
                continue
            patch = image[y_min:y_max, x_min:x_max]
            color_features[region_name] = {
                "mean_r": round(float(patch[:, :, 0].mean()), 2),
                "mean_g": round(float(patch[:, :, 1].mean()), 2),
                "mean_b": round(float(patch[:, :, 2].mean()), 2),
                "std": round(float(patch.std()), 2),
            }
        feats["skin_color"] = color_features

        # Dark circle intensity (periorbital vs cheek comparison)
        peri_left = color_features.get("periorbital_left", {})
        peri_right = color_features.get("periorbital_right", {})
        cheek_left = color_features.get("left_cheek", {})
        cheek_right = color_features.get("right_cheek", {})
        if peri_left and cheek_left:
            peri_brightness = (peri_left.get("mean_r", 128) + peri_left.get("mean_g", 128) + peri_left.get("mean_b", 128)) / 3
            cheek_brightness = (cheek_left.get("mean_r", 128) + cheek_left.get("mean_g", 128) + cheek_left.get("mean_b", 128)) / 3
            feats["dark_circle_intensity_left"] = round(max(0, cheek_brightness - peri_brightness) / max(cheek_brightness, 1), 4)
        if peri_right and cheek_right:
            peri_brightness = (peri_right.get("mean_r", 128) + peri_right.get("mean_g", 128) + peri_right.get("mean_b", 128)) / 3
            cheek_brightness = (cheek_right.get("mean_r", 128) + cheek_right.get("mean_g", 128) + cheek_right.get("mean_b", 128)) / 3
            feats["dark_circle_intensity_right"] = round(max(0, cheek_brightness - peri_brightness) / max(cheek_brightness, 1), 4)

    # Color consistency check (variance of mean skin color across regions)
    if "skin_color" in feats and len(feats["skin_color"]) >= 3:
        brightnesses = []
        for region_data in feats["skin_color"].values():
            brightnesses.append(
                (region_data.get("mean_r", 0) + region_data.get("mean_g", 0) + region_data.get("mean_b", 0)) / 3
            )
        feats["skin_color_consistency"] = round(1.0 - min(np.std(brightnesses) / 40.0, 1.0), 4)

    # High-frequency texture energy (skin micro-detail)
    face_gray = gray
    gx = np.abs(np.diff(face_gray, axis=1))
    gy = np.abs(np.diff(face_gray, axis=0))
    feats["high_freq_texture_energy"] = round(float((gx.mean() + gy.mean()) / 50.0), 4)

    return feats


# ─────────────────────────────────────────────────────────────────────────
# Main composite extraction
# ─────────────────────────────────────────────────────────────────────────

def extract_geometry_metrics(landmarks: list[list[float]]) -> dict[str, Any]:
    """Extract the full suite of granular geometric features from landmarks."""
    pts = _array(landmarks)
    if pts.size == 0:
        return {"face_present": 0.0}

    metrics: dict[str, Any] = {"face_present": 1.0}

    try:
        metrics.update(_extract_eye_features(pts))
    except (IndexError, ValueError):
        pass

    try:
        metrics.update(_extract_brow_features(pts))
    except (IndexError, ValueError):
        pass

    try:
        metrics.update(_extract_nose_features(pts))
    except (IndexError, ValueError):
        pass

    try:
        metrics.update(_extract_lip_features(pts))
    except (IndexError, ValueError):
        pass

    try:
        metrics.update(_extract_jawline_features(pts))
    except (IndexError, ValueError):
        pass

    try:
        metrics.update(_extract_pose(pts))
    except (IndexError, ValueError):
        pass

    return metrics


def extract_full_features(
    landmarks: list[list[float]],
    image: np.ndarray | None = None,
) -> dict[str, Any]:
    """Extract both geometric and image-based features."""
    metrics = extract_geometry_metrics(landmarks)
    pts = _array(landmarks)
    if image is not None and pts.size > 0:
        skin = extract_skin_features(image, pts)
        metrics["skin"] = skin
    return metrics


# ─────────────────────────────────────────────────────────────────────────
# Embedding computation
# ─────────────────────────────────────────────────────────────────────────

def compute_embedding(landmarks: list[list[float]], dimensions: int = 128) -> list[float]:
    """Generate a deterministic 128-d face embedding from landmark geometry."""
    pts = _array(landmarks)
    if pts.size == 0:
        return [0.0] * dimensions

    # Use key landmark subset for embedding
    valid_indices = [i for i in KEY_INDICES if i < len(pts)]
    if not valid_indices:
        return [0.0] * dimensions

    subset = pts[valid_indices]
    center = subset.mean(axis=0, keepdims=True)
    ref_dist = np.linalg.norm(subset[1] - subset[min(19, len(subset) - 1)]) or 1.0
    normalised = ((subset - center) / ref_dist).reshape(-1)

    # Deterministic random projection (seeded)
    rng = np.random.default_rng(42)
    projection = rng.normal(0, 0.25, size=(normalised.shape[0], dimensions))
    embedding = normalised @ projection
    norm = np.linalg.norm(embedding) or 1.0
    embedding = embedding / norm
    return embedding.astype(float).round(6).tolist()


# ─────────────────────────────────────────────────────────────────────────
# Similarity helpers
# ─────────────────────────────────────────────────────────────────────────

def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    a = np.array(list(left), dtype=np.float32)
    b = np.array(list(right), dtype=np.float32)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
    return float(np.dot(a, b) / denom)


# ─────────────────────────────────────────────────────────────────────────
# Template building & comparison
# ─────────────────────────────────────────────────────────────────────────

FEATURE_COMPARISON_KEYS = [
    "ear_left", "ear_right", "ear_average", "eye_symmetry_score",
    "inter_pupillary_distance", "left_eye_width", "right_eye_width",
    "left_brow_eye_dist", "right_brow_eye_dist", "inter_brow_distance",
    "brow_symmetry_score",
    "nose_length", "alar_base_width", "nasolabial_angle", "nose_asymmetry",
    "mouth_width", "mar", "smile_score", "upper_lip_height", "lower_lip_height",
    "lip_volume_ratio", "cupid_bow_depth", "lip_symmetry_score",
    "face_whr", "facial_third_upper", "facial_third_middle", "facial_third_lower",
    "facial_asymmetry_index", "face_convexity_angle",
    "face_width", "face_height",
]

FEATURE_WEIGHTS = {
    "ear_left": 1.2, "ear_right": 1.2, "eye_symmetry_score": 0.8,
    "inter_pupillary_distance": 1.5,
    "nose_length": 1.3, "alar_base_width": 1.3, "nasolabial_angle": 1.0,
    "mouth_width": 1.0, "mar": 1.0, "lip_volume_ratio": 0.9,
    "face_whr": 1.4, "facial_asymmetry_index": 1.2,
    "face_convexity_angle": 0.8,
}


def build_template(captures: list[dict], quality_score: float) -> dict:
    """Build a comprehensive biometric template from multi-angle captures."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for capture in captures:
        grouped[capture["step"]].append(capture)

    steps: dict[str, dict] = {}
    for step, samples in grouped.items():
        embeddings = [compute_embedding(s["landmarks"]) for s in samples]
        metrics_list = [extract_geometry_metrics(s["landmarks"]) for s in samples]
        all_keys = {k for m in metrics_list for k in m.keys()}
        averaged_metrics = {}
        for key in all_keys:
            values = [m.get(key) for m in metrics_list if isinstance(m.get(key), (int, float))]
            if values:
                averaged_metrics[key] = round(float(np.mean(values)), 5)
        steps[step] = {
            "embedding": np.mean(np.array(embeddings, dtype=np.float32), axis=0).round(6).tolist(),
            "metrics": averaged_metrics,
            "samples": len(samples),
        }

    enrollment_completeness = min(len(grouped) / 10, 1.0)
    security_score = min(100.0, quality_score * 0.7 + enrollment_completeness * 30)

    return {
        "version": 2,
        "quality_score": quality_score,
        "security_score": round(security_score, 2),
        "steps": steps,
    }


def compare_template(
    template: dict,
    landmarks: list[list[float]],
    client_metrics: dict | None = None,
) -> tuple[float, float, list[str]]:
    """Compare a live observation against a stored template.

    Returns (recognition_score, feature_score, anomalies).
    """
    embedding = compute_embedding(landmarks)
    geometry = extract_geometry_metrics(landmarks)
    if client_metrics:
        geometry.update({k: float(v) for k, v in client_metrics.items() if isinstance(v, (float, int))})

    recognition_scores: list[float] = []
    feature_scores: list[float] = []
    anomalies: list[str] = []

    for step_name, step_data in template.get("steps", {}).items():
        recognition_scores.append(cosine_similarity(embedding, step_data["embedding"]))

        ref = step_data["metrics"]
        weighted_sum = 0.0
        weight_total = 0.0
        mismatches: list[str] = []

        for key in FEATURE_COMPARISON_KEYS:
            current = geometry.get(key)
            reference = ref.get(key)
            if current is None or reference is None or reference == 0:
                continue
            delta = abs(current - reference) / max(abs(reference), 1e-6)
            score = max(0.0, 1.0 - delta)
            w = FEATURE_WEIGHTS.get(key, 1.0)
            weighted_sum += score * w
            weight_total += w
            if score < 0.5:
                mismatches.append(key)

        if weight_total > 0:
            feature_scores.append(weighted_sum / weight_total)

        if len(mismatches) >= 3:
            anomalies.append(f"Multiple feature mismatches in {step_name}: {', '.join(mismatches[:5])}")

    recognition_score = max(recognition_scores or [0.0])
    feature_score = max(feature_scores or [0.0])

    if recognition_score < 0.82:
        anomalies.append("Face geometry diverges from enrolled template")
    if feature_score < 0.75:
        anomalies.append("Granular feature verification is weak")

    return recognition_score, feature_score, anomalies
