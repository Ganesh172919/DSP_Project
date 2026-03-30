# Deployment

## Development Stack

Docker Compose starts:

- `frontend`
- `backend`
- `face-detection`
- `deepfake-detection`
- `database`
- `cache`
- `reverse-proxy`

Run:

```bash
docker compose up --build
```

## Kubernetes Starter

The repository includes starter manifests in `infra/k8s`. These are meant as a base, not a final hardened production deployment.

Production recommendations:

- Use a managed PostgreSQL offering or a separately hardened StatefulSet
- Put ML services on autoscaled CPU/GPU node pools
- Store secrets in Vault or cloud secret managers
- Terminate TLS at an Ingress controller with HSTS enabled
- Export metrics to Prometheus and dashboards to Grafana

## Environment Variables

Important backend variables:

- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `BIOMETRIC_MASTER_KEY`
- `FACE_SERVICE_URL`
- `RISK_SERVICE_URL`
- `CORS_ORIGINS`

## Hardening Checklist

- Move `SECRET_KEY` and `BIOMETRIC_MASTER_KEY` into managed secrets
- Enable TLS 1.3 and strong reverse-proxy headers
- Add request rate limiting by IP, account, and device fingerprint
- Replace in-process heuristic ML with calibrated ONNX or TorchServe models
- Add log shipping and alert thresholds for repeated PAD failures

