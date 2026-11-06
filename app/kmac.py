"""KMAC(Toast 전자책 뷰어) 슬라이드 수집 및 PDF 병합."""
import asyncio
import io
import json
import re
from urllib.parse import urlparse

import httpx
import img2pdf

ALLOWED_HOST = "edu.kmac.co.kr"
BOOK_RE = re.compile(r"^/ebook/[\w\-]+/[\w\-]+/?")
MAX_BOOKS = 30
CONCURRENCY = 8


class SlideError(Exception):
    pass


def normalize_book_url(url: str) -> str:
    """검증 후 책 루트 URL(끝에 / 포함)을 반환. SSRF 방지를 위해 호스트를 제한한다."""
    p = urlparse(url.strip())
    if p.scheme not in ("http", "https") or p.hostname != ALLOWED_HOST:
        raise SlideError(f"{ALLOWED_HOST} 주소만 지원합니다: {url}")
    m = BOOK_RE.match(p.path)
    if not m:
        raise SlideError(f"전자책 주소 형식이 아닙니다: {url}")
    return f"https://{ALLOWED_HOST}{m.group(0).rstrip('/')}/"


def expand_range(url: str, start: int, end: int) -> list[str]:
    """.../ebook/2026_kmes/02/ 형태의 마지막 번호를 start~end로 치환."""
    base = normalize_book_url(url).rstrip("/")
    head, _, tail = base.rpartition("/")
    width = len(tail) if tail.isdigit() else 2
    return [f"{head}/{i:0{width}d}/" for i in range(start, end + 1)]


async def get_page_urls(client: httpx.AsyncClient, book: str) -> tuple[str, list[str]]:
    r = await client.get(book + "project.json")
    if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
        raise SlideError(f"슬라이드 정보를 찾을 수 없습니다: {book}")
    data = json.loads(r.content)
    urls = []
    for page in data.get("pages", []):
        bg = (page.get("background") or {}).get("url")
        if bg:
            urls.append(book + bg.replace("{ASSETS_DIR}", "assets/"))
    if not urls:
        raise SlideError(f"슬라이드 이미지가 없습니다: {book}")
    return data.get("title") or book, urls


async def build_pdf(book_urls: list[str]) -> tuple[bytes, list[tuple[str, int]]]:
    """여러 책의 슬라이드를 순서대로 하나의 PDF로 만든다. (pdf, [(제목, 페이지수)]) 반환."""
    books = [normalize_book_url(u) for u in book_urls]
    if not books:
        raise SlideError("URL이 없습니다.")
    if len(books) > MAX_BOOKS:
        raise SlideError(f"한 번에 최대 {MAX_BOOKS}개까지 가능합니다.")

    sem = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:

        async def fetch(u: str) -> bytes:
            async with sem:
                r = await client.get(u)
            if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image/"):
                raise SlideError(f"이미지를 받지 못했습니다: {u}")
            return r.content

        images: list[bytes] = []
        summary: list[tuple[str, int]] = []
        for book in books:
            title, urls = await get_page_urls(client, book)
            images += await asyncio.gather(*(fetch(u) for u in urls))
            summary.append((title, len(urls)))

    return img2pdf.convert(images), summary
