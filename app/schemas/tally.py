from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SummarySchema(BaseModel):
    vouchers: int = 0
    ledgerEntries: int = 0
    inventoryEntries: int = 0
    warnings: int = 0
    errors: int = 0


class ImportUploadResponse(BaseModel):
    importId: str
    documentType: str
    status: str
    duplicate: bool = False
    summary: SummarySchema


class TallyResponseSummary(BaseModel):
    businessStatus: str
    counters: dict[str, str | int]
    lineError: str | None = None


class ImportDetailResponse(BaseModel):
    importId: str
    documentType: str
    status: str
    contentHash: str
    detectedEncoding: str | None = None
    summary: SummarySchema
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    tallyResponse: TallyResponseSummary | None = None


class VoucherSourceSchema(BaseModel):
    importId: str
    contentHash: str
    voucherIndex: int


class VoucherRateDetailSchema(BaseModel):
    dutyHead: str | None = None
    rate: str | None = None


class VoucherBillAllocationSchema(BaseModel):
    name: str | None = None
    billType: str | None = None
    amount: str | None = None


class VoucherBankAllocationSchema(BaseModel):
    date: str | None = None
    name: str | None = None
    transactionType: str | None = None
    amount: str | None = None


class VoucherLedgerEntrySchema(BaseModel):
    sourceTag: str
    ledgerName: str | None = None
    isDeemedPositive: str | None = None
    amount: str | None = None
    billAllocations: list[VoucherBillAllocationSchema] = Field(default_factory=list)
    bankAllocations: list[VoucherBankAllocationSchema] = Field(default_factory=list)
    rateDetails: list[VoucherRateDetailSchema] = Field(default_factory=list)


class VoucherBatchAllocationSchema(BaseModel):
    godownName: str | None = None
    batchName: str | None = None
    actualQty: str | None = None
    billedQty: str | None = None
    amount: str | None = None


class VoucherAccountingAllocationSchema(BaseModel):
    ledgerName: str | None = None
    isDeemedPositive: str | None = None
    amount: str | None = None
    rateDetails: list[VoucherRateDetailSchema] = Field(default_factory=list)


class VoucherInventoryEntrySchema(BaseModel):
    sourceTag: str
    stockItemName: str | None = None
    isDeemedPositive: str | None = None
    actualQty: str | None = None
    billedQty: str | None = None
    rate: str | None = None
    amount: str | None = None
    batchAllocations: list[VoucherBatchAllocationSchema] = Field(default_factory=list)
    accountingAllocations: list[VoucherAccountingAllocationSchema] = Field(default_factory=list)
    rateDetails: list[VoucherRateDetailSchema] = Field(default_factory=list)


class VoucherSchema(BaseModel):
    source: VoucherSourceSchema
    attributes: dict[str, str] = Field(default_factory=dict)
    date: str | None = None
    voucherType: str | None = None
    voucherNumber: str | None = None
    partyLedgerName: str | None = None
    narration: str | None = None
    ledgerEntries: list[VoucherLedgerEntrySchema] = Field(default_factory=list)
    inventoryEntries: list[VoucherInventoryEntrySchema] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class VoucherListResponse(BaseModel):
    items: list[VoucherSchema] = Field(default_factory=list)
    count: int = 0
