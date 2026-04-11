# Evaluation And Reporting

This document explains how to report results without overstating the system's current validation level.

## Current State

The repository records per-attempt runtime scores, but it does not include a committed dataset-backed benchmark table. Therefore documentation and presentations should avoid fixed claims such as:

- accuracy percentage
- FAR
- FRR
- EER
- AUC
- production latency guarantees

Those values should be generated from a known dataset and committed as a separate result table.

## Runtime Scores Available

Every authentication attempt can produce:

| Score | Meaning |
| --- | --- |
| `similarity` | ArcFace cosine similarity against the registered template. |
| `liveness` | Fused liveness score. |
| `deepfake` | Estimated synthetic/manipulation probability. Lower is better. |
| `injection` | Anti-injection confidence when that layer is active. |
| `instruction_scores` | Optional challenge confidence values. |
| `processing_time_ms` | Backend processing duration. |
| `threat_flags` | Flags such as `no_face`, `liveness_fail`, `synthetic_face`, or `identity_mismatch`. |

VLM authentication can additionally return:

- VLM identity confidence.
- VLM liveness confidence.
- VLM authenticity confidence.
- VLM overall score.
- VLM natural-language reasoning.
- VLM override status.
- VLM model used.

## Evaluation Script

The repository includes:

```text
backend/training/evaluate.py
```

Suggested command:

```powershell
cd backend
python -m training.evaluate --data_root data/test --weights_dir weights --model all
```

The evaluation script is intended to support metrics such as:

- AUC-ROC
- FAR
- FRR
- EER
- precision
- recall
- F1
- mean latency
- p95 latency

## Suggested Dataset Layout

Use a clearly labeled evaluation folder. A practical local structure could be:

```text
backend/data/test/
|-- live/
|-- photo_spoof/
|-- screen_replay/
|-- deepfake/
`-- mismatch/
```

For final reporting, document the dataset source, user count, sample count, camera type, lighting conditions, attack types, train/test separation, model weights, and threshold values.

## Report Table Template

Use a table like this only after running evaluation:

| Model path | Dataset split | AUC | EER | FAR @ threshold | FRR @ threshold | F1 | Mean latency | p95 latency |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Traditional video | `data/test` | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| VLM hybrid | `data/test` | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## Presentation Guidance

Safe claims:

- The system returns multiple score types for each attempt.
- The system stores audit logs for later analysis.
- The architecture is designed for multi-layer defense.
- Benchmark numbers should be generated from a controlled dataset.

Avoid claiming:

- The system is production-ready.
- The system detects all deepfakes.
- The VLM can always identify spoofing.
- A fixed accuracy value unless backed by a committed benchmark.

## Recommended Next Evaluation Work

1. Create a small controlled evaluation set with live, photo, screen replay, mismatch, and synthetic samples.
2. Run traditional video authentication over the set.
3. Run VLM hybrid authentication over the same set if hardware permits.
4. Export raw per-attempt scores.
5. Compute metrics and confusion matrices.
6. Add a results markdown file under `docs/`.
7. Revisit thresholds only after looking at score distributions.

