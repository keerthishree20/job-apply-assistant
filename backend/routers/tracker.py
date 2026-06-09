from fastapi import APIRouter
from fastapi.responses import FileResponse
from services.excel_tracker import get_excel_path

router = APIRouter()


@router.get("/api/tracker/export")
def export_tracker():
    path = get_excel_path()
    return FileResponse(
        path=str(path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="jobs_applied.xlsx",
    )
