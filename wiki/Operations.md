# Operations

## CI/CD
- Frontend: build Astro → upload to S3 → CloudFront invalidation
- Infra: CDK synth/deploy with OIDC to AWS; stacks: api, auth, data, sfn (optional), web
- Keep artifacts retention low; prefer Linux runners; cache dependencies prudently

## Observability
- Structured logging and correlation IDs
- Tracing (where relevant) and custom metrics (latency, errors, throttles)
- Alarms on error rates, latency, throttles, and SES bounces

## Cost controls
- Use DynamoDB TTL for data lifecycle; avoid long-running workflows
- Prefer polling for MVP; add WebSockets only if needed
- Email first (SES), SMS only for critical cases; monitor Actions minutes/storage

## Security hygiene
- Least-privilege IAM; no long-lived secrets in CI (use OIDC)
- HTTPS everywhere; CSP and security headers
- Validate inputs strictly; sanitize message content; enforce size limits on uploads