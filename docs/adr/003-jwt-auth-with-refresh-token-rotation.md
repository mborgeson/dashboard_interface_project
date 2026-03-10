# ADR-003: JWT authentication with refresh token rotation

## Status
Accepted

## Context
The dashboard needs stateless authentication that works with the SPA frontend (no server-side sessions). Tokens are stored in `localStorage`, not cookies, so CSRF is inherently mitigated. However, refresh tokens present a replay attack risk if intercepted -- a stolen refresh token could be used indefinitely to mint new access tokens.

## Decision
We implemented JWT access + refresh tokens with refresh token rotation and replay attack detection (`backend/app/api/v1/endpoints/auth.py`, `backend/app/core/security.py`, `backend/app/core/token_blacklist.py`).

Key mechanics:
- Each token carries a unique `jti` (JWT ID) claim for individual revocation.
- On refresh, the old refresh token's `jti` is blacklisted and a new refresh + access token pair is issued.
- If a blacklisted refresh token is reused (replay attack), ALL tokens for that user are revoked via `revoke_user_tokens()`.
- Token blacklist uses async Redis in production with automatic TTL expiration; falls back to in-memory dict for development.
- Logout blacklists the current access token's `jti` for its remaining TTL.
- Origin validation middleware provides defense-in-depth for state-changing requests.

## Consequences
- Refresh token rotation limits the window for stolen token exploitation to a single use.
- Replay attack detection (reuse = full revocation) forces attackers to race the legitimate user, which is detectable.
- Redis dependency in production adds an infrastructure requirement; the memory fallback keeps development simple.
- Token blacklist state is lost on process restart when using the memory backend (acceptable for development only).
