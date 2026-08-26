# Requirements Checklist

| Requirement | Implemented | Evidence/Test |
| --- | --- | --- |
| Health check endpoint | Yes | `GET /health` in `app/main.py`, verified via `pytest` |
| Multipart import endpoint | Yes | `POST /api/tally/imports` in `app/api/routes/tally.py` |
| `ENVELOPE` voucher import | Yes | Fixtures `01_receipt_with_allocations.xml`, `02_sales_invoice_nested.xml`, `05_empty_collection.xml` |
| `RESPONSE` Tally import | Yes | Fixture `03_tally_error_response.xml`; `businessStatus: failed` assertion in tests |
| Exact-byte SHA-256 content identity | Yes | `app/services/tally_service.py` computes `hashlib.sha256(file_bytes).hexdigest()` |
| Atomic idempotency | Yes | Duplicate fixture test verifies same import id and `duplicate: true` |
| Import details endpoint | Yes | `GET /api/tally/imports/{importId}` |
| Voucher list endpoint | Yes | `GET /api/tally/imports/{importId}/vouchers` |
| Preserve parent-child ownership | Yes | `app/services/tally_service.py` parses direct children and keeps arrays under their owner |
| Preserve repeated `.LIST` order | Yes | Voucher arrays built in source order from parsed XML |
| Lossless financial and quantity values | Yes | Values stored as source strings, not floats |
| UTF-8, BOM, UTF-16 handling | Yes | Fixture `07_utf8_bom_payment.xml` and `04_utf16_invalid_control_ref.xml` |
| Illegal control references sanitized with warning | Yes | `app/utils/xml.py` sanitizes numeric refs and records warning |
| Empty collection handling | Yes | `05_empty_collection.xml` test passes |
| Unknown children do not crash | Yes | Unknown branches are ignored with warnings |
| Raw-source retention | Yes | `ImportRecord.raw_upload` stores uploaded bytes |
| Safe XML parsing | Yes | DTD/entity protection enforced in parser approach |
| Upload limit enforcement | Yes | Configurable `UPLOAD_MAX_SIZE_MB` in `app/core/config.py` |
| Structured errors | Yes | FastAPI JSON responses and 400/404 handling |
| Database-backed persistence | Yes | SQLAlchemy models and SQLite DB |
| Inspectable relationships | Yes | Models link imports -> vouchers -> ledger entries, inventory entries, allocations |
| pytest coverage | Yes | `tests/test_tally_api.py` with 7 behavioral tests |
| README + docs | Yes | `README.md`, `docs/assignment-analysis.md`, `docs/architecture.md`, `docs/requirements-checklist.md` |

## Notes

- Optional partial-failure extension is intentionally not implemented in the required core.
- The project uses SQLite by default for a simple local implementation, while keeping the architecture compatible with a production SQLAlchemy-based transition.
