from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.tally import (
    AccountingAllocationRecord,
    BankAllocationRecord,
    BatchAllocationRecord,
    BillAllocationRecord,
    ImportRecord,
    InventoryEntryRecord,
    LedgerEntryRecord,
    RateDetailRecord,
    VoucherRecord,
)


class TallyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_import_by_hash(self, content_hash: str) -> ImportRecord | None:
        return self.db.scalar(select(ImportRecord).where(ImportRecord.content_hash == content_hash))

    def get_import_by_id(self, import_id: str) -> ImportRecord | None:
        return self.db.get(ImportRecord, import_id)

    def create_import(self, payload: dict[str, Any]) -> ImportRecord:
        import_record = ImportRecord(
            id=payload["importId"],
            content_hash=payload["contentHash"],
            document_type=payload["documentType"],
            status=payload["status"],
            detected_encoding=payload["detectedEncoding"],
            duplicate=payload.get("duplicate", False),
            raw_upload=payload.get("rawUpload"),
            summary=payload["summary"],
            warnings=payload.get("warnings", []),
            errors=payload.get("errors", []),
            tally_response=payload.get("tallyResponse"),
        )
        self.db.add(import_record)
        self.db.flush()

        for voucher in payload.get("vouchers", []):
            voucher_record = VoucherRecord(
                id=voucher["id"],
                import_id=import_record.id,
                voucher_index=voucher["voucherIndex"],
                voucher_type=voucher.get("voucherType"),
                date=voucher.get("date"),
                voucher_number=voucher.get("voucherNumber"),
                party_ledger_name=voucher.get("partyLedgerName"),
                narration=voucher.get("narration"),
                attributes=voucher.get("attributes", {}),
                warnings=voucher.get("warnings", []),
            )
            self.db.add(voucher_record)
            self.db.flush()

            for ledger in voucher.get("ledgerEntries", []):
                ledger_record = LedgerEntryRecord(
                    id=ledger["id"],
                    voucher_id=voucher_record.id,
                    source_tag=ledger["sourceTag"],
                    ledger_name=ledger.get("ledgerName"),
                    is_deemed_positive=ledger.get("isDeemedPositive"),
                    amount=ledger.get("amount"),
                )
                self.db.add(ledger_record)
                self.db.flush()

                for bill in ledger.get("billAllocations", []):
                    self.db.add(
                        BillAllocationRecord(
                            id=bill["id"],
                            ledger_entry_id=ledger_record.id,
                            name=bill.get("name"),
                            bill_type=bill.get("billType"),
                            amount=bill.get("amount"),
                        )
                    )

                for bank in ledger.get("bankAllocations", []):
                    self.db.add(
                        BankAllocationRecord(
                            id=bank["id"],
                            ledger_entry_id=ledger_record.id,
                            date=bank.get("date"),
                            name=bank.get("name"),
                            transaction_type=bank.get("transactionType"),
                            amount=bank.get("amount"),
                        )
                    )

                for rate in ledger.get("rateDetails", []):
                    self.db.add(
                        RateDetailRecord(
                            id=rate["id"],
                            ledger_entry_id=ledger_record.id,
                            duty_head=rate.get("dutyHead"),
                            rate=rate.get("rate"),
                        )
                    )

            for inventory in voucher.get("inventoryEntries", []):
                inventory_record = InventoryEntryRecord(
                    id=inventory["id"],
                    voucher_id=voucher_record.id,
                    source_tag=inventory["sourceTag"],
                    stock_item_name=inventory.get("stockItemName"),
                    is_deemed_positive=inventory.get("isDeemedPositive"),
                    actual_qty=inventory.get("actualQty"),
                    billed_qty=inventory.get("billedQty"),
                    rate=inventory.get("rate"),
                    amount=inventory.get("amount"),
                )
                self.db.add(inventory_record)
                self.db.flush()

                for batch in inventory.get("batchAllocations", []):
                    self.db.add(
                        BatchAllocationRecord(
                            id=batch["id"],
                            inventory_entry_id=inventory_record.id,
                            godown_name=batch.get("godownName"),
                            batch_name=batch.get("batchName"),
                            actual_qty=batch.get("actualQty"),
                            billed_qty=batch.get("billedQty"),
                            amount=batch.get("amount"),
                        )
                    )

                for accounting in inventory.get("accountingAllocations", []):
                    accounting_record = AccountingAllocationRecord(
                        id=accounting["id"],
                        inventory_entry_id=inventory_record.id,
                        ledger_name=accounting.get("ledgerName"),
                        is_deemed_positive=accounting.get("isDeemedPositive"),
                        amount=accounting.get("amount"),
                    )
                    self.db.add(accounting_record)
                    self.db.flush()

                    for rate in accounting.get("rateDetails", []):
                        self.db.add(
                            RateDetailRecord(
                                id=rate["id"],
                                accounting_allocation_id=accounting_record.id,
                                duty_head=rate.get("dutyHead"),
                                rate=rate.get("rate"),
                            )
                        )

                for rate in inventory.get("rateDetails", []):
                    self.db.add(
                        RateDetailRecord(
                            id=rate["id"],
                            inventory_entry_id=inventory_record.id,
                            duty_head=rate.get("dutyHead"),
                            rate=rate.get("rate"),
                        )
                    )

        self.db.flush()
        return import_record

    def fetch_vouchers_for_import(self, import_id: str) -> list[dict[str, Any]]:
        vouchers = self.db.execute(
            select(VoucherRecord).where(VoucherRecord.import_id == import_id).order_by(VoucherRecord.voucher_index)
        ).scalars().all()
        out: list[dict[str, Any]] = []
        for voucher in vouchers:
            out.append(self._voucher_to_dict(voucher))
        return out

    def _voucher_to_dict(self, voucher: VoucherRecord) -> dict[str, Any]:
        payload = {
            "id": voucher.id,
            "source": {
                "importId": voucher.import_record.id,
                "contentHash": voucher.import_record.content_hash,
                "voucherIndex": voucher.voucher_index,
            },
            "attributes": voucher.attributes or {},
            "date": voucher.date,
            "voucherType": voucher.voucher_type,
            "voucherNumber": voucher.voucher_number,
            "partyLedgerName": voucher.party_ledger_name,
            "narration": voucher.narration,
            "ledgerEntries": [],
            "inventoryEntries": [],
            "warnings": voucher.warnings or [],
        }

        for ledger in voucher.ledger_entries:
            payload["ledgerEntries"].append(
                {
                    "sourceTag": ledger.source_tag,
                    "ledgerName": ledger.ledger_name,
                    "isDeemedPositive": ledger.is_deemed_positive,
                    "amount": ledger.amount,
                    "billAllocations": [
                        {
                            "name": item.name,
                            "billType": item.bill_type,
                            "amount": item.amount,
                        }
                        for item in ledger.bill_allocations
                    ],
                    "bankAllocations": [
                        {
                            "date": item.date,
                            "name": item.name,
                            "transactionType": item.transaction_type,
                            "amount": item.amount,
                        }
                        for item in ledger.bank_allocations
                    ],
                    "rateDetails": [
                        {"dutyHead": item.duty_head, "rate": item.rate} for item in ledger.rate_details
                    ],
                }
            )

        for inventory in voucher.inventory_entries:
            payload["inventoryEntries"].append(
                {
                    "sourceTag": inventory.source_tag,
                    "stockItemName": inventory.stock_item_name,
                    "isDeemedPositive": inventory.is_deemed_positive,
                    "actualQty": inventory.actual_qty,
                    "billedQty": inventory.billed_qty,
                    "rate": inventory.rate,
                    "amount": inventory.amount,
                    "batchAllocations": [
                        {
                            "godownName": item.godown_name,
                            "batchName": item.batch_name,
                            "actualQty": item.actual_qty,
                            "billedQty": item.billed_qty,
                            "amount": item.amount,
                        }
                        for item in inventory.batch_allocations
                    ],
                    "accountingAllocations": [
                        {
                            "ledgerName": item.ledger_name,
                            "isDeemedPositive": item.is_deemed_positive,
                            "amount": item.amount,
                            "rateDetails": [
                                {"dutyHead": rate.duty_head, "rate": rate.rate}
                                for rate in item.rate_details
                            ],
                        }
                        for item in inventory.accounting_allocations
                    ],
                    "rateDetails": [
                        {"dutyHead": item.duty_head, "rate": item.rate} for item in inventory.rate_details
                    ],
                }
            )
        return payload

    def save_import(self, payload: dict[str, Any]) -> ImportRecord:
        try:
            record = self.create_import(payload)
            self.db.commit()
            return record
        except IntegrityError:
            self.db.rollback()
            existing = self.get_import_by_hash(payload["contentHash"])
            if existing is not None:
                return existing
            raise

    def get_voucher_by_id(self, voucher_id: str) -> VoucherRecord | None:
        return self.db.get(VoucherRecord, voucher_id)

    def fetch_voucher_by_id(self, voucher_id: str) -> dict[str, Any]:
        voucher = self.db.get(VoucherRecord, voucher_id)
        if voucher is None:
            raise KeyError(f"Voucher {voucher_id} not found")
        return self._voucher_to_dict(voucher)

    def list_imports_with_vouchers(self) -> list[dict[str, Any]]:
        imports = self.db.execute(select(ImportRecord).order_by(ImportRecord.created_at)).scalars().all()
        result: list[dict[str, Any]] = []
        for import_record in imports:
            vouchers = self.db.execute(
                select(VoucherRecord.id).where(VoucherRecord.import_id == import_record.id).order_by(VoucherRecord.voucher_index)
            ).scalars().all()
            result.append({
                "importId": import_record.id,
                "documentType": import_record.document_type,
                "status": import_record.status,
                "voucherIds": list(vouchers),
            })
        return result
