# ComputePilot bounded diagnostic assistant

This adds one small workflow to the existing diagnostics: collect public FLOP
model availability, optionally ask that model to explain the observed facts,
validate its answer, and save the outcome. It can also assess a local GPU
preflight report. Python 3.10+ and the standard library are sufficient; a GPU,
MacBook connection and package installation are not required for these commands.

This is a single-turn assistant with deterministic diagnostic rules. It does
not autonomously choose shell tools, execute repairs, provision rentals, sign
chain transactions or start mining. The old simulation receipt engine stays
separate; this workflow does not enable its disabled FLOP provider.

## Start without a credential

From the repository root:

```bash
python3 -m computepilot.agent_workflow network
python3 -m computepilot.agent_workflow history
```

The first command performs one anonymous GET to the official model catalog and
saves a private result. CHECKS_CLEAR here means only that the selected model was
listed. Inference, settlement, mining and rewards remain unknown. An empty,
malformed, rejected or unreachable catalog is saved as an unsuccessful check.

To inspect an existing GPU preflight report entirely offline:

```bash
python3 -m computepilot.agent_workflow inspect --report miner-results/preflight.json
```

Use the existing `computepilot.miner_test preflight` collector on an authorized
host to create that input. Historical model-smoke files such as `flop-results.json`
have a different schema and are not GPU preflight inputs. Missing or stale
observations never become current healthy readings. Raw logs, hostnames and
arbitrary input fields are excluded from the model context; GPU names become
hashes in the existing diagnostic module.

## Obtain a devnet credential

The published official `@flop-labs/cli@0.4.0` README documents this enrollment path
(Node.js 22+ is required for that CLI):

```bash
npm exec --yes --ignore-scripts --package=@flop-labs/cli@0.4.0 -- flop --network devnet agent credential --json
```

Enrollment creates a separate local sr25519 devnet wallet, may request a faucet
grant and signs a gateway challenge. It is an explicit devnet enrollment action;
the Python assistant never invokes it automatically. The command prints metadata
without printing its bearer. Its README documents private wallet/key caches under
`~/.flop/` (0600 files, 0700 directory). Preserve them privately; do not commit them
or send them in chat. Do not use a real-value wallet or owner credential for this
development workflow.

The public allowance is model-scoped, operator-configured and expires within
24 hours according to that README. Re-enrollment rotates a bearer without
renewing quota or expiry. Check the returned model, quota and expiry rather than
assuming a documented example is the live allowance. The client API does not
mint grants itself. A faucet rejection is an enrollment failure, not evidence
that inference ran or that mining is available.

Have a local secret manager supply the resulting scoped, server-capped credential
as `FLOP_API_KEY`. Never put its value in a command line, repository or screenshot.
For an interactive shell with an already obtained key, `getpass` avoids echo and
history; the key is used only by this Python process:

```bash
python3 - <<'PY'
import getpass
import os
from computepilot.agent_workflow import main
os.environ['FLOP_API_KEY'] = getpass.getpass('Scoped FLOP devnet API key: ')
raise SystemExit(main(['network', '--allow-inference']))
PY
```

`network` checks the live catalog before inference; an absent selected model
blocks the POST. If enrollment scopes a different model, pass its exact catalog
ID using `--model`. To explain a GPU report instead, use `explain --report FILE
--allow-inference` with the credential supplied privately in the environment.

## Limits and outcomes

An enabled call sends exactly one non-streaming POST to
`https://api.flop.network/v1/chat/completions`. The default output limit is 192
tokens, adjustable only within 32–256; the sanitized request is limited to 16 KB.
These are request-size limits, not a currency budget. Spend protection must be
enforced by the credential's server-side quota, model scope and expiry. There is
no automatic retry, alternate provider, response repair call or paid fallback.
Redirects are refused and provider error bodies are not emitted.

Only one finished text choice with a response ID, matching model and consistent
usage counters is considered completed. Tool calls, refusal, truncation, missing
usage, oversized output, duplicate JSON keys and mismatched facts are rejected.
An assessment has exactly `state`, `issue_codes`, `recommended_action`, and
`summary`. Its first three fields must agree with the deterministic diagnosis.
Summary prose remains model-generated and is not fact-checked. Nothing in a model
answer authenticates a host, establishes root cause or verifies FLOP settlement.

One entire JSON Markdown fence can be removed. Such a result records
`output_format: FENCE_NORMALIZED`, `raw_json_valid: false`, and
`normalized_content_valid: true`; it is never reported as strict raw JSON.
Surrounding prose, additional objects and extra fields are rejected.

Exit codes: 0 is a completed offline inspection, successful catalog check or
accepted model assessment; 2 means an unmet requirement or rejected/unavailable
assessment; 1 means invalid input or an unavailable private history store.
Check the separate inference, validation and diagnostic states, not just exit 0.

## History and interrupted calls

Results live under ignored `miner-results/agent-history/` by default. The directory
must be owned by the current user, private and not a symlink. Each job gets a
UUID and a new 0600 JSON result file. No result is overwritten. `history --limit
10` returns brief summaries; full files are available at the printed local path.

Before POST dispatch, a separate immutable `started` record is flushed to disk.
It contains the exact sanitized request, its hash and the request identity, but
no credential. That identity is sent as both `Idempotency-Key` and
`X-Correlation-ID`, following the official client README. A result file records
the final observation. An orphaned started record is listed as OUTCOME_UNKNOWN;
it never becomes a success just because a process stopped.

A timeout, HTTP failure or malformed reply may follow accepted work. Do not
blindly rerun with a new identity: reconcile the recorded identity with FLOP
first. This version intentionally supplies no automatic replay command. Any
reviewed replay must preserve the original payload, idempotency key and
correlation ID. Gateway-reported usage is retained, but arbitrary receipt fields
are discarded and settlement remains NOT_VERIFIED.

## Validation

```bash
python3 -m unittest discover -s tests
npm test
```

The new fixtures cover JSON/content separation, contradictory facts, truncation,
unexpected tools/models/usage, credential omission, sanitized context, bounded
single dispatch, durable pre-dispatch history and partial/corrupt history. They
are offline tests and do not prove real hardware behavior or a live completion.

References reviewed 4 November 2026:

- [Official SDK references](https://docs.flop.network/docs/sdk-references)
- [Official client 0.2.1](https://www.npmjs.com/package/@flop-labs/client/v/0.2.1)
- [Official CLI 0.4.0](https://www.npmjs.com/package/@flop-labs/cli/v/0.4.0)
- [Live check log](agent-live-check-2026-11-04.md)
