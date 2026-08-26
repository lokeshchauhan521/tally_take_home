# Submission Checklist

Before submitting, please confirm:

- [ ] I stopped at or before 6 hours and recorded my approximate active time.
- [ ] `GET /health` works.
- [ ] `POST /api/tally/imports` accepts multipart field `file`.
- [ ] `GET /api/tally/imports/{importId}` returns import details.
- [ ] `GET /api/tally/imports/{importId}/vouchers` returns the normalized contract.
- [ ] Both `ENVELOPE` and `RESPONSE` roots are handled as documented.
- [ ] Repeated `.LIST` nodes remain arrays under their direct parent.
- [ ] Signed amounts are lossless and not stored as binary floating-point.
- [ ] UTF-8, BOM, and UTF-16 behavior is tested.
- [ ] Duplicate content is idempotent regardless of filename.
- [ ] Exact-byte SHA-256 uniqueness is enforced atomically in persistence.
- [ ] Import warnings and errors are persisted.
- [ ] Raw source or a secure raw-source reference is retained.
- [ ] Tally `ERRORS` and `LINEERROR` produce `businessStatus: failed` without confusing upload acceptance.
- [ ] Unknown children do not crash ingestion and produce a warning.
- [ ] An empty collection completes with zero vouchers.
- [ ] Tests run with one documented command.
- [ ] Database setup/migrations are documented.
- [ ] The 500 MB ingestion design is explained.
- [ ] Security assumptions are explained.
- [ ] Incomplete work and next steps are stated honestly.
- [ ] AI tool usage is disclosed.

Optional extensions:

- [ ] If I claim per-voucher partial failure, I tested valid and invalid vouchers in one document.
- [ ] I listed every optional extension I attempted and did not present unimplemented work as complete.
