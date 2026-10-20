# FLOP testnet connectivity gate — 2026-10-20

Sources:
- https://flop.finance/testnet/ (updated 2026-10-05)
- https://flop.finance/intro/agent/
- https://flop.finance/intro/yellowpaper/
- https://github.com/flop-labs/yellowpaper

## Verified public statements
- Testnet opens Q4 2026, dates provisional; onboarding documentation is published when testnet opens.
- Agents require DID, wallet and access to test-token faucet.
- Agent airdrop credit requires compute purchased in settled sessions, with minimum activity floors yet to be published.
- Spend to miners under common control or circular transactions does not count as independent demand.
- Protocol target uses pallet_compute_channel for inference sessions; published normative specification is not proof that a publicly accessible RPC currently exists.

## Connection evidence status
- Public FLOP RPC URL: NOT VERIFIED from official documentation.
- Public faucet URL: NOT VERIFIED from official documentation.
- Agent enrollment/API instructions: NOT YET PUBLISHED on official testnet page.
- On-chain query: NOT EXECUTED.
- Signed testnet transaction: NOT EXECUTED.
- Verified settlement: NONE.

## Safe implementation plan
1. Wait for official agent onboarding, chain spec, and RPC endpoint; verify chain genesis hash and metadata before connection.
2. Implement a read-only RPC status probe with timeout and genesis allowlist, then agent wallet capability checks without storing private keys in browser localStorage.
3. Only after public docs confirm live operations, implement compute-channel transactions with user confirmation and test tokens.
4. Verify transaction inclusion, finality, event and settlement; label separately from OpenAI API usage.
5. Keep paid OpenAI mode locked until database spending gate has passed concurrency and cost tests.

No inference, FLOP wallet transaction or paid API call was executed in preparing this report.
