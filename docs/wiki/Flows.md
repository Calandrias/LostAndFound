# Core Flows

## Scan QR
1. `GET /t/{hash}` → resolve tagId → fetch tag status
2. If `not_lost` → show neutral page (no contact), optionally "Report anyway" guarded by token/CAPTCHA
3. If `lost` → show minimal contact form or chat island

## Send message (finder)
1. Render short form: message (+ optional location on consent)
2. Client requests One-Time Token (OTT) for POST
3. `POST /chat/{sessionId}` with OTT → store message (TTL) → if tag is lost: notify owner; else inbox-only

## Owner response
1. Owner logs in via IdP (Cognito hosted UI); minimal scopes (pseudonymous sub)
2. Owner UI shows inbox by sessionId; reply posts message via admin API
3. Owner may selectively reveal contact channel (relay stays default)

## Status switching

### "Not lost" → "Lost"
- Prompt to add optional email for notifications
- Deliver buffered messages and enable notifications

### "Lost" → "Recovered" 
- Disable further push notifications
- Schedule TTL cleanup

## Payments / Donations (optional)

### Success-based payment
- After confirmed recovery, show "Success fee" payment link in owner UI
- Webhook marks case as "paid"; schedule TTL and generate receipt if billing details provided

### Voluntary donations
- GitHub Sponsors link/button available in UI
- No payment enforcement; purely voluntary support

## Navigation
- [← Architecture](Architecture.md) | [Privacy & Security →](Privacy-Security.md)
- [↑ Back to README](../../README.md)