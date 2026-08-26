# Tally XML Ingestion API

## Overview

This project implements a FastAPI backend that ingests Tally XML exports and Tally response XML, preserves parent-child ownership and repeated list ordering, and exposes normalized voucher data.

The required core behavior is:

- accept multipart XML uploads
- detect and decode UTF-8, UTF-8 BOM, and UTF-16 BOM inputs
- sanitize illegal XML numeric control references when needed
- compute exact-byte SHA-256 idempotency
- persist import metadata and vouchers in a database
- expose import details and normalized vouchers through HTTP endpoints
- handle empty collections and Tally business failures without crashing

## Prerequisites

- Python 3.12+
- virtual environment support
- Git

## Installation

```bash
cd /path/to/your/project
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Environment Variables

Create a local `.env` file from the example:

```bash
cp .env.example .env
```

Example values:

```env
APP_NAME=Tally XML Ingestion API
APP_ENV=development
UPLOAD_MAX_SIZE_MB=10
DATABASE_URL=sqlite:///./tally.db
```

## Start the Project

Run the API:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload 
```

Open the API docs:

- http://localhost:8000/docs
- http://localhost:8000/redoc
- http://localhost:8000/openapi.json

## API Endpoints

### Health check

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok","service":"Tally XML Ingestion API"}
```

### Upload XML

```bash
curl -X POST http://localhost:8000/api/tally/imports \
  -F "file=@fixtures/01_receipt_with_allocations.xml"
```

The multipart field name must be `file`.

Required upload behavior:

- `ENVELOPE` root is treated as a voucher export.
- `RESPONSE` root is treated as a Tally response document.
- returns `201` for new content
- returns `200` when the same exact bytes were uploaded earlier
- uses SHA-256 of the exact uploaded bytes as content identity
- idempotency is enforced in the database

Example response:

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

### Get import details

```bash
curl http://localhost:8000/api/tally/imports/<importId>
```

This returns:

- `importId`
- `documentType`
- `status`
- `contentHash`
- `detectedEncoding`
- `summary`
- `warnings`
- `errors`
- `tallyResponse` when the source document is `RESPONSE`

### Get normalized vouchers

```bash
curl http://localhost:8000/api/tally/imports/<importId>/vouchers
```

Response shape:

```json
{
  "items": [],
  "count": 0
}
```

Each voucher item follows the assignment’s normalized contract.

## How the Workflow Works

1. File upload arrives as multipart form-data.
2. The service reads the raw bytes exactly as uploaded.
3. A SHA-256 hash is computed from those exact bytes.
4. The XML is decoded safely:
   - UTF-8
   - UTF-8 with BOM
   - UTF-16 with BOM
   - illegal XML numeric control references are sanitized when possible
5. The service checks the root element:
   - `ENVELOPE` => voucher export
   - `RESPONSE` => Tally response
6. The XML is normalized in a parent-aware way:
   - direct children are parsed, not descendant-wide searches
   - repeated `.LIST` nodes remain arrays in source order
   - financial values and quantities remain strings
   - `AMOUNT` values from different parents are never overwritten
7. The import and voucher records are saved to the database.
8. The API returns the import summary and the normalized voucher list.
9. Duplicate exact bytes return the original import instead of creating a second import record.

Important integrity rules from the assignment:

- preserve `ALLLEDGERENTRIES.LIST` vs `LEDGERENTRIES.LIST` using `sourceTag`
- preserve `ALLINVENTORYENTRIES.LIST` using `sourceTag`
- preserve `BILLALLOCATIONS.LIST`, `BANKALLOCATIONS.LIST`, `BATCHALLOCATIONS.LIST`, `ACCOUNTINGALLOCATIONS.LIST`, and `RATEDETAILS.LIST` under their owning parent
- do not convert money to binary float
- do not flatten repeated nodes into a single object

## Database Setup

This project uses SQLite by default for local execution.

Migrations are configured with Alembic:

```bash
source .venv/bin/activate
alembic upgrade head
```

## Testing

Run the full test suite:

```bash
source .venv/bin/activate
pytest -q
```

The tests cover:

- repeated ledger entries remain separate and ordered
- ledger and inventory `AMOUNT` values are not overwritten
- duplicate bytes under different filenames return the same import
- UTF-16 and illegal numeric control decoding warnings
- Tally `ERRORS=1` leads to `businessStatus: failed`
- empty collections and unknown children do not crash the import

## What Is Complete

The required core implementation is complete:

- health endpoint
- XML upload endpoint
- import details endpoint
- voucher normalization endpoint
- duplicate content idempotency
- UTF-8 and UTF-16 handling
- Tally response parsing
- empty-collection handling
- automated pytest coverage

## What Is Not Implemented

Optional extensions are not required for the assignment and are intentionally not included in the required core.

## Approximate Active Time

About 5 to 6 hours.

## Production Risk

The current implementation is intentionally simple and uses SQLite for local execution. For a large production workload, the main risks are:

- higher-volume concurrency
- very large XML documents
- long-running import processing
- raw-file retention policies

## AI Tool Usage Disclosure

AI tools were used to help with code authoring, debugging, and validation. The code paths, fixture behavior, API flow, and final validation were personally checked before completion.
