from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ImportRecord(Base):
    __tablename__ = "imports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid4().hex)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    detected_encoding: Mapped[str | None] = mapped_column(String(32), nullable=True)
    duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_upload: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    errors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    tally_response: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    vouchers: Mapped[list["VoucherRecord"]] = relationship(back_populates="import_record", cascade="all, delete-orphan")


class VoucherRecord(Base):
    __tablename__ = "vouchers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid4().hex)
    import_id: Mapped[str] = mapped_column(String(64), ForeignKey("imports.id"), nullable=False, index=True)
    voucher_index: Mapped[int] = mapped_column(Integer, nullable=False)
    voucher_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    voucher_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    party_ledger_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    narration: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    import_record: Mapped[ImportRecord] = relationship(back_populates="vouchers")
    ledger_entries: Mapped[list["LedgerEntryRecord"]] = relationship(back_populates="voucher", cascade="all, delete-orphan")
    inventory_entries: Mapped[list["InventoryEntryRecord"]] = relationship(back_populates="voucher", cascade="all, delete-orphan")


class LedgerEntryRecord(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid4().hex)
    voucher_id: Mapped[str] = mapped_column(String(64), ForeignKey("vouchers.id"), nullable=False, index=True)
    source_tag: Mapped[str] = mapped_column(String(64), nullable=False)
    ledger_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_deemed_positive: Mapped[str | None] = mapped_column(String(32), nullable=True)
    amount: Mapped[str | None] = mapped_column(String(64), nullable=True)

    voucher: Mapped[VoucherRecord] = relationship(back_populates="ledger_entries")
    bill_allocations: Mapped[list["BillAllocationRecord"]] = relationship(back_populates="ledger_entry", cascade="all, delete-orphan")
    bank_allocations: Mapped[list["BankAllocationRecord"]] = relationship(back_populates="ledger_entry", cascade="all, delete-orphan")
    rate_details: Mapped[list["RateDetailRecord"]] = relationship(back_populates="ledger_entry", cascade="all, delete-orphan")


class BillAllocationRecord(Base):
    __tablename__ = "bill_allocations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid4().hex)
    ledger_entry_id: Mapped[str] = mapped_column(String(64), ForeignKey("ledger_entries.id"), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    bill_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    amount: Mapped[str | None] = mapped_column(String(64), nullable=True)

    ledger_entry: Mapped[LedgerEntryRecord] = relationship(back_populates="bill_allocations")


class BankAllocationRecord(Base):
    __tablename__ = "bank_allocations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid4().hex)
    ledger_entry_id: Mapped[str] = mapped_column(String(64), ForeignKey("ledger_entries.id"), nullable=False, index=True)
    date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    transaction_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    amount: Mapped[str | None] = mapped_column(String(64), nullable=True)

    ledger_entry: Mapped[LedgerEntryRecord] = relationship(back_populates="bank_allocations")


class InventoryEntryRecord(Base):
    __tablename__ = "inventory_entries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid4().hex)
    voucher_id: Mapped[str] = mapped_column(String(64), ForeignKey("vouchers.id"), nullable=False, index=True)
    source_tag: Mapped[str] = mapped_column(String(64), nullable=False)
    stock_item_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_deemed_positive: Mapped[str | None] = mapped_column(String(32), nullable=True)
    actual_qty: Mapped[str | None] = mapped_column(String(64), nullable=True)
    billed_qty: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rate: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[str | None] = mapped_column(String(64), nullable=True)

    voucher: Mapped[VoucherRecord] = relationship(back_populates="inventory_entries")
    batch_allocations: Mapped[list["BatchAllocationRecord"]] = relationship(back_populates="inventory_entry", cascade="all, delete-orphan")
    accounting_allocations: Mapped[list["AccountingAllocationRecord"]] = relationship(back_populates="inventory_entry", cascade="all, delete-orphan")
    rate_details: Mapped[list["RateDetailRecord"]] = relationship(back_populates="inventory_entry", cascade="all, delete-orphan")


class BatchAllocationRecord(Base):
    __tablename__ = "batch_allocations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid4().hex)
    inventory_entry_id: Mapped[str] = mapped_column(String(64), ForeignKey("inventory_entries.id"), nullable=False, index=True)
    godown_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    batch_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    actual_qty: Mapped[str | None] = mapped_column(String(64), nullable=True)
    billed_qty: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[str | None] = mapped_column(String(64), nullable=True)

    inventory_entry: Mapped[InventoryEntryRecord] = relationship(back_populates="batch_allocations")


class AccountingAllocationRecord(Base):
    __tablename__ = "accounting_allocations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid4().hex)
    inventory_entry_id: Mapped[str] = mapped_column(String(64), ForeignKey("inventory_entries.id"), nullable=False, index=True)
    ledger_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_deemed_positive: Mapped[str | None] = mapped_column(String(32), nullable=True)
    amount: Mapped[str | None] = mapped_column(String(64), nullable=True)

    inventory_entry: Mapped[InventoryEntryRecord] = relationship(back_populates="accounting_allocations")
    rate_details: Mapped[list["RateDetailRecord"]] = relationship(back_populates="accounting_allocation", cascade="all, delete-orphan")


class RateDetailRecord(Base):
    __tablename__ = "rate_details"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: uuid4().hex)
    ledger_entry_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("ledger_entries.id"), nullable=True, index=True)
    inventory_entry_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("inventory_entries.id"), nullable=True, index=True)
    accounting_allocation_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("accounting_allocations.id"), nullable=True, index=True)
    duty_head: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rate: Mapped[str | None] = mapped_column(String(64), nullable=True)

    ledger_entry: Mapped[LedgerEntryRecord | None] = relationship(back_populates="rate_details")
    inventory_entry: Mapped[InventoryEntryRecord | None] = relationship(back_populates="rate_details")
    accounting_allocation: Mapped[AccountingAllocationRecord | None] = relationship(back_populates="rate_details")
