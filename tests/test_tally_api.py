import hashlib
import os
from pathlib import Path

import pytest

os.environ["DATABASE_URL"] = "sqlite:///./test_tally.db"

from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.database import engine
from app.main import app

client = TestClient(app)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def read_fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_import_voucher_export_and_nested_values():
    payload = read_fixture("01_receipt_with_allocations.xml")
    response = client.post("/api/tally/imports", files={"file": ("receipt.xml", payload, "application/xml")})
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["documentType"] == "voucherExport"
    assert data["status"] == "completed"
    assert data["summary"]["vouchers"] == 1
    assert data["summary"]["ledgerEntries"] == 2
    assert data["summary"]["inventoryEntries"] == 0

    import_id = data["importId"]
    details = client.get(f"/api/tally/imports/{import_id}")
    assert details.status_code == 200, details.text
    details_json = details.json()
    assert details_json["contentHash"] == hashlib.sha256(payload).hexdigest()

    vouchers = client.get(f"/api/tally/imports/{import_id}/vouchers")
    assert vouchers.status_code == 200, vouchers.text
    voucher_data = vouchers.json()["items"][0]
    assert voucher_data["ledgerEntries"][0]["amount"] == "1250.00"
    assert voucher_data["ledgerEntries"][1]["amount"] == "-1250.00"
    assert voucher_data["ledgerEntries"][0]["bankAllocations"][0]["amount"] == "1250.00"
    assert voucher_data["ledgerEntries"][1]["billAllocations"][0]["amount"] == "-1250.00"


def test_duplicate_upload_returns_original_import():
    payload = read_fixture("06_duplicate_receipt.xml")
    first = client.post("/api/tally/imports", files={"file": ("first.xml", payload, "application/xml")})
    second = client.post("/api/tally/imports", files={"file": ("second.xml", payload, "application/xml")})
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["importId"] == second.json()["importId"]
    assert second.json()["duplicate"] is True


def test_tally_response_business_status_failed():
    payload = read_fixture("03_tally_error_response.xml")
    response = client.post("/api/tally/imports", files={"file": ("response.xml", payload, "application/xml")})
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["documentType"] == "tallyResponse"
    assert data["summary"]["errors"] == 1

    import_id = data["importId"]
    details = client.get(f"/api/tally/imports/{import_id}")
    details_json = details.json()
    assert details_json["tallyResponse"]["businessStatus"] == "failed"
    assert details_json["tallyResponse"]["lineError"] == "Demo ledger does not exist"


def test_utf16_and_illegal_control_reference_warnings():
    payload = read_fixture("04_utf16_invalid_control_ref.xml")
    response = client.post("/api/tally/imports", files={"file": ("utf16.xml", payload, "application/xml")})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["summary"]["warnings"] >= 1

    details = client.get(f"/api/tally/imports/{body['importId']}")
    details_json = details.json()
    assert details_json["detectedEncoding"] == "UTF-16"
    assert any("Sanitized" in warning for warning in details_json["warnings"])


def test_empty_collection_is_valid():
    payload = read_fixture("05_empty_collection.xml")
    response = client.post("/api/tally/imports", files={"file": ("empty.xml", payload, "application/xml")})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["summary"]["vouchers"] == 0


def test_sales_invoice_inventory_ownership_and_rate_details():
    payload = read_fixture("02_sales_invoice_nested.xml")
    response = client.post("/api/tally/imports", files={"file": ("invoice.xml", payload, "application/xml")})
    assert response.status_code == 201, response.text
    import_id = response.json()["importId"]
    voucher = client.get(f"/api/tally/imports/{import_id}/vouchers").json()["items"][0]
    assert voucher["inventoryEntries"][0]["amount"] == "100.00"
    assert voucher["inventoryEntries"][0]["batchAllocations"][0]["amount"] == "100.00"
    assert voucher["inventoryEntries"][0]["accountingAllocations"][0]["amount"] == "100.00"
    assert voucher["inventoryEntries"][0]["accountingAllocations"][0]["rateDetails"][0]["dutyHead"] == "CGST"
    assert voucher["inventoryEntries"][0]["accountingAllocations"][0]["rateDetails"][0]["rate"] == "9"


def test_get_voucher_by_id_returns_stored_record():
    payload = read_fixture("01_receipt_with_allocations.xml")
    response = client.post("/api/tally/imports", files={"file": ("receipt.xml", payload, "application/xml")})
    assert response.status_code == 201, response.text

    import_id = response.json()["importId"]
    vouchers = client.get(f"/api/tally/imports/{import_id}/vouchers")
    assert vouchers.status_code == 200, vouchers.text
    voucher_id = vouchers.json()["items"][0]["id"]

    detail = client.get(f"/api/tally/vouchers/{voucher_id}")
    assert detail.status_code == 200, detail.text
    data = detail.json()
    assert data["id"] == voucher_id
    assert data["source"]["importId"] == import_id
    assert data["voucherType"] == "Receipt"
    assert data["ledgerEntries"][0]["amount"] == "1250.00"
    assert data["ledgerEntries"][1]["billAllocations"][0]["amount"] == "-1250.00"
