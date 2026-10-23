# ComputePilot V3 — Netlify deployment notes

Development branch: `computepilot-v3`. This is an upgrade to the existing V4-labeled frontend, not a FLOP miner.

## Improvements
- OpenAI Responses API maximum output length raised from 300 to 4,000 tokens (configurable via `MAX_OUTPUT_TOKENS`).
- Up to 60-second upstream API timeout (configurable via `INFERENCE_TIMEOUT_MS`; actual Netlify hosting timeout may be lower).
- Optional **Use live web research** checkbox sends the Responses API `web_search` tool and requires web use. This may add search charges.
- Frontend displays model, token usage, search-use status, citations, and Markdown pipe tables.
- Server access secret remains required, and the OpenAI API key stays server-side.
- FLOP airdrop eligibility remains **false**. There is no FLOP miner, wallet, or settlement integration.

## Netlify steps
1. Deploy branch `computepilot-v3` to a preview, or merge the PR into `main` when you want production updated.
2. Keep existing `OPENAI_API_KEY` and `AGENT_ACCESS_TOKEN` secrets. Never put these in GitHub.
3. Optional environment variables: `OPENAI_MODEL=gpt-4.1-mini`, `MAX_OUTPUT_TOKENS=4000`, `INFERENCE_TIMEOUT_MS=60000`.
4. Submit a short normal question; confirm full output and token usage. Try a Markdown table.
5. Enable live research and ask for a source-backed GPU rental comparison; confirm search performed = yes and source links appear.
6. If a research request times out, check Netlify function execution limits and logs. Longer web searches can exceed the platform limit.

## Cost warning
**No hard monthly API spending cap is implemented.** A global $20 monthly cap requires durable, atomic shared usage tracking, not browser localStorage or per-invocation memory. Set an account/project budget/alerts and restrict access in the API provider dashboard before broad deployment. Search requests may incur extra cost.

## Testing status
Code syntax verified. Runtime API and Netlify integration tests are pending your preview deployment and API credentials.
