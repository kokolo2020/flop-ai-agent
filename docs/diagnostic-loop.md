# ComputePilot diagnostic tool layer

This is a deterministic tool layer for the future agent, not an autonomous LLM
agent or a FLOP miner. It reads reports from the existing preflight collector,
returns evidence and recommendations, and compares two snapshots after an
operator makes a correction. It never executes repairs, installs packages,
opens paid sessions or activates mining.

## Collect, inspect, compare

On the authorized GPU host, from the project root:

```bash
python3 -m computepilot.miner_test preflight --out miner-results/before.json
python3 -m computepilot.diagnose --report miner-results/before.json --out miner-results/diagnosis-before.json
```

The collector's exit 2 means some prerequisites remain incomplete; it still
writes the report. Without an approved CUDA diagnostic image, the collector does
not test Docker GPU access. The diagnostic module covers only NVIDIA telemetry
access, Docker server access, temperature and allocated memory. CHECKS_CLEAR
does not imply inference, Docker GPU access or FLOP readiness.

Inspect a recommendation and decide whether a correction is appropriate. This
module does not establish the root cause. After the correction, collect a new
report on the same host, then compare:

```bash
python3 -m computepilot.miner_test preflight --out miner-results/after.json
python3 -m computepilot.diagnose --before miner-results/before.json --report miner-results/after.json --same-host --out miner-results/diagnosis-after.json
```

Use new filenames for each run; output files use mode 0600 and never overwrite.
Diagnosis exit codes: 0 means CHECKS_CLEAR for its limited scope; 2 means attention,
missing observations or stale data; 1 means invalid/unavailable input. Check the
separate recovery field; exit zero alone does not establish recovery.

The current snapshot must be no older than five minutes or over one minute in
the future. Comparison requires a strictly newer snapshot, the same ordered GPU
name hashes and memory totals, and the operator's explicit same-host assertion.
The collector lacks an authenticated host identifier. `--same-host` is an
assertion, not proof; cloned/replaced hosts with matching inventories cannot be
distinguished. Unknown metrics cannot clear a prior condition.

OBSERVED_CLEARANCE_UNSIGNED means all prior flagged conditions are absent and
these limited checks are clear in the new report. It is not an independent
verification, proof that a fix caused recovery, or proof of sustained health.
Two snapshots cannot establish those properties. A changed host, stale report,
missing observation or absent assertion leaves recovery INCONCLUSIVE.

The 85 C temperature and 95% allocation rules are heuristics inherited from the
monitoring tools. High memory allocation does not alone prove an out-of-memory
error; manufacturer temperature limits and workload context still matter.
Raw logs and arbitrary extra report fields are ignored. No model inference is
performed, and model/tool selection remains future integration work.

## Validation and next live trial

```bash
python3 -m unittest discover -s tests -p 'test_diagnose.py' -v
```

Eleven synthetic tests cover observed conditions, missing/invalid metrics,
unsupported schemas, stale timestamps, persistent conditions, limited observed
clearance, log omission and private non-overwriting results. These fixtures do
not establish real GPU behavior.

For the first authorized live trial, collect a real baseline, exercise a safe
reversible failure of an isolated test service, and confirm both the failure and
recovery are reported. Do not deliberately overheat a GPU or disrupt active miner
work. Finish with saved results and rental termination confirmation. No rental
has been started by this code change.

Remaining milestones are authenticated host correlation, real-host validation,
a bounded LLM tool loop and separately verified FLOP network integration.
