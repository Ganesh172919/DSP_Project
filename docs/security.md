# Security Documentation

## Threat Model

Primary threats in scope:

- Printed photo attacks
- Screen replay attacks
- Real-time deepfake and virtual camera attacks
- 3D mask and presentation attacks
- Template theft and biometric database compromise
- API abuse, brute force, and replay of stale challenge evidence

## Controls Implemented

### Data Protection

- AES-256-GCM style authenticated encryption for biometric templates
- Template integrity hashing
- Separation of password hashes and encrypted biometric payloads
- Database-ready schema for audit records and attempt histories

### Authentication Pipeline Controls

- Single-face expectation and face quality gating
- Passive PAD scoring using sharpness, exposure, spectral balance, and moire-like anomaly checks
- Template comparison using deterministic geometric embeddings
- Randomized challenge-response selection with accessibility filtering
- Fail-secure decision engine: one failed stage blocks approval

### Operational Controls To Add For Production

- KMS-backed key wrapping and rotation
- Redis-backed nonce issuance and challenge replay prevention
- JWT access and refresh token rotation
- IP, session, and identity claim rate limiting
- Proxy-layer CSP, HSTS, X-Frame-Options, and strict cookie settings
- Immutable log shipping to SIEM

## Attack Surface Analysis

### Browser Capture Surface

Risk:

- Virtual webcams
- Injected prerecorded streams
- DOM tampering

Mitigations:

- Device fingerprinting and allow/deny lists
- Frame timing consistency checks
- Browser integrity hints and server-side verification

### API Surface

Risk:

- Flooding and replay
- Tampered JSON payloads
- Enumeration of registered users

Mitigations:

- Schema validation
- Audit logging
- Future rate-limiting middleware
- Generic error messages for identity claim failures

### Data Layer

Risk:

- Template exfiltration
- Insider misuse

Mitigations:

- Encrypted templates
- Principle-of-least-privilege DB roles
- Time-bound audit retention with controlled access

## Incident Response Outline

1. Isolate suspicious user IDs, sessions, and IP/device clusters.
2. Export related audit events and frame-derived evidence.
3. Force re-enrollment or temporary lockout for impacted identities.
4. Rotate application secrets and KMS-wrapped material if compromise is suspected.
5. Patch detection thresholds or models, then replay retained samples through the offline evaluation pipeline.

