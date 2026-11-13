# FLOP agent integration

Entry: /flop-agent.html. Handler: /.netlify/functions/flop-agent.

## Deployment configuration

Set server-only Netlify function environment variables:
- COMPUTEPILOT_ACCESS_TOKEN: private app access gate, never a provider key.
- FLOP_API_KEY: an active bounded child or wallet credential. Do not host an owner key, wallet seed, or signer.
- FLOP_MODEL: exact advertised model slug allowed by that credential.

No secrets are included in this repository. With no app access token the handler stays disabled. The current Netlify project has no environment variables configured (verified November 13, 2026). Existing local FLOP allowance is expired; deployment alone cannot renew it. FLOP's issuer must grant working access. Do not create wallets to bypass issuer limits.

## Behavior and limits

One non-streaming completion per task; 1000 input characters and 64 output tokens. Checks healthy devnet genesis, bounded credential expiry/quota and model availability first. Never falls back to a paid provider. No tool execution, mining, enrollment, funding or automated retries.

The browser saves an unresolved request UUID before submission and blocks new tasks until the exact receipt is terminal or the server confirms no submission occurred. This is per-browser protection, not a global task queue; don't open simultaneous sessions or clear storage while work is unresolved. POST and receipt GET carry the same original request ID. Timeout/404 do not establish that no work occurred. API errors never echo raw credential-bearing responses.

Ledger `settled`/`released` is current gateway evidence, not independent on-chain finality or proof of earnings. Receiving text is displayed separately. Evidence download contains sanitized output and receipt only. Preserve downloads before closing; this release has no server-side output archive.

## Verification

Run `node --test tests/flop-agent.test.cjs` (10 scenarios) and `node --check public/flop-agent.js`.
Mock tests cover auth, network identity, missing/expired/owner credentials, one bounded POST, overload, timeout ambiguity, exact receipt matching and read-only recovery. Live paid inference remains unverified until an active bounded key is configured.

Contract: https://flop.network/llms.txt and https://api.flop.network/openapi.json (read November 13, 2026).
