# V6 setup and safety status

V6 alpha is **not production-ready** and is NOT connected to FLOP. It is not yet deployed. V4 production and V5 branch remain unchanged.

## Budget reservation implementation
- Database schema: `database/v6_budget.sql`, run in a private Supabase SQL editor.
- Uses a PostgreSQL atomic UPDATE to authorize up to 500 reserved cents per Bangkok calendar day.
- Every paid task reserves 10 cents before calling OpenAI; optional second audit is included in that same reservation.
- No refunds for failed tasks; reservations are conservative and intentionally overstate estimated costs.
- This is **not a guarantee of billed USD cost**: token rates may change, model behavior may change, other OpenAI API keys/projects are outside this gate, and provider-side retries/charges may differ.
- No automated daily scheduling enabled. FLOP network eligibility remains unverified.

## Environment variables (Netlify branch context only)
- `AGENT_ACCESS_TOKEN`: private random token >=24 characters.
- `OPENAI_API_KEY`: OpenAI API key.
- `SUPABASE_URL`: private Supabase project URL.
- `SUPABASE_SERVICE_ROLE_KEY`: **server-side secret only**; never expose in client or public repository.
- `COMPUTEPILOT_LIVE_ENABLED`: set to `true` **only after** schema is installed, budget tests pass and costs reviewed. Omit otherwise.

## Before any live test
1. Verify SQL permissions and RLS, especially no anonymous access to tables or function.
2. Test concurrent requests against a throwaway database: <=50 approvals/day; 51st rejected.
3. Test midnight Asia/Bangkok reset and failed database requests (fail closed).
4. Check current OpenAI API pricing for the pinned `gpt-4.1-mini` model, max 2,000 characters input, max 400 answer tokens, and max 220 audit tokens. Confirm the 10-cent reservation comfortably exceeds worst-case actual provider cost.
5. Run unit tests and a single controlled live call.
6. Do not infer FLOP protocol participation from OpenAI response IDs.

## Known gaps
No cross-device task history, signed receipt keys, FLOP network adapter, automated scheduler, pricing reconciliation, or verified official FLOP integration yet. The current local SHA-256 receipt is not a signed proof.
