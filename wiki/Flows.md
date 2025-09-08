# Core Flows

## Scan QR
- GET /t/{hash} → resolve tagId → fetch tag status
- If not_lost → show neutral page (no contact), optionally "Report anyway" guarded by token/CAPTCHA
- If lost → show minimal contact form or chat island

## Send message (finder)
- Render short form: message (+ optional location on consent)
- Client requests One-Time Token (OTT) for POST
- POST /chat/{sessionId} with OTT → store message (TTL) → if tag is lost: notify owner; else inbox-only

## Owner response
- Owner logs in via IdP (Cognito hosted UI); minimal scopes (pseudonymous sub)
- Owner UI shows inbox by sessionId; reply posts message via admin API
- Owner may selectively reveal contact channel (relay stays default)

## Status switching
- "Not lost" → "Lost": prompt to add optional email for notifications; deliver buffered messages and enable notifications
- "Lost" → "Recovered": disable further push notifications; schedule TTL cleanup

## Payments / Donations (optional)
- After confirmed recovery, show "Success fee" payment link or donation link in owner UI
- Webhook marks case as "paid"; schedule TTL and generate receipt if billing details provided