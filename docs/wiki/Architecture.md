# Architecture

## Overview
- **Frontend**: Astro (static) with small interactive islands for chat/forms. Deployed to S3 + CloudFront.
- **Backend**: API Gateway (HTTP) → Lambda (public/admin) → DynamoDB (messages/sessions, with TTL). Optional Step Functions for time-based orchestration.
- **Auth**: Cognito User Pool with minimal scopes; external IdPs (Amazon, Google; optionally Apple/Microsoft/GitHub via OIDC). Finder is guest; Owner authenticates.
- **Notifications**: Email via SES; optional SMS via SNS.

## Repository structure (proposed)
```
├── frontend/          # Astro app (chat island, landing pages), static build artifacts
├── runtime/
│   ├── public/        # finder-facing Lambdas (message create, session handling)
│   ├── owner/         # owner-facing Lambdas (reply, status, preferences)
│   ├── shared/        # common utils, schema validation, auth middleware
│   └── admin/         # admin-facing Lambdas (auditing, configuration, performance logs)
├── infra/
│   ├── stacks         # cdk stacks, split by responsibility zones (ui, )
├── docs/
│   ├── wiki/          # project documentation (this)
│   └── adr/           # ADRs and architectural docs (docs-as-code)
└── .github/workflows/ # CI/CD pipelines

 
```

## Data model (DynamoDB)

### Table: messages
- **PK**: sessionId
- **SK**: ts (ISO or epoch)
- **Attributes**: text, sender ("finder"|"owner"), status, optional location {lat, lon, acc}, expiresAt (TTL)

### Table: tags
- **PK**: tagId (hash in QR)
- **Attributes**: status ("not_lost"|"lost"), ownerSub, createdAt, updatedAt

## Integration points
- **Geolocation**: client consent-driven, HTTPS only
- **File uploads**: presigned S3 URLs with strict MIME/size checks
- **Payments** (optional): payment links via PSP (e.g., Stripe), webhooks to mark "paid"
- **Sponsors** (optional): GitHub Sponsors link/button in UI

## Navigation
- [← Home](Home.md) | [Flows →](Flows.md)
- [↑ Back to README](../../README.md)