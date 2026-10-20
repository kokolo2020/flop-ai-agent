# FLOP Yellow Paper alignment — ComputePilot V6

Sources reviewed 2026-10-20:
- https://flop.finance/intro/yellowpaper/
- https://github.com/flop-labs/yellowpaper

## Protocol facts
- FLOP is a Substrate/FRAME verified-inference settlement layer (Yellow Paper §0.1).
- Agent is a compute consumer that opens sessions and pays escrow; miner executes inference; validator finalizes and verifies (§1.1, §12).
- Ordinary OpenAI Responses API calls and locally hashed receipts are **not** FLOP inference transactions or settlement proofs.
- Agent on-chain spending windows are block-aligned and start on wallet/session creation (§1.2); our $5/day Bangkok API budget is a **separate local safety control**, not the protocol wallet cap.
- TEE is optional but activation commitments and sampled re-execution form the intended mandatory verification floor (§0, §3); do not label generic AI audits as PoUI.
- The yellow paper is a target normative draft, not a guarantee of currently available testnet APIs. Consult Appendix H (implementation status) and Appendix E (open specification items).

## V6 integration priorities
1. Check official testnet docs and Appendix H for live agent enrollment, RPC endpoints, extrinsics and availability.
2. Identify agent account/signature/key management and delegation (§6.2, §6.5).
3. Map compute-channel open, fund, request, receipt, close/settle (§12, Appendix F.3, Appendix G.1). Implement only verified available endpoints.
4. Require actual on-chain transaction hash and finalized state before reporting FLOP settlement.
5. Keep FLOP provider disabled until end-to-end testnet transaction and settlement are verified.
6. Keep private OpenAI API budget separate from FLOP wallet/session caps.

## Current status
Research alignment only. No FLOP-compatible adapter, wallet, transaction or verified settlement has been implemented. No airdrop eligibility is established.
