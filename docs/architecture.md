# Architecture

## Components

This service is intentionally small and follows a standard FastAPI layering approach:

- API layer: HTTP routes and dependency injection
- Service layer: XML parsing, content hashing, validation, normalization
- Repository layer: database read/write operations and atomic idempotency checks
- Model layer: SQLAlchemy ORM models for imports, vouchers, and nested XML-derived records
- Utility layer: XML sanitization, encoding detection, and hash helpers

## Request lifecycle

1. The client uploads a multipart file to `POST /api/tally/imports`.
2. FastAPI validates the request and imposes upload size limits.
3. The file bytes are read as-is and hashed using SHA-256 before interpretation.
4. The XML is decoded safely using a strict parser with DTD/entity protections disabled.
5. The parser determines whether the root is a supported `ENVELOPE` export or a `RESPONSE`.
6. The service normalizes the parsed structure into import summaries, warnings, and voucher records.
7. The import and nested voucher data are persisted via SQLAlchemy.
8. The service returns a structured response with `importId`, `status`, `duplicate`, and summary counts.

## Database design

The project uses SQLAlchemy with SQLite for a simple local-first setup. This satisfies the assignment’s database requirement while keeping the project easy to run and test locally.

Entities are designed around the underlying XML ownership model:

- `ImportRecord`: one uploaded XML payload, its hash, detected encoding, document type, and summary
- `VoucherRecord`: each voucher parsed from the XML; linked to the import
- `LedgerEntryRecord`: direct ledger entries beneath a voucher
- `BillAllocationRecord` and `BankAllocationRecord`: nested allocations owned by a ledger entry
- `InventoryEntryRecord`: inventory entries beneath a voucher
- `BatchAllocationRecord` and `AccountingAllocationRecord`: nested allocations owned by an inventory entry
- `RateDetailRecord`: rate detail rows owned by a direct parent node

This design makes the parent-child model inspectable in the database while still allowing a relatively straightforward relationship graph.

## Authentication

This assignment does not require application authentication. The service therefore avoids introducing JWT or session-based auth unless the assignment explicitly requires it. The focus is on XML import processing, normalization, and reliability.

## API structure

The API is intentionally narrow:

- `GET /health`
- `POST /api/tally/imports`
- `GET /api/tally/imports/{importId}`
- `GET /api/tally/imports/{importId}/vouchers`

This is enough to satisfy the contract without adding unrelated endpoints or admin surfaces.

## Important design decisions

### Atomic idempotency

The project uses the exact uploaded bytes to compute a SHA-256 digest. The import table enforces a unique content hash constraint, ensuring duplicate uploads are rejected as duplicates in a thread-safe, atomic way.

### Lossless money handling

The service stores values as source strings, not Python floats, to prevent rounding and sign corruption. This matches the assignment’s requirement to preserve financial values exactly.

### Source-order preservation

Repeated XML `.LIST` nodes are kept as ordered arrays, and each database row is linked to its direct parent record. This preserves source order and avoids accidental deduplication.

### Safe XML parsing

The XML parser is configured to disable DTD processing, external entities, and entity expansion. This enforces the security requirement without sacrificing the ability to parse the required contract files.

### Structured error handling

The service returns predictable JSON error payloads and avoids exposing stack traces, local paths, or full XML payloads.

## Result

The design balances the assignment’s required correctness, local usability, and a modest production-style structure without unnecessary complexity.
