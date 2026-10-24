# V12 integration plan

No VM is provisioned or authorized in this session. Wait for the FLOP operator
reply before renting. No AIPerf, DCGM exporter or miner service was installed or
started by this change.

## AIPerf: future authorized inference drill

Reference: [NVIDIA AIPerf](https://github.com/ai-dynamo/aiperf), its
[CLI options](https://github.com/ai-dynamo/aiperf/blob/main/docs/cli-options.md),
and [per-request exports](https://github.com/ai-dynamo/aiperf/blob/main/docs/tutorials/working-with-profile-exports.md).
Review and pin the installed version before running; CLI flags and export schemas
can change. The adapter implements the documented per-request metric subset and
fails on incompatible units or missing request timestamps.

1. Use an authorized, isolated benchmark environment on the VM. First complete
   the built-in V12 benchmark with the operator's exact model/policy hashes. Keep
   the worker stopped. Confirm streaming is supported by that backend release.
2. Use the local exact-revision checkpoint for tokenization, not a mutable Hub
   revision. No remote-code tokenizer execution is needed for this Qwen model.
3. Start with a synthetic non-private workload: chat endpoint, streaming, 10
   requests, concurrency 1, input target 128 tokens and output target 128 tokens.
   Use operator-approved decode settings. Output lengths may be shorter at EOS;
   do not claim a fixed token count from the target alone.
4. Connect only to the loopback backend from its execution context. Configure
   authentication locally using the reviewed installed AIPerf version; do not
   paste API keys into chat, shell arguments, committed config or result exports.
   An exact authenticated launch command remains pending that review. The agent
   must not work around authentication by opening a public unauthenticated port.
5. Keep exports private, avoid raw request/response exports, disable optional
   MLflow/W&B/OTel uploads, and inspect locally for secrets before any sharing.
   Import only `profile_export.jsonl` with `computepilot.integrations aiperf-import`.
6. Read median/p95 TTFT, inter-token latency, request latency and per-user output
   throughput with the sample counts. Missing metrics remain unavailable. These
   timing statistics are not a FLOP calibration result or an earnings estimate.

## DCGM: future approved exporter

Reference: [NVIDIA DCGM exporter](https://github.com/NVIDIA/dcgm-exporter) and
[default counters](https://github.com/NVIDIA/dcgm-exporter/blob/main/etc/default-counters.csv).
Review a digest-pinned exporter compatible with the actual NVIDIA driver/DCGM
version and the provider's privileges. Exporter deployment is pending VM access
and authorization. Bind it only to `127.0.0.1:9400`; do not expose GPU telemetry
or a Docker socket publicly. No exporter startup command is executed by V12.

Once present, the read-only adapter samples temperature, power, utilization,
used/free VRAM and last XID. It discards host/UUID/job labels and rejects duplicate
series. One snapshot does not establish uptime or a new XID incident. The bounded
`miner_test monitor` command remains the initial host telemetry collector.

## Borrowed ideas, not executed agents

Readiness states were inspired by
[FLOP Evidence Scout](https://github.com/Mariukasfak/flop-evidence-scout), and the
instruction flow by [FLOPPY](https://github.com/Ephrett/floppy). No code from those
agents was executed or copied. Their registrations and independent receipts do
not establish official FLOP miner participation. The only vendored artifact is
FLOP Labs' attributed public synthetic wire corpus.
