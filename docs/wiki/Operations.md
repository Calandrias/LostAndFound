# Operations

## CI/CD

### Frontend Pipeline
- **Build**: `npm run build` (Astro) → static artifacts in `dist/`
- **Deploy**: Upload to S3 → CloudFront invalidation
- **Triggers**: Push to `main`, PR for staging

### Infrastructure Pipeline  
- **Build**: CDK synth/deploy with OIDC to AWS
- **Stacks**: api, auth, data, sfn (optional), web
- **Triggers**: Changes in `infra/` directory

### Best Practices
- Keep artifacts retention low (7-14 days)
- Prefer Linux runners for cost efficiency
- Cache dependencies prudently (`node_modules`, CDK assets)
- Use OIDC instead of long-lived AWS keys

## Observability

### Logging
- Structured logging with correlation IDs
- Lambda Powertools for consistent format
- CloudWatch Logs with retention policies

### Monitoring
- Custom metrics: latency, errors, throttles  
- SES bounce/complaint tracking
- DynamoDB throttles and consumed capacity

### Alerting
- Error rates above threshold
- High latency (p99 > 2s)
- SES bounces/complaints
- DynamoDB throttles

## Cost Controls

### Data Lifecycle
- Use DynamoDB TTL for automatic cleanup
- Avoid long-running workflows (prefer event-driven)
- Monitor RCU/WCU consumption

### Notifications
- Email first (SES ~$0.10/1000) 
- SMS only for critical cases (SNS ~$0.75/100 in US)
- Implement digest options to reduce volume

### Compute
- Prefer polling for MVP; add WebSockets only if needed
- Monitor GitHub Actions minutes/storage usage
- Use ARM64 Lambdas where possible (20% cost reduction)

## Security Hygiene

### IAM & Access
- Least-privilege IAM roles
- No long-lived secrets in CI (use OIDC)
- Separate environments (dev/staging/prod)

### Transport & Headers
- HTTPS everywhere, HTTP→HTTPS redirects
- CSP and security headers in CloudFront
- HSTS, X-Frame-Options, X-Content-Type-Options

### Input Validation
- Validate inputs strictly at API boundaries
- Sanitize message content (XSS prevention)
- Enforce size limits on uploads (if implemented)
- Rate limiting at multiple layers

### Secrets Management
- AWS Secrets Manager for API keys
- Parameter Store for configuration
- Rotate secrets regularly

## Navigation
- [← ADR Index](ADR-Index.md)
- [↑ Back to README](../../README.md)