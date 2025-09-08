# Privacy & Security

## Data minimization
- **Default**: only pseudonymous user ID (Cognito sub) for owners; no mandatory email/phone
- **Optional contact info** requested only when tag is set to "lost" (purpose: notifications)
- **Explicit consent** for geolocation sharing; never mandatory

## Tokens & transport
- **Always HTTPS**; never embed sensitive data into QR/hash
- **One-Time Tokens** for message POST; short TTLs and single-use
- **Magic links** for owner notifications with short expiry
- **Session cookies** (httpOnly, Secure, SameSite) for rejoin; optional human-friendly rejoin key

## Abuse protection
- **Rate limiting** per tag/IP/user-agent; progressive soft CAPTCHA on threshold
- **In neutral ("not lost") state**: display-only page; inbox buffering without owner notification
- **Status-based gating**: messages only delivered to owner when tag marked as "lost"

## IP and logs
- **Treat IP addresses as personal data**; store only for security (rate limit/abuse)
- **Masked/hashed** with short retention
- **Keep security logs separate**; document retention windows clearly

## Deletion & TTL
- **DynamoDB TTL** on messages/sessions (e.g., 7–14 days for inactive, shorter for "not lost")
- **After case closure** or payment, schedule clean-up
- **Implement explicit deletion endpoints** where appropriate for user-requested deletion

## GDPR compliance
- **Privacy by Design**: minimal data collection, purpose limitation, storage minimization
- **Lawful basis**: legitimate interest for security; consent for optional features
- **Data subject rights**: access, rectification, erasure, portability (where applicable)
- **Documentation**: clear privacy policy, retention schedules, deletion procedures

## Navigation
- [← Flows](Flows.md) | [Roadmap →](Roadmap.md)
- [↑ Back to README](../../README.md)