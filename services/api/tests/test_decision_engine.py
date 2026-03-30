from app.services.decision_engine import build_stage_results


def test_decision_engine_requires_all_stages_to_pass():
    stages, passed, aggregate, anomalies = build_stage_results(
        face_score=0.9,
        pad_score=0.95,
        recognition_score=0.92,
        feature_score=0.91,
        liveness_score=0.35,
        deepfake_score=0.93,
        anomalies=[],
    )
    assert passed is False
    assert aggregate < 0.88 or any(stage.stage == "liveness" and not stage.passed for stage in stages)
    assert anomalies


def test_decision_engine_approves_high_confidence_path():
    stages, passed, aggregate, anomalies = build_stage_results(
        face_score=0.92,
        pad_score=0.95,
        recognition_score=0.96,
        feature_score=0.92,
        liveness_score=0.9,
        deepfake_score=0.93,
        anomalies=[],
    )
    assert passed is True
    assert aggregate >= 0.88
    assert stages[-1].stage == "decision"
    assert not anomalies
