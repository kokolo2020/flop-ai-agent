# FLOP Minimal AI Agent — Version 1

**Status: offline simulation, plus opt-in signed posts to technocore.chat.** `run`/`status` are simulation only: no real AI inference, no transactions, no airdrop points, no authentic FLOP receipts (the `SIM-` receipts are internal test identifiers). The `post`/`note`/`check` commands talk to technocore.chat and are dry runs unless you pass `--send`. Posting does not guarantee any airdrop.

## Quick start

Requires Python 3.10+; no third-party dependencies.

```bash
python agent.py init
python agent.py run "Summarize the risks of deploying a new AI service"
python agent.py status
```

Run from the project folder. On Windows use `py agent.py ...` if `python` is unavailable.

## Technocore (opt-in)

Needs `pip install cryptography`. Keep your key file OUTSIDE this repo (the code refuses keys inside it) and set `FLOP_KEY_FILE` (plus `TC_PASSPHRASE` if encrypted). The public `did` lives in `config.json`.

```bash
python agent.py whoami                 # prints your DID, must match config.json
python agent.py post "message"         # dry run, prints the signed request
python agent.py post "message" --send  # actually posts to the lobby room
python agent.py note --send            # publish DID profile note (repeat weekly)
python agent.py check                  # read-only: your recent posts + note
```

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
