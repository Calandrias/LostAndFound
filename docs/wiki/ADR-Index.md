# ADR Index

> Architecture Decision Records are stored in `docs/adr/`.  
> This index provides a summary and status overview.

---

## Active ADRs

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| ADR-001 | Use DynamoDB as primary data store | ✅ Accepted | – |
| ADR-002 | Privacy-first: no email/name required | ✅ Accepted | – |
| ADR-003 | owner_hash as pseudonymous identifier | ✅ Accepted | – |
| ADR-004 | Lambda + API Gateway over containers | ✅ Accepted | – |
| ADR-005 | AWS CDK (Python) as IaC framework | ✅ Accepted | – |
| ADR-006 | Mono-repo structure | ✅ Accepted | – |
| ADR-007 | SRP (RFC 5054) vs Cognito → SRP | ✅ Accepted | – |
| ADR-008 | Key derivation parameters (PBKDF2) | 🔲 To be written | – |
| ADR-009 | E2EE roadmap (Phase 1→3) | 🔲 To be written | – |
| ADR-010 | Frontend stack (Astro + Preact) | 🔲 To be written | – |

---

## New ADRs (from v2 refactor)

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| ADR-011 | AWS Lambda Powertools as routing/validation framework | ✅ Accepted | 2026-03-26 |
| ADR-012 | 3-stack CDK layout (Database / API / UI) | ✅ Accepted | 2026-03-26 |
| ADR-013 | CloudFront + S3 OAC for frontend (no public bucket) | ✅ Accepted | 2026-03-26 |
| ADR-014 | OpenAPI spec as generated output (not maintained input) | ✅ Accepted | 2026-03-26 |
| ADR-015 | GitHub Actions OIDC for AWS auth (no static keys) | ✅ Accepted | 2026-03-26 |
| ADR-016 | Zone-based mypy strictness (strict own code, overrides for 3rd party) | ✅ Accepted | 2026-03-26 |
| ADR-017 | Lambda Layer build without Docker (manylinux wheels + pip --only-binary) | ✅ Accepted | 2026-03-26 |

---

## Decision: No Cognito (ADR-007)

Cognito requires an email address or phone number for account creation, which directly
violates the Zero-Knowledge privacy principle of this platform. SRP (RFC 5054) with
PBKDF2-HMAC-SHA256 key derivation is implemented entirely in the Lambda layer.
This keeps the server from ever seeing plaintext credentials or real identifiers.

## Decision: Powertools over custom routing (ADR-011)

The v1 codegen pipeline (3 scripts + ABC + handler impl + templates) is replaced
by AWS Lambda Powertools `APIGatewayRestResolver` + `Router`. Benefits:
- Pydantic validation is automatic (no manual `model_validate_json`)
- OpenAPI spec is generated directly from route definitions
- Standard observability (Logger, Tracer, Metrics) is built-in
- No generated code to maintain or regenerate

## Decision: 3-stack CDK layout (ADR-012)

`DatabaseStack` is isolated from `ApiStack` so that `cdk destroy` on the API
never risks touching data. `RemovalPolicy.RETAIN` on all tables provides a
second layer of protection. `UIStack` is independent to allow frontend-only
redeployments without touching backend resources.
