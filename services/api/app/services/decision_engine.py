"""Decision engine — multi-stage weighted scoring with adaptive thresholds.

Consumes scores from face detection, PAD, recognition, feature verification,
liveness, and deepfake scanning to produce a final authenticate/deny decision
with detailed reasoning.
"""

from __future__ import annotations

from typing import Any


# ── Stage configuration ──

STAGE_CONFIG = {
    "face_detection": {
        "weight": 0.08,
        "threshold": 0.45,
        "label": "Face Detection",
        "fail_message": "Face not reliably detected in frame",
    },
    "presentation_attack_detection": {
        "weight": 0.18,
        "threshold": 0.50,
        "label": "Presentation Attack Detection",
        "fail_message": "Frame shows signs of spoofing (screen, photo, or mask)",
    },
    "recognition": {
        "weight": 0.25,
        "threshold": 0.60,
        "label": "Facial Recognition Match",
        "fail_message": "Face geometry does not match enrolled template",
    },
    "feature_verification": {
        "weight": 0.10,
        "threshold": 0.55,
        "label": "Granular Feature Verification",
        "fail_message": "Biometric feature comparison below confidence threshold",
    },
    "liveness": {
        "weight": 0.22,
        "threshold": 0.45,
        "label": "Liveness Verification",
        "fail_message": "Challenge-response liveness verification incomplete or failed",
    },
    "deepfake_scan": {
        "weight": 0.17,
        "threshold": 0.45,
        "label": "Deepfake Scan",
        "fail_message": "Frame shows indicators of synthetic generation",
    },
}

AGGREGATE_THRESHOLD = 0.62
ANOMALY_REVIEW_THRESHOLD = 0.78  # Even if passed, flag for review if below this


def build_stage_results(
    face_score: float = 0.0,
    pad_score: float = 0.0,
    recognition_score: float = 0.0,
    feature_score: float = 0.0,
    liveness_score: float = 0.0,
    deepfake_score: float = 0.0,
    anomalies: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Build structured stage results with pass/fail for each stage."""
    scores = {
        "face_detection": face_score,
        "presentation_attack_detection": pad_score,
        "recognition": recognition_score,
        "feature_verification": feature_score,
        "liveness": liveness_score,
        "deepfake_scan": deepfake_score,
    }

    results = []
    for stage_key, config in STAGE_CONFIG.items():
        score = scores.get(stage_key, 0.0)
        passed = score >= config["threshold"]
        message = "Stage passed" if passed else config["fail_message"]

        # Add score context
        detail = f" (score: {score:.3f}, threshold: {config['threshold']:.2f})"
        message += detail

        results.append({
            "stage": stage_key,
            "label": config["label"],
            "score": round(score, 4),
            "weight": config["weight"],
            "threshold": config["threshold"],
            "passed": passed,
            "message": message,
        })

    return results


def compute_decision(
    stage_results: list[dict[str, Any]],
    anomalies: list[str] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute the final authentication decision.

    Uses:
    1. All-pass gate: every individual stage must meet its threshold
    2. Weighted aggregate: must exceed AGGREGATE_THRESHOLD
    3. Anomaly check: even passing scores get flagged if anomalies exist

    Context can include:
    - device_known: bool — is this a previously-seen device?
    - time_of_day: str — for contextual risk adjustment
    - consecutive_failures: int — recent failure count
    """
    all_anomalies = list(anomalies or [])
    ctx = context or {}

    # Gate 1: All stages must pass individually
    all_passed = all(r["passed"] for r in stage_results)

    # Gate 2: Weighted aggregate
    aggregate = sum(
        r["score"] * r["weight"] for r in stage_results
    )
    total_weight = sum(r["weight"] for r in stage_results)
    if total_weight > 0:
        aggregate /= total_weight
    aggregate = round(aggregate, 4)
    aggregate_passed = aggregate >= AGGREGATE_THRESHOLD

    # Contextual adjustments
    adjusted_threshold = AGGREGATE_THRESHOLD
    if ctx.get("consecutive_failures", 0) >= 3:
        adjusted_threshold += 0.015
        all_anomalies.append(f"Threshold raised slightly due to {ctx['consecutive_failures']} recent failures")

    aggregate_passed = aggregate >= adjusted_threshold

    # Final decision
    authenticated = all_passed and aggregate_passed

    # Even if authenticated, flag for review if borderline
    needs_review = False
    if authenticated:
        if aggregate < ANOMALY_REVIEW_THRESHOLD:
            needs_review = True
            all_anomalies.append("Authentication approved but borderline — flagged for review")
        if len(all_anomalies) >= 2:
            needs_review = True

    # Determine denial reasons
    denial_reasons: list[str] = []
    if not all_passed:
        failed_stages = [r for r in stage_results if not r["passed"]]
        for fs in failed_stages:
            denial_reasons.append(f"{fs['label']}: {fs['message']}")
    if not aggregate_passed:
        denial_reasons.append(
            f"Aggregate score {aggregate:.4f} below threshold {adjusted_threshold:.2f}"
        )

    # Build reasoning trace
    reasoning = {
        "individual_gates_passed": all_passed,
        "aggregate_score": aggregate,
        "adjusted_threshold": adjusted_threshold,
        "aggregate_passed": aggregate_passed,
        "authenticated": authenticated,
        "needs_review": needs_review,
        "denial_reasons": denial_reasons,
        "anomaly_count": len(all_anomalies),
        "stage_breakdown": {
            r["stage"]: {
                "score": r["score"],
                "weight": r["weight"],
                "weighted_contribution": round(r["score"] * r["weight"], 4),
                "passed": r["passed"],
            }
            for r in stage_results
        },
    }

    return {
        "authenticated": authenticated,
        "final_score": aggregate,
        "stage_results": stage_results,
        "anomalies": all_anomalies,
        "reasoning": reasoning,
        "needs_review": needs_review,
    }
