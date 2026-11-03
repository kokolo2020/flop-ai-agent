# ComputePilot V12 · FLOP miner preparation

**4 November 2026 agent workflow:** `python3 -m computepilot.agent_workflow network`
checks FLOP's public model catalog and saves private history without a GPU. The
optional single-request assessment requires an explicitly enabled scoped API
credential; output format and consistency are validated before acceptance.
GPU preflight reports can also be inspected or explained. See the
[workflow and credential instructions](docs/agent-workflow.md) and
[live access observations](docs/agent-live-check-2026-11-04.md).
The official enrollment attempt hit the faucet's daily cap; authenticated
inference remains unverified. No new rental or miner activation was performed.

**Diagnostic tool layer:** `python3 -m computepilot.diagnose` now reads preflight
reports, recommends investigation and compares fresh before/after observations.
This is deterministic diagnostic tooling; it does not run an LLM, execute repairs
or activate mining. See the [workflow and limits](docs/diagnostic-loop.md).

**3 November 2026 gateway discovery:** run `python3 -m computepilot.gateway_discovery`
for a read-only public model-list check. Listing, inference, mining and rewards are
reported separately. No key or paid request is sent. See the
[discovery instructions and limitations](docs/gateway-discovery-2026-11-03.md).
For later live observations, see the dated agent check log above. A listed model
does not establish a completed inference request.

**2 November 2026 preparation update:** the offline bundle checker now supports
same-host or split RunPod backend inventories and tailnet or public-preview
connection profiles. Image pins require both a version and digest. See the
[dated readiness checklist](docs/mining-readiness-2026-11-02.md) and
[profile instructions](docs/v12-operator-bundle.md#deployment-profiles).
These checks do not establish operator admission or activate mining.
For account/template preparation and a first SSH diagnostic, see the
[Vast.ai VM setup guide](docs/vast-vm-setup.md). H100 PCIe/NVL profiles check
hardware prerequisites only; they do not certify FLOP compatibility.

## ComputePilot V12 miner preparation

The local branch `computepilot-v12-a40-test` extends the V10.3 application from
`computepilot-v6`. It adds host diagnostics, bounded telemetry collection, a model
download helper, and an inference benchmark. These tools do not activate a miner.
The entry point is now a focused V12 workspace in `public/index.html`.
The result viewer is `public/miner-test.html`, linked from the workspace. V12
now adds evidence-derived readiness states, a five-step instruction viewer,
offline receipt encoding checks, A40/A100 target profiles, and read-only
DCGM/AIPerf adapters. These are local changes; the deployed V10.3 site is unchanged.

Older simulations and existing browser history are retained in
`public/legacy-lab.html`. Its paid-call path and browser vault/signing implementation
have been removed. `public/receipts.html` provides a separate local integrity
checker. These pages do not activate a miner or establish accepted FLOP work.

New local job receipts use the versioned V6 contract in
`computepilot/receipts.py` and `public/receipt-core.js`. Browser and Python fixtures
verify both directions. Legacy V5 receipts retain read-only compatibility for the
supported JSON domain and remain explicitly unsigned. See
[the receipt contract](docs/receipt-contract.md).

The optional paid server adapter now accepts only a completed response with a
request ID and nonempty text. Incomplete responses return 422 with an explicit
`INCOMPLETE` state, invalid/empty responses return 502 with `FAILED`, and neither
triggers the optional auditor. A failed/flagged/unavailable second review is kept
separate from mechanical format checks. No live-enable environment settings have
been changed; tests mock every budget and provider request.

Read the [official miner installation guide](https://ask.flop.finance/docs/run-miner)
and [GPU.ai VM guide](https://gpu.ai/docs/guides/gpu-instances) before provisioning.
Use the operator's release files; this repository does not contain or replace them.
No rental, paid registration, chain transaction or worker start is authorized here.

The next local tool is `python3 -m computepilot.operator_bundle`: an offline,
secret-redacting check of operator-supplied pins, release artifacts and private
env consistency. Use the [handoff instructions](docs/v12-operator-bundle.md) and
the intentionally incomplete `examples/operator-plan.example.json`. Keep private
files on the host; import only the sanitized checker report into the dashboard.
Passing these checks does not authenticate a release or establish admission.

From this repository, collect a local diagnostic report (exit 2 means incomplete):

```bash
python3 -m computepilot.miner_test preflight --out miner-results/preflight.json
```

After a GPU VM is provisioned and authorized, configure its verified SSH host key,
username, port and identity locally under an SSH config alias. Do not paste keys
into chat. The following streams the diagnostic code to that host without
installing it. Supply the approved CUDA image digest to actually test GPU access
inside Docker; without it that check remains NOT_RUN.

```bash
python3 -m computepilot.miner_test ssh-preflight --host a40-authorized \
  --cuda-image 'nvidia/cuda@sha256:REPLACE_WITH_APPROVED_DIGEST' \
  --out miner-results/vm-preflight.json
```

For current same-host miner setup, follow the official guide's `flop model fetch` procedure
with the operator's registered model hash and a fresh checkpoint directory.
Stop if the fetched bytes do not reproduce the registered root.

The older helper below remains an optional download experiment only. It requires
`uvx` and an operator-approved revision. It cannot establish the registered root
or replace the official model-fetch gate, and does not start inference or mining.

```bash
bash scripts/download-qwen.sh --authorized-vm APPROVED_40_HEX_REV /opt/flop-miner/models/qwen-test
```

Use the operator's Compose files and env file to configure and validate the
backend according to the official guide. Review resolved service dependencies
before starting anything; only the inference backend may be started for this
test. Keep the worker stopped pending separate approval. Do not print resolved
Compose configuration or raw logs into chat because they may contain secrets.

The benchmark is designed to run **inside the running backend container** using
its existing `INFERENCE_API_KEY`. It contacts only loopback and checks model and
policy identity before inference. From the operator Compose directory on the VM:

```bash
docker compose --env-file miner-01.env -f docker-compose.miner.yml -f docker-compose.backend.yml \
  exec -T backend python - benchmark \
  --model-hash 0xAPPROVED_MODEL_HASH --policy-hash 0xAPPROVED_POLICY_HASH \
  < /path/to/flop-ai-agent/computepilot/miner_test.py > /private/path/benchmark.json
```

Create the private output directory with mode 0700 and use `umask 077` before
shell redirection. Inspect exit status: zero means requests succeeded, two means
partial failure, one means the test could not proceed. The health parser expects
`model_identity`, `model_hash`, `precision`, and `decode_policy_hash`; a different
release schema requires review and fails closed. This parser and the request
schema have not been exercised against a real FLOP backend yet.

To monitor host GPU telemetry and Docker availability, run on the VM:

```bash
python3 -m computepilot.miner_test monitor --samples 60 --interval 10 \
  --out miner-results/monitor.json
```

This collects a bounded ten-minute session, with an incremental `.json.jsonl`
journal. For backend health, run the monitor inside the backend with both expected
hash options; GPU and Docker host probes can be unavailable there. Host and
container reports must be interpreted in their own execution contexts. Temperature
(85C) and VRAM (95%) alerts are test heuristics. There is no remote alert service,
automatic restart, rental shutdown, or ongoing scheduled monitor.

All host reports are unsigned observations. The benchmark measures sequential
end-to-end latency and reported output tokens per full request second; it does
not measure decode-only speed, TTFT, TOPLOC correctness, or accepted network work.
The existing offline benchmarks remain separate and cannot establish FLOP activity.
Results and operator secrets are ignored by Git. Never commit miner env files,
signers, tailnet keys, keystores or identity-vault exports.

The SSH preflight also accepts `--target a100-40` or `--target a100-80` (default
`a40`). Profiles require one whole card; additional GPUs and MIG devices need a
separate whole-host calibration review. A100 hardware matching is a host check,
not validation of FLOP/TOPLOC compatibility.

The guided dashboard displays READY, ACTION NEEDED, BLOCKED and UNREACHABLE per
stage. It derives host readiness from the actual GPU inventory, Linux architecture,
Docker GPU probes and SSH result. A benchmark cannot prove host readiness and
reports from different hosts are never combined. Snapshots expire after five
minutes; timestamps over a minute in the future fail readiness. All imports are
unsigned, so these states do not authenticate a host. Operator access and miner
activation stay blocked; there are no activation controls or secret inputs.

### Offline wire checks and optional monitoring adapters

```bash
python3 -m computepilot.wire_check
python3 -m computepilot.integrations dcgm --base http://127.0.0.1:9400 \
  --out miner-results/dcgm.json
python3 -m computepilot.integrations aiperf-import \
  --records /private/path/profile_export.jsonl --out miner-results/aiperf.json
```

The offline check runs 45 comparisons against the unchanged public
[FLOP Appendix F corpus](https://github.com/flop-labs/yellowpaper/blob/70e691c758e53eed17a016a02b0a2ae1200d3744/evidence/wire-format-v1.json).
It checks its pinned SHA-256 before comparing independent encoders for compact
integers, channel/receipt preimages, token commitments, leaves, Merkle roots/paths
and the policy digest. Attribution, source commit, SHA-256 and CC BY 4.0 license
are in `tests/fixtures/flop-wire-v1/`. It does **not** check sr25519 signatures,
FCC4 decoding, all semantic rejection cases, live runtime compatibility, TOPLOC
or accepted work. Its report is explicitly synthetic and cannot enter the host
evidence viewer. This is a tested subset, not full protocol conformance.

DCGM collection requires an **already approved** NVIDIA exporter on loopback.
The adapter only reads `/metrics`; it never installs or starts the exporter.
It keeps GPU index and selected numeric counters, discards other labels, treats
missing/sentinel/NaN values as unknown, and rejects duplicate GPU series rather
than silently aggregating MIG or replicas. A nonzero XID may be historical.

AIPerf import reads per-request `profile_export.jsonl`, keeps only selected numeric
metrics and a source-file hash, and omits response text, headers, configuration and
error messages. Source timestamps are preserved, so importing an old result does
not make it current. It does not authenticate model, precision, policy or GPU and
cannot promote inference readiness. See [the integration plan](docs/v12-integrations.md)
for the future authorized VM drill. Neither adapter has run against a GPU here.

Run regression checks:

```bash
python3 -m unittest discover -s tests -v
npm test
```

## Archived V1 simulator

**Status of the original V1 simulator: offline simulation only.** Its `SIM-`
receipts are internal test identifiers. It does not establish real inference,
FLOP transactions, points or authentic protocol receipts. The V12 host tools
described above are separate and still require an authorized GPU VM for live tests.

## Quick start

Requires Python 3.10+; no third-party dependencies.

```bash
python agent.py init
python agent.py run "Summarize the risks of deploying a new AI service"
python agent.py status
```

Run from the project folder. On Windows use `py agent.py ...` if `python` is unavailable.

## Features

- Offline adapter with explicitly simulated outputs
- Dedicated wallet **public-address placeholder** (no secret keys)
- Atomic SQLite budget enforcement with a daily UTC reset
- Local SQLite job history, cost units, and synthetic receipts
- No automatic loops or self-dealing
- No network access, so no unexpected on-chain spending

## Configuration

Edit `config.json` to change `daily_budget_units` and `simulated_cost_units_per_job`. The units are **fictional simulation units**, not FLOP tokens or dollars. `wallet_public_address` may be set to a public address only after confirming the project's supported address format. Never put a private key or seed phrase in this file.

## Live integration checklist (not implemented)

1. Confirm the official FLOP testnet RPC/API and supported client or SDK from authoritative project documentation.
2. Verify chain ID, wallet type, address format, transaction signing, DID registration, and faucet eligibility.
3. Implement an explicit opt-in live adapter with request schema validation and receipt verification.
4. Enforce **both** a per-request and daily budget in actual chain denomination; reject unknown fees and require explicit confirmation for any real spend.
5. Verify independently settled inference requests and reconcile actual chain fees against SQLite history.
6. Implement timeout, retry with idempotency, and stop on budget or connectivity errors.
7. Store signing keys in OS keychain/hardware wallet, not in source code, config, logs, or GitHub.
8. Only count genuine third-party inference activity; never label simulation activity as airdrop eligible.

This prototype is intentionally conservative. It can be extended after the official interface is confirmed.
