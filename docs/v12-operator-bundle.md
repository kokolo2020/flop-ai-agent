# Operator bundle handoff

Reviewed **2 November 2026** against the
[installation guide, updated 30 October](https://ask.flop.finance/docs/run-miner).
The public connection preview still needs operator approval; public endpoint
addresses do not establish admission. See the
[November preparation checklist](mining-readiness-2026-11-02.md) for deployment
profiles and the remaining live-test gates. Review the official guide again at
the time of the test; no live endpoint or release was verified here.

The current dependency is the operator reply. Renting remains on hold. After a
VM and installation are authorized, keep its private files on that host. Never
paste an env file, signer, private key, session token or decrypted tailnet key
into chat or upload it to the dashboard.

## Prepare the non-secret inventory

`examples/operator-plan.example.json` is **ComputePilot's own preparation
manifest**, not the format or signature of an official FLOP release receipt.
Copy it into the private bundle directory and fill the pins from the operator.
Use the actual relative artifact filenames the operator supplies. Put the
operator's RPC, DA and mailbox addresses in its endpoint fields; keep this
inventory on the host. Do not put seeds, tokens, key contents or endpoint
credentials in this manifest.

Confirm the genesis, runtime spec name/version/transaction version, exact Qwen
checkpoint revision, BF16 model hash, policy hash, version-and-digest image pins and artifact
SHA-256 values through the trusted operator channel. The manifest's SHA-256 must
also be confirmed separately. Computing a hash of whatever files arrived only
checks internal consistency; it does not authenticate their source. Release
signature verification and the operator's version-matched official verifier are
still required, and this checker never claims to have performed them.

The default inventory includes both Compose files, the matching env template,
decode policy JSON and operator release receipt. Public preview additionally
requires `tls_compose`. The split RunPod profile replaces `backend_compose` with
an operator-reviewed `backend_deployment` artifact describing the Pod settings.
A receipt's raw SHA-256 match only
identifies those bytes; its authenticity, network and release semantics are not
validated by this tool. The same caveat applies to Compose topology and image
availability. Do not run an unreviewed script just because its hash matches.

## Run the read-only checker on the host

From this repository installed on the authorized VM:

```bash
python3 -m computepilot.operator_bundle \
  --directory /opt/flop-miner \
  --manifest operator-plan.json \
  --expected-manifest-sha256 OPERATOR_CONFIRMED_MANIFEST_SHA256 \
  --env miner-01.env \
  --out miner-results/bundle-check.json
```

The directory must already exist. Relative paths cannot escape it or traverse
symlinks. The checker will not execute shell substitutions, source an env,
contact endpoints, invoke Compose, read signer contents, decrypt tailnet access,
generate keys, register anything or start a worker. It refuses a manifest pin
mismatch before opening the env or artifacts.

The private env must be a regular file with no group/other access (typically
0600). The supported parser handles one `KEY=value` assignment per line and
optional outer quotes. Duplicate keys, interpolation, escaping and unsupported
syntax fail for manual review. It compares the supplied model/image/policy pins,
BF16/bf16 pair, same-host backend URL, loopback session binding, required URL/path
shapes, and the two distinct 64-hex private tokens. RunPod uses the explicit HTTPS
Pod origin and a second private backend env instead of the same-host backend URL.
Shape checks do not prove
token randomness, endpoint reachability or signer ownership. The tokens and all
raw values are discarded from the report.

Policy JSON must match the pinned artifact structurally. Its runtime hash is
**not** a SHA-256 of the JSON file: this checker does not recompute SCALE policy
encoding. The approved backend and chain must subsequently agree on the measured
model and policy identity. The checkpoint itself is not downloaded or measured
by this checker.

## Deployment profiles

The optional `deployment` object has two independent fields:

| Field | Supported values | Additional manifest input |
| --- | --- | --- |
| `topology` | `same-host` (both services on the GPU VM), `runpod-backend` (Pod backend plus separate worker host) | RunPod needs `backend_origin`, e.g. `https://YOURPODID-8000.proxy.runpod.net` |
| `network_path` | `tailnet`, `public-preview` | Public preview needs `session_public_host`, a DNS hostname without a scheme, path or port |

Existing manifests without `deployment` retain the original same-host/tailnet
meaning. An explicit incomplete or unknown profile fails rather than falling back.
The [RunPod/public-preview example](../examples/operator-plan.runpod-public.example.json)
shows the additional inventory fields and artifact entries. It deliberately has
invalid placeholders; published endpoint addresses alone are not a usable bundle.
For public preview the checker requires encrypted RPC/mailbox URL shapes,
the matching public hostname in `SESSION_PUBLIC_HOST`, the TLS Compose artifact
and a loopback worker binding. Custom tunnels need separate manual review; this
profile checks the documented TLS Compose variant only. Tailnet profiles reject
a nonempty `SESSION_PUBLIC_HOST` to avoid accidentally mixing connection modes.

RunPod requires a versioned backend at least `v0.1.237`, plus its digest, and
`OPENAI_BASE_URL` equal to `backend_origin` plus `/v1` on the worker. Serverless
URLs are unsupported. Keep an operator-reviewed backend env in the private
bundle directory and add `--backend-env backend.env` to the command above. The
checker compares its `MODEL_NAME`, `MODEL_HASH`, `MODEL_REVISION`, BF16 precision,
policy JSON/hash, absolute `MODEL_DIR` and inference token against the worker and
manifest. Both env files must deny group/other access. It never prints values or
reads seed/key contents. These comparisons do not inspect the actual Pod, prove
image availability, or confirm that either service uses the checked files.

The current `miner_test` SSH/host-readiness path still checks a **full same-host
GPU VM**. Do not use a failed GPU probe on the CPU worker to judge the separate
Pod, or combine different hosts' reports to grant readiness. RunPod needs
separate measured backend health, TOPLOC and end-to-end session evidence.

Exit 0 means the supported offline checks passed, 2 means incomplete/mismatched
inputs, and 1 means an input/output failure. The report always keeps release
verification, network identity and admission unverified, and activation blocked.
Only its sanitized `bundle-check.json` may be reviewed in the dashboard. It can
never establish GPU compatibility, TOPLOC, calibration or accepted network work.

## Required evidence after the handoff

Before any signing, compare a read-only network observation against the supplied
genesis and runtime identity. Then verify the approved release, actual VM/SSH and
Docker GPU access, model-root/policy health, and measured inference. Starting the
worker, sponsorship, registration and stake changes require explicit approval.
Keep registration, calibration, TOPLOC publication, accepted work and settlement
as separate evidence stages. Calibration obligations and billing shutdown require
an operator-reviewed plan before worker activation.
