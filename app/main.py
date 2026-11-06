from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse, Response

from .kmac import SlideError, build_pdf, expand_range

app = FastAPI(title="KMAC 슬라이드 PDF 다운로더")
STATIC = Path(__file__).parent / "static"


@app.exception_handler(SlideError)
async def slide_error(_, exc: SlideError):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/pdf")
async def pdf(
    url: list[str] = Query(..., description="전자책 URL (여러 개 가능, 순서대로 병합)"),
    range_end: int | None = Query(None, description="지정 시 url의 번호부터 이 번호까지 일괄 병합"),
    filename: str = "kmac-slides",
):
    urls = url
    if range_end is not None:
        first = url[0].rstrip("/").rpartition("/")[2]
        if not first.isdigit() or range_end < int(first):
            raise SlideError("범위 지정 형식이 올바르지 않습니다.")
        urls = expand_range(url[0], int(first), range_end)
    data, _ = await build_pdf(urls)
    safe = quote(filename.replace("/", "_").replace("\\", "_")[:80] or "slides")
    return Response(
        data,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe}.pdf"},
    )
