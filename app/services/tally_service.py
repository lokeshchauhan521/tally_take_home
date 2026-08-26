from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any
import xml.etree.ElementTree as ET

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.tally_repository import TallyRepository
from app.utils.xml import parse_xml_document


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _text(node: ET.Element | None) -> str | None:
    if node is None or node.text is None:
        return None
    value = node.text.strip()
    return value if value else None


def _coerce_int(value: str | None) -> int:
    if value is None:
        return 0
    try:
        return int(str(value).strip())
    except ValueError:
        return 0


def _record_warning(warnings: list[str], message: str) -> None:
    if message and message not in warnings:
        warnings.append(message)


def _parse_rate_details(node_list: list[ET.Element]) -> list[dict[str, str | None]]:
    items: list[dict[str, str | None]] = []
    for element in node_list:
        item: dict[str, str | None] = {}
        for child in list(element):
            tag = child.tag
            if tag in {"GSTRATEDUTYHEAD", "DUTYHEAD"}:
                item["dutyHead"] = _text(child)
            elif tag in {"GSTRATE", "RATE"}:
                item["rate"] = _text(child)
        if item:
            items.append(item)
    return items


def _parse_bill_allocation(node: ET.Element) -> dict[str, Any]:
    payload = {}
    for child in list(node):
        tag = child.tag
        if tag == "NAME":
            payload["name"] = _text(child)
        elif tag == "BILLTYPE":
            payload["billType"] = _text(child)
        elif tag == "AMOUNT":
            payload["amount"] = _text(child)
    return payload


def _parse_bank_allocation(node: ET.Element) -> dict[str, Any]:
    payload = {}
    for child in list(node):
        tag = child.tag
        if tag == "DATE":
            payload["date"] = _text(child)
        elif tag == "NAME":
            payload["name"] = _text(child)
        elif tag == "TRANSACTIONTYPE":
            payload["transactionType"] = _text(child)
        elif tag == "AMOUNT":
            payload["amount"] = _text(child)
    return payload


def _parse_ledger_entry(node: ET.Element, warnings: list[str]) -> dict[str, Any]:
    entry: dict[str, Any] = {"sourceTag": node.tag, "billAllocations": [], "bankAllocations": [], "rateDetails": []}
    for child in list(node):
        tag = child.tag
        if tag == "LEDGERNAME":
            entry["ledgerName"] = _text(child)
        elif tag == "ISDEEMEDPOSITIVE":
            entry["isDeemedPositive"] = _text(child)
        elif tag == "AMOUNT":
            entry["amount"] = _text(child)
        elif tag == "BILLALLOCATIONS.LIST":
            entry["billAllocations"].append(_parse_bill_allocation(child))
        elif tag == "BANKALLOCATIONS.LIST":
            entry["bankAllocations"].append(_parse_bank_allocation(child))
        elif tag == "RATEDETAILS.LIST":
            entry["rateDetails"].extend(_parse_rate_details([child]))
        else:
            _record_warning(warnings, f"Unknown ledger child retained without normalization: {tag}")
    return entry


def _parse_inventory_entry(node: ET.Element, warnings: list[str]) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "sourceTag": node.tag,
        "batchAllocations": [],
        "accountingAllocations": [],
        "rateDetails": [],
    }
    for child in list(node):
        tag = child.tag
        if tag == "STOCKITEMNAME":
            entry["stockItemName"] = _text(child)
        elif tag == "ISDEEMEDPOSITIVE":
            entry["isDeemedPositive"] = _text(child)
        elif tag == "ACTUALQTY":
            entry["actualQty"] = _text(child)
        elif tag == "BILLEDQTY":
            entry["billedQty"] = _text(child)
        elif tag == "RATE":
            entry["rate"] = _text(child)
        elif tag == "AMOUNT":
            entry["amount"] = _text(child)
        elif tag == "BATCHALLOCATIONS.LIST":
            batch = {}
            for batch_child in list(child):
                if batch_child.tag == "GODOWNNAME":
                    batch["godownName"] = _text(batch_child)
                elif batch_child.tag == "BATCHNAME":
                    batch["batchName"] = _text(batch_child)
                elif batch_child.tag == "ACTUALQTY":
                    batch["actualQty"] = _text(batch_child)
                elif batch_child.tag == "BILLEDQTY":
                    batch["billedQty"] = _text(batch_child)
                elif batch_child.tag == "AMOUNT":
                    batch["amount"] = _text(batch_child)
            if batch:
                entry["batchAllocations"].append(batch)
        elif tag == "ACCOUNTINGALLOCATIONS.LIST":
            account = {"rateDetails": []}
            for alloc_child in list(child):
                if alloc_child.tag == "LEDGERNAME":
                    account["ledgerName"] = _text(alloc_child)
                elif alloc_child.tag == "ISDEEMEDPOSITIVE":
                    account["isDeemedPositive"] = _text(alloc_child)
                elif alloc_child.tag == "AMOUNT":
                    account["amount"] = _text(alloc_child)
                elif alloc_child.tag == "RATEDETAILS.LIST":
                    account["rateDetails"].extend(_parse_rate_details([alloc_child]))
            if account:
                entry["accountingAllocations"].append(account)
        elif tag == "RATEDETAILS.LIST":
            entry["rateDetails"].extend(_parse_rate_details([child]))
        else:
            _record_warning(warnings, f"Unknown inventory child retained without normalization: {tag}")
    return entry


def _normalize_voucher(voucher_elem: ET.Element, import_id: str, content_hash: str, voucher_index: int, warnings: list[str]) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": uuid.uuid4().hex,
        "source": {"importId": import_id, "contentHash": content_hash, "voucherIndex": voucher_index},
        "attributes": {k: v for k, v in voucher_elem.attrib.items() if k in {"VCHTYPE", "ACTION"}},
        "date": None,
        "voucherType": None,
        "voucherNumber": None,
        "partyLedgerName": None,
        "narration": None,
        "ledgerEntries": [],
        "inventoryEntries": [],
        "warnings": [],
    }
    voucher_warnings = item["warnings"]

    for child in list(voucher_elem):
        tag = child.tag
        if tag == "DATE":
            item["date"] = _text(child)
        elif tag == "VOUCHERTYPENAME":
            item["voucherType"] = _text(child)
        elif tag == "VOUCHERNUMBER":
            item["voucherNumber"] = _text(child)
        elif tag == "PARTYLEDGERNAME":
            item["partyLedgerName"] = _text(child)
        elif tag == "NARRATION":
            item["narration"] = _text(child)
        elif tag in {"ALLLEDGERENTRIES.LIST", "LEDGERENTRIES.LIST"}:
            entry = _parse_ledger_entry(child, voucher_warnings)
            item["ledgerEntries"].append(entry)
        elif tag == "ALLINVENTORYENTRIES.LIST":
            entry = _parse_inventory_entry(child, voucher_warnings)
            item["inventoryEntries"].append(entry)
        else:
            _record_warning(voucher_warnings, f"Unknown voucher child retained without normalization: {tag}")
            _record_warning(warnings, f"Unknown voucher child retained without normalization: {tag}")

    item["warnings"] = list(dict.fromkeys(voucher_warnings))
    return item


def _coerce_summary(vouchers: list[dict[str, Any]], import_warnings: list[str], import_errors: list[str]) -> dict[str, Any]:
    summary = {
        "vouchers": len(vouchers),
        "ledgerEntries": sum(len(v.get("ledgerEntries", [])) for v in vouchers),
        "inventoryEntries": sum(len(v.get("inventoryEntries", [])) for v in vouchers),
        "warnings": len(import_warnings),
        "errors": len(import_errors),
    }
    return summary


def _parse_tally_response(root: ET.Element) -> dict[str, Any]:
    counters: dict[str, str] = {}
    for tag in ["CREATED", "ALTERED", "DELETED", "IGNORED", "ERRORS"]:
        value = _text(root.find(tag))
        counters[tag] = value if value is not None else "0"
    line_error = _text(root.find("LINEERROR")) or ""
    business_status = "failed" if _coerce_int(counters.get("ERRORS")) > 0 or bool(line_error) else "succeeded"
    return {
        "businessStatus": business_status,
        "counters": counters,
        "lineError": line_error,
    }


def process_upload(db: Session, filename: str, file_bytes: bytes) -> dict[str, Any]:
    del filename
    content_hash = sha256_hex(file_bytes)
    repository = TallyRepository(db)
    existing = repository.get_import_by_hash(content_hash)
    if existing is not None:
        return {
            "importId": existing.id,
            "documentType": existing.document_type,
            "status": existing.status,
            "duplicate": True,
            "summary": existing.summary,
            "contentHash": existing.content_hash,
            "detectedEncoding": existing.detected_encoding,
            "warnings": existing.warnings,
            "errors": existing.errors,
            "tallyResponse": existing.tally_response,
            "vouchers": repository.fetch_vouchers_for_import(existing.id),
        }

    detected_encoding, root, _, parse_warnings = parse_xml_document(file_bytes)
    root_tag = root.tag if root is not None else ""
    import_warnings = list(parse_warnings)
    import_errors: list[str] = []
    voucher_payloads: list[dict[str, Any]] = []
    summary = {"vouchers": 0, "ledgerEntries": 0, "inventoryEntries": 0, "warnings": 0, "errors": 0}

    if root_tag == "ENVELOPE":
        body = root.find("BODY")
        data = body.find("DATA") if body is not None else None
        collection = data.find("COLLECTION") if data is not None else None
        if collection is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported ENVELOPE structure: missing COLLECTION element")
        for index, voucher_elem in enumerate(collection.findall("VOUCHER")):
            voucher = _normalize_voucher(voucher_elem, "", content_hash, index, import_warnings)
            voucher["source"]["importId"] = ""
            voucher_payloads.append(voucher)
            summary["vouchers"] += 1
            summary["ledgerEntries"] += len(voucher["ledgerEntries"])
            summary["inventoryEntries"] += len(voucher["inventoryEntries"])
            summary["warnings"] += len(voucher["warnings"])
        summary["warnings"] += len(import_warnings)
        document_type = "voucherExport"
        status_text = "completed"
    elif root_tag == "RESPONSE":
        response_map = _parse_tally_response(root)
        document_type = "tallyResponse"
        summary = {"vouchers": 0, "ledgerEntries": 0, "inventoryEntries": 0, "warnings": len(import_warnings), "errors": 0}
        if _coerce_int(response_map["counters"].get("ERRORS")) > 0 or bool(response_map["lineError"]):
            summary["errors"] = max(1, _coerce_int(response_map["counters"].get("ERRORS")) or 1)
            import_errors.append(response_map["lineError"] or "Tally response reported business errors")
        status_text = "completed"
        response_map["counters"] = {k: str(v) for k, v in response_map["counters"].items()}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported XML document root: {root_tag}")

    import_id = uuid.uuid4().hex
    if root_tag == "ENVELOPE":
        for voucher in voucher_payloads:
            voucher["source"]["importId"] = import_id

    payload = {
        "importId": import_id,
        "contentHash": content_hash,
        "documentType": document_type,
        "status": status_text,
        "duplicate": False,
        "detectedEncoding": detected_encoding,
        "summary": summary,
        "warnings": import_warnings,
        "errors": import_errors,
        "rawUpload": file_bytes,
        "tallyResponse": _parse_tally_response(root) if root_tag == "RESPONSE" else None,
        "vouchers": [],
    }

    payload["vouchers"] = [
        {
            "id": voucher["id"],
            "source": voucher["source"],
            "voucherIndex": voucher["source"]["voucherIndex"],
            "attributes": voucher["attributes"],
            "date": voucher["date"],
            "voucherType": voucher["voucherType"],
            "voucherNumber": voucher["voucherNumber"],
            "partyLedgerName": voucher["partyLedgerName"],
            "narration": voucher["narration"],
            "ledgerEntries": [
                {
                    "id": uuid.uuid4().hex,
                    "sourceTag": entry.get("sourceTag"),
                    "ledgerName": entry.get("ledgerName"),
                    "isDeemedPositive": entry.get("isDeemedPositive"),
                    "amount": entry.get("amount"),
                    "billAllocations": [
                        {"id": uuid.uuid4().hex, **allocation} for allocation in entry.get("billAllocations", [])
                    ],
                    "bankAllocations": [
                        {"id": uuid.uuid4().hex, **allocation} for allocation in entry.get("bankAllocations", [])
                    ],
                    "rateDetails": [
                        {"id": uuid.uuid4().hex, **detail} for detail in entry.get("rateDetails", [])
                    ],
                }
                for entry in voucher["ledgerEntries"]
            ],
            "inventoryEntries": [
                {
                    "id": uuid.uuid4().hex,
                    "sourceTag": entry.get("sourceTag"),
                    "stockItemName": entry.get("stockItemName"),
                    "isDeemedPositive": entry.get("isDeemedPositive"),
                    "actualQty": entry.get("actualQty"),
                    "billedQty": entry.get("billedQty"),
                    "rate": entry.get("rate"),
                    "amount": entry.get("amount"),
                    "batchAllocations": [
                        {"id": uuid.uuid4().hex, **allocation} for allocation in entry.get("batchAllocations", [])
                    ],
                    "accountingAllocations": [
                        {
                            "id": uuid.uuid4().hex,
                            "ledgerName": allocation.get("ledgerName"),
                            "isDeemedPositive": allocation.get("isDeemedPositive"),
                            "amount": allocation.get("amount"),
                            "rateDetails": [
                                {"id": uuid.uuid4().hex, **detail} for detail in allocation.get("rateDetails", [])
                            ],
                        }
                        for allocation in entry.get("accountingAllocations", [])
                    ],
                    "rateDetails": [
                        {"id": uuid.uuid4().hex, **detail} for detail in entry.get("rateDetails", [])
                    ],
                }
                for entry in voucher["inventoryEntries"]
            ],
            "warnings": voucher["warnings"],
        }
        for voucher in voucher_payloads
    ]

    import_record = repository.save_import(payload)
    db.refresh(import_record)

    return {
        "importId": import_record.id,
        "documentType": import_record.document_type,
        "status": import_record.status,
        "duplicate": False,
        "summary": import_record.summary,
        "contentHash": import_record.content_hash,
        "detectedEncoding": import_record.detected_encoding,
        "warnings": import_record.warnings,
        "errors": import_record.errors,
        "tallyResponse": import_record.tally_response,
        "vouchers": repository.fetch_vouchers_for_import(import_record.id),
    }


def get_import_details(db: Session, import_id: str) -> dict[str, Any]:
    repository = TallyRepository(db)
    import_record = repository.get_import_by_id(import_id)
    if import_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found")
    return {
        "importId": import_record.id,
        "documentType": import_record.document_type,
        "status": import_record.status,
        "contentHash": import_record.content_hash,
        "detectedEncoding": import_record.detected_encoding,
        "summary": import_record.summary,
        "warnings": import_record.warnings,
        "errors": import_record.errors,
        "tallyResponse": import_record.tally_response,
    }


def get_voucher_details(db: Session, voucher_id: str) -> dict[str, Any]:
    repository = TallyRepository(db)
    voucher_record = repository.get_voucher_by_id(voucher_id)
    if voucher_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voucher not found")
    return repository.fetch_voucher_by_id(voucher_id)


def get_vouchers_for_import(db: Session, import_id: str) -> list[dict[str, Any]]:
    repository = TallyRepository(db)
    import_record = repository.get_import_by_id(import_id)
    if import_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found")
    return repository.fetch_vouchers_for_import(import_id)


def list_imports_with_vouchers(db: Session) -> list[dict[str, Any]]:
    repository = TallyRepository(db)
    return repository.list_imports_with_vouchers()
