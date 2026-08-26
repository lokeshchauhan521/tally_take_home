# Assignment Analysis

## Assignment Summary

This project is a take-home backend engineering challenge focused on ingesting Tally XML exports and Tally operation responses, preserving the original parent-child ownership of repeated XML nodes, and exposing normalized vouchers through a small FastAPI service.

The core business problem is that Tally XML repeats tags such as `AMOUNT`, `RATE`, `LEDGERNAME`, and `DATE` under multiple parent collections (`ALLLEDGERENTRIES.LIST`, `BILLALLOCATIONS.LIST`, `ALLINVENTORYENTRIES.LIST`, etc.). A naive flattening strategy would lose ownership and produce incorrect data. The service must therefore preserve source paths, direct parent relationships, repeated list ordering, and lossless source text for financial values.

The assignment explicitly defines the required integration contract using:

- `ASSIGNMENT.md`
- `NORMALIZED_DATA_CONTRACT.md`
- `SUBMISSION_CHECKLIST.md`
- fixture XML examples under `fixtures/`

The repository is intentionally minimal and does not include a prebuilt app; it is a greenfield implementation task.

## Functional Requirements

### Required API endpoints

- `GET /health`
  - Returns HTTP 200 with a simple JSON health payload.

- `POST /api/tally/imports`
  - Accepts multipart form-data with a single field named `file`.
  - Supports root document types:
    - `ENVELOPE` with `BODY/DATA/COLLECTION/VOUCHER`
    - `RESPONSE` for Tally operation result XML
  - Computes exact-byte SHA-256 as content identity.
  - Uses atomic idempotency: duplicate content under a different filename must return the original import instead of creating a duplicate record.
  - Returns `201` for newly accepted content and `200` when the exact bytes were previously imported.

- `GET /api/tally/imports/{importId}`
  - Returns import metadata, content hash, detected encoding, status, warnings/errors, and Tally response details when applicable.
  - Must not expose raw XML, stack traces, or filesystem paths.

- `GET /api/tally/imports/{importId}/vouchers`
  - Returns a paginated-style JSON object with `items` and `count`.
  - Each voucher must follow the normalized contract precisely.
  - A `tallyResponse` import has zero vouchers.

### XML normalization behavior

- Preserve direct-parent ownership rather than flattening across all matching tags.
- Preserve repeated `.LIST` nodes as arrays in source order.
- Keep `BILLALLOCATIONS.LIST`, `BANKALLOCATIONS.LIST`, `BATCHALLOCATIONS.LIST`, `ACCOUNTINGALLOCATIONS.LIST`, and `RATEDETAILS.LIST` under the direct parent that owns them.
- Preserve `ALLLEDGERENTRIES.LIST` vs `LEDGERENTRIES.LIST` using `sourceTag`.
- Preserve `ALLINVENTORYENTRIES.LIST` using `sourceTag`.
- Parse only supported paths and do not overreach into descendants.
- Preserve financial and quantity strings losslessly; do not convert values to binary floating point.
- Preserve values such as `2 PCS`, `50.00/PCS`, negative signed money, and source strings exactly as provided.
- Never merge child rows just because values happen to match.

### Encoding and sanitization

The service must support:

- UTF-8
- UTF-8 with BOM
- UTF-16 with BOM
- XML with illegal XML 1.0 numeric control references such as `&#4;` when recoverable

If sanitization is required, a warning must be recorded. The raw uploaded bytes or a secure raw-source reference must be retained for later investigation.

### Unknown data handling

- Unknown child nodes must not crash ingestion.
- Unknown fields must not be falsely presented as normalized data.
- A warning should be recorded when source data is retained but not normalized.

### Tally response handling

When the root is `RESPONSE`, the service must read direct children:

- `CREATED`
- `ALTERED`
- `DELETED`
- `IGNORED`
- `ERRORS`
- `LINEERROR`

A `tallyResponse` is considered `businessStatus: failed` when:

- `ERRORS` > 0, or
- `LINEERROR` is non-empty

Otherwise it is `succeeded`.

This is independent from upload acceptance; an HTTP `201` does not mean the business operation succeeded.

## Technical Requirements

### Languages and framework

- Python
- FastAPI
- Pydantic
- SQLAlchemy or SQLModel
- PostgreSQL preferred for production-style relational implementation
- Alembic if using PostgreSQL/SQLAlchemy
- Avoid Django

The assignment does not require authentication or a UI; this is a small backend service.

### Persistence requirements

- Must use a real database, not in-memory-only storage.
- Relationship visibility is required:
  - Import to vouchers
  - Voucher to ledger entries
  - Ledger entry to bill allocations and bank allocations
  - Voucher to inventory entries
  - Inventory entry to batch allocations and accounting allocations
  - Owning node to `rateDetails`
- Source order for repeated arrays must be retained.
- JSON columns are acceptable where justified.
- The service must support atomic content-hash uniqueness.

### Security and operational requirements

- Configurable upload-size limit
- Disable or reject DTD/external entity processing and entity expansion
- Do not execute XML-provided content
- Do not log raw accounting XML
- Return structured errors without stack traces or local file paths
- Document additional production controls to add later

## API Requirements

### Import response schema

The API must return a JSON object in the shape:

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

`documentType` is:

- `voucherExport` for `ENVELOPE`
- `tallyResponse` for `RESPONSE`

`status` should be `completed` for valid supported documents and may be `failed` for unsupported or unsafe input, with optional `partial` if the extension is implemented.

### Import details schema

Required details include:

- `importId`
- `documentType`
- `status`
- `contentHash`
- `detectedEncoding`
- `summary`
- `warnings`
- `errors`
- `tallyResponse` object for a Tally response import

### Voucher response schema

The voucher JSON must match `NORMALIZED_DATA_CONTRACT.md` precisely. The required fields include:

- `source.importId`
- `source.contentHash`
- `source.voucherIndex`
- `attributes`
- `date`
- `voucherType`
- `voucherNumber`
- `partyLedgerName`
- `narration`
- `ledgerEntries[]`
- `inventoryEntries[]`
- `warnings[]`

Each array field must remain an array even if empty or length 1.

## Database Requirements

The assignment allows SQLite, PostgreSQL, or another documented database, but a database-backed persistence layer is mandatory. SQLite is the simplest implementation path for a local run, but a production-style PostgreSQL + SQLAlchemy + Alembic design is acceptable if the project is set up for that pattern.

The database must support:

- persistent import records
- persistent voucher records
- nested ledger entries and inventory entries
- nested allocations and `rateDetails`
- raw source retention or secure reference keepers
- content hash uniqueness
- import status and error/warning tracking

The exact architecture choice should balance simplicity with the requirement for inspectable relationships and idempotent atomic insertion.

## Architecture Recommendation

A simple, production-friendly FastAPI architecture is recommended:

- `app/main.py` — application entrypoint
- `app/api/routes/` — HTTP router(s)
- `app/core/config.py` — environment config
- `app/db/database.py` — SQLAlchemy engine/session config
- `app/models/` — SQLAlchemy models
- `app/schemas/` — Pydantic request/response models
- `app/services/` — XML parsing and business logic
- `app/repositories/` — DB access and transaction boundaries
- `app/utils/` — XML decoding, hashing, sanitization helpers

This matches the assignment’s favored layering:

FastAPI -> API Router -> Service Layer -> Repository/Data Access -> Database

This is sufficient without overengineering. The main concern is not “framework prettiness” but correctness at the XML ownership and atomic idempotency boundaries.

## Testing Strategy

Tests must cover at least the required scenarios:

1. Repeated ledger entries remain separate and ordered.
2. Different `AMOUNT` fields are not overwritten across ledger, bill, inventory, batch, and accounting nodes.
3. Duplicate bytes under a different filename return the original import instead of creating a duplicate voucher set.
4. UTF-16 and illegal-control recovery record a warning.
5. A Tally response with `ERRORS=1` is `businessStatus: failed` even when upload was accepted.
6. Empty collections and unknown children do not crash or invent vouchers.
7. Validation errors are surfaced predictably.

Preferred test mode:

- pytest
- FastAPI TestClient or httpx
- a small in-memory SQLite database for isolated tests
- fixture-driven tests using the supplied XML files

## Potential Risks / Ambiguities

- The assignment allows SQLite or PostgreSQL, but the repository doesn’t mandate one. We should choose a documented approach that satisfies the requirement without unnecessary complexity.
- The assignment says the core is required and optional extensions are not necessary. We should not over-invest in optional work before the required behavior is correct.
- Unknown-node preservation and warning semantics are not fully specified beyond “retain raw upload and warn,” so a documented, conservative interpretation is acceptable.
- The assignment allows source strings or integers for counters, but the API contract should remain consistent and clearly documented.
- The exact raw-upload retention strategy can vary, but it must be secure, inspectable, and non-raw-log exposure.

## Key Takeaways

The critical integrity gates are:

- parent-child ownership preservation,
- exact-value financial preservation,
- exact-byte SHA-256 idempotency,
- safe XML parsing and entity defense,
- proper Tally business-failure interpretation.

A polished implementation is not sufficient if these fail. The required core should be completed first with tests proving the critical behaviors, then optional extensions can be considered if time permits.
