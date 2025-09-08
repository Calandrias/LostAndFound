# Roadmap

## Phase 1 — MVP
- Astro static landing + minimal chat island (polling)
- API: GET/POST chat, validate OTT, store to DynamoDB with TTL
- Owner login (Cognito), simple inbox view
- Email notifications via SES when status is "lost"

## Phase 2 — Privacy/Security hardening
- Status gating ("not lost" vs. "lost") with inbox buffering
- One-Time Tokens, rate limits, soft CAPTCHA
- Session rejoin cookie + optional human-friendly rejoin key
- IP masking + retention policy

## Phase 3 — UX/Realtime
- WebSocket API for near real-time updates (optional)
- Optional geolocation button and presigned upload for photos
- Preferences for notifications (digest vs. instant)

## Phase 4 — Payments & Sponsors (optional)
- Payment links and webhook handling; "success fee" confirmation screen
- Sponsor link/button in UI; FUNDING.yml in repo

## Phase 5 — Polish & Docs
- ADRs finalized, diagrams, API reference
- Observability (logs, metrics, traces), alarms
- WAF/rate-limiting at edge (optional)