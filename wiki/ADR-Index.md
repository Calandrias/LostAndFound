# Architecture Decision Records (Index)

List of accepted decisions. New proposals are added as PRs under docs/adr.

- ADR-001: Authentication via Cognito with minimal scopes (use sub only; email optional at "lost")
- ADR-002: Data in DynamoDB with TTL; no mandatory personal fields
- ADR-003: Hosting model: S3 + CloudFront for frontend; API Gateway + Lambda for backend
- ADR-004: Anti-abuse: One-Time Tokens, rate-limiting, soft CAPTCHA
- ADR-005: Optional real-time over WebSocket; default polling for MVP
- ADR-006: Optional payments via hosted payment links; receipts via PSP

## Template (copy for new ADRs)
```
# ADR-XXX: Title
- Status: Proposed/Accepted/Deprecated
- Context: …
- Options considered: …
- Decision: …
- Consequences: …
- Links: …
```