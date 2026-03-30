from app.services.challenge_engine import select_challenges


def test_challenge_selection_respects_count_and_uniqueness():
    challenges = select_challenges({}, count=3)
    assert len(challenges) == 3
    assert len({challenge["id"] for challenge in challenges}) == 3


def test_challenge_selection_can_exclude_head_turns():
    challenges = select_challenges({"no_head_turns": True}, count=3)
    assert all(challenge["category"] != "head" for challenge in challenges)

