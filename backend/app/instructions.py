"""
instructions.py — 200 Authentication Challenge Instructions

Each instruction is a dict with:
  id:           int (0-199)
  text:         str — displayed to the user
  category:     "face" | "hand"
  sub_category: specific type (blink, head_turn, expression, gesture, etc.)
  verify_key:   str — maps to a verification function in instruction_verifier.py
  duration_sec: float — how long to record
  difficulty:   int (1-3)

During authentication, the system picks CHALLENGE_COUNT random instructions
(1 face + 1 hand) and the user must perform them on camera.
"""

import random
from typing import Optional
from app.config import CHALLENGE_COUNT, INSTRUCTION_CATEGORIES


# ═══════════════════════════════════════════════════════════════════════════
# INSTRUCTION DATABASE — 200 entries
# ═══════════════════════════════════════════════════════════════════════════

INSTRUCTIONS = [
    # ─── BLINK / EYES (0-24) ────────────────────────────────────────────
    {"id": 0,   "text": "Blink both eyes once",                    "category": "face", "sub_category": "blink",      "verify_key": "blink_once",             "duration_sec": 3, "difficulty": 1},
    {"id": 1,   "text": "Blink both eyes three times",             "category": "face", "sub_category": "blink",      "verify_key": "blink_three",            "duration_sec": 4, "difficulty": 1},
    {"id": 2,   "text": "Blink rapidly five times",                "category": "face", "sub_category": "blink",      "verify_key": "blink_five",             "duration_sec": 4, "difficulty": 2},
    {"id": 3,   "text": "Close your left eye only (wink)",         "category": "face", "sub_category": "blink",      "verify_key": "wink_left",              "duration_sec": 3, "difficulty": 2},
    {"id": 4,   "text": "Close your right eye only (wink)",        "category": "face", "sub_category": "blink",      "verify_key": "wink_right",             "duration_sec": 3, "difficulty": 2},
    {"id": 5,   "text": "Close both eyes for 2 seconds",           "category": "face", "sub_category": "blink",      "verify_key": "eyes_closed_hold",       "duration_sec": 4, "difficulty": 1},
    {"id": 6,   "text": "Look up",                                 "category": "face", "sub_category": "gaze",       "verify_key": "look_up",                "duration_sec": 3, "difficulty": 1},
    {"id": 7,   "text": "Look down",                               "category": "face", "sub_category": "gaze",       "verify_key": "look_down",              "duration_sec": 3, "difficulty": 1},
    {"id": 8,   "text": "Look to your left",                       "category": "face", "sub_category": "gaze",       "verify_key": "look_left",              "duration_sec": 3, "difficulty": 1},
    {"id": 9,   "text": "Look to your right",                      "category": "face", "sub_category": "gaze",       "verify_key": "look_right",             "duration_sec": 3, "difficulty": 1},
    {"id": 10,  "text": "Look to the upper left corner",           "category": "face", "sub_category": "gaze",       "verify_key": "look_upper_left",        "duration_sec": 3, "difficulty": 2},
    {"id": 11,  "text": "Look to the upper right corner",          "category": "face", "sub_category": "gaze",       "verify_key": "look_upper_right",       "duration_sec": 3, "difficulty": 2},
    {"id": 12,  "text": "Widen your eyes as much as possible",     "category": "face", "sub_category": "eyes",       "verify_key": "eyes_wide",              "duration_sec": 3, "difficulty": 1},
    {"id": 13,  "text": "Squint your eyes",                        "category": "face", "sub_category": "eyes",       "verify_key": "squint",                 "duration_sec": 3, "difficulty": 1},
    {"id": 14,  "text": "Slowly close and open your eyes",         "category": "face", "sub_category": "blink",      "verify_key": "slow_blink",             "duration_sec": 4, "difficulty": 2},
    {"id": 15,  "text": "Blink only your left eye twice",          "category": "face", "sub_category": "blink",      "verify_key": "wink_left_twice",        "duration_sec": 4, "difficulty": 3},
    {"id": 16,  "text": "Blink only your right eye twice",         "category": "face", "sub_category": "blink",      "verify_key": "wink_right_twice",       "duration_sec": 4, "difficulty": 3},
    {"id": 17,  "text": "Look left then right quickly",            "category": "face", "sub_category": "gaze",       "verify_key": "look_left_right",        "duration_sec": 3, "difficulty": 2},
    {"id": 18,  "text": "Look up then down",                       "category": "face", "sub_category": "gaze",       "verify_key": "look_up_down",           "duration_sec": 3, "difficulty": 2},
    {"id": 19,  "text": "Roll your eyes in a circle",              "category": "face", "sub_category": "gaze",       "verify_key": "eye_roll",               "duration_sec": 4, "difficulty": 3},
    {"id": 20,  "text": "Close eyes then open wide",               "category": "face", "sub_category": "blink",      "verify_key": "close_then_wide",        "duration_sec": 3, "difficulty": 2},
    {"id": 21,  "text": "Flutter your eyelids rapidly",            "category": "face", "sub_category": "blink",      "verify_key": "flutter_blink",          "duration_sec": 3, "difficulty": 2},
    {"id": 22,  "text": "Wink alternating left and right",         "category": "face", "sub_category": "blink",      "verify_key": "alternating_wink",       "duration_sec": 4, "difficulty": 3},
    {"id": 23,  "text": "Look at the camera and hold still",       "category": "face", "sub_category": "gaze",       "verify_key": "look_center_hold",       "duration_sec": 3, "difficulty": 1},
    {"id": 24,  "text": "Cross your eyes briefly",                 "category": "face", "sub_category": "gaze",       "verify_key": "cross_eyes",             "duration_sec": 3, "difficulty": 3},

    # ─── HEAD MOVEMENT (25-54) ──────────────────────────────────────────
    {"id": 25,  "text": "Turn your head to the right",             "category": "face", "sub_category": "head",       "verify_key": "head_turn_right",        "duration_sec": 3, "difficulty": 1},
    {"id": 26,  "text": "Turn your head to the left",              "category": "face", "sub_category": "head",       "verify_key": "head_turn_left",         "duration_sec": 3, "difficulty": 1},
    {"id": 27,  "text": "Nod your head yes",                       "category": "face", "sub_category": "head",       "verify_key": "nod_yes",                "duration_sec": 3, "difficulty": 1},
    {"id": 28,  "text": "Shake your head no",                      "category": "face", "sub_category": "head",       "verify_key": "shake_no",               "duration_sec": 3, "difficulty": 1},
    {"id": 29,  "text": "Tilt your head to the left",              "category": "face", "sub_category": "head",       "verify_key": "tilt_left",              "duration_sec": 3, "difficulty": 1},
    {"id": 30,  "text": "Tilt your head to the right",             "category": "face", "sub_category": "head",       "verify_key": "tilt_right",             "duration_sec": 3, "difficulty": 1},
    {"id": 31,  "text": "Look over your right shoulder",           "category": "face", "sub_category": "head",       "verify_key": "look_over_right",        "duration_sec": 3, "difficulty": 2},
    {"id": 32,  "text": "Look over your left shoulder",            "category": "face", "sub_category": "head",       "verify_key": "look_over_left",         "duration_sec": 3, "difficulty": 2},
    {"id": 33,  "text": "Slowly turn right then left",             "category": "face", "sub_category": "head",       "verify_key": "turn_right_left",        "duration_sec": 4, "difficulty": 2},
    {"id": 34,  "text": "Nod slowly three times",                  "category": "face", "sub_category": "head",       "verify_key": "nod_three",              "duration_sec": 4, "difficulty": 2},
    {"id": 35,  "text": "Tilt head left then right",               "category": "face", "sub_category": "head",       "verify_key": "tilt_left_right",        "duration_sec": 4, "difficulty": 2},
    {"id": 36,  "text": "Turn your head far right",                "category": "face", "sub_category": "head",       "verify_key": "head_far_right",         "duration_sec": 3, "difficulty": 2},
    {"id": 37,  "text": "Turn your head far left",                 "category": "face", "sub_category": "head",       "verify_key": "head_far_left",          "duration_sec": 3, "difficulty": 2},
    {"id": 38,  "text": "Look down at your chin",                  "category": "face", "sub_category": "head",       "verify_key": "chin_down",              "duration_sec": 3, "difficulty": 1},
    {"id": 39,  "text": "Look up at the ceiling",                  "category": "face", "sub_category": "head",       "verify_key": "chin_up",                "duration_sec": 3, "difficulty": 1},
    {"id": 40,  "text": "Make a small circular head motion",       "category": "face", "sub_category": "head",       "verify_key": "head_circle",            "duration_sec": 4, "difficulty": 3},
    {"id": 41,  "text": "Turn right, pause, return to center",     "category": "face", "sub_category": "head",       "verify_key": "turn_right_return",      "duration_sec": 4, "difficulty": 2},
    {"id": 42,  "text": "Turn left, pause, return to center",      "category": "face", "sub_category": "head",       "verify_key": "turn_left_return",       "duration_sec": 4, "difficulty": 2},
    {"id": 43,  "text": "Lean your head forward slightly",         "category": "face", "sub_category": "head",       "verify_key": "lean_forward",           "duration_sec": 3, "difficulty": 1},
    {"id": 44,  "text": "Lean your head backward slightly",        "category": "face", "sub_category": "head",       "verify_key": "lean_backward",          "duration_sec": 3, "difficulty": 1},
    {"id": 45,  "text": "Shake head no quickly",                   "category": "face", "sub_category": "head",       "verify_key": "shake_quick",            "duration_sec": 3, "difficulty": 2},
    {"id": 46,  "text": "Nod vigorously",                          "category": "face", "sub_category": "head",       "verify_key": "nod_vigorous",           "duration_sec": 3, "difficulty": 2},
    {"id": 47,  "text": "Slowly turn head 90 degrees right",       "category": "face", "sub_category": "head",       "verify_key": "slow_turn_right",        "duration_sec": 4, "difficulty": 2},
    {"id": 48,  "text": "Slowly turn head 90 degrees left",        "category": "face", "sub_category": "head",       "verify_key": "slow_turn_left",         "duration_sec": 4, "difficulty": 2},
    {"id": 49,  "text": "Tilt head and hold for 2 seconds",        "category": "face", "sub_category": "head",       "verify_key": "tilt_hold",              "duration_sec": 4, "difficulty": 2},
    {"id": 50,  "text": "Drop chin to chest",                      "category": "face", "sub_category": "head",       "verify_key": "chin_to_chest",          "duration_sec": 3, "difficulty": 2},
    {"id": 51,  "text": "Look straight ahead and stay still",      "category": "face", "sub_category": "head",       "verify_key": "stay_still",             "duration_sec": 3, "difficulty": 1},
    {"id": 52,  "text": "Rotate head right then nod",              "category": "face", "sub_category": "head",       "verify_key": "turn_then_nod",          "duration_sec": 4, "difficulty": 3},
    {"id": 53,  "text": "Tilt head right and blink",               "category": "face", "sub_category": "head",       "verify_key": "tilt_and_blink",         "duration_sec": 4, "difficulty": 3},
    {"id": 54,  "text": "Move head in a figure-eight motion",      "category": "face", "sub_category": "head",       "verify_key": "head_figure_eight",      "duration_sec": 5, "difficulty": 3},

    # ─── EXPRESSIONS (55-84) ────────────────────────────────────────────
    {"id": 55,  "text": "Smile widely",                            "category": "face", "sub_category": "expression", "verify_key": "smile_wide",             "duration_sec": 3, "difficulty": 1},
    {"id": 56,  "text": "Give a subtle smile",                     "category": "face", "sub_category": "expression", "verify_key": "smile_subtle",           "duration_sec": 3, "difficulty": 2},
    {"id": 57,  "text": "Frown",                                   "category": "face", "sub_category": "expression", "verify_key": "frown",                  "duration_sec": 3, "difficulty": 1},
    {"id": 58,  "text": "Raise both eyebrows high",                "category": "face", "sub_category": "expression", "verify_key": "raise_eyebrows",         "duration_sec": 3, "difficulty": 1},
    {"id": 59,  "text": "Raise only your left eyebrow",            "category": "face", "sub_category": "expression", "verify_key": "raise_left_brow",        "duration_sec": 3, "difficulty": 3},
    {"id": 60,  "text": "Raise only your right eyebrow",           "category": "face", "sub_category": "expression", "verify_key": "raise_right_brow",       "duration_sec": 3, "difficulty": 3},
    {"id": 61,  "text": "Make a surprised face",                   "category": "face", "sub_category": "expression", "verify_key": "surprised",              "duration_sec": 3, "difficulty": 1},
    {"id": 62,  "text": "Puff out your cheeks",                    "category": "face", "sub_category": "expression", "verify_key": "puff_cheeks",            "duration_sec": 3, "difficulty": 1},
    {"id": 63,  "text": "Puff only your left cheek",               "category": "face", "sub_category": "expression", "verify_key": "puff_left_cheek",        "duration_sec": 3, "difficulty": 2},
    {"id": 64,  "text": "Puff only your right cheek",              "category": "face", "sub_category": "expression", "verify_key": "puff_right_cheek",       "duration_sec": 3, "difficulty": 2},
    {"id": 65,  "text": "Purse your lips like a kiss",             "category": "face", "sub_category": "expression", "verify_key": "purse_lips",             "duration_sec": 3, "difficulty": 1},
    {"id": 66,  "text": "Show your teeth",                         "category": "face", "sub_category": "expression", "verify_key": "show_teeth",             "duration_sec": 3, "difficulty": 1},
    {"id": 67,  "text": "Make an angry expression",                "category": "face", "sub_category": "expression", "verify_key": "angry_face",             "duration_sec": 3, "difficulty": 2},
    {"id": 68,  "text": "Wrinkle your nose",                       "category": "face", "sub_category": "expression", "verify_key": "wrinkle_nose",           "duration_sec": 3, "difficulty": 2},
    {"id": 69,  "text": "Make a sad face",                         "category": "face", "sub_category": "expression", "verify_key": "sad_face",               "duration_sec": 3, "difficulty": 2},
    {"id": 70,  "text": "Smile then go neutral",                   "category": "face", "sub_category": "expression", "verify_key": "smile_then_neutral",     "duration_sec": 4, "difficulty": 2},
    {"id": 71,  "text": "Raise eyebrows then frown",               "category": "face", "sub_category": "expression", "verify_key": "brows_then_frown",       "duration_sec": 4, "difficulty": 2},
    {"id": 72,  "text": "Clench your jaw",                         "category": "face", "sub_category": "expression", "verify_key": "clench_jaw",             "duration_sec": 3, "difficulty": 2},
    {"id": 73,  "text": "Move your jaw to the left",               "category": "face", "sub_category": "expression", "verify_key": "jaw_left",               "duration_sec": 3, "difficulty": 2},
    {"id": 74,  "text": "Move your jaw to the right",              "category": "face", "sub_category": "expression", "verify_key": "jaw_right",              "duration_sec": 3, "difficulty": 2},
    {"id": 75,  "text": "Make a fish face (suck cheeks in)",        "category": "face", "sub_category": "expression", "verify_key": "fish_face",              "duration_sec": 3, "difficulty": 2},
    {"id": 76,  "text": "Scrunch your whole face tight",           "category": "face", "sub_category": "expression", "verify_key": "scrunch_face",           "duration_sec": 3, "difficulty": 2},
    {"id": 77,  "text": "Relax your face completely",              "category": "face", "sub_category": "expression", "verify_key": "relax_face",             "duration_sec": 3, "difficulty": 1},
    {"id": 78,  "text": "Alternate smiling and frowning",          "category": "face", "sub_category": "expression", "verify_key": "smile_frown_alternate",  "duration_sec": 4, "difficulty": 3},
    {"id": 79,  "text": "Yawn widely",                             "category": "face", "sub_category": "expression", "verify_key": "yawn",                   "duration_sec": 3, "difficulty": 2},
    {"id": 80,  "text": "Pout your lower lip",                     "category": "face", "sub_category": "expression", "verify_key": "pout",                   "duration_sec": 3, "difficulty": 2},
    {"id": 81,  "text": "Grin showing all teeth",                  "category": "face", "sub_category": "expression", "verify_key": "big_grin",               "duration_sec": 3, "difficulty": 1},
    {"id": 82,  "text": "Make an 'O' shape with your mouth",       "category": "face", "sub_category": "expression", "verify_key": "mouth_o",                "duration_sec": 3, "difficulty": 1},
    {"id": 83,  "text": "Bite your lower lip",                     "category": "face", "sub_category": "expression", "verify_key": "bite_lip",               "duration_sec": 3, "difficulty": 2},
    {"id": 84,  "text": "Flare your nostrils",                     "category": "face", "sub_category": "expression", "verify_key": "flare_nostrils",         "duration_sec": 3, "difficulty": 3},

    # ─── MOUTH (85-104) ────────────────────────────────────────────────
    {"id": 85,  "text": "Open your mouth wide",                    "category": "face", "sub_category": "mouth",      "verify_key": "mouth_open_wide",        "duration_sec": 3, "difficulty": 1},
    {"id": 86,  "text": "Stick out your tongue",                   "category": "face", "sub_category": "mouth",      "verify_key": "tongue_out",             "duration_sec": 3, "difficulty": 1},
    {"id": 87,  "text": "Move your tongue to the left",            "category": "face", "sub_category": "mouth",      "verify_key": "tongue_left",            "duration_sec": 3, "difficulty": 2},
    {"id": 88,  "text": "Move your tongue to the right",           "category": "face", "sub_category": "mouth",      "verify_key": "tongue_right",           "duration_sec": 3, "difficulty": 2},
    {"id": 89,  "text": "Say 'Ahh' with mouth wide open",         "category": "face", "sub_category": "mouth",      "verify_key": "say_ahh",                "duration_sec": 3, "difficulty": 1},
    {"id": 90,  "text": "Move your lips side to side",             "category": "face", "sub_category": "mouth",      "verify_key": "lips_side_to_side",      "duration_sec": 4, "difficulty": 2},
    {"id": 91,  "text": "Open and close your mouth three times",   "category": "face", "sub_category": "mouth",      "verify_key": "mouth_open_close_three", "duration_sec": 4, "difficulty": 2},
    {"id": 92,  "text": "Smile with mouth closed",                 "category": "face", "sub_category": "mouth",      "verify_key": "closed_smile",           "duration_sec": 3, "difficulty": 1},
    {"id": 93,  "text": "Blow air out (like blowing a candle)",    "category": "face", "sub_category": "mouth",      "verify_key": "blow_air",               "duration_sec": 3, "difficulty": 2},
    {"id": 94,  "text": "Press your lips together tightly",        "category": "face", "sub_category": "mouth",      "verify_key": "press_lips",             "duration_sec": 3, "difficulty": 1},
    {"id": 95,  "text": "Open mouth then smile",                   "category": "face", "sub_category": "mouth",      "verify_key": "open_then_smile",        "duration_sec": 4, "difficulty": 2},
    {"id": 96,  "text": "Move jaw up and down slowly",             "category": "face", "sub_category": "mouth",      "verify_key": "jaw_up_down",            "duration_sec": 4, "difficulty": 1},
    {"id": 97,  "text": "Whistle position (lips rounded)",         "category": "face", "sub_category": "mouth",      "verify_key": "whistle_lips",           "duration_sec": 3, "difficulty": 2},
    {"id": 98,  "text": "Smile with only the right side",          "category": "face", "sub_category": "mouth",      "verify_key": "half_smile_right",       "duration_sec": 3, "difficulty": 3},
    {"id": 99,  "text": "Smile with only the left side",           "category": "face", "sub_category": "mouth",      "verify_key": "half_smile_left",        "duration_sec": 3, "difficulty": 3},
    {"id": 100, "text": "Open mouth then stick out tongue",        "category": "face", "sub_category": "mouth",      "verify_key": "open_then_tongue",       "duration_sec": 4, "difficulty": 2},
    {"id": 101, "text": "Make an 'Eee' sound shape",               "category": "face", "sub_category": "mouth",      "verify_key": "mouth_eee",              "duration_sec": 3, "difficulty": 1},
    {"id": 102, "text": "Open mouth wide and close slowly",        "category": "face", "sub_category": "mouth",      "verify_key": "slow_mouth_close",       "duration_sec": 4, "difficulty": 2},
    {"id": 103, "text": "Stretch your mouth as wide as possible",  "category": "face", "sub_category": "mouth",      "verify_key": "stretch_mouth",          "duration_sec": 3, "difficulty": 1},
    {"id": 104, "text": "Touch your upper lip with lower lip",     "category": "face", "sub_category": "mouth",      "verify_key": "lip_over_lip",           "duration_sec": 3, "difficulty": 3},

    # ─── HAND GESTURES (105-139) ────────────────────────────────────────
    {"id": 105, "text": "Wave at the camera with your right hand",  "category": "hand", "sub_category": "gesture",   "verify_key": "wave_right",             "duration_sec": 4, "difficulty": 1},
    {"id": 106, "text": "Wave at the camera with your left hand",   "category": "hand", "sub_category": "gesture",   "verify_key": "wave_left",              "duration_sec": 4, "difficulty": 1},
    {"id": 107, "text": "Show a thumbs up",                         "category": "hand", "sub_category": "gesture",   "verify_key": "thumbs_up",              "duration_sec": 3, "difficulty": 1},
    {"id": 108, "text": "Show a thumbs down",                       "category": "hand", "sub_category": "gesture",   "verify_key": "thumbs_down",            "duration_sec": 3, "difficulty": 1},
    {"id": 109, "text": "Show the peace sign (V sign)",             "category": "hand", "sub_category": "gesture",   "verify_key": "peace_sign",             "duration_sec": 3, "difficulty": 1},
    {"id": 110, "text": "Show an open palm facing the camera",      "category": "hand", "sub_category": "gesture",   "verify_key": "open_palm",              "duration_sec": 3, "difficulty": 1},
    {"id": 111, "text": "Make a fist",                              "category": "hand", "sub_category": "gesture",   "verify_key": "fist",                   "duration_sec": 3, "difficulty": 1},
    {"id": 112, "text": "Show one finger (index finger up)",        "category": "hand", "sub_category": "gesture",   "verify_key": "one_finger",             "duration_sec": 3, "difficulty": 1},
    {"id": 113, "text": "Show two fingers",                         "category": "hand", "sub_category": "gesture",   "verify_key": "two_fingers",            "duration_sec": 3, "difficulty": 1},
    {"id": 114, "text": "Show three fingers",                       "category": "hand", "sub_category": "gesture",   "verify_key": "three_fingers",          "duration_sec": 3, "difficulty": 1},
    {"id": 115, "text": "Show four fingers",                        "category": "hand", "sub_category": "gesture",   "verify_key": "four_fingers",           "duration_sec": 3, "difficulty": 1},
    {"id": 116, "text": "Show all five fingers spread",             "category": "hand", "sub_category": "gesture",   "verify_key": "five_fingers",           "duration_sec": 3, "difficulty": 1},
    {"id": 117, "text": "Make the OK sign (thumb + index circle)",  "category": "hand", "sub_category": "gesture",   "verify_key": "ok_sign",                "duration_sec": 3, "difficulty": 2},
    {"id": 118, "text": "Point upward with your index finger",      "category": "hand", "sub_category": "gesture",   "verify_key": "point_up",               "duration_sec": 3, "difficulty": 1},
    {"id": 119, "text": "Point downward",                           "category": "hand", "sub_category": "gesture",   "verify_key": "point_down",             "duration_sec": 3, "difficulty": 1},
    {"id": 120, "text": "Point to the left",                        "category": "hand", "sub_category": "gesture",   "verify_key": "point_left",             "duration_sec": 3, "difficulty": 1},
    {"id": 121, "text": "Point to the right",                       "category": "hand", "sub_category": "gesture",   "verify_key": "point_right",            "duration_sec": 3, "difficulty": 1},
    {"id": 122, "text": "Make a pinching motion",                   "category": "hand", "sub_category": "gesture",   "verify_key": "pinch",                  "duration_sec": 3, "difficulty": 2},
    {"id": 123, "text": "Rotate your wrist clockwise",              "category": "hand", "sub_category": "gesture",   "verify_key": "wrist_rotate_cw",        "duration_sec": 4, "difficulty": 2},
    {"id": 124, "text": "Rotate your wrist counter-clockwise",      "category": "hand", "sub_category": "gesture",   "verify_key": "wrist_rotate_ccw",       "duration_sec": 4, "difficulty": 2},
    {"id": 125, "text": "Open fist then close slowly",              "category": "hand", "sub_category": "gesture",   "verify_key": "open_close_fist",        "duration_sec": 4, "difficulty": 2},
    {"id": 126, "text": "Spread fingers wide then close",           "category": "hand", "sub_category": "gesture",   "verify_key": "spread_close",           "duration_sec": 4, "difficulty": 2},
    {"id": 127, "text": "Show the 'rock on' sign (pinky + index)",  "category": "hand", "sub_category": "gesture",   "verify_key": "rock_sign",              "duration_sec": 3, "difficulty": 2},
    {"id": 128, "text": "Give a thumbs up with both hands",         "category": "hand", "sub_category": "gesture",   "verify_key": "double_thumbs_up",       "duration_sec": 3, "difficulty": 2},
    {"id": 129, "text": "Wiggle your fingers",                      "category": "hand", "sub_category": "gesture",   "verify_key": "wiggle_fingers",         "duration_sec": 4, "difficulty": 2},
    {"id": 130, "text": "Show your palm then flip to back of hand",  "category": "hand", "sub_category": "gesture",   "verify_key": "palm_flip",             "duration_sec": 4, "difficulty": 2},
    {"id": 131, "text": "Count 1-2-3 with your fingers",            "category": "hand", "sub_category": "gesture",   "verify_key": "count_123",              "duration_sec": 4, "difficulty": 2},
    {"id": 132, "text": "Make a 'stop' gesture (palm forward)",     "category": "hand", "sub_category": "gesture",   "verify_key": "stop_gesture",           "duration_sec": 3, "difficulty": 1},
    {"id": 133, "text": "Cup your hand like holding water",         "category": "hand", "sub_category": "gesture",   "verify_key": "cup_hand",               "duration_sec": 3, "difficulty": 2},
    {"id": 134, "text": "Make a phone-call gesture",                "category": "hand", "sub_category": "gesture",   "verify_key": "phone_gesture",          "duration_sec": 3, "difficulty": 2},
    {"id": 135, "text": "Clap your hands once",                     "category": "hand", "sub_category": "gesture",   "verify_key": "clap_once",              "duration_sec": 3, "difficulty": 1},
    {"id": 136, "text": "Snap your fingers",                        "category": "hand", "sub_category": "gesture",   "verify_key": "snap_fingers",           "duration_sec": 3, "difficulty": 3},
    {"id": 137, "text": "Make finger guns",                         "category": "hand", "sub_category": "gesture",   "verify_key": "finger_guns",            "duration_sec": 3, "difficulty": 2},
    {"id": 138, "text": "Cross your fingers",                       "category": "hand", "sub_category": "gesture",   "verify_key": "cross_fingers",          "duration_sec": 3, "difficulty": 3},
    {"id": 139, "text": "Salute like a soldier",                    "category": "hand", "sub_category": "gesture",   "verify_key": "salute",                 "duration_sec": 3, "difficulty": 2},

    # ─── HAND + FACE (140-169) ──────────────────────────────────────────
    {"id": 140, "text": "Touch the tip of your nose with a finger",  "category": "hand", "sub_category": "hand_face", "verify_key": "touch_nose",            "duration_sec": 3, "difficulty": 1},
    {"id": 141, "text": "Cover your left eye with your hand",        "category": "hand", "sub_category": "hand_face", "verify_key": "cover_left_eye",        "duration_sec": 3, "difficulty": 1},
    {"id": 142, "text": "Cover your right eye with your hand",       "category": "hand", "sub_category": "hand_face", "verify_key": "cover_right_eye",       "duration_sec": 3, "difficulty": 1},
    {"id": 143, "text": "Put your hand on your chin",                "category": "hand", "sub_category": "hand_face", "verify_key": "hand_on_chin",          "duration_sec": 3, "difficulty": 1},
    {"id": 144, "text": "Touch your left ear",                       "category": "hand", "sub_category": "hand_face", "verify_key": "touch_left_ear",        "duration_sec": 3, "difficulty": 1},
    {"id": 145, "text": "Touch your right ear",                      "category": "hand", "sub_category": "hand_face", "verify_key": "touch_right_ear",       "duration_sec": 3, "difficulty": 1},
    {"id": 146, "text": "Put your hand on your forehead",            "category": "hand", "sub_category": "hand_face", "verify_key": "hand_on_forehead",      "duration_sec": 3, "difficulty": 1},
    {"id": 147, "text": "Touch your left cheek",                     "category": "hand", "sub_category": "hand_face", "verify_key": "touch_left_cheek",      "duration_sec": 3, "difficulty": 1},
    {"id": 148, "text": "Touch your right cheek",                    "category": "hand", "sub_category": "hand_face", "verify_key": "touch_right_cheek",     "duration_sec": 3, "difficulty": 1},
    {"id": 149, "text": "Cover your mouth with your hand",           "category": "hand", "sub_category": "hand_face", "verify_key": "cover_mouth",           "duration_sec": 3, "difficulty": 1},
    {"id": 150, "text": "Put your index finger on your lips (shh)",  "category": "hand", "sub_category": "hand_face", "verify_key": "finger_on_lips",        "duration_sec": 3, "difficulty": 2},
    {"id": 151, "text": "Frame your face with both hands",           "category": "hand", "sub_category": "hand_face", "verify_key": "frame_face",            "duration_sec": 3, "difficulty": 2},
    {"id": 152, "text": "Hold your hand beside your face (wave bye)", "category": "hand", "sub_category": "hand_face", "verify_key": "hand_beside_face",     "duration_sec": 3, "difficulty": 1},
    {"id": 153, "text": "Scratch your head",                         "category": "hand", "sub_category": "hand_face", "verify_key": "scratch_head",          "duration_sec": 3, "difficulty": 2},
    {"id": 154, "text": "Put both hands on your cheeks",             "category": "hand", "sub_category": "hand_face", "verify_key": "hands_on_cheeks",       "duration_sec": 3, "difficulty": 2},
    {"id": 155, "text": "Tap your forehead twice",                   "category": "hand", "sub_category": "hand_face", "verify_key": "tap_forehead",          "duration_sec": 3, "difficulty": 2},
    {"id": 156, "text": "Brush hair away from your face",            "category": "hand", "sub_category": "hand_face", "verify_key": "brush_hair",            "duration_sec": 3, "difficulty": 2},
    {"id": 157, "text": "Rest your chin on your fist",               "category": "hand", "sub_category": "hand_face", "verify_key": "chin_on_fist",          "duration_sec": 3, "difficulty": 2},
    {"id": 158, "text": "Stroke your chin thoughtfully",             "category": "hand", "sub_category": "hand_face", "verify_key": "stroke_chin",           "duration_sec": 3, "difficulty": 2},
    {"id": 159, "text": "Put hand over your heart",                  "category": "hand", "sub_category": "hand_face", "verify_key": "hand_on_heart",         "duration_sec": 3, "difficulty": 1},
    {"id": 160, "text": "Touch the bridge of your nose",             "category": "hand", "sub_category": "hand_face", "verify_key": "touch_nose_bridge",     "duration_sec": 3, "difficulty": 2},
    {"id": 161, "text": "Place palm flat on top of your head",       "category": "hand", "sub_category": "hand_face", "verify_key": "palm_on_head",          "duration_sec": 3, "difficulty": 1},
    {"id": 162, "text": "Pinch your nose",                           "category": "hand", "sub_category": "hand_face", "verify_key": "pinch_nose",            "duration_sec": 3, "difficulty": 2},
    {"id": 163, "text": "Rub your eyes gently",                      "category": "hand", "sub_category": "hand_face", "verify_key": "rub_eyes",              "duration_sec": 3, "difficulty": 2},
    {"id": 164, "text": "Pull your ear lobe gently",                 "category": "hand", "sub_category": "hand_face", "verify_key": "pull_ear",              "duration_sec": 3, "difficulty": 2},
    {"id": 165, "text": "Press your temples with fingertips",        "category": "hand", "sub_category": "hand_face", "verify_key": "press_temples",         "duration_sec": 3, "difficulty": 2},
    {"id": 166, "text": "Cover one eye and wave with other hand",    "category": "hand", "sub_category": "hand_face", "verify_key": "cover_eye_wave",        "duration_sec": 4, "difficulty": 3},
    {"id": 167, "text": "Touch your nose then your chin",            "category": "hand", "sub_category": "hand_face", "verify_key": "nose_then_chin",        "duration_sec": 4, "difficulty": 2},
    {"id": 168, "text": "Hold hand next to ear (listening pose)",    "category": "hand", "sub_category": "hand_face", "verify_key": "listening_pose",        "duration_sec": 3, "difficulty": 2},
    {"id": 169, "text": "Make glasses shape around eyes with fingers","category": "hand", "sub_category": "hand_face", "verify_key": "finger_glasses",       "duration_sec": 3, "difficulty": 3},

    # ─── COMPOUND SEQUENCES (170-184) ──────────────────────────────────
    {"id": 170, "text": "Smile then blink twice",                    "category": "face", "sub_category": "compound",  "verify_key": "smile_then_blink",      "duration_sec": 5, "difficulty": 2},
    {"id": 171, "text": "Nod then smile",                            "category": "face", "sub_category": "compound",  "verify_key": "nod_then_smile",        "duration_sec": 4, "difficulty": 2},
    {"id": 172, "text": "Turn right then blink",                     "category": "face", "sub_category": "compound",  "verify_key": "turn_right_blink",      "duration_sec": 4, "difficulty": 2},
    {"id": 173, "text": "Raise eyebrows then open mouth",            "category": "face", "sub_category": "compound",  "verify_key": "brows_then_mouth",      "duration_sec": 4, "difficulty": 2},
    {"id": 174, "text": "Close eyes and smile",                      "category": "face", "sub_category": "compound",  "verify_key": "close_eyes_smile",      "duration_sec": 4, "difficulty": 2},
    {"id": 175, "text": "Blink then turn left",                      "category": "face", "sub_category": "compound",  "verify_key": "blink_then_turn_left",  "duration_sec": 4, "difficulty": 2},
    {"id": 176, "text": "Shake head then smile",                     "category": "face", "sub_category": "compound",  "verify_key": "shake_then_smile",      "duration_sec": 4, "difficulty": 2},
    {"id": 177, "text": "Frown then raise eyebrows",                 "category": "face", "sub_category": "compound",  "verify_key": "frown_then_brows",      "duration_sec": 4, "difficulty": 2},
    {"id": 178, "text": "Open mouth wide then close and smile",      "category": "face", "sub_category": "compound",  "verify_key": "mouth_open_smile",      "duration_sec": 5, "difficulty": 2},
    {"id": 179, "text": "Blink, pause, blink again",                 "category": "face", "sub_category": "compound",  "verify_key": "blink_pause_blink",     "duration_sec": 4, "difficulty": 2},
    {"id": 180, "text": "Thumbs up then wave",                       "category": "hand", "sub_category": "compound",  "verify_key": "thumbs_then_wave",      "duration_sec": 5, "difficulty": 2},
    {"id": 181, "text": "Wave then peace sign",                      "category": "hand", "sub_category": "compound",  "verify_key": "wave_then_peace",       "duration_sec": 5, "difficulty": 2},
    {"id": 182, "text": "Touch nose then wave",                      "category": "hand", "sub_category": "compound",  "verify_key": "touch_nose_wave",       "duration_sec": 5, "difficulty": 2},
    {"id": 183, "text": "Show fist then open palm",                  "category": "hand", "sub_category": "compound",  "verify_key": "fist_then_palm",        "duration_sec": 4, "difficulty": 2},
    {"id": 184, "text": "Count 1-2-3 then thumbs up",               "category": "hand", "sub_category": "compound",  "verify_key": "count_then_thumbs",     "duration_sec": 5, "difficulty": 2},

    # ─── POSITIONING (185-199) ─────────────────────────────────────────
    {"id": 185, "text": "Bring your face closer to the camera",      "category": "face", "sub_category": "position",  "verify_key": "move_closer",           "duration_sec": 3, "difficulty": 1},
    {"id": 186, "text": "Move your face back from the camera",       "category": "face", "sub_category": "position",  "verify_key": "move_back",             "duration_sec": 3, "difficulty": 1},
    {"id": 187, "text": "Move your face to the left of the frame",   "category": "face", "sub_category": "position",  "verify_key": "face_left",             "duration_sec": 3, "difficulty": 1},
    {"id": 188, "text": "Move your face to the right of the frame",  "category": "face", "sub_category": "position",  "verify_key": "face_right",            "duration_sec": 3, "difficulty": 1},
    {"id": 189, "text": "Center your face in the frame",             "category": "face", "sub_category": "position",  "verify_key": "face_center",           "duration_sec": 3, "difficulty": 1},
    {"id": 190, "text": "Move face up in the frame",                 "category": "face", "sub_category": "position",  "verify_key": "face_up",               "duration_sec": 3, "difficulty": 1},
    {"id": 191, "text": "Move face down in the frame",               "category": "face", "sub_category": "position",  "verify_key": "face_down",             "duration_sec": 3, "difficulty": 1},
    {"id": 192, "text": "Lean forward then lean back",               "category": "face", "sub_category": "position",  "verify_key": "lean_forward_back",     "duration_sec": 4, "difficulty": 2},
    {"id": 193, "text": "Sway side to side slowly",                  "category": "face", "sub_category": "position",  "verify_key": "sway_side",             "duration_sec": 4, "difficulty": 2},
    {"id": 194, "text": "Move closer then wave",                     "category": "hand", "sub_category": "position",  "verify_key": "closer_then_wave",      "duration_sec": 5, "difficulty": 2},
    {"id": 195, "text": "Step to your left briefly",                 "category": "face", "sub_category": "position",  "verify_key": "step_left",             "duration_sec": 3, "difficulty": 2},
    {"id": 196, "text": "Step to your right briefly",                "category": "face", "sub_category": "position",  "verify_key": "step_right",            "duration_sec": 3, "difficulty": 2},
    {"id": 197, "text": "Move in a small circle on camera",          "category": "face", "sub_category": "position",  "verify_key": "circle_movement",       "duration_sec": 5, "difficulty": 3},
    {"id": 198, "text": "Move face to bottom-right corner",          "category": "face", "sub_category": "position",  "verify_key": "face_bottom_right",     "duration_sec": 3, "difficulty": 2},
    {"id": 199, "text": "Move face to top-left corner",              "category": "face", "sub_category": "position",  "verify_key": "face_top_left",         "duration_sec": 3, "difficulty": 2},
]


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

# Index for fast lookup
_INSTRUCTIONS_MAP: dict[int, dict] = {inst["id"]: inst for inst in INSTRUCTIONS}
_FACE_INSTRUCTIONS: list[dict] = [i for i in INSTRUCTIONS if i["category"] == "face"]
_HAND_INSTRUCTIONS: list[dict] = [i for i in INSTRUCTIONS if i["category"] == "hand"]


def get_instruction(instruction_id: int) -> Optional[dict]:
    """Get an instruction by ID."""
    return _INSTRUCTIONS_MAP.get(instruction_id)


def get_all_instructions() -> list[dict]:
    """Get all 200 instructions."""
    return INSTRUCTIONS


def pick_random_instructions(
    count: int = CHALLENGE_COUNT,
    categories: Optional[list[str]] = None,
    max_difficulty: int = 2,
) -> list[dict]:
    """
    Pick random instructions for an auth challenge.

    Default: 1 face + 1 hand instruction, difficulty ≤ 2.
    This ensures variety and tests both modalities.
    """
    if categories is None:
        categories = INSTRUCTION_CATEGORIES

    selected = []

    for cat in categories:
        if cat == "face":
            pool = [i for i in _FACE_INSTRUCTIONS if i["difficulty"] <= max_difficulty]
        elif cat == "hand":
            pool = [i for i in _HAND_INSTRUCTIONS if i["difficulty"] <= max_difficulty]
        else:
            pool = [i for i in INSTRUCTIONS if i["difficulty"] <= max_difficulty]

        if pool:
            selected.append(random.choice(pool))

    # If we need more, fill from any category
    while len(selected) < count:
        pool = [i for i in INSTRUCTIONS if i["difficulty"] <= max_difficulty and i not in selected]
        if not pool:
            break
        selected.append(random.choice(pool))

    return selected[:count]


def get_instruction_stats() -> dict:
    """Get statistics about the instruction database."""
    return {
        "total": len(INSTRUCTIONS),
        "face": len(_FACE_INSTRUCTIONS),
        "hand": len(_HAND_INSTRUCTIONS),
        "by_sub_category": {
            sub: len([i for i in INSTRUCTIONS if i["sub_category"] == sub])
            for sub in set(i["sub_category"] for i in INSTRUCTIONS)
        },
        "by_difficulty": {
            d: len([i for i in INSTRUCTIONS if i["difficulty"] == d])
            for d in [1, 2, 3]
        },
    }
