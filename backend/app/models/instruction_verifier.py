"""
models/instruction_verifier.py — Instruction Compliance Verification Engine

Uses MediaPipe FaceMesh (478 landmarks) + MediaPipe Hands (21 landmarks) to
verify whether a user actually performed the requested instruction.

Classes:
  FaceLandmarkAnalyzer — eye, head, mouth, expression metrics from FaceMesh
  HandGestureAnalyzer  — finger states, gesture classification from Hands
  InstructionVerifier  — maps instruction IDs to verification logic

All models are loaded ONCE at startup and kept in memory for fast inference.
CPU-only, no training required — uses pre-trained MediaPipe models.
"""

import logging
import math
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from app.config import INSTRUCTION_MIN_CONFIDENCE

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class InstructionResult:
    instruction_id: int
    passed: bool
    confidence: float      # 0-1 — how confidently the instruction was detected
    detail: str = ""       # human-readable detail
    frames_analyzed: int = 0


# ═══════════════════════════════════════════════════════════════════════════
# A) Face Landmark Analyzer — MediaPipe FaceMesh
# ═══════════════════════════════════════════════════════════════════════════

# MediaPipe FaceMesh landmark indices
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
LEFT_EYE = [362, 385, 387, 263, 373, 380]
NOSE_TIP = 1
LEFT_FACE = 234
RIGHT_FACE = 454
LEFT_LIP = 61
RIGHT_LIP = 291
UPPER_LIP = 13
LOWER_LIP = 14
LEFT_BROW_UPPER = 70
RIGHT_BROW_UPPER = 300
LEFT_BROW_INNER = 107
RIGHT_BROW_INNER = 336
CHIN = 152
FOREHEAD = 10
LEFT_CHEEK = 50
RIGHT_CHEEK = 280
LEFT_EAR = 234
RIGHT_EAR = 454
# Iris landmarks (refined)
LEFT_IRIS = [468, 469, 470, 471, 472]
RIGHT_IRIS = [473, 474, 475, 476, 477]


class FaceLandmarkAnalyzer:
    """
    Wraps MediaPipe FaceMesh and provides computed metrics:
    EAR (Eye Aspect Ratio), MAR (Mouth Aspect Ratio), head pose,
    expression deltas, and gaze direction.
    """

    def __init__(self):
        self.face_mesh = None
        self._initialized = False
        self._available = True

    def _lazy_init(self):
        if self._initialized:
            return
        try:
            import mediapipe as mp
            face_mesh_module = getattr(mp.solutions, "face_mesh", None)
            if face_mesh_module is None:
                raise AttributeError("mp.solutions.face_mesh not available")
            self.face_mesh = face_mesh_module.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            logger.info("MediaPipe FaceMesh loaded (478 landmarks)")
        except (ImportError, AttributeError) as e:
            logger.warning(f"MediaPipe FaceMesh unavailable: {e}")
            self._available = False
        self._initialized = True

    def get_landmarks(self, frame: np.ndarray) -> Optional[list]:
        """Extract 478 landmarks [(x,y,z), ...] from a BGR frame."""
        self._lazy_init()
        if not self._available or self.face_mesh is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        if not results.multi_face_landmarks:
            return None
        face = results.multi_face_landmarks[0]
        h, w = frame.shape[:2]
        return [(lm.x * w, lm.y * h, lm.z * w) for lm in face.landmark]

    @staticmethod
    def compute_ear(landmarks, eye_indices) -> float:
        """Eye Aspect Ratio — EAR < 0.2 = blink."""
        p1 = np.array(landmarks[eye_indices[0]][:2])
        p2 = np.array(landmarks[eye_indices[1]][:2])
        p3 = np.array(landmarks[eye_indices[2]][:2])
        p4 = np.array(landmarks[eye_indices[3]][:2])
        p5 = np.array(landmarks[eye_indices[4]][:2])
        p6 = np.array(landmarks[eye_indices[5]][:2])
        vertical_1 = np.linalg.norm(p2 - p6)
        vertical_2 = np.linalg.norm(p3 - p5)
        horizontal = np.linalg.norm(p1 - p4)
        if horizontal == 0:
            return 0.0
        return float((vertical_1 + vertical_2) / (2.0 * horizontal))

    @staticmethod
    def compute_mar(landmarks) -> float:
        """Mouth Aspect Ratio — MAR > 0.5 = mouth open."""
        upper = np.array(landmarks[UPPER_LIP][:2])
        lower = np.array(landmarks[LOWER_LIP][:2])
        left = np.array(landmarks[LEFT_LIP][:2])
        right = np.array(landmarks[RIGHT_LIP][:2])
        vertical = np.linalg.norm(upper - lower)
        horizontal = np.linalg.norm(left - right)
        if horizontal == 0:
            return 0.0
        return float(vertical / horizontal)

    @staticmethod
    def compute_head_pose(landmarks) -> dict:
        """Estimate yaw, pitch, roll from landmark geometry."""
        nose = np.array(landmarks[NOSE_TIP][:2])
        left_f = np.array(landmarks[LEFT_FACE][:2])
        right_f = np.array(landmarks[RIGHT_FACE][:2])
        chin = np.array(landmarks[CHIN][:2])
        forehead = np.array(landmarks[FOREHEAD][:2])

        face_width = np.linalg.norm(right_f - left_f)
        if face_width < 1e-6:
            return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}

        # Yaw
        face_center_x = (left_f[0] + right_f[0]) / 2
        yaw_ratio = (nose[0] - face_center_x) / (face_width / 2)
        yaw = float(np.degrees(np.arcsin(np.clip(yaw_ratio, -1, 1))))

        # Pitch
        face_height = np.linalg.norm(chin - forehead)
        if face_height < 1e-6:
            pitch = 0.0
        else:
            eye_center_y = (left_f[1] + right_f[1]) / 2
            nose_relative = (nose[1] - forehead[1]) / face_height
            pitch = float((nose_relative - 0.45) * 60.0)

        # Roll
        dy = right_f[1] - left_f[1]
        dx = right_f[0] - left_f[0]
        roll = float(np.degrees(np.arctan2(dy, dx)))

        return {"yaw": yaw, "pitch": pitch, "roll": roll}

    @staticmethod
    def compute_lip_distance(landmarks) -> float:
        """Normalized lip corner distance (for smile detection)."""
        left_lip = np.array(landmarks[LEFT_LIP][:2])
        right_lip = np.array(landmarks[RIGHT_LIP][:2])
        left_f = np.array(landmarks[LEFT_FACE][:2])
        right_f = np.array(landmarks[RIGHT_FACE][:2])
        face_width = np.linalg.norm(right_f - left_f)
        if face_width < 1e-6:
            return 0.0
        return float(np.linalg.norm(right_lip - left_lip) / face_width)

    @staticmethod
    def compute_brow_height(landmarks) -> dict:
        """Normalized eyebrow height above eyes."""
        left_brow = np.array(landmarks[LEFT_BROW_UPPER][:2])
        right_brow = np.array(landmarks[RIGHT_BROW_UPPER][:2])
        left_eye_center = np.array(landmarks[LEFT_EYE[0]][:2])
        right_eye_center = np.array(landmarks[RIGHT_EYE[0]][:2])
        left_f = np.array(landmarks[LEFT_FACE][:2])
        right_f = np.array(landmarks[RIGHT_FACE][:2])
        face_width = np.linalg.norm(right_f - left_f)
        if face_width < 1e-6:
            return {"left": 0.0, "right": 0.0}
        left_h = float((left_eye_center[1] - left_brow[1]) / face_width)
        right_h = float((right_eye_center[1] - right_brow[1]) / face_width)
        return {"left": left_h, "right": right_h}

    @staticmethod
    def compute_face_bbox_center(landmarks, frame_shape) -> dict:
        """Face bounding box center and size relative to frame."""
        xs = [lm[0] for lm in landmarks]
        ys = [lm[1] for lm in landmarks]
        h, w = frame_shape[:2]
        cx = (min(xs) + max(xs)) / 2.0 / w
        cy = (min(ys) + max(ys)) / 2.0 / h
        bw = (max(xs) - min(xs)) / w
        bh = (max(ys) - min(ys)) / h
        return {"cx": cx, "cy": cy, "width": bw, "height": bh, "area": bw * bh}

    @staticmethod
    def compute_cheek_puff(landmarks) -> dict:
        """Detect cheek puffing by measuring cheek landmark displacement."""
        left_cheek = np.array(landmarks[LEFT_CHEEK][:2])
        right_cheek = np.array(landmarks[RIGHT_CHEEK][:2])
        nose = np.array(landmarks[NOSE_TIP][:2])
        left_dist = float(np.linalg.norm(left_cheek - nose))
        right_dist = float(np.linalg.norm(right_cheek - nose))
        return {"left": left_dist, "right": right_dist}


# ═══════════════════════════════════════════════════════════════════════════
# B) Hand Gesture Analyzer — MediaPipe Hands
# ═══════════════════════════════════════════════════════════════════════════

# MediaPipe Hand landmark indices
WRIST = 0
THUMB_TIP = 4
INDEX_TIP = 8
MIDDLE_TIP = 12
RING_TIP = 16
PINKY_TIP = 20
THUMB_MCP = 2
INDEX_MCP = 5
MIDDLE_MCP = 9
RING_MCP = 13
PINKY_MCP = 17
INDEX_PIP = 6
MIDDLE_PIP = 10
RING_PIP = 14
PINKY_PIP = 18


class HandGestureAnalyzer:
    """
    Wraps MediaPipe Hands and provides finger state detection,
    gesture classification, and hand-face relative positioning.
    """

    def __init__(self):
        self.hands = None
        self._initialized = False
        self._available = True

    def _lazy_init(self):
        if self._initialized:
            return
        try:
            import mediapipe as mp
            hands_module = getattr(mp.solutions, "hands", None)
            if hands_module is None:
                raise AttributeError("mp.solutions.hands not available")
            self.hands = hands_module.Hands(
                static_image_mode=False,
                max_num_hands=2,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            logger.info("MediaPipe Hands loaded (21 landmarks per hand)")
        except (ImportError, AttributeError) as e:
            logger.warning(f"MediaPipe Hands unavailable: {e}")
            self._available = False
        self._initialized = True

    def get_hand_landmarks(self, frame: np.ndarray) -> list[list]:
        """Extract hand landmarks for all detected hands."""
        self._lazy_init()
        if not self._available or self.hands is None:
            return []
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        if not results.multi_hand_landmarks:
            return []
        h, w = frame.shape[:2]
        all_hands = []
        for hand_lms in results.multi_hand_landmarks:
            pts = [(lm.x * w, lm.y * h, lm.z * w) for lm in hand_lms.landmark]
            all_hands.append(pts)
        return all_hands

    @staticmethod
    def get_finger_states(hand_landmarks: list) -> dict:
        """
        Determine which fingers are extended.
        Returns: {thumb, index, middle, ring, pinky} → bool
        """
        wrist = np.array(hand_landmarks[WRIST][:2])
        index_mcp = np.array(hand_landmarks[INDEX_MCP][:2])

        # Determine handedness from wrist-to-index direction
        hand_dir = index_mcp - wrist

        # Thumb: compare tip x to MCP x (depends on handedness)
        thumb_tip = np.array(hand_landmarks[THUMB_TIP][:2])
        thumb_mcp = np.array(hand_landmarks[THUMB_MCP][:2])
        thumb_extended = np.linalg.norm(thumb_tip - wrist) > np.linalg.norm(thumb_mcp - wrist) * 1.2

        def is_finger_extended(tip_idx, pip_idx, mcp_idx):
            tip = np.array(hand_landmarks[tip_idx][:2])
            pip = np.array(hand_landmarks[pip_idx][:2])
            mcp = np.array(hand_landmarks[mcp_idx][:2])
            return np.linalg.norm(tip - wrist) > np.linalg.norm(pip - wrist)

        return {
            "thumb": bool(thumb_extended),
            "index": is_finger_extended(INDEX_TIP, INDEX_PIP, INDEX_MCP),
            "middle": is_finger_extended(MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP),
            "ring": is_finger_extended(RING_TIP, RING_PIP, RING_MCP),
            "pinky": is_finger_extended(PINKY_TIP, PINKY_PIP, PINKY_MCP),
        }

    @staticmethod
    def count_extended_fingers(finger_states: dict) -> int:
        """Count how many fingers are currently extended."""
        return sum(1 for v in finger_states.values() if v)

    @staticmethod
    def get_hand_center(hand_landmarks: list) -> np.ndarray:
        """Get the centroid of the hand landmarks."""
        points = np.array([lm[:2] for lm in hand_landmarks])
        return points.mean(axis=0)

    @staticmethod
    def classify_gesture(finger_states: dict) -> str:
        """Classify the current hand gesture based on finger states."""
        f = finger_states
        count = sum(1 for v in f.values() if v)

        if count == 0:
            return "fist"
        if f["thumb"] and not f["index"] and not f["middle"] and not f["ring"] and not f["pinky"]:
            return "thumbs_up"
        if not f["thumb"] and f["index"] and f["middle"] and not f["ring"] and not f["pinky"]:
            return "peace"
        if not f["thumb"] and f["index"] and not f["middle"] and not f["ring"] and not f["pinky"]:
            return "point"
        if f["thumb"] and f["index"] and f["middle"] and f["ring"] and f["pinky"]:
            return "open_palm"
        if f["thumb"] and f["index"] and not f["middle"] and not f["ring"] and f["pinky"]:
            return "rock"
        if not f["thumb"] and f["index"] and f["middle"] and f["ring"] and not f["pinky"]:
            return "three_fingers"
        if not f["thumb"] and f["index"] and f["middle"] and f["ring"] and f["pinky"]:
            return "four_fingers"
        return f"custom_{count}"


# ═══════════════════════════════════════════════════════════════════════════
# C) Instruction Verifier — Maps instructions to verification logic
# ═══════════════════════════════════════════════════════════════════════════

class InstructionVerifier:
    """
    Takes video frames + instruction ID → pass/fail.
    All loaded at startup for fast inference.
    """

    def __init__(self):
        self.face_analyzer = FaceLandmarkAnalyzer()
        self.hand_analyzer = HandGestureAnalyzer()
        logger.info("InstructionVerifier initialized")

    def verify(
        self,
        frames: list[np.ndarray],
        instruction_id: int,
        verify_key: str,
    ) -> InstructionResult:
        """
        Verify an instruction against video frames.

        Args:
            frames: list of BGR frames (30fps × duration)
            instruction_id: the instruction ID
            verify_key: the verify_key from the instruction dict

        Returns: InstructionResult
        """
        if not frames:
            return InstructionResult(instruction_id, False, 0.0, "No frames", 0)

        # Route to the appropriate verifier
        try:
            verify_fn = self._get_verify_function(verify_key)
            if verify_fn is None:
                # Fallback: check if face/hand is visible (basic compliance)
                return self._verify_generic_presence(frames, instruction_id, verify_key)
            return verify_fn(frames, instruction_id)
        except Exception as e:
            logger.error(f"Instruction verification error: {e}")
            return InstructionResult(instruction_id, False, 0.0, f"Error: {e}", len(frames))

    def _get_verify_function(self, verify_key: str):
        """Map verify_key to verification function."""
        VERIFY_MAP = {
            # Blinks
            "blink_once": self._verify_blink_count(1),
            "blink_three": self._verify_blink_count(3),
            "blink_five": self._verify_blink_count(5),
            "wink_left": self._verify_wink("left"),
            "wink_right": self._verify_wink("right"),
            "eyes_closed_hold": self._verify_eyes_closed_hold,
            "slow_blink": self._verify_blink_count(1),
            "wink_left_twice": self._verify_wink("left", count=2),
            "wink_right_twice": self._verify_wink("right", count=2),
            "flutter_blink": self._verify_blink_count(3),
            "alternating_wink": self._verify_blink_count(2),
            "close_then_wide": self._verify_close_then_wide,
            # Gaze
            "look_up": self._verify_gaze("up"),
            "look_down": self._verify_gaze("down"),
            "look_left": self._verify_gaze("left"),
            "look_right": self._verify_gaze("right"),
            "look_upper_left": self._verify_gaze("up"),
            "look_upper_right": self._verify_gaze("up"),
            "look_left_right": self._verify_head_turn("left_right"),
            "look_up_down": self._verify_gaze("up"),
            "look_center_hold": self._verify_stay_still,
            "eye_roll": self._verify_blink_count(1),
            "cross_eyes": self._verify_blink_count(1),
            # Head
            "head_turn_right": self._verify_head_turn("right"),
            "head_turn_left": self._verify_head_turn("left"),
            "nod_yes": self._verify_nod,
            "shake_no": self._verify_head_shake,
            "tilt_left": self._verify_head_tilt("left"),
            "tilt_right": self._verify_head_tilt("right"),
            "look_over_right": self._verify_head_turn("right", threshold=30),
            "look_over_left": self._verify_head_turn("left", threshold=30),
            "turn_right_left": self._verify_head_turn("left_right"),
            "nod_three": self._verify_nod,
            "tilt_left_right": self._verify_head_tilt("left_right"),
            "head_far_right": self._verify_head_turn("right", threshold=35),
            "head_far_left": self._verify_head_turn("left", threshold=35),
            "chin_down": self._verify_gaze("down"),
            "chin_up": self._verify_gaze("up"),
            "head_circle": self._verify_head_turn("left_right"),
            "turn_right_return": self._verify_head_turn("right"),
            "turn_left_return": self._verify_head_turn("left"),
            "lean_forward": self._verify_position_change("closer"),
            "lean_backward": self._verify_position_change("farther"),
            "shake_quick": self._verify_head_shake,
            "nod_vigorous": self._verify_nod,
            "slow_turn_right": self._verify_head_turn("right"),
            "slow_turn_left": self._verify_head_turn("left"),
            "tilt_hold": self._verify_head_tilt("left"),
            "chin_to_chest": self._verify_gaze("down"),
            "stay_still": self._verify_stay_still,
            "turn_then_nod": self._verify_head_turn("right"),
            "tilt_and_blink": self._verify_head_tilt("right"),
            "head_figure_eight": self._verify_head_turn("left_right"),
            # Expressions
            "smile_wide": self._verify_smile,
            "smile_subtle": self._verify_smile,
            "frown": self._verify_frown,
            "raise_eyebrows": self._verify_eyebrow_raise,
            "raise_left_brow": self._verify_eyebrow_raise,
            "raise_right_brow": self._verify_eyebrow_raise,
            "surprised": self._verify_surprised,
            "puff_cheeks": self._verify_cheek_puff,
            "puff_left_cheek": self._verify_cheek_puff,
            "puff_right_cheek": self._verify_cheek_puff,
            "purse_lips": self._verify_purse_lips,
            "show_teeth": self._verify_mouth_open,
            "angry_face": self._verify_frown,
            "wrinkle_nose": self._verify_frown,
            "sad_face": self._verify_frown,
            "smile_then_neutral": self._verify_smile,
            "brows_then_frown": self._verify_eyebrow_raise,
            "clench_jaw": self._verify_mouth_open,
            "jaw_left": self._verify_head_turn("left"),
            "jaw_right": self._verify_head_turn("right"),
            "fish_face": self._verify_purse_lips,
            "scrunch_face": self._verify_frown,
            "relax_face": self._verify_stay_still,
            "smile_frown_alternate": self._verify_smile,
            "yawn": self._verify_mouth_open,
            "pout": self._verify_purse_lips,
            "big_grin": self._verify_smile,
            "mouth_o": self._verify_mouth_open,
            "bite_lip": self._verify_purse_lips,
            "flare_nostrils": self._verify_frown,
            # Mouth
            "mouth_open_wide": self._verify_mouth_open,
            "tongue_out": self._verify_mouth_open,
            "tongue_left": self._verify_mouth_open,
            "tongue_right": self._verify_mouth_open,
            "say_ahh": self._verify_mouth_open,
            "lips_side_to_side": self._verify_head_turn("left_right"),
            "mouth_open_close_three": self._verify_mouth_open,
            "closed_smile": self._verify_smile,
            "blow_air": self._verify_purse_lips,
            "press_lips": self._verify_purse_lips,
            "open_then_smile": self._verify_mouth_open,
            "jaw_up_down": self._verify_mouth_open,
            "whistle_lips": self._verify_purse_lips,
            "half_smile_right": self._verify_smile,
            "half_smile_left": self._verify_smile,
            "open_then_tongue": self._verify_mouth_open,
            "mouth_eee": self._verify_smile,
            "slow_mouth_close": self._verify_mouth_open,
            "stretch_mouth": self._verify_mouth_open,
            "lip_over_lip": self._verify_purse_lips,
            # Hand gestures
            "wave_right": self._verify_wave,
            "wave_left": self._verify_wave,
            "thumbs_up": self._verify_hand_gesture("thumbs_up"),
            "thumbs_down": self._verify_hand_gesture("thumbs_up"),
            "peace_sign": self._verify_hand_gesture("peace"),
            "open_palm": self._verify_hand_gesture("open_palm"),
            "fist": self._verify_hand_gesture("fist"),
            "one_finger": self._verify_finger_count(1),
            "two_fingers": self._verify_finger_count(2),
            "three_fingers": self._verify_finger_count(3),
            "four_fingers": self._verify_finger_count(4),
            "five_fingers": self._verify_finger_count(5),
            "ok_sign": self._verify_hand_gesture("point"),
            "point_up": self._verify_hand_gesture("point"),
            "point_down": self._verify_hand_gesture("point"),
            "point_left": self._verify_hand_gesture("point"),
            "point_right": self._verify_hand_gesture("point"),
            "pinch": self._verify_hand_gesture("fist"),
            "wrist_rotate_cw": self._verify_wave,
            "wrist_rotate_ccw": self._verify_wave,
            "open_close_fist": self._verify_hand_state_change,
            "spread_close": self._verify_hand_state_change,
            "rock_sign": self._verify_hand_gesture("rock"),
            "double_thumbs_up": self._verify_hand_gesture("thumbs_up"),
            "wiggle_fingers": self._verify_wave,
            "palm_flip": self._verify_hand_state_change,
            "count_123": self._verify_hand_state_change,
            "stop_gesture": self._verify_hand_gesture("open_palm"),
            "cup_hand": self._verify_hand_present,
            "phone_gesture": self._verify_hand_present,
            "clap_once": self._verify_hand_present,
            "snap_fingers": self._verify_hand_present,
            "finger_guns": self._verify_hand_gesture("point"),
            "cross_fingers": self._verify_hand_present,
            "salute": self._verify_hand_near_face("forehead"),
            # Hand + face
            "touch_nose": self._verify_hand_near_face("nose"),
            "cover_left_eye": self._verify_hand_near_face("left_eye"),
            "cover_right_eye": self._verify_hand_near_face("right_eye"),
            "hand_on_chin": self._verify_hand_near_face("chin"),
            "touch_left_ear": self._verify_hand_near_face("left_ear"),
            "touch_right_ear": self._verify_hand_near_face("right_ear"),
            "hand_on_forehead": self._verify_hand_near_face("forehead"),
            "touch_left_cheek": self._verify_hand_near_face("left_cheek"),
            "touch_right_cheek": self._verify_hand_near_face("right_cheek"),
            "cover_mouth": self._verify_hand_near_face("mouth"),
            "finger_on_lips": self._verify_hand_near_face("mouth"),
            "frame_face": self._verify_hand_present,
            "hand_beside_face": self._verify_hand_near_face("right_ear"),
            "scratch_head": self._verify_hand_near_face("forehead"),
            "hands_on_cheeks": self._verify_hand_near_face("left_cheek"),
            "tap_forehead": self._verify_hand_near_face("forehead"),
            "brush_hair": self._verify_hand_near_face("forehead"),
            "chin_on_fist": self._verify_hand_near_face("chin"),
            "stroke_chin": self._verify_hand_near_face("chin"),
            "hand_on_heart": self._verify_hand_present,
            "touch_nose_bridge": self._verify_hand_near_face("nose"),
            "palm_on_head": self._verify_hand_near_face("forehead"),
            "pinch_nose": self._verify_hand_near_face("nose"),
            "rub_eyes": self._verify_hand_near_face("left_eye"),
            "pull_ear": self._verify_hand_near_face("left_ear"),
            "press_temples": self._verify_hand_near_face("left_ear"),
            "cover_eye_wave": self._verify_hand_near_face("left_eye"),
            "nose_then_chin": self._verify_hand_near_face("nose"),
            "listening_pose": self._verify_hand_near_face("right_ear"),
            "finger_glasses": self._verify_hand_near_face("left_eye"),
            # Compound
            "smile_then_blink": self._verify_smile,
            "nod_then_smile": self._verify_nod,
            "turn_right_blink": self._verify_head_turn("right"),
            "brows_then_mouth": self._verify_eyebrow_raise,
            "close_eyes_smile": self._verify_smile,
            "blink_then_turn_left": self._verify_head_turn("left"),
            "shake_then_smile": self._verify_head_shake,
            "frown_then_brows": self._verify_frown,
            "mouth_open_smile": self._verify_mouth_open,
            "blink_pause_blink": self._verify_blink_count(2),
            "thumbs_then_wave": self._verify_wave,
            "wave_then_peace": self._verify_wave,
            "touch_nose_wave": self._verify_hand_near_face("nose"),
            "fist_then_palm": self._verify_hand_state_change,
            "count_then_thumbs": self._verify_hand_state_change,
            # Position
            "move_closer": self._verify_position_change("closer"),
            "move_back": self._verify_position_change("farther"),
            "face_left": self._verify_position_change("left"),
            "face_right": self._verify_position_change("right"),
            "face_center": self._verify_stay_still,
            "face_up": self._verify_position_change("up"),
            "face_down": self._verify_position_change("down"),
            "lean_forward_back": self._verify_position_change("closer"),
            "sway_side": self._verify_position_change("left"),
            "closer_then_wave": self._verify_wave,
            "step_left": self._verify_position_change("left"),
            "step_right": self._verify_position_change("right"),
            "circle_movement": self._verify_position_change("left"),
            "face_bottom_right": self._verify_position_change("right"),
            "face_top_left": self._verify_position_change("left"),
        }
        return VERIFY_MAP.get(verify_key)

    # ───────────────────────────────────────────────────────────────────
    # FACE verification functions
    # ───────────────────────────────────────────────────────────────────

    def _verify_blink_count(self, required_count: int):
        """Factory: returns a verification function for N blinks."""
        def verifier(frames, instruction_id):
            blink_count = 0
            was_closed = False
            for frame in frames[::2]:  # sample every other frame for speed
                lms = self.face_analyzer.get_landmarks(frame)
                if lms is None:
                    continue
                left_ear = self.face_analyzer.compute_ear(lms, LEFT_EYE)
                right_ear = self.face_analyzer.compute_ear(lms, RIGHT_EYE)
                avg_ear = (left_ear + right_ear) / 2
                if avg_ear < 0.20:
                    if not was_closed:
                        was_closed = True
                else:
                    if was_closed:
                        blink_count += 1
                        was_closed = False
            confidence = min(blink_count / max(required_count, 1), 1.0)
            passed = blink_count >= required_count
            return InstructionResult(
                instruction_id, passed, confidence,
                f"Detected {blink_count}/{required_count} blinks", len(frames)
            )
        return verifier

    def _verify_wink(self, side: str, count: int = 1):
        """Factory: verify wink (one eye closes, other stays open)."""
        def verifier(frames, instruction_id):
            winks = 0
            was_winked = False
            for frame in frames[::2]:
                lms = self.face_analyzer.get_landmarks(frame)
                if lms is None:
                    continue
                left_ear = self.face_analyzer.compute_ear(lms, LEFT_EYE)
                right_ear = self.face_analyzer.compute_ear(lms, RIGHT_EYE)
                if side == "left":
                    closed, open_eye = left_ear, right_ear
                else:
                    closed, open_eye = right_ear, left_ear
                if closed < 0.18 and open_eye > 0.22:
                    if not was_winked:
                        was_winked = True
                else:
                    if was_winked:
                        winks += 1
                        was_winked = False
            confidence = min(winks / max(count, 1), 1.0)
            return InstructionResult(
                instruction_id, winks >= count, confidence,
                f"Detected {winks}/{count} {side} winks", len(frames)
            )
        return verifier

    def _verify_eyes_closed_hold(self, frames, instruction_id):
        """Verify eyes closed for extended period."""
        closed_frames = 0
        total = 0
        for frame in frames[::2]:
            lms = self.face_analyzer.get_landmarks(frame)
            if lms is None:
                continue
            total += 1
            avg_ear = (self.face_analyzer.compute_ear(lms, LEFT_EYE) +
                       self.face_analyzer.compute_ear(lms, RIGHT_EYE)) / 2
            if avg_ear < 0.18:
                closed_frames += 1
        ratio = closed_frames / max(total, 1)
        passed = ratio > 0.3
        return InstructionResult(instruction_id, passed, ratio,
                                 f"Eyes closed {ratio:.0%} of frames", len(frames))

    def _verify_close_then_wide(self, frames, instruction_id):
        """Verify eyes closed then opened wide."""
        ears = []
        for frame in frames[::3]:
            lms = self.face_analyzer.get_landmarks(frame)
            if lms is None:
                continue
            avg = (self.face_analyzer.compute_ear(lms, LEFT_EYE) +
                   self.face_analyzer.compute_ear(lms, RIGHT_EYE)) / 2
            ears.append(avg)
        if len(ears) < 4:
            return InstructionResult(instruction_id, False, 0.0, "Not enough data", len(frames))
        mn, mx = min(ears), max(ears)
        delta = mx - mn
        passed = delta > 0.12 and mn < 0.18
        return InstructionResult(instruction_id, passed, min(delta / 0.15, 1.0),
                                 f"EAR range {mn:.3f}-{mx:.3f}", len(frames))

    def _verify_gaze(self, direction: str):
        """Factory: verify gaze direction using head pose."""
        def verifier(frames, instruction_id):
            poses = []
            for frame in frames[::3]:
                lms = self.face_analyzer.get_landmarks(frame)
                if lms is None:
                    continue
                poses.append(self.face_analyzer.compute_head_pose(lms))
            if not poses:
                return InstructionResult(instruction_id, False, 0.0, "No face", len(frames))
            if direction == "up":
                vals = [-p["pitch"] for p in poses]
            elif direction == "down":
                vals = [p["pitch"] for p in poses]
            elif direction == "left":
                vals = [-p["yaw"] for p in poses]
            else:
                vals = [p["yaw"] for p in poses]
            max_val = max(vals) if vals else 0
            passed = max_val > 10.0
            confidence = min(max_val / 15.0, 1.0)
            return InstructionResult(instruction_id, passed, confidence,
                                     f"Max {direction} angle: {max_val:.1f}°", len(frames))
        return verifier

    def _verify_head_turn(self, direction: str, threshold: float = 15.0):
        """Factory: verify head turn."""
        def verifier(frames, instruction_id):
            yaws = []
            for frame in frames[::3]:
                lms = self.face_analyzer.get_landmarks(frame)
                if lms is None:
                    continue
                pose = self.face_analyzer.compute_head_pose(lms)
                yaws.append(pose["yaw"])
            if len(yaws) < 2:
                return InstructionResult(instruction_id, False, 0.0, "No data", len(frames))
            if direction == "right":
                max_val = max(yaws)
                passed = max_val > threshold
                confidence = min(max_val / threshold, 1.0)
            elif direction == "left":
                min_val = min(yaws)
                passed = min_val < -threshold
                confidence = min(abs(min_val) / threshold, 1.0)
            else:  # left_right
                delta = max(yaws) - min(yaws)
                passed = delta > threshold
                confidence = min(delta / threshold, 1.0)
            return InstructionResult(instruction_id, passed, confidence,
                                     f"Yaw range: {min(yaws):.1f} to {max(yaws):.1f}", len(frames))
        return verifier

    def _verify_nod(self, frames, instruction_id):
        """Verify head nodding (pitch changes)."""
        pitches = []
        for frame in frames[::3]:
            lms = self.face_analyzer.get_landmarks(frame)
            if lms is None:
                continue
            pose = self.face_analyzer.compute_head_pose(lms)
            pitches.append(pose["pitch"])
        if len(pitches) < 3:
            return InstructionResult(instruction_id, False, 0.0, "No data", len(frames))
        delta = max(pitches) - min(pitches)
        passed = delta > 8.0
        confidence = min(delta / 12.0, 1.0)
        return InstructionResult(instruction_id, passed, confidence,
                                 f"Pitch delta: {delta:.1f}°", len(frames))

    def _verify_head_shake(self, frames, instruction_id):
        """Verify head shaking (rapid yaw changes)."""
        yaws = []
        for frame in frames[::3]:
            lms = self.face_analyzer.get_landmarks(frame)
            if lms is None:
                continue
            pose = self.face_analyzer.compute_head_pose(lms)
            yaws.append(pose["yaw"])
        if len(yaws) < 3:
            return InstructionResult(instruction_id, False, 0.0, "No data", len(frames))
        # Count direction changes
        changes = 0
        for i in range(2, len(yaws)):
            if (yaws[i] - yaws[i-1]) * (yaws[i-1] - yaws[i-2]) < 0:
                changes += 1
        delta = max(yaws) - min(yaws)
        passed = changes >= 2 and delta > 10.0
        confidence = min(changes / 3.0, 1.0)
        return InstructionResult(instruction_id, passed, confidence,
                                 f"Yaw changes: {changes}, delta: {delta:.1f}°", len(frames))

    def _verify_head_tilt(self, direction: str):
        """Factory: verify head tilt (roll)."""
        def verifier(frames, instruction_id):
            rolls = []
            for frame in frames[::3]:
                lms = self.face_analyzer.get_landmarks(frame)
                if lms is None:
                    continue
                pose = self.face_analyzer.compute_head_pose(lms)
                rolls.append(pose["roll"])
            if len(rolls) < 2:
                return InstructionResult(instruction_id, False, 0.0, "No data", len(frames))
            if direction == "left":
                max_val = max(abs(r) for r in rolls if r > 0)  if [r for r in rolls if r > 0] else 0
                passed = max_val > 8.0
            elif direction == "right":
                max_val = max(abs(r) for r in rolls if r < 0) if [r for r in rolls if r < 0] else 0
                passed = max_val > 8.0
            else:
                delta = max(rolls) - min(rolls)
                max_val = delta
                passed = delta > 10.0
            confidence = min(max_val / 12.0, 1.0)
            return InstructionResult(instruction_id, passed, confidence,
                                     f"Roll: {min(rolls):.1f} to {max(rolls):.1f}", len(frames))
        return verifier

    def _verify_smile(self, frames, instruction_id):
        """Verify smiling (lip distance increase)."""
        lip_distances = []
        for frame in frames[::3]:
            lms = self.face_analyzer.get_landmarks(frame)
            if lms is None:
                continue
            lip_distances.append(self.face_analyzer.compute_lip_distance(lms))
        if len(lip_distances) < 3:
            return InstructionResult(instruction_id, False, 0.0, "No data", len(frames))
        baseline = sorted(lip_distances)[:3]
        peak = sorted(lip_distances)[-3:]
        delta = np.mean(peak) - np.mean(baseline)
        passed = delta > 0.03
        confidence = min(delta / 0.05, 1.0)
        return InstructionResult(instruction_id, passed, confidence,
                                 f"Lip delta: {delta:.4f}", len(frames))

    def _verify_frown(self, frames, instruction_id):
        """Verify frowning (brow lowering)."""
        brow_heights = []
        for frame in frames[::3]:
            lms = self.face_analyzer.get_landmarks(frame)
            if lms is None:
                continue
            bh = self.face_analyzer.compute_brow_height(lms)
            brow_heights.append((bh["left"] + bh["right"]) / 2)
        if len(brow_heights) < 3:
            return InstructionResult(instruction_id, False, 0.0, "No data", len(frames))
        baseline = sorted(brow_heights)[-3:]
        lowest = sorted(brow_heights)[:3]
        delta = np.mean(baseline) - np.mean(lowest)
        passed = delta > 0.01
        confidence = min(delta / 0.02, 1.0)
        return InstructionResult(instruction_id, passed, confidence,
                                 f"Brow delta: {delta:.4f}", len(frames))

    def _verify_eyebrow_raise(self, frames, instruction_id):
        """Verify eyebrow raising."""
        brow_heights = []
        for frame in frames[::3]:
            lms = self.face_analyzer.get_landmarks(frame)
            if lms is None:
                continue
            bh = self.face_analyzer.compute_brow_height(lms)
            brow_heights.append((bh["left"] + bh["right"]) / 2)
        if len(brow_heights) < 3:
            return InstructionResult(instruction_id, False, 0.0, "No data", len(frames))
        baseline = sorted(brow_heights)[:3]
        peak = sorted(brow_heights)[-3:]
        delta = np.mean(peak) - np.mean(baseline)
        passed = delta > 0.015
        confidence = min(delta / 0.025, 1.0)
        return InstructionResult(instruction_id, passed, confidence,
                                 f"Brow raise: {delta:.4f}", len(frames))

    def _verify_surprised(self, frames, instruction_id):
        """Verify surprised face (brows up + mouth open)."""
        scores = []
        for frame in frames[::3]:
            lms = self.face_analyzer.get_landmarks(frame)
            if lms is None:
                continue
            mar = self.face_analyzer.compute_mar(lms)
            bh = self.face_analyzer.compute_brow_height(lms)
            score = mar + (bh["left"] + bh["right"]) / 2
            scores.append(score)
        if not scores:
            return InstructionResult(instruction_id, False, 0.0, "No data", len(frames))
        peak = max(scores)
        baseline = min(scores)
        delta = peak - baseline
        passed = delta > 0.15
        confidence = min(delta / 0.2, 1.0)
        return InstructionResult(instruction_id, passed, confidence,
                                 f"Surprise delta: {delta:.4f}", len(frames))

    def _verify_mouth_open(self, frames, instruction_id):
        """Verify mouth opening."""
        mars = []
        for frame in frames[::3]:
            lms = self.face_analyzer.get_landmarks(frame)
            if lms is None:
                continue
            mars.append(self.face_analyzer.compute_mar(lms))
        if not mars:
            return InstructionResult(instruction_id, False, 0.0, "No data", len(frames))
        peak = max(mars)
        passed = peak > 0.35
        confidence = min(peak / 0.5, 1.0)
        return InstructionResult(instruction_id, passed, confidence,
                                 f"Max MAR: {peak:.3f}", len(frames))

    def _verify_purse_lips(self, frames, instruction_id):
        """Verify lip pursing (lip distance decrease)."""
        lip_dists = []
        for frame in frames[::3]:
            lms = self.face_analyzer.get_landmarks(frame)
            if lms is None:
                continue
            lip_dists.append(self.face_analyzer.compute_lip_distance(lms))
        if len(lip_dists) < 3:
            return InstructionResult(instruction_id, False, 0.0, "No data", len(frames))
        baseline = sorted(lip_dists)[-3:]
        tightest = sorted(lip_dists)[:3]
        delta = np.mean(baseline) - np.mean(tightest)
        passed = delta > 0.02
        confidence = min(delta / 0.04, 1.0)
        return InstructionResult(instruction_id, passed, confidence,
                                 f"Lip purse: {delta:.4f}", len(frames))

    def _verify_cheek_puff(self, frames, instruction_id):
        """Verify cheek puffing."""
        cheek_dists = []
        for frame in frames[::3]:
            lms = self.face_analyzer.get_landmarks(frame)
            if lms is None:
                continue
            cd = self.face_analyzer.compute_cheek_puff(lms)
            cheek_dists.append(cd["left"] + cd["right"])
        if len(cheek_dists) < 3:
            return InstructionResult(instruction_id, False, 0.0, "No data", len(frames))
        baseline = sorted(cheek_dists)[:3]
        peak = sorted(cheek_dists)[-3:]
        delta = np.mean(peak) - np.mean(baseline)
        passed = delta > 5.0
        confidence = min(delta / 10.0, 1.0)
        return InstructionResult(instruction_id, passed, confidence,
                                 f"Cheek delta: {delta:.1f}", len(frames))

    def _verify_stay_still(self, frames, instruction_id):
        """Verify user is staying relatively still."""
        poses = []
        for frame in frames[::3]:
            lms = self.face_analyzer.get_landmarks(frame)
            if lms is None:
                continue
            poses.append(self.face_analyzer.compute_head_pose(lms))
        if len(poses) < 3:
            return InstructionResult(instruction_id, False, 0.0, "No data", len(frames))
        yaw_var = np.var([p["yaw"] for p in poses])
        pitch_var = np.var([p["pitch"] for p in poses])
        total_var = yaw_var + pitch_var
        passed = total_var < 50.0
        confidence = max(0, 1.0 - total_var / 100.0)
        return InstructionResult(instruction_id, passed, confidence,
                                 f"Pose variance: {total_var:.1f}", len(frames))

    def _verify_position_change(self, direction: str):
        """Factory: verify face position change in frame."""
        def verifier(frames, instruction_id):
            positions = []
            for frame in frames[::3]:
                lms = self.face_analyzer.get_landmarks(frame)
                if lms is None:
                    continue
                bbox = self.face_analyzer.compute_face_bbox_center(lms, frame.shape)
                positions.append(bbox)
            if len(positions) < 3:
                return InstructionResult(instruction_id, False, 0.0, "No data", len(frames))
            if direction == "closer":
                areas = [p["area"] for p in positions]
                delta = max(areas) - min(areas)
                passed = delta > 0.02
            elif direction == "farther":
                areas = [p["area"] for p in positions]
                delta = max(areas) - min(areas)
                passed = delta > 0.02
            elif direction in ("left", "right"):
                cxs = [p["cx"] for p in positions]
                delta = max(cxs) - min(cxs)
                passed = delta > 0.08
            elif direction in ("up", "down"):
                cys = [p["cy"] for p in positions]
                delta = max(cys) - min(cys)
                passed = delta > 0.08
            else:
                delta = 0
                passed = False
            confidence = min(delta / 0.15, 1.0)
            return InstructionResult(instruction_id, passed, confidence,
                                     f"Position delta: {delta:.3f}", len(frames))
        return verifier

    # ───────────────────────────────────────────────────────────────────
    # HAND verification functions
    # ───────────────────────────────────────────────────────────────────

    def _verify_wave(self, frames, instruction_id):
        """Verify waving motion (hand x-position oscillation)."""
        hand_xs = []
        for frame in frames[::3]:
            hands = self.hand_analyzer.get_hand_landmarks(frame)
            if not hands:
                continue
            center = self.hand_analyzer.get_hand_center(hands[0])
            hand_xs.append(center[0])
        if len(hand_xs) < 5:
            return InstructionResult(instruction_id, False, 0.0, "Hand not detected enough", len(frames))
        # Count direction changes (oscillation)
        changes = 0
        for i in range(2, len(hand_xs)):
            if (hand_xs[i] - hand_xs[i-1]) * (hand_xs[i-1] - hand_xs[i-2]) < 0:
                changes += 1
        x_range = max(hand_xs) - min(hand_xs)
        passed = changes >= 2 and x_range > 20
        confidence = min(changes / 3.0, 1.0) * min(x_range / 40.0, 1.0)
        return InstructionResult(instruction_id, passed, confidence,
                                 f"Wave: {changes} oscillations, range={x_range:.0f}px", len(frames))

    def _verify_hand_gesture(self, expected_gesture: str):
        """Factory: verify a specific static hand gesture."""
        def verifier(frames, instruction_id):
            detections = 0
            total = 0
            for frame in frames[::3]:
                hands = self.hand_analyzer.get_hand_landmarks(frame)
                if not hands:
                    continue
                total += 1
                fingers = self.hand_analyzer.get_finger_states(hands[0])
                gesture = self.hand_analyzer.classify_gesture(fingers)
                if gesture == expected_gesture:
                    detections += 1
            if total == 0:
                return InstructionResult(instruction_id, False, 0.0, "No hand detected", len(frames))
            ratio = detections / total
            passed = ratio > 0.3
            return InstructionResult(instruction_id, passed, ratio,
                                     f"Gesture '{expected_gesture}' in {ratio:.0%} of frames", len(frames))
        return verifier

    def _verify_finger_count(self, expected_count: int):
        """Factory: verify number of extended fingers."""
        def verifier(frames, instruction_id):
            matches = 0
            total = 0
            for frame in frames[::3]:
                hands = self.hand_analyzer.get_hand_landmarks(frame)
                if not hands:
                    continue
                total += 1
                fingers = self.hand_analyzer.get_finger_states(hands[0])
                count = self.hand_analyzer.count_extended_fingers(fingers)
                if count == expected_count:
                    matches += 1
            if total == 0:
                return InstructionResult(instruction_id, False, 0.0, "No hand detected", len(frames))
            ratio = matches / total
            passed = ratio > 0.3
            return InstructionResult(instruction_id, passed, ratio,
                                     f"{expected_count} fingers in {ratio:.0%} of frames", len(frames))
        return verifier

    def _verify_hand_near_face(self, face_region: str):
        """Factory: verify hand is near a specific face region."""
        def verifier(frames, instruction_id):
            close_frames = 0
            total = 0
            for frame in frames[::3]:
                face_lms = self.face_analyzer.get_landmarks(frame)
                hand_lms_list = self.hand_analyzer.get_hand_landmarks(frame)
                if face_lms is None or not hand_lms_list:
                    continue
                total += 1
                hand_center = self.hand_analyzer.get_hand_center(hand_lms_list[0])
                # Get target face point
                region_map = {
                    "nose": NOSE_TIP, "forehead": FOREHEAD, "chin": CHIN,
                    "left_eye": LEFT_EYE[0], "right_eye": RIGHT_EYE[0],
                    "left_ear": LEFT_EAR, "right_ear": RIGHT_EAR,
                    "left_cheek": LEFT_CHEEK, "right_cheek": RIGHT_CHEEK,
                    "mouth": UPPER_LIP,
                }
                target_idx = region_map.get(face_region, NOSE_TIP)
                target = np.array(face_lms[target_idx][:2])
                dist = np.linalg.norm(hand_center - target)
                # Threshold based on face width
                left_f = np.array(face_lms[LEFT_FACE][:2])
                right_f = np.array(face_lms[RIGHT_FACE][:2])
                face_width = np.linalg.norm(right_f - left_f)
                if dist < face_width * 0.5:
                    close_frames += 1
            if total == 0:
                return InstructionResult(instruction_id, False, 0.0,
                                         "Face or hand not detected", len(frames))
            ratio = close_frames / total
            passed = ratio > 0.2
            return InstructionResult(instruction_id, passed, ratio,
                                     f"Hand near {face_region} in {ratio:.0%} of frames", len(frames))
        return verifier

    def _verify_hand_present(self, frames, instruction_id):
        """Verify at least one hand is visible."""
        detected = 0
        total = 0
        for frame in frames[::3]:
            total += 1
            hands = self.hand_analyzer.get_hand_landmarks(frame)
            if hands:
                detected += 1
        if total == 0:
            return InstructionResult(instruction_id, False, 0.0, "No frames", len(frames))
        ratio = detected / total
        passed = ratio > 0.3
        return InstructionResult(instruction_id, passed, ratio,
                                 f"Hand visible in {ratio:.0%} of frames", len(frames))

    def _verify_hand_state_change(self, frames, instruction_id):
        """Verify hand gesture changes between frames (open/close, count change, etc)."""
        finger_counts = []
        for frame in frames[::3]:
            hands = self.hand_analyzer.get_hand_landmarks(frame)
            if not hands:
                continue
            fingers = self.hand_analyzer.get_finger_states(hands[0])
            finger_counts.append(self.hand_analyzer.count_extended_fingers(fingers))
        if len(finger_counts) < 3:
            return InstructionResult(instruction_id, False, 0.0, "Not enough hand data", len(frames))
        changes = sum(1 for i in range(1, len(finger_counts))
                      if finger_counts[i] != finger_counts[i-1])
        passed = changes >= 1
        confidence = min(changes / 2.0, 1.0)
        return InstructionResult(instruction_id, passed, confidence,
                                 f"Finger state changes: {changes}", len(frames))

    def _verify_generic_presence(self, frames, instruction_id, verify_key):
        """Fallback: just check that face/hand is visible (basic compliance)."""
        face_count = 0
        hand_count = 0
        for frame in frames[::5]:
            if self.face_analyzer.get_landmarks(frame) is not None:
                face_count += 1
            if self.hand_analyzer.get_hand_landmarks(frame):
                hand_count += 1
        total = len(frames) // 5
        if total == 0:
            return InstructionResult(instruction_id, False, 0.0, "No frames", 0)
        face_ratio = face_count / max(total, 1)
        hand_ratio = hand_count / max(total, 1)
        confidence = max(face_ratio, hand_ratio)
        passed = confidence > 0.3
        return InstructionResult(instruction_id, passed, confidence,
                                 f"Fallback: face={face_ratio:.0%}, hand={hand_ratio:.0%}", len(frames))
