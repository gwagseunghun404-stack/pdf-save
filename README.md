# KMAC 슬라이드 PDF 다운로더

`edu.kmac.co.kr/ebook/...` (Toast 전자책) 슬라이드를 PDF 하나로 묶어 다운로드하는 웹 서비스.

```bash
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

- 웹: http://localhost:8000
- API: `GET /api/pdf?url=https://edu.kmac.co.kr/ebook/2026_kmes/02/` (`url` 반복 시 순서대로 병합)
- 일괄: `GET /api/pdf?url=.../2026_kmes/01/&range_end=10` (01~10번 병합)

동작: `<책 URL>/project.json`의 페이지 목록에서 `assets/page-images/*.jpg`를 받아 img2pdf로 병합.
`edu.kmac.co.kr` 외 호스트는 거부합니다.
