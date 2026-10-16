# ComputePilot V5.0 — Autonomous AI Work & Verification

## V5.0A: implemented (offline-first scaffold)
- `computepilot.engine.execute(task)` runs the explicitly simulated provider.
- Deterministic auditor reports mechanical checks; **does not claim factual accuracy**.
- Receipts contain task/output hashes, provider metadata and explicit `NOT_VERIFIED` settlement.
- `verify_receipt` detects changes to the record or output using SHA-256. **Hash-only receipts are not cryptographic signatures** and do not establish trusted authorship.
- Live and FLOP adapters fail closed. No secrets, network requests or spending.
- The original `agent.py` and Netlify V4 dashboard are unchanged.

## Local commands
```bash
python -m unittest discover -s tests -v
python -m computepilot.cli run "Summarize AI reliability risks"
```

## Planned next steps
1. V5.0B: a server-side live inference provider with explicit credentials, cost ceilings, timeout and redacted logs.
2. V5.0C: independent model review and deterministic ground-truth tests.
3. V5.0D: Ed25519 signed receipts with key rotation and signature verification.
4. V5.0E: authenticated task API, persistent job queue and phone-friendly Netlify dashboard.
5. FLOP adapter: implement only against confirmed official protocol documentation; distinguish submitted, confirmed and settled statuses.

**No airdrop eligibility or mining status is claimed.**
