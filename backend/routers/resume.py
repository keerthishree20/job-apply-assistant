import io
from fastapi import APIRouter, UploadFile, File, HTTPException
from pypdf import PdfReader

router = APIRouter()


@router.post("/api/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    contents = await file.read()
    try:
        reader = PdfReader(io.BytesIO(contents))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read PDF: {e}")
    if not text:
        raise HTTPException(status_code=422, detail="PDF appears to be scanned/image-based. Please use a text PDF.")
    return {"text": text}
