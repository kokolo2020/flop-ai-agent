# ComputePilot — AI Agent Testnet Readiness (2026-10-25)

Scope: **AI agent / compute buyer only**. No miner, GPU rental, validator, or hardware operations.

## Verified official references
- https://flop.finance/official/ (updated 2026-10-23)
- https://flop.finance/testnet/
- https://flop.finance/airdrop/
- https://flop.finance/intro/yellowpaper/

## Status gates
- Public testnet: **NOT CONFIRMED LIVE**. 2026-11-03 is a *working target*, not a launch commitment.
- Devnet: named endpoints at api.flop.network, mcp.flop.network, faucet.flop.network, rpc.devnet.flop.network; endpoint existence, API schema, authentication and actual operability MUST be verified before use.
- Wallet / DID: no keys committed or entered into the browser; require official supported formats and signing instructions.
- Test tokens: no monetary value; devnet usage earns no airdrop weight.
- Airdrop: provisional agent pool; only genuine independent compute purchases in finalized, settled sessions count, subject to minimums and anti-Sybil rules.
- Never infer eligibility from DID creation, faucet grants, simulated receipts, test prompts or unsigned logs.

## Agent-only implementation plan
1. Read-only discovery: verify official HTTPS origin, health, published schema, chain ID, and protocol version. Reject mismatches; do not blindly connect.
2. DID / wallet readiness: support verified DID and wallet binding with OS-protected secrets; no signing or funds until explicit operator approval.
3. Faucet adapter: opt-in only after official onboarding documentation is published; rate-limit and record grant without marking it as earned.
4. Inference buyer: bounded provider discovery, request validation, explicit per-session budget, retry/idempotency, timeouts, and no self-dealing.
5. Settlement verifier: correlate request ID, independent provider, finalized chain receipt, escrow/claim state, paid amount, and dispute/finality status. Keep UNSUBMITTED, SUBMITTED, SERVED, SETTLEMENT_PENDING, FINALIZED, FAILED distinct.
6. Quality auditor: record latency, cost, content checks and independent audit outcome separately from protocol verification.
7. Evidence export: reproducible signed metadata when supported; never fabricate on-chain proofs or reward totals.
8. Mobile dashboard: distinct DEVNET / TESTNET / SIMULATION banners; network and reward status must fail closed on unknowns.

## Launch acceptance checklist
- Official testnet launch announced at flop.finance/official or verified @flop_labs.
- Official agent onboarding, DID, wallet, faucet and RPC/API schemas published.
- A genuinely independent paid inference completes and its settlement can be independently verified.
- Rate limits, spend ceilings, identity protection and anti-Sybil checks pass.
- No autonomous paid operation before explicit approval.

## Repository caution
This branch starts from main. The existing `computepilot-v12-a40-test` branch is miner-oriented and MUST NOT be merged into this agent-only workstream by default. Existing V10.3 deployed code has not been independently reconciled with main; do not claim deployment or feature parity until that audit is complete.
