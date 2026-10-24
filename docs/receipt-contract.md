# Local receipt contract

This contract is ComputePilot's unsigned local integrity format. It is separate
from FLOP Appendix F receipts and does not verify model execution, authorship,
TOPLOC, network participation or settlement.

## Version 6

New records use schema `computepilot.receipt.v6` and
`record_encoding: computepilot.json.v1`. Remove only `record_sha256`, encode the
remaining object as below, then SHA-256 the UTF-8 bytes. Hash output text
independently as UTF-8 into `output_sha256`.

The same contract is implemented by `public/receipt-core.js` and
`computepilot/receipts.py`:

- JSON objects use string keys sorted lexicographically by Unicode code points,
  including numeric-looking keys. Nested objects follow the same ordering.
- Arrays retain their order. Strings retain their Unicode content without
  normalization; standard JSON quote, backslash and control-character escaping
  applies. Lone UTF-16 surrogate values are rejected.
- Values may be strings, booleans, null, arrays, objects or exact integers in
  `[-9007199254740991, 9007199254740991]`. Fractional numbers, nonfinite values,
  unsafe integers, cycles and non-JSON values are rejected. Encode decimal costs
  or timing quantities as explicit decimal strings in this receipt format.
- Serialization emits no optional whitespace. A new receipt's schema and
  encoding are themselves included in its hash.

The numeric restriction prevents silent differences in Python/JavaScript float
formatting and precision. Other V12 measurement report schemas continue to use
their existing numeric fields; they are not V6 job receipts.

## Version 5 compatibility

Old Python V5 records used sorted JSON, while the old browser accidentally used
insertion-order JSON. V5 records with no `record_encoding` may be checked against
either legacy layout for the supported JSON domain. They are identified as
legacy local integrity records. V6 records cannot opt into that fallback, and
unknown schemas/encodings fail verification. Historical fractional-number V5
records outside this domain require separate review and are not silently migrated.

Existing lab history uses the same browser storage key and is not rewritten on
load. A trusted original hash is needed to detect alteration; somebody able to
replace both a record and its hash can forge a new local integrity record.

## Tests and UI

`tests/fixtures/receipt-contract.json` freezes independent expected encodings and
digests, including nested data, numeric-looking keys, Unicode, escaping and safe
integer limits. Python invokes the Node/browser implementation to seal and verify
synthetic receipts in both directions. Separate mocked handler tests cover empty
and incomplete responses, missing IDs, audit failures and the disabled paid gate.

Run `python3 -m unittest discover -s tests -v` and `npm test` from the repository.
The Python contract suite requires Node 20+ on PATH. No dependency installation,
credentials, external service or GPU is needed. The browser checker processes
pasted job exports in memory and never uploads or persists them.
