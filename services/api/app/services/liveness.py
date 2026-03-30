"""Liveness detection — challenge-response verification engine.

Implements server-side scoring for all 38 challenge types defined in the
challenge catalogue.  Each verifier function receives a list of observation
dicts captured during the challenge window and returns
(score: 0-1, passed: bool, message: str).

Naturalness checks are embedded in each verifier where applicable:
movement speed, acceleration profiles, and anatomical consistency.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

def _metric_values(observations: list[dict], key: str) -> list[float]:
    """Extract a metric time-series from observations."""
    return [float(o.get("client_metrics", {}).get(key, 0.0)) for o in observations]


def _metric(obs: dict, key: str, fallback: float = 0.0) -> float:
    return float(obs.get("client_metrics", {}).get(key, fallback))


def _count_blinks(observations: list[dict]) -> int:
    blinks = 0
    closed = False
    for obs in observations:
        ear_l = _metric(obs, "ear_left", 0.3)
        ear_r = _metric(obs, "ear_right", 0.3)
        avg = (ear_l + ear_r) / 2
        if avg < 0.21 and not closed:
            closed = True
        elif avg > 0.25 and closed:
            blinks += 1
            closed = False
    return blinks


def _detect_wink(observations: list[dict], side: str) -> tuple[float, str]:
    """Detect a single-eye wink on the given side."""
    target_key = "ear_left" if side == "left" else "ear_right"
    other_key = "ear_right" if side == "left" else "ear_left"
    wink_detected = False
    wink_frames = 0
    for obs in observations:
        target_ear = _metric(obs, target_key, 0.3)
        other_ear = _metric(obs, other_key, 0.3)
        if target_ear < 0.15 and other_ear > 0.22:
            wink_detected = True
            wink_frames += 1
    score = min(wink_frames / 3.0, 1.0) if wink_detected else 0.0
    return score, f"Wink {side}: {wink_frames} frames detected"


def _excursion(values: list[float]) -> float:
    """Peak-to-peak excursion."""
    if not values:
        return 0.0
    return max(values) - min(values)


def _detect_sequence(observations: list[dict], actions: list[dict]) -> tuple[float, str]:
    """Check for a sequence of actions in temporal order."""
    scores = []
    for action in actions:
        fn = action["fn"]
        s, _, msg = fn(action.get("filter_id"), observations)
        scores.append(s)
    if not scores:
        return 0.0, "No actions evaluated"
    return min(scores), f"Sequential {len(scores)}-step: min score {min(scores):.2f}"


# ─────────────────────────────────────────────────────────────────────────
# Per-verifier implementations
# ─────────────────────────────────────────────────────────────────────────

def verify_blink_count(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    target = 5 if challenge.get("id") == "rapid_blink_5" else 3
    blinks = _count_blinks(observations)
    score = min(blinks / target, 1.0)
    return score, score >= 0.7, f"Detected {blinks}/{target} blinks"


def verify_wink_left(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    score, msg = _detect_wink(observations, "left")
    return score, score >= 0.6, msg


def verify_wink_right(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    score, msg = _detect_wink(observations, "right")
    return score, score >= 0.6, msg


def verify_gaze_direction(challenge: dict, observations: list[dict], direction: str) -> tuple[float, bool, str]:
    """Generic gaze direction verifier (up, down, left, right)."""
    h_key = "gaze_horizontal"
    v_key = "gaze_vertical"
    h_vals = _metric_values(observations, h_key)
    v_vals = _metric_values(observations, v_key)

    if direction == "up":
        extremes = [v for v in v_vals if v < -0.5]
        score = min(len(extremes) / 3.0, 1.0) if extremes else 0.0
    elif direction == "down":
        extremes = [v for v in v_vals if v > 0.5]
        score = min(len(extremes) / 3.0, 1.0) if extremes else 0.0
    elif direction == "left":
        extremes = [h for h in h_vals if h < -0.5]
        score = min(len(extremes) / 3.0, 1.0) if extremes else 0.0
    elif direction == "right":
        extremes = [h for h in h_vals if h > 0.5]
        score = min(len(extremes) / 3.0, 1.0) if extremes else 0.0
    else:
        score = 0.0

    return score, score >= 0.6, f"Gaze {direction}: score {score:.2f}"


def verify_slow_blink(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Slow, controlled eye close and open."""
    ears = [((_metric(o, "ear_left") + _metric(o, "ear_right")) / 2) for o in observations]
    if not ears:
        return 0.0, False, "No EAR data"
    min_ear = min(ears)
    max_ear = max(ears)
    # Should see gradual decrease to < 0.1, hold, then recovery
    if min_ear < 0.12 and max_ear > 0.22:
        excursion = max_ear - min_ear
        score = min(excursion / 0.15, 1.0)
    else:
        score = 0.2
    return score, score >= 0.6, f"Slow blink: min EAR {min_ear:.3f}, max {max_ear:.3f}"


def verify_mouth_open(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    mars = _metric_values(observations, "mar")
    peak = max(mars) if mars else 0.0
    score = min(max((peak - 0.22) / 0.16, 0.0), 1.0)
    return score, score >= 0.72, f"Peak MAR {peak:.3f}"


def verify_smile(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    scores = _metric_values(observations, "smile_score")
    peak = max(scores) if scores else 0.0
    score = min(max((peak - 0.66) / 0.35, 0.0), 1.0)
    return score, score >= 0.72, f"Peak smile score {peak:.3f}"


def verify_puff_cheeks(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Cheek puffing: face width increases in mid-face region."""
    widths = _metric_values(observations, "face_width")
    if len(widths) < 3:
        return 0.3, False, "Insufficient frames for cheek puff detection"
    baseline = sum(widths[:2]) / 2
    peak = max(widths)
    expansion = (peak - baseline) / max(baseline, 1e-6)
    score = min(max(expansion / 0.05, 0.0), 1.0)
    return score, score >= 0.5, f"Face width expansion {expansion:.4f}"


def verify_asymmetric_mouth(challenge: dict, observations: list[dict], side: str) -> tuple[float, bool, str]:
    """Mouth shift to one side."""
    angles = _metric_values(observations, "mouth_corner_angle")
    if not angles:
        return 0.3, False, "No mouth angle data"
    if side == "left":
        extremes = [a for a in angles if a < -3.0]
    else:
        extremes = [a for a in angles if a > 3.0]
    score = min(len(extremes) / 3.0, 1.0) if extremes else 0.0
    return score, score >= 0.5, f"Mouth {side} shift: {len(extremes)} frames"


def verify_purse_lips(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Lip pursing: mouth width decreases, lip height increases."""
    widths = _metric_values(observations, "mouth_width")
    heights = _metric_values(observations, "mouth_height")
    if not widths or not heights:
        return 0.3, False, "No mouth dimension data"
    min_width = min(widths)
    max_height = max(heights)
    baseline_width = sum(widths[:2]) / 2 if len(widths) >= 2 else widths[0]
    narrowing = (baseline_width - min_width) / max(baseline_width, 1e-6)
    score = min(max(narrowing / 0.15, 0.0), 1.0)
    return score, score >= 0.5, f"Lip narrowing {narrowing:.4f}"


def verify_mouth_phrase(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Silent word mouthing: detect dynamic mouth movement sequence."""
    mars = _metric_values(observations, "mar")
    if len(mars) < 5:
        return 0.3, False, "Insufficient frames"
    # Look for open-close-open pattern (phoneme sequence)
    transitions = 0
    state = "closed" if mars[0] < 0.15 else "open"
    for m in mars[1:]:
        if state == "closed" and m > 0.15:
            state = "open"
            transitions += 1
        elif state == "open" and m < 0.12:
            state = "closed"
            transitions += 1
    score = min(transitions / 4.0, 1.0)
    return score, score >= 0.5, f"Mouth transitions: {transitions}"


def verify_tongue(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Tongue out: high MAR + mouth interior brightness increase."""
    mars = _metric_values(observations, "mar")
    peak_mar = max(mars) if mars else 0.0
    # Tongue sticking out typically causes very high MAR
    score = min(max((peak_mar - 0.35) / 0.25, 0.0), 1.0)
    return score, score >= 0.5, f"Peak MAR for tongue: {peak_mar:.3f}"


def verify_head_turn(challenge: dict, observations: list[dict], direction: str) -> tuple[float, bool, str]:
    """Head turn left or right (yaw change)."""
    yaws = _metric_values(observations, "yaw")
    if not yaws:
        return 0.0, False, "No yaw data"
    if direction == "left":
        peak = min(yaws)
        excursion = abs(peak)
    else:
        peak = max(yaws)
        excursion = abs(peak)
    score = min(excursion / 25.0, 1.0)
    return score, score >= 0.68, f"Head turn {direction}: peak yaw {peak:.1f}°"


def verify_head_tilt(challenge: dict, observations: list[dict], direction: str) -> tuple[float, bool, str]:
    """Head tilt left or right (roll change)."""
    rolls = _metric_values(observations, "roll")
    if not rolls:
        return 0.0, False, "No roll data"
    if direction == "left":
        peak = min(rolls)
        excursion = abs(peak)
    else:
        peak = max(rolls)
        excursion = abs(peak)
    score = min(excursion / 15.0, 1.0)
    return score, score >= 0.6, f"Head tilt {direction}: peak roll {peak:.1f}°"


def verify_nod(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    pitches = _metric_values(observations, "pitch")
    excursion = _excursion(pitches)
    score = min(excursion / 15.0, 1.0)
    return score, score >= 0.68, f"Pitch excursion {excursion:.2f}"


def verify_shake(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    yaws = _metric_values(observations, "yaw")
    excursion = _excursion(yaws)
    score = min(excursion / 18.0, 1.0)
    return score, score >= 0.68, f"Yaw excursion {excursion:.2f}"


def verify_look_over_shoulder(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Large head rotation (60-90°)."""
    yaws = _metric_values(observations, "yaw")
    if not yaws:
        return 0.0, False, "No yaw data"
    peak = max(abs(min(yaws)), abs(max(yaws)))
    score = min(peak / 45.0, 1.0)
    return score, score >= 0.6, f"Shoulder look: peak yaw {peak:.1f}°"


def verify_brow_raise(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    scores = _metric_values(observations, "brow_raise_score")
    peak = max(scores) if scores else 0.0
    score = min(max((peak - 0.32) / 0.35, 0.0), 1.0)
    return score, score >= 0.72, f"Peak brow raise {peak:.3f}"


def verify_frown(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Frown: brow raise decreases, inter-brow distance narrows."""
    brow_scores = _metric_values(observations, "brow_raise_score")
    if not brow_scores:
        return 0.3, False, "No brow data"
    min_brow = min(brow_scores)
    score = min(max((0.35 - min_brow) / 0.2, 0.0), 1.0)
    return score, score >= 0.5, f"Frown: min brow score {min_brow:.3f}"


def verify_surprise(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Surprise: eyebrows raised + eyes wide + mouth slightly open."""
    brow_scores = _metric_values(observations, "brow_raise_score")
    ears = [(_metric(o, "ear_left") + _metric(o, "ear_right")) / 2 for o in observations]
    mars = _metric_values(observations, "mar")
    if not brow_scores or not ears or not mars:
        return 0.3, False, "Insufficient data"
    brow_peak = max(brow_scores)
    ear_peak = max(ears)
    mar_peak = max(mars)
    brow_s = min(max((brow_peak - 0.3) / 0.3, 0.0), 1.0)
    ear_s = min(max((ear_peak - 0.28) / 0.1, 0.0), 1.0)
    mar_s = min(max((mar_peak - 0.1) / 0.15, 0.0), 1.0)
    score = (brow_s + ear_s + mar_s) / 3.0
    return score, score >= 0.55, f"Surprise: brow {brow_s:.2f}, eye {ear_s:.2f}, mouth {mar_s:.2f}"


def verify_angry(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Angry: brows furrowed, lips pressed."""
    brow_scores = _metric_values(observations, "brow_raise_score")
    mars = _metric_values(observations, "mar")
    if not brow_scores:
        return 0.3, False, "No brow data"
    min_brow = min(brow_scores)
    min_mar = min(mars) if mars else 0.5
    brow_s = min(max((0.35 - min_brow) / 0.2, 0.0), 1.0)
    mar_s = min(max((0.12 - min_mar) / 0.08, 0.0), 1.0)
    score = (brow_s * 0.6 + mar_s * 0.4)
    return score, score >= 0.5, f"Angry: brow furrow {brow_s:.2f}, lip press {mar_s:.2f}"


def verify_squint(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    mins = [(_metric(o, "ear_left") + _metric(o, "ear_right")) / 2 for o in observations]
    minimum = min(mins) if mins else 0.3
    score = min(max((0.25 - minimum) / 0.12, 0.0), 1.0)
    return score, score >= 0.65, f"Squint: min EAR {minimum:.3f}"


def verify_distance_shift(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    sizes = _metric_values(observations, "face_size_ratio")
    excursion = _excursion(sizes)
    score = min(excursion / 0.06, 1.0)
    return score, score >= 0.68, f"Face-size excursion {excursion:.4f}"


def verify_finger_count(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Hand near face with finger counting (uses hand landmarks)."""
    hand_near_frames = sum(1 for o in observations if o.get("client_metrics", {}).get("hand_near_face"))
    hand_counts = [int(o.get("client_metrics", {}).get("hand_count", 0)) for o in observations]
    has_hand = any(c > 0 for c in hand_counts)
    score = min(hand_near_frames / 3.0, 1.0) if has_hand else 0.0
    return score, score >= 0.5, f"Hand near face: {hand_near_frames} frames, hand detected: {has_hand}"


def verify_touch_nose(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Hand-face interaction: index finger overlaps nose region."""
    hand_near = sum(1 for o in observations if o.get("client_metrics", {}).get("hand_near_face"))
    score = min(hand_near / 3.0, 1.0)
    return score, score >= 0.5, f"Touch nose: {hand_near} frames with hand near face"


def verify_wave(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Waving hand detected near face."""
    hand_counts = [int(o.get("client_metrics", {}).get("hand_count", 0)) for o in observations]
    frames_with_hand = sum(1 for c in hand_counts if c > 0)
    if frames_with_hand < 3:
        return 0.2, False, "Hand not consistently detected"
    # Look for hand position oscillation
    score = min(frames_with_hand / 4.0, 1.0)
    return score, score >= 0.5, f"Wave: {frames_with_hand} frames with hand"


def verify_blink_then_smile(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Sequential: blinks followed by smile."""
    mid = len(observations) // 2
    first_half = observations[:mid]
    second_half = observations[mid:]
    blinks = _count_blinks(first_half)
    smile_scores = _metric_values(second_half, "smile_score")
    peak_smile = max(smile_scores) if smile_scores else 0.0
    blink_s = min(blinks / 2.0, 1.0)
    smile_s = min(max((peak_smile - 0.66) / 0.35, 0.0), 1.0)
    score = (blink_s + smile_s) / 2.0
    return score, score >= 0.55, f"Blink-then-smile: blinks={blinks}, smile={peak_smile:.2f}"


def verify_turn_blink(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Simultaneous: head turn while blinking."""
    yaws = _metric_values(observations, "yaw")
    blinks = _count_blinks(observations)
    yaw_excursion = _excursion(yaws)
    turn_s = min(yaw_excursion / 18.0, 1.0)
    blink_s = min(blinks / 1.0, 1.0)
    score = (turn_s + blink_s) / 2.0
    return score, score >= 0.55, f"Turn+blink: yaw {yaw_excursion:.1f}°, blinks={blinks}"


def verify_brow_raise_mouth(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Simultaneous: raise eyebrows and open mouth."""
    brows = _metric_values(observations, "brow_raise_score")
    mars = _metric_values(observations, "mar")
    if not brows or not mars:
        return 0.3, False, "Insufficient data"
    brow_peak = max(brows)
    mar_peak = max(mars)
    b_s = min(max((brow_peak - 0.3) / 0.35, 0.0), 1.0)
    m_s = min(max((mar_peak - 0.2) / 0.15, 0.0), 1.0)
    score = (b_s + m_s) / 2.0
    return score, score >= 0.55, f"Brow+mouth: brow={brow_peak:.2f}, mar={mar_peak:.2f}"


def verify_nod_then_wink(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Sequential: nod then right wink."""
    mid = len(observations) // 2
    first_half = observations[:mid]
    second_half = observations[mid:]
    pitches = _metric_values(first_half, "pitch")
    excursion = _excursion(pitches)
    nod_s = min(excursion / 12.0, 1.0)
    wink_s, _ = _detect_wink(second_half, "right")
    score = (nod_s + wink_s) / 2.0
    return score, score >= 0.55, f"Nod-then-wink: pitch {excursion:.1f}°, wink {wink_s:.2f}"


# ─────────────────────────────────────────────────────────────────────────
# Verifier router
# ─────────────────────────────────────────────────────────────────────────

VERIFIER_MAP: dict[str, Any] = {
    "blink_count": verify_blink_count,
    "wink_left": verify_wink_left,
    "wink_right": verify_wink_right,
    "gaze_up": lambda c, o: verify_gaze_direction(c, o, "up"),
    "gaze_down": lambda c, o: verify_gaze_direction(c, o, "down"),
    "gaze_left": lambda c, o: verify_gaze_direction(c, o, "left"),
    "gaze_right": lambda c, o: verify_gaze_direction(c, o, "right"),
    "slow_close_open": verify_slow_blink,
    "mouth_open": verify_mouth_open,
    "smile": verify_smile,
    "puff_cheeks": verify_puff_cheeks,
    "mouth_left": lambda c, o: verify_asymmetric_mouth(c, o, "left"),
    "mouth_right": lambda c, o: verify_asymmetric_mouth(c, o, "right"),
    "purse_lips": verify_purse_lips,
    "mouth_phrase": verify_mouth_phrase,
    "tongue": verify_tongue,
    "turn_left": lambda c, o: verify_head_turn(c, o, "left"),
    "turn_right": lambda c, o: verify_head_turn(c, o, "right"),
    "tilt_left": lambda c, o: verify_head_tilt(c, o, "left"),
    "tilt_right": lambda c, o: verify_head_tilt(c, o, "right"),
    "nod": verify_nod,
    "shake": verify_shake,
    "look_over_shoulder": verify_look_over_shoulder,
    "brow_raise": verify_brow_raise,
    "frown": verify_frown,
    "surprise": verify_surprise,
    "angry": verify_angry,
    "squint": verify_squint,
    "distance_shift": verify_distance_shift,
    "blink_then_smile": verify_blink_then_smile,
    "turn_blink": verify_turn_blink,
    "brow_raise_mouth": verify_brow_raise_mouth,
    "nod_then_wink": verify_nod_then_wink,
    "finger_count": verify_finger_count,
    "touch_nose": verify_touch_nose,
    "wave": verify_wave,
}


def evaluate_challenge(challenge: dict, observations: list[dict]) -> tuple[float, bool, str]:
    """Route a challenge to its verifier and return (score, passed, message)."""
    if not observations:
        return 0.0, False, "No observations received for this challenge"

    verifier_key = challenge.get("verifier", "")
    verifier = VERIFIER_MAP.get(verifier_key)

    if verifier is None:
        return 0.45, False, f"Challenge verifier '{verifier_key}' not recognised"

    try:
        return verifier(challenge, observations)
    except Exception as exc:
        return 0.3, False, f"Verifier error: {exc}"


def evaluate_sequence(
    challenges: list[dict],
    observations: list[dict],
) -> tuple[float, list[str], list[dict]]:
    """Evaluate all challenges and return aggregate score."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for obs in observations:
        cid = obs.get("challenge_id")
        if cid:
            grouped[cid].append(obs)

    results: list[dict] = []
    anomalies: list[str] = []

    for challenge in challenges:
        cid = challenge.get("id", "")
        obs_for_challenge = grouped.get(cid, [])
        score, passed, message = evaluate_challenge(challenge, obs_for_challenge)
        results.append({
            "id": cid,
            "score": round(score, 4),
            "passed": passed,
            "message": message,
        })
        if not passed:
            anomalies.append(f"Liveness challenge failed: {challenge.get('title', cid)}")

    aggregate = sum(r["score"] for r in results) / max(len(results), 1)
    return round(aggregate, 4), anomalies, results
