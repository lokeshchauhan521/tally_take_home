"""Initial schema.

Revision ID: 20260825_0001
Revises: 
Create Date: 2026-08-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260825_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "imports",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("detected_encoding", sa.String(length=32), nullable=True),
        sa.Column("duplicate", sa.Boolean(), nullable=False),
        sa.Column("raw_upload", sa.LargeBinary(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("tally_response", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_imports_content_hash"), "imports", ["content_hash"], unique=True)

    op.create_table(
        "vouchers",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("import_id", sa.String(length=64), nullable=False),
        sa.Column("voucher_index", sa.Integer(), nullable=False),
        sa.Column("voucher_type", sa.String(length=128), nullable=True),
        sa.Column("date", sa.String(length=32), nullable=True),
        sa.Column("voucher_number", sa.String(length=128), nullable=True),
        sa.Column("party_ledger_name", sa.String(length=256), nullable=True),
        sa.Column("narration", sa.String(length=2048), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["import_id"], ["imports.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vouchers_import_id"), "vouchers", ["import_id"], unique=False)

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("voucher_id", sa.String(length=64), nullable=False),
        sa.Column("source_tag", sa.String(length=64), nullable=False),
        sa.Column("ledger_name", sa.String(length=256), nullable=True),
        sa.Column("is_deemed_positive", sa.String(length=32), nullable=True),
        sa.Column("amount", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["voucher_id"], ["vouchers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ledger_entries_voucher_id"), "ledger_entries", ["voucher_id"], unique=False)

    op.create_table(
        "bill_allocations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("ledger_entry_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("bill_type", sa.String(length=128), nullable=True),
        sa.Column("amount", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["ledger_entry_id"], ["ledger_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bill_allocations_ledger_entry_id"), "bill_allocations", ["ledger_entry_id"], unique=False)

    op.create_table(
        "bank_allocations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("ledger_entry_id", sa.String(length=64), nullable=False),
        sa.Column("date", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("transaction_type", sa.String(length=128), nullable=True),
        sa.Column("amount", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["ledger_entry_id"], ["ledger_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bank_allocations_ledger_entry_id"), "bank_allocations", ["ledger_entry_id"], unique=False)

    op.create_table(
        "inventory_entries",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("voucher_id", sa.String(length=64), nullable=False),
        sa.Column("source_tag", sa.String(length=64), nullable=False),
        sa.Column("stock_item_name", sa.String(length=256), nullable=True),
        sa.Column("is_deemed_positive", sa.String(length=32), nullable=True),
        sa.Column("actual_qty", sa.String(length=64), nullable=True),
        sa.Column("billed_qty", sa.String(length=64), nullable=True),
        sa.Column("rate", sa.String(length=64), nullable=True),
        sa.Column("amount", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["voucher_id"], ["vouchers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inventory_entries_voucher_id"), "inventory_entries", ["voucher_id"], unique=False)

    op.create_table(
        "batch_allocations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("inventory_entry_id", sa.String(length=64), nullable=False),
        sa.Column("godown_name", sa.String(length=256), nullable=True),
        sa.Column("batch_name", sa.String(length=256), nullable=True),
        sa.Column("actual_qty", sa.String(length=64), nullable=True),
        sa.Column("billed_qty", sa.String(length=64), nullable=True),
        sa.Column("amount", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["inventory_entry_id"], ["inventory_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_batch_allocations_inventory_entry_id"), "batch_allocations", ["inventory_entry_id"], unique=False)

    op.create_table(
        "accounting_allocations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("inventory_entry_id", sa.String(length=64), nullable=False),
        sa.Column("ledger_name", sa.String(length=256), nullable=True),
        sa.Column("is_deemed_positive", sa.String(length=32), nullable=True),
        sa.Column("amount", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["inventory_entry_id"], ["inventory_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_accounting_allocations_inventory_entry_id"), "accounting_allocations", ["inventory_entry_id"], unique=False)

    op.create_table(
        "rate_details",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("ledger_entry_id", sa.String(length=64), nullable=True),
        sa.Column("inventory_entry_id", sa.String(length=64), nullable=True),
        sa.Column("accounting_allocation_id", sa.String(length=64), nullable=True),
        sa.Column("duty_head", sa.String(length=128), nullable=True),
        sa.Column("rate", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["ledger_entry_id"], ["ledger_entries.id"]),
        sa.ForeignKeyConstraint(["inventory_entry_id"], ["inventory_entries.id"]),
        sa.ForeignKeyConstraint(["accounting_allocation_id"], ["accounting_allocations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rate_details_ledger_entry_id"), "rate_details", ["ledger_entry_id"], unique=False)
    op.create_index(op.f("ix_rate_details_inventory_entry_id"), "rate_details", ["inventory_entry_id"], unique=False)
    op.create_index(op.f("ix_rate_details_accounting_allocation_id"), "rate_details", ["accounting_allocation_id"], unique=False)


def downgrade() -> None:
    op.drop_table("rate_details")
    op.drop_table("accounting_allocations")
    op.drop_table("batch_allocations")
    op.drop_table("inventory_entries")
    op.drop_table("bank_allocations")
    op.drop_table("bill_allocations")
    op.drop_table("ledger_entries")
    op.drop_table("vouchers")
    op.drop_index(op.f("ix_imports_content_hash"), table_name="imports")
    op.drop_table("imports")
