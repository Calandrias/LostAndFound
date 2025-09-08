# Privacy & Security

## Data minimization
- Default: only pseudonymous user ID (Cognito sub) for owners; no mandatory email/phone
- Optional contact info requested only when tag is set to "lost" (purpose: notifications)

## Tokens & transport
- Always HTTPS; never embed sensitive data into QR/hash
- One-Time Tokens for message POST; short TTLs and single-use
- Magic links for owner notifications with short expiry

## Abuse protection
- Rate limiting per tag/IP/user-agent; progressive soft CAPTCHA on threshold
- In neutral ("not lost") state: display-only page; inbox buffering without owner notification
- Session cookies (httpOnly, Secure, SameSite) for rejoin; optional human-friendly rejoin key

## IP and logs
- Treat IP addresses as personal data; store only for security (rate limit/abuse), masked/hashed with short retention
- Keep security logs separate; document retention windows

## Deletion & TTL
- DynamoDB TTL on messages/sessions (e.g., 7–14 days for inactive, shorter for "not lost")
- After case closure or payment, schedule clean-up; implement explicit deletion endpoints where appropriate