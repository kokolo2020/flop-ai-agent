# Operator bundle handoff

The [public devnet reference](https://ask.flop.finance/networks/devnet) currently
lists no verified public genesis, RPC, or supported release. The
[installation guide](https://ask.flop.finance/docs/run-miner) supplies development
instructions, with version-matched private artifacts obtained from the operator.
Neither a public application form nor this repository establishes admission.
Review these sources again at the time of the test.

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
checkpoint revision, BF16 model hash, policy hash, image digests and artifact
SHA-256 values through the trusted operator channel. The manifest's SHA-256 must
also be confirmed separately. Computing a hash of whatever files arrived only
checks internal consistency; it does not authenticate their source. Release
signature verification and the operator's version-matched official verifier are
still required, and this checker never claims to have performed them.

The inventory includes both Compose files, the matching env template, decode
policy JSON and operator release receipt. A receipt's raw SHA-256 match only
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
shapes, and the two distinct 64-hex private tokens. Shape checks do not prove
token randomness, endpoint reachability or signer ownership. The tokens and all
raw values are discarded from the report.

Policy JSON must match the pinned artifact structurally. Its runtime hash is
**not** a SHA-256 of the JSON file: this checker does not recompute SCALE policy
encoding. The approved backend and chain must subsequently agree on the measured
model and policy identity. The checkpoint itself is not downloaded or measured
by this checker.

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
