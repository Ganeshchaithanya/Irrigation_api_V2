"""
API Router — Subsidy & Governance
Handles subsidy record submissions, status tracking, and PDF generation.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import os

from backend.db.session import get_db
from backend.services.diary_builder import diary_builder
from backend.models.state import FarmDiaryEntry
from backend.utils.logger import logger

router = APIRouter(prefix="/subsidy", tags=["Subsidy"])

@router.get("/reports/{entry_id}/download")
async def download_subsidy_report(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Generates and returns the branded PDF/HTML report for subsidy."""
    data = await diary_builder.get_subsidy_data_for_pdf(entry_id, db)
    if not data:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    entry, farm_name, zone_name = data
    html_content = diary_builder.generate_html_report(entry, farm_name, zone_name)
    
    # Try actual PDF generation if xhtml2pdf is installed (it will be in production)
    try:
        from io import BytesIO
        from xhtml2pdf import pisa
        
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
        
        if not pisa_status.err:
            return Response(
                content=pdf_buffer.getvalue(),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=subsidy_record_{entry_id.hex[:8]}.pdf"}
            )
    except ImportError:
        logger.warning("[subsidy] xhtml2pdf not found, falling back to HTML")
    
    # Fallback to HTML view if PDF fails or library missing
    return HTMLResponse(content=html_content)

@router.post("/simulate-government-callback")
async def simulate_payment(
    entry_id: uuid.UUID,
    status: str = "paid", # "approved" | "paid"
    db: AsyncSession = Depends(get_db)
):
    """模擬 government backend calling back to approve or pay the subsidy."""
    from sqlalchemy import select
    res = await db.execute(select(FarmDiaryEntry).where(FarmDiaryEntry.id == entry_id))
    entry = res.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    entry.subsidy_status = status
    if status == "paid":
        entry.payment_status = "paid"
        entry.payment_reference = f"GOV-TXN-{uuid.uuid4().hex[:8].upper()}"
        
    await db.commit()
    
    logger.info(f"[subsidy] Entry {entry_id} updated to {status} with ref {entry.payment_reference}")
    return {
        "status": "success", 
        "new_status": status, 
        "payment_ref": entry.payment_reference
    }

@router.post("/submit")
async def submit_subsidy_claim(
    entry_id: uuid.UUID,
    bank_name: str = None,
    account_number: str = None,
    ifsc_code: str = None,
    holder_name: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Marks an entry as submitted to the government (status: pending)."""
    from sqlalchemy import select
    import json
    res = await db.execute(select(FarmDiaryEntry).where(FarmDiaryEntry.id == entry_id))
    entry = res.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    entry.subsidy_status = "pending"
    
    # Save bank account details to JSON metadata
    meta = json.loads(entry.record_data) if entry.record_data else {}
    if bank_name: meta["bank_name"] = bank_name
    if account_number: meta["account_number"] = account_number
    if ifsc_code: meta["ifsc_code"] = ifsc_code
    if holder_name: meta["holder_name"] = holder_name
    entry.record_data = json.dumps(meta)
    
    await db.commit()
    
    logger.info(f"[subsidy] Entry {entry_id} submitted to government with bank details.")
    return {"status": "success", "message": "Claim submitted successfully.", "record_data": meta}
