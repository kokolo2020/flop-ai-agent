# ComputePilot live access check — 4 November 2026 (Bangkok)

The existing RTX 5090 trial was completed and its rental ended. No new GPU was
rented for these agent integration checks.

| Check | Observation | What it establishes |
| --- | --- | --- |
| Direct public model GET in the preceding session | HTTP 200; `qwen/qwen2.5-0.5b-instruct` listed | Catalog access at that observation only |
| Hosted MCP initialize in the preceding session | HTTP 200; `flop-network` 0.2.0 | Protocol handshake only; no tools or inference executed |
| First new workflow catalog check, 2026-11-03 23:34 UTC / 4 November 06:34 Bangkok | HTTP 403; result saved locally | Access failed for that request; no inference was sent |
| Workflow catalog check with explicit ComputePilot application identification, 2026-11-03 23:36 UTC / 4 November 06:36 Bangkok | HTTP 200; `qwen/qwen2.5-0.5b-instruct` listed; private history saved | The implemented discovery-to-history path worked live; no inference was sent |
| Official CLI 0.4.0 devnet credential enrollment | `COMMAND_FAILED`: faucet HTTP 429, daily cap reached | Enrollment did not complete; no usable credential was issued by this attempt |
| Authenticated chat completion | NOT_RUN | No live answer, usage, payment, settlement or reward was verified |

The enrollment command was the documented `flop --network devnet agent credential
--json` path. It may create its private local devnet wallet before asking the
faucet; wallet/key contents are not included in this repository. It stopped on
the daily cap and was not retried. No real-value account was funded.

The earlier six local Qwen content checks remain local smoke evidence: strict
raw JSON passed 1/6, and content after whole-fence handling passed 6/6. Those
results do not establish FLOP network execution.

Next live gate: complete official devnet enrollment when capacity is available,
check the returned model scope, quota and expiry, and enable one bounded request.
Public miner admission and reward eligibility remain separate checks.

Validation of this change: 96 Python tests and 21 Node tests passed, including
15 new offline assistant workflow tests. Mocked completions are test fixtures,
not live FLOP answers.
