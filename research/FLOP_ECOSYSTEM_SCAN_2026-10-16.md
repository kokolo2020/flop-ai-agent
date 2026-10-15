# FLOP ecosystem signals — initial evidence scan (2026-10-16)

## Objective
Identify public signs of what FLOP agent builders actually implement, and discriminate verified code from speculation or airdrop marketing. Public projects do NOT prove access to private roadmap or insider information.

## Official, high-signal activity
- FLOP Labs: https://github.com/flop-labs — official README describes `coordinate → agree → settle → verify` with Technocore Chat, TCLK and FLOP inference network.
- Technocore Chat: https://github.com/flop-labs/technocore-chat — HTTP-native messaging and shared notes for agents.
- TCLK: https://github.com/flop-labs/tclk — signed HTLC/PTLC agreement primitives, initial protocol and library; **no live settlement rail holding value** according to repo/spec.
- Yellowpaper: https://github.com/flop-labs/yellowpaper — network verification design, NOT evidence that mainnet APIs are available.

## Independent builders (public code / README claims)
- https://github.com/d4ncboz/technocore — Ed25519 DIDs, signed messages and contribution claims. Claims about rewards are not verified.
- https://github.com/zunmax/technocore-did-starter — encrypted identity and signed participation starter, with explicit no-guarantee warnings.
- https://github.com/hunter20000002-pixel/flop-agent — task planning, memory, provider connectors and authenticated Technocore communications; explicitly says FLOP network integration is future work.
- https://github.com/Luwwin/flop-marketcap-agent — crypto-data publisher, alerts and signed posts; not evidence of FLOP inference settlement.
- https://github.com/gentlejay/Flop-Labs-Agent_Technocore — Windows identity/communication starter, distinguishes DID possession from network rewards.

## Preliminary read
Lots of builders implement onboarding, identity, chat and generalized agent wrappers. Official engineering investment focuses on settlement coordination and verifiable inference. Potential unfilled need: interoperable, testable agent execution receipts + provider-neutral quality and cost checks that can eventually plug into FLOP's actual settled-inference interfaces. This is a **hypothesis**, not a proven market gap.

## ComputePilot V4 priorities
1. Build a read-only discovery index of public GitHub repositories (dedupe by canonical repo URL; timestamp evidence; detect actual source files/tests).
2. Categorize `announcement | runnable prototype | deployed service | documented verified network settlement`; never upgrade a category solely from self-description.
3. Track official repo releases, commits, specs and API availability; separately track independent builders. Attribute every observation with URL + observation date.
4. Prioritize DID/signature compatibility, request/response traceability, independent validation and cost controls.
5. No autonomous public posting, artificial activity, buying inference or mining rewards without official verified interfaces and explicit authorization.

## Open questions
- Is an official FLOP agent SDK/RPC testnet callable now?
- Are any public third-party agents producing real settled inference receipts?
- Which published jobs involve paid third-party demand rather than speculative token participation?
- What is the provenance and freshness of any community-level 'leaderboard'?

Sources collected 2026-10-16. Public code can evolve; re-check before implementing integrations.
