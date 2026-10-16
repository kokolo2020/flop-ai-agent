# ComputePilot V4 signed-task prototype

Run locally with Node.js 18+ (no dependencies):

```sh
node agent-v4/demo.js
node agent-v4/test.js
```

Two ephemeral Ed25519 identities exchange a signed task request and signed result receipt. The demo verifies signatures, a deterministic arithmetic result, and rejection of a modified receipt. This is a **local simulation** only: no DID registration, Technocore API connection, FLOP inference execution, FLOP verification, or settlement. Do not interpret signatures alone as proof of real computation.

Next: verify official identity/message schema and implement a read-only Technocore transport adapter, then integrate authenticated communication and replay protection. Avoid saving private keys to source control.
