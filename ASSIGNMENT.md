# Assignment

Build a small backend service that ingests Tally XML and exposes normalized vouchers without losing parent-child relationships.

Prior Tally knowledge is not expected. Treat this document, the normalized contract, and the supplied fixtures as the complete integration contract.

## Scope And Priority

The **required core** is what we score. Complete it before attempting an extension.

The **optional extensions** are genuinely optional. An incomplete extension is not a hidden failure, and a candidate can receive a positive result without implementing any extension.

## The Core Problem

Tally XML cannot safely be flattened into an object such as `{ tagName: value }`.

For example, all of these nodes may exist in one voucher:

```text
VOUCHER/ALLLEDGERENTRIES.LIST/AMOUNT
VOUCHER/ALLLEDGERENTRIES.LIST/BILLALLOCATIONS.LIST/AMOUNT
VOUCHER/ALLINVENTORYENTRIES.LIST/AMOUNT
VOUCHER/ALLINVENTORYENTRIES.LIST/BATCHALLOCATIONS.LIST/AMOUNT
VOUCHER/ALLINVENTORYENTRIES.LIST/ACCOUNTINGALLOCATIONS.LIST/AMOUNT
```

They share the tag name `AMOUNT`, but each value belongs to a different parent. The same issue applies to `NAME`, `DATE`, `LEDGERNAME`, `RATE`, `ACTUALQTY`, and `BILLEDQTY`.

Your service must preserve that ownership and source order.

## Required HTTP API

### Health Check

```http
GET /health
```

Return HTTP `200` with a JSON object indicating that the service is running.

### Import XML

```http
POST /api/tally/imports
Content-Type: multipart/form-data
```

The multipart field must be named `file`. For the required core, the endpoint accepts both supported document shapes:

- `ENVELOPE` containing `BODY/DATA/COLLECTION/VOUCHER`: a voucher export.
- `RESPONSE`: the result of a Tally operation.

Tally can produce other envelope and report variants in production. They are outside the required core unless listed as an optional extension.

Return HTTP `201` for newly accepted content and HTTP `200` when the exact bytes were imported earlier.

Required response shape:

```json
{
  "importId": "stable-id",
  "documentType": "voucherExport",
  "status": "completed",
  "duplicate": false,
  "summary": {
    "vouchers": 1,
    "ledgerEntries": 2,
    "inventoryEntries": 0,
    "warnings": 0,
    "errors": 0
  }
}
```

Rules:

- `documentType` is `voucherExport` for `ENVELOPE` and `tallyResponse` for `RESPONSE`.
- `status: completed` means the supported document was decoded, parsed, and persisted. It does **not** mean that the Tally business operation succeeded.
- `status: partial` is used only if you implement the optional per-voucher partial-failure extension.
- `status: failed` may be used if you choose to persist an import that could not be safely processed.
- Syntactically unreadable or unsupported documents may instead return a documented structured `4xx` error.
- A valid empty collection is `completed` with zero counts; it is not an error.

Compute content identity from the exact uploaded bytes using SHA-256. Return the lowercase 64-character hexadecimal hash in import details. Filename, whitespace-normalized XML, and decoded text are not content identity.

Idempotency must be protected atomically by the database or persistence layer. A check-then-insert sequence without a uniqueness guarantee is not sufficient under concurrent requests.

### Import Details

```http
GET /api/tally/imports/{importId}
```

Return a JSON object containing at least:

```json
{
  "importId": "stable-id",
  "documentType": "voucherExport",
  "status": "completed",
  "contentHash": "lowercase-sha256-hex",
  "detectedEncoding": "UTF-8",
  "summary": {},
  "warnings": [],
  "errors": []
}
```

For a `tallyResponse`, details must also contain:

```json
{
  "tallyResponse": {
    "businessStatus": "failed",
    "counters": {
      "CREATED": "0",
      "ALTERED": "0",
      "DELETED": "0",
      "IGNORED": "1",
      "ERRORS": "1"
    },
    "lineError": "Demo ledger does not exist"
  }
}
```

The details `summary` uses the same five integer fields as the upload response: `vouchers`, `ledgerEntries`, `inventoryEntries`, `warnings`, and `errors`.

For this exercise, `businessStatus` is `failed` when `ERRORS` is greater than zero or `LINEERROR` is non-empty. Otherwise it is `succeeded`. Counter values may be source strings or lossless integers, but use one representation consistently.

Do not expose raw XML, secrets, stack traces, or local filesystem paths through this endpoint.

### Normalized Vouchers

```http
GET /api/tally/imports/{importId}/vouchers
```

Return:

```json
{
  "items": [],
  "count": 0
}
```

Each voucher item must follow [NORMALIZED_DATA_CONTRACT.md](NORMALIZED_DATA_CONTRACT.md). A `tallyResponse` import has zero vouchers.

## Required XML Behavior

### 1. Preserve The Tree

- Voucher scalar children remain separate from ledger and inventory children.
- Every supported repeated `.LIST` occurrence remains an ordered array item, even when only one occurrence exists.
- Keep `BILLALLOCATIONS.LIST`, `BANKALLOCATIONS.LIST`, `BATCHALLOCATIONS.LIST`, `ACCOUNTINGALLOCATIONS.LIST`, and `RATEDETAILS.LIST` under the direct parent where they appeared.
- Preserve `ALLLEDGERENTRIES.LIST` versus `LEDGERENTRIES.LIST` using `sourceTag`.
- Preserve `ALLINVENTORYENTRIES.LIST` using `sourceTag`.
- Parse supported fields from direct children, not descendant-wide searches.

Only the paths described in the normalized contract are required. Broad Tally support is out of scope.

### 2. Preserve Financial Values Losslessly

- Do not use binary floating-point for money.
- Returning signed amounts as source strings is recommended.
- Do not turn `-1250.00` into `1250.00` based on `ISDEEMEDPOSITIVE`.
- Preserve quantity and rate text containing units, such as `2 PCS` or `50.00/PCS`.
- Do not combine child rows merely because their values are equal.

### 3. Decode The Supplied Encodings

Support:

- UTF-8.
- UTF-8 with BOM.
- UTF-16 with BOM.
- Illegal XML 1.0 numeric control references such as `&#4;` in otherwise recoverable text.

If sanitization is required, record a warning. Retain the original uploaded bytes or a secure raw-source reference so the decision can be investigated later.

### 4. Handle Unknown Children Safely

Tally installations may include custom UDF or unknown child nodes.

- Unknown nodes must not crash the import.
- Do not claim unknown fields were normalized when they were not.
- Retaining the complete raw upload satisfies source preservation for the core exercise.
- Record a warning when source data was retained but not normalized.

### 5. Parse Tally Response XML

When the root is `RESPONSE`, parse these direct children when present:

- `CREATED`
- `ALTERED`
- `DELETED`
- `IGNORED`
- `ERRORS`
- `LINEERROR`

The upload request can return HTTP `201` while `tallyResponse.businessStatus` is `failed`. Transport acceptance, document processing, and Tally business outcome are three separate facts.

## Persistence Requirements

Use SQLite, PostgreSQL, or another documented database. In-memory-only storage does not satisfy the core requirement.

The persisted model must make these relationships inspectable:

- Import to vouchers.
- Voucher to ledger entries.
- Ledger entry to bill allocations and bank allocations.
- Voucher to inventory entries.
- Inventory entry to batch allocations and accounting allocations.
- An owning ledger, inventory, or accounting-allocation node to its rate details.

JSON columns are allowed where justified. Explain why you chose relational rows, JSON, or a hybrid. Retain source order for every repeated array.

## Security And Operations

At minimum:

- Enforce a configurable upload-size limit.
- Disable or reject DTD/external entity processing and entity expansion.
- Do not execute XML-provided content.
- Do not log complete raw accounting XML.
- Return structured errors without stack traces or local paths.

Briefly document additional production controls you would add.

## Automated Tests

Include behavioral tests covering at least:

1. Repeated ledger entries remain separate and ordered.
2. Ledger, bill, inventory, batch, and accounting `AMOUNT` values are not overwritten.
3. Duplicate bytes under a different filename return the original import without duplicate vouchers.
4. UTF-16 and illegal-control-reference recovery records a warning.
5. A Tally response with `ERRORS=1` has `businessStatus: failed` even though the upload was accepted.
6. An empty collection and an unknown child do not crash or invent vouchers.

Tests may be unit, integration, or a sensible mix. They must run with one documented command.

## Required Large-File Design Note

You do not need to include a large fixture or implement streaming in the core.

In your README, explain how a production version would ingest a 500 MB export with bounded memory. Cover:

- Incremental XML parsing and object boundaries.
- Database chunking, restart checkpoints, and idempotency.
- Raw-file storage, cleanup, backpressure, and request timeouts.

Specific tradeoffs are more valuable than naming a streaming library.

## Optional Extensions

Attempt these only after the core is correct:

1. **Per-voucher partial failure:** treat a voucher missing `DATE`, `VOUCHERTYPENAME`, or `VOUCHERNUMBER` as an object-level error; persist other valid vouchers; return `status: partial`; leave no child rows for the invalid voucher.
2. **Streaming implementation:** process vouchers incrementally with bounded memory rather than loading the complete decoded document.
3. **Concurrency proof:** add a test showing simultaneous uploads of identical bytes produce one import.
4. **Richer unknown-node preservation:** persist source paths or unknown subtrees in addition to retaining the raw upload.
5. **Alternate response envelope:** normalize counters from `ENVELOPE/BODY/DATA/IMPORTRESULT` into the same `tallyResponse` details shape.

State which extensions, if any, you attempted. Optional work should not weaken the required core.

## What To Submit

- Source code.
- Database schema or migrations.
- Automated tests.
- A project README with one-command startup, setup, migration, and test instructions.
- API examples using curl or equivalent.
- Design and tradeoff notes, including the large-file note.
- Approximate active time and incomplete work.
- AI usage disclosure.

The service must run locally using one documented command. Docker Compose is welcome but not required.

## Scoring Shared With Candidates

| Area | Points | What produces evidence |
| --- | ---: | --- |
| XML ownership and normalization | 30 | Direct-parent parsing, ordered arrays, exact values, required JSON contract |
| Persistence and idempotency | 20 | Inspectable relationships, raw-source traceability, atomic content-hash uniqueness |
| Reliability and diagnostics | 15 | Encodings, sanitization warning, empty/unknown handling, Tally business result |
| Automated tests | 15 | Behavioral assertions that would catch real regressions |
| Security | 5 | Entity defense, limits, safe logging, structured errors |
| Large-file design | 5 | Concrete bounded-memory, restart, storage, and backpressure reasoning |
| Clarity and engineering judgment | 10 | Reproducible setup, focused code, honest assumptions and tradeoffs |
| **Total** | **100** |  |

The integrity gates are parent-child ownership, lossless money, content-based idempotency, safe XML entity handling, and correct Tally business-failure interpretation. A severe failure in one of these can outweigh polish elsewhere.

We do not score prior Tally knowledge, framework choice, unrelated UI, authentication, deployment infrastructure, or optional-extension count. Private checks use unseen variants of disclosed core rules; the partial-failure extension is checked only when a candidate says it is implemented.
