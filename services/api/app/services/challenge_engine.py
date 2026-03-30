"""Challenge engine — builds randomised, accessibility-aware challenge sequences.

All 38 challenge types are catalogued and marked as implemented.
Security-level-based selection determines difficulty and quantity.
"""

from __future__ import annotations

import random
from typing import Any

CHALLENGE_CATALOG: list[dict[str, Any]] = [
    # ── Eye challenges ──
    {"id": "blink_count", "title": "Blink 3 times", "description": "Blink your eyes three times naturally at a steady pace.", "category": "eye", "duration_seconds": 5, "difficulty": 1, "verifier": "blink_count", "implemented": True},
    {"id": "rapid_blink_5", "title": "Blink 5 times quickly", "description": "Blink your eyes five times rapidly.", "category": "eye", "duration_seconds": 6, "difficulty": 2, "verifier": "blink_count", "implemented": True},
    {"id": "wink_left", "title": "Wink left eye", "description": "Close only your left eye briefly.", "category": "eye", "duration_seconds": 4, "difficulty": 2, "verifier": "wink_left", "implemented": True},
    {"id": "wink_right", "title": "Wink right eye", "description": "Close only your right eye briefly.", "category": "eye", "duration_seconds": 4, "difficulty": 2, "verifier": "wink_right", "implemented": True},
    {"id": "gaze_up", "title": "Look up", "description": "Look upward without moving your head.", "category": "eye", "duration_seconds": 4, "difficulty": 2, "verifier": "gaze_up", "implemented": True},
    {"id": "gaze_down", "title": "Look down", "description": "Look downward without moving your head.", "category": "eye", "duration_seconds": 4, "difficulty": 2, "verifier": "gaze_down", "implemented": True},
    {"id": "gaze_left", "title": "Look left", "description": "Look to your left without moving your head.", "category": "eye", "duration_seconds": 4, "difficulty": 2, "verifier": "gaze_left", "implemented": True},
    {"id": "gaze_right", "title": "Look right", "description": "Look to your right without moving your head.", "category": "eye", "duration_seconds": 4, "difficulty": 2, "verifier": "gaze_right", "implemented": True},
    {"id": "slow_close_open", "title": "Slowly close and open eyes", "description": "Slowly close your eyes, hold for a moment, then open.", "category": "eye", "duration_seconds": 6, "difficulty": 2, "verifier": "slow_close_open", "implemented": True},

    # ── Mouth challenges ──
    {"id": "mouth_open", "title": "Open mouth wide", "description": "Open your mouth as wide as comfortable.", "category": "mouth", "duration_seconds": 4, "difficulty": 1, "verifier": "mouth_open", "implemented": True},
    {"id": "smile", "title": "Smile", "description": "Give a natural, wide smile.", "category": "mouth", "duration_seconds": 4, "difficulty": 1, "verifier": "smile", "implemented": True},
    {"id": "puff_cheeks", "title": "Puff your cheeks", "description": "Inflate your cheeks with air.", "category": "mouth", "duration_seconds": 5, "difficulty": 2, "verifier": "puff_cheeks", "implemented": True},
    {"id": "mouth_left", "title": "Move mouth left", "description": "Shift your mouth to the left side.", "category": "mouth", "duration_seconds": 4, "difficulty": 3, "verifier": "mouth_left", "implemented": True},
    {"id": "mouth_right", "title": "Move mouth right", "description": "Shift your mouth to the right side.", "category": "mouth", "duration_seconds": 4, "difficulty": 3, "verifier": "mouth_right", "implemented": True},
    {"id": "purse_lips", "title": "Purse lips", "description": "Push your lips forward into a kissing shape.", "category": "mouth", "duration_seconds": 4, "difficulty": 2, "verifier": "purse_lips", "implemented": True},
    {"id": "mouth_phrase", "title": "Mouth a phrase silently", "description": "Silently mouth the words 'open sesame'.", "category": "mouth", "duration_seconds": 6, "difficulty": 3, "verifier": "mouth_phrase", "implemented": True},
    {"id": "tongue", "title": "Stick out your tongue", "description": "Briefly stick out your tongue.", "category": "mouth", "duration_seconds": 4, "difficulty": 2, "verifier": "tongue", "implemented": True},

    # ── Head movement challenges ──
    {"id": "turn_left", "title": "Turn head left", "description": "Slowly turn your head to the left.", "category": "head", "duration_seconds": 5, "difficulty": 1, "verifier": "turn_left", "implemented": True},
    {"id": "turn_right", "title": "Turn head right", "description": "Slowly turn your head to the right.", "category": "head", "duration_seconds": 5, "difficulty": 1, "verifier": "turn_right", "implemented": True},
    {"id": "tilt_left", "title": "Tilt head left", "description": "Tilt your head to the left shoulder.", "category": "head", "duration_seconds": 5, "difficulty": 2, "verifier": "tilt_left", "implemented": True},
    {"id": "tilt_right", "title": "Tilt head right", "description": "Tilt your head to the right shoulder.", "category": "head", "duration_seconds": 5, "difficulty": 2, "verifier": "tilt_right", "implemented": True},
    {"id": "nod", "title": "Nod up and down", "description": "Nod your head up and down slowly.", "category": "head", "duration_seconds": 5, "difficulty": 1, "verifier": "nod", "implemented": True},
    {"id": "shake", "title": "Shake head side to side", "description": "Shake your head left to right slowly.", "category": "head", "duration_seconds": 5, "difficulty": 1, "verifier": "shake", "implemented": True},
    {"id": "look_over_shoulder", "title": "Look over your shoulder", "description": "Turn your head far to one side as if looking behind you.", "category": "head", "duration_seconds": 6, "difficulty": 3, "verifier": "look_over_shoulder", "implemented": True},

    # ── Expression challenges ──
    {"id": "brow_raise", "title": "Raise eyebrows", "description": "Raise both eyebrows as high as possible.", "category": "expression", "duration_seconds": 4, "difficulty": 1, "verifier": "brow_raise", "implemented": True},
    {"id": "frown", "title": "Frown", "description": "Furrow your brows as if concentrating hard.", "category": "expression", "duration_seconds": 4, "difficulty": 2, "verifier": "frown", "implemented": True},
    {"id": "surprise", "title": "Show surprise", "description": "Make a surprised face: raise brows, open eyes wide, open mouth slightly.", "category": "expression", "duration_seconds": 5, "difficulty": 2, "verifier": "surprise", "implemented": True},
    {"id": "angry", "title": "Look angry", "description": "Make an angry face: furrow brows, narrow eyes, press lips.", "category": "expression", "duration_seconds": 5, "difficulty": 2, "verifier": "angry", "implemented": True},
    {"id": "squint", "title": "Squint", "description": "Narrow both eyes without closing them.", "category": "expression", "duration_seconds": 4, "difficulty": 1, "verifier": "squint", "implemented": True},

    # ── Distance / proximity ──
    {"id": "distance_shift", "title": "Move closer then further", "description": "Lean towards the camera, then lean back.", "category": "distance", "duration_seconds": 6, "difficulty": 1, "verifier": "distance_shift", "implemented": True},

    # ── Combined / sequential challenges ──
    {"id": "blink_then_smile", "title": "Blink then smile", "description": "Blink 2-3 times, then immediately smile.", "category": "combined", "duration_seconds": 7, "difficulty": 3, "verifier": "blink_then_smile", "implemented": True},
    {"id": "turn_blink", "title": "Turn and blink", "description": "Turn your head slightly while blinking.", "category": "combined", "duration_seconds": 6, "difficulty": 3, "verifier": "turn_blink", "implemented": True},
    {"id": "brow_raise_mouth", "title": "Eyebrows up and open mouth", "description": "Raise your eyebrows and open your mouth at the same time.", "category": "combined", "duration_seconds": 5, "difficulty": 3, "verifier": "brow_raise_mouth", "implemented": True},
    {"id": "nod_then_wink", "title": "Nod then wink", "description": "Nod your head, then give a right-eye wink.", "category": "combined", "duration_seconds": 7, "difficulty": 3, "verifier": "nod_then_wink", "implemented": True},

    # ── Cognitive / hand challenges ──
    {"id": "finger_count", "title": "Show a number with fingers", "description": "Hold up 3 fingers near your face.", "category": "cognitive", "duration_seconds": 6, "difficulty": 2, "verifier": "finger_count", "implemented": True},
    {"id": "touch_nose", "title": "Touch your nose", "description": "Briefly touch the tip of your nose with a fingertip.", "category": "cognitive", "duration_seconds": 5, "difficulty": 2, "verifier": "touch_nose", "implemented": True},
    {"id": "wave", "title": "Wave at the camera", "description": "Give a short wave with your hand near your face.", "category": "cognitive", "duration_seconds": 5, "difficulty": 1, "verifier": "wave", "implemented": True},
]


# ── Security level configurations ──

SECURITY_LEVELS = {
    "basic": {
        "challenge_count": 3,
        "max_difficulty": 2,
        "required_categories": ["eye", "mouth"],
    },
    "enhanced": {
        "challenge_count": 4,
        "max_difficulty": 3,
        "required_categories": ["eye", "mouth", "head"],
    },
    "maximum": {
        "challenge_count": 5,
        "max_difficulty": 3,
        "required_categories": ["eye", "mouth", "head", "expression"],
    },
}


def select_challenges(
    security_level: str = "enhanced",
    accessibility_profile: dict[str, bool] | None = None,
) -> list[dict]:
    """Select a randomised set of challenges respecting user accessibility and security level.

    Accessibility flags:
    - eye_only: only eye-based challenges
    - no_head_turns: exclude head movement challenges
    - no_hand: exclude hand/cognitive challenges

    Returns a list of challenge dicts suitable for sending to the client.
    """
    prefs = accessibility_profile or {}
    config = SECURITY_LEVELS.get(security_level, SECURITY_LEVELS["enhanced"])
    target_count = config["challenge_count"]
    max_diff = config["max_difficulty"]
    required_cats = config["required_categories"]

    # Build eligible pool
    pool = [c for c in CHALLENGE_CATALOG if c["implemented"] and c["difficulty"] <= max_diff]

    # Apply accessibility filters
    if prefs.get("eye_only"):
        pool = [c for c in pool if c["category"] == "eye"]
    if prefs.get("no_head_turns"):
        pool = [c for c in pool if c["category"] != "head"]
    if prefs.get("no_hand"):
        pool = [c for c in pool if c["category"] not in ("cognitive",)]

    if not pool:
        pool = [c for c in CHALLENGE_CATALOG if c["category"] == "eye"][:3]

    # Ensure category diversity
    selected: list[dict] = []
    seen_categories: set[str] = set()
    used_ids: set[str] = set()

    # First pass: pick one per required category
    for cat in required_cats:
        candidates = [c for c in pool if c["category"] == cat and c["id"] not in used_ids]
        if candidates:
            choice = random.choice(candidates)
            selected.append(choice)
            used_ids.add(choice["id"])
            seen_categories.add(cat)

    # Fill remaining slots
    remaining = [c for c in pool if c["id"] not in used_ids]
    random.shuffle(remaining)
    while len(selected) < target_count and remaining:
        choice = remaining.pop()
        selected.append(choice)
        used_ids.add(choice["id"])

    # Randomise order
    random.shuffle(selected)

    # Return client-safe dicts
    return [
        {
            "id": c["id"],
            "title": c["title"],
            "description": c["description"],
            "category": c["category"],
            "duration_seconds": c["duration_seconds"],
        }
        for c in selected
    ]
