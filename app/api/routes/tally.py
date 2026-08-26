from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.services.tally_service import (
    get_import_details,
    get_voucher_details,
    get_vouchers_for_import,
    list_imports_with_vouchers,
    process_upload,
)

router = APIRouter(prefix="/tally", tags=["tally"])


def _serialize_upload_result(result: dict) -> dict:
    response = {
        "importId": result["importId"],
        "documentType": result["documentType"],
        "status": result["status"],
        "duplicate": result.get("duplicate", False),
        "summary": result["summary"],
    }
    if result.get("duplicate"):
        response["duplicate"] = True
    return response


@router.get("/imports")
def list_imports(db: Session = Depends(get_db)):
    return {"items": list_imports_with_vouchers(db), "count": len(list_imports_with_vouchers(db))}


@router.get("/imports/{import_id}")
def read_import(import_id: str, db: Session = Depends(get_db)):
    return get_import_details(db, import_id)


@router.get("/imports/{import_id}/vouchers")
def list_vouchers(import_id: str, db: Session = Depends(get_db)):
    items = get_vouchers_for_import(db, import_id)
    return {"items": items, "count": len(items)}


@router.get("/vouchers/{voucher_id}")
def read_voucher(voucher_id: str, db: Session = Depends(get_db)):
    return get_voucher_details(db, voucher_id)


@router.get("/imports/{import_id}/vouchers/{voucher_id}")
def read_voucher_for_import(import_id: str, voucher_id: str, db: Session = Depends(get_db)):
    voucher = get_voucher_details(db, voucher_id)
    if voucher.get("source", {}).get("importId") != import_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voucher not found for this import")
    return voucher


@router.post("/imports", status_code=status.HTTP_201_CREATED)
async def create_import(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A file is required")
    data = await file.read()
    result = process_upload(db, file.filename, data)
    response = _serialize_upload_result(result)
    if result.get("duplicate"):
        return JSONResponse(content=response, status_code=status.HTTP_200_OK)
    return response


@router.post("/imports/batch", status_code=status.HTTP_201_CREATED)
async def create_imports(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one file is required")

    results = []
    for file in files:
        if not file.filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All uploaded files must include a filename")
        data = await file.read()
        result = process_upload(db, file.filename, data)
        response = _serialize_upload_result(result)
        results.append(response)

    response_status = status.HTTP_200_OK if any(item["duplicate"] for item in results) else status.HTTP_201_CREATED
    if len(results) == 1:
        single_response = results[0]
        if single_response["duplicate"]:
            return JSONResponse(content=single_response, status_code=status.HTTP_200_OK)
        return single_response

    return JSONResponse(content={"items": results, "count": len(results)}, status_code=response_status)
