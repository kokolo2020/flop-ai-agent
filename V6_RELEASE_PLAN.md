# ComputePilot V6 — consolidated release plan

Status: planning only. Branch: computepilot-v6 (from computepilot-v5).
Do not deploy, enable live API calls, or claim FLOP eligibility until gates pass.

## Objective
Build a provider-agnostic inference and audit agent, with verifiable receipts and a verified FLOP protocol adapter where official documentation supports it. Do not conflate OpenAI usage with FLOP activity.

## Requirements
1. Research official FLOP documentation and testnet interfaces; document citations, authentication, DID requirements, transaction and settlement proofs, and eligibility uncertainties. No speculative integration.
2. Provider abstraction: simulation, paid OpenAI, FLOP adapter (disabled unless independently verified).
3. Atomic durable budget ledger: USD $5 per Asia/Bangkok calendar day, covering inference + audit, with concurrency-safe preauthorization and reconciliation. Conservative upper-bound reservation; fail closed if price is unknown, budget backend unavailable, or reservation fails. Explicitly disclose that this cannot cap other OpenAI projects or account spending.
4. Authenticated API, server-side secrets, rate limiting, request IDs and idempotency.
5. Optional independent audit with clear limitations (same provider is not an external fact-checker).
6. Signed receipt records with key identity, signature verification, provider request IDs, usage and settlement status; never imply SHA-256 alone proves network settlement.
7. Persistent history and device-independent task dashboard with export.
8. Scheduler disabled by default until budget, persistence and cancellation controls are tested.
9. Dashboard distinguishes simulated, OpenAI-paid, FLOP-submitted, FLOP-settled, and eligibility-unknown.
10. Offline automated tests with mocked provider responses and protocol fixtures; one controlled live test only after gates pass.

## Acceptance gates
- Unit/integration tests: budget concurrency, timezone rollover, retries, failures, auditor cost, receipts, authentication and protocol responses.
- No paid API calls during routine testing.
- Verified FLOP docs and a genuine network receipt required before reporting network activity.
- No unreviewed production branch changes.
- Single planned deployment after the complete release is tested.

## Current status
V5.1 real OpenAI inference and second-model review were demonstrated; V5.2 has a paid-call safety pause. The V6 branch is a planning baseline, NOT a finished release.
