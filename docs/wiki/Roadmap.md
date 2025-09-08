# Roadmap

## Phase 1 — MVP ⏳
**Goal**: Basic working service with core privacy protections

- Astro static landing + minimal chat island (polling)
- API: GET/POST chat, validate OTT, store to DynamoDB with TTL
- Owner login (Cognito), simple inbox view
- Email notifications via SES when status is "lost"
- Basic status switching ("not lost" ↔ "lost")

**Estimated**: 4-6 weeks for single developer

## Phase 2 — Privacy/Security hardening 🔒
**Goal**: Production-ready privacy and abuse protection

- Status gating ("not lost" vs. "lost") with inbox buffering
- One-Time Tokens, rate limits, soft CAPTCHA
- Session rejoin cookie + optional human-friendly rejoin key
- IP masking + retention policy
- GDPR compliance documentation

**Estimated**: 2-3 weeks

## Phase 3 — UX/Realtime 🚀
**Goal**: Enhanced user experience and real-time features

- WebSocket API for near real-time updates (optional)
- Optional geolocation button and presigned upload for photos
- Preferences for notifications (digest vs. instant)
- Mobile-optimized UI improvements

**Estimated**: 3-4 weeks

## Phase 4 — Payments & Sponsors (optional) 💝
**Goal**: Sustainable funding model

- Payment links and webhook handling; "success fee" confirmation screen
- Sponsor link/button in UI; FUNDING.yml in repo
- Receipt generation and basic accounting exports

**Estimated**: 2-3 weeks

## Phase 5 — Polish & Docs 📚
**Goal**: Community-ready open source project

- ADRs finalized, diagrams, API reference
- Observability (logs, metrics, traces), alarms
- WAF/rate-limiting at edge (optional)
- Comprehensive setup guides and deployment docs

**Estimated**: 2-3 weeks

## Total estimated effort
**16-22 weeks** for complete implementation by single developer working part-time

## Navigation
- [← Privacy & Security](Privacy-Security.md) | [ADR Index →](ADR-Index.md)
- [↑ Back to README](../../README.md)