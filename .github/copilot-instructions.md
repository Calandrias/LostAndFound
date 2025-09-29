# Copilot Instructions for Lost & Found

## Project Overview
- **Lost & Found** is a privacy-first QR tag service for lost property, emphasizing anonymous contact, minimal data retention, and user consent.
- The system is composed of a static frontend (Astro), AWS Lambda-based backend (public/admin/owner), and infrastructure-as-code (CDK in Python).
- Documentation is centralized in `docs/wiki/` (see `Architecture.md`, `Flows.md`, `Privacy-Security.md`).

## Key Components & Structure
- `frontend/`: Astro static app (not present in repo yet)
- `runtime/`:
  - `shared/`: Common models, validation, and utilities (e.g., `owner_model.py`, `session_store.py`)
- `infra/`: AWS CDK stacks (Python) for deploying API Gateway, Lambdas, DynamoDB, Cognito, etc.
- `models/`: OpenAPI specs and DB schemas
- `docs/wiki/`: Project documentation, architecture, flows, and ADRs

## Developer Workflows
- **Infrastructure**: Use `cdk synth`, `cdk deploy`, and `cdk diff` from `infra/` (see `infra/README.md`).
- **Lambdas**: Each handler is a Python module; shared logic in `runtime/shared/`. Testable as plain Python functions.
- **Testing**: Pytest is used; tests are in `runtime/tests/`.
- **Environment**: Use a Python 3.12+ virtualenv. Install dependencies from `requirements.txt` or `requirements-dev.txt`.
- **Data Models**: DynamoDB tables for `messages` (sessionId, ts, sender, status, location, TTL) and `tags` (tagId, status, ownerSub, timestamps).

## Project Conventions
- **Privacy by Design**: Never log or persist PII beyond what is strictly required. Use pseudonymous IDs.
- **Status-driven Messaging**: Messages are buffered and only delivered when tag status is "lost".
- **Minimal Owner Auth**: Owners authenticate via Cognito; finders are always guests.
- **Schema Validation**: Use shared models in `runtime/shared/` for all data validation and serialization.
- **Infrastructure as Code**: All AWS resources are defined in `infra/` using CDK Python stacks.

## Integration & Patterns
- **External Services**: Email via SES, optional SMS via SNS, payments via Stripe (future), file uploads via presigned S3 URLs.
- **Cross-component Communication**: API Gateway routes to Lambda handlers; shared code in `runtime/shared/`.
- **Documentation-first**: All major flows and decisions are documented in `docs/wiki/`.

## Examples
- To add a new Lambda handler: create a module in `runtime/public/` or `runtime/owner/`, use models from `runtime/shared/`, and update infra as needed.
- To update the data model: edit schemas in `models/` and update shared models in `runtime/shared/`.

## References
- [docs/wiki/Architecture.md](../docs/wiki/Architecture.md)
- [infra/README.md](../infra/README.md)
- [runtime/shared/](../runtime/shared/)

---
For questions or unclear conventions, check the wiki or ask for clarification in issues.
