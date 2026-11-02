# FLOP miner preparation · 2 November 2026

## Official status reviewed today

Source: [FLOP miner guide](https://ask.flop.finance/docs/run-miner), last updated
30 October 2026. This is a dated documentation review, not a live network probe.

| Path | Published status | ComputePilot preparation |
| --- | --- | --- |
| Same-host NVIDIA VM | Backend and worker together | Existing host preflight and benchmark; updated offline bundle checks |
| RunPod GPU Pod | Backend capture validated on A40; complete paid session still untested | Separate backend env consistency checks; worker runs on another Docker host |
| Public connection preview | Invite-only; sponsorship, registration and calibration described as working; paid sessions not open | TLS Compose inventory, HTTPS/WSS shapes and loopback binding checks |

The RunPod backend requires a versioned, digest-pinned release at least 0.1.237.
Serverless is unsupported. Operator approval, matching release files, model and
policy pins are still prerequisites. Public endpoints do not remove these gates.
No GPU rental, registry access, registration, calibration or accepted work has
been verified by this change.

## What is ready locally

1. Select a topology and connection path in the preparation manifest. Use the
   [profile reference](v12-operator-bundle.md#deployment-profiles); the checked-in
   example intentionally contains placeholders and cannot pass as a real bundle.
2. Obtain approved artifacts through the operator's trusted channel. Version and
   digest must both be present in each image pin. A historical digest alone will
   now fail the checker. Confirm the preparation manifest hash separately.
3. Keep private env files and identity material on the host. Run the offline
   bundle checker and review only its sanitized result. A consistency pass
   remains separate from official release verification and network admission.
4. For a full GPU VM, use the existing host diagnostics. For a split Pod, obtain
   separate backend and worker evidence; the existing full-VM preflight is not a
   RunPod deployment validator.
5. For a same-host VM, use the current official model-fetch procedure with the
   operator's registered model hash. A split Pod uses the approved backend's
   pinned download and measurement. The older `scripts/download-qwen.sh` is only a download experiment;
   it cannot establish the registered checkpoint root or substitute for that gate.

## Inputs still needed for an actual test

Record the operator approval and release identity, expected genesis/runtime,
registered model identity and policy, approved host route, and spending limit.
Keep private credentials out of this inventory. Unknown inputs stay unknown;
do not fabricate image digests, model hashes or account admission.

Before starting a worker, separately review sponsored registration, calibration
obligations and how to terminate provider billing. A healthy backend is not
accepted network work. Record measured inference, TOPLOC validation, finalized
registration, accepted calibration, accepted work and settlement separately.

No rental or miner activation is performed by this preparation workflow.
