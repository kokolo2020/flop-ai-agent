# Public gateway discovery — 3 November 2026

Run from the project root with Python 3.10 or later; no extra packages:

```bash
python3 -m computepilot.gateway_discovery
```

This makes one unauthenticated GET to the official
`https://api.flop.network/v1/models` endpoint with a ten-second timeout and a
one-MiB response limit. It does not follow redirects or retry. It sends no API key
and makes no inference request or chain transaction.

`model_listing` distinguishes AVAILABLE, EMPTY, HTTP_ERROR, INVALID_RESPONSE and
UNREACHABLE. Exit zero means a nonempty, structurally valid model listing only;
exit two means discovery did not establish that. The validator checks the minimal
`data` array and unique nonempty string IDs; it does not implement the complete
`@flop-labs/contracts` schema. Raw provider errors and extra model fields are omitted.
Inference remains NOT_RUN, and mining and rewards remain NOT_VERIFIED in every
case. Listing a model does not establish that inference or paid public mining works.

Offline tests:

```bash
python3 -m unittest discover -s tests -p 'test_gateway_discovery.py' -v
```

Sources checked on 3 November 2026:

- https://docs.flop.network/docs/sdk-references documents public model discovery
  without a key; chat completions require an API key. Use a bounded child credential
  for any future separately authorized paid inference test.
- https://docs.flop.network/docs/run-miner still describes invite-only miner
  sponsorship and says public paid sessions are not open yet. It does not establish
  a public reward launch.

Live endpoint access has not been verified in this development session. Offline
fixtures are synthetic; they do not establish network health, accepted inference,
settlement, rewards or RTX 5090 compatibility with FLOP's backend.
