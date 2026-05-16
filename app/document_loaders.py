from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class LoadedDocument:
    title: str
    text: str
    source_type: str
    source: str


def load_path(path: Path) -> LoadedDocument:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(path)
    if suffix in {".md", ".markdown", ".txt"}:
        return _load_text(path)
    raise ValueError(f"Unsupported document type: {suffix}. Use PDF, Markdown, or TXT.")


def load_url(url: str) -> LoadedDocument:
    request = Request(url, headers={"User-Agent": "SupportIQ/0.1"})
    with urlopen(request, timeout=20) as response:
        raw = response.read()
        content_type = response.headers.get("content-type", "")
    text = raw.decode("utf-8", errors="ignore")
    title = url.rstrip("/").split("/")[-1] or url

    if "html" in content_type or "<html" in text.lower():
        text = _html_to_text(text)
        title_match = re.search(r"<title>(.*?)</title>", raw.decode("utf-8", errors="ignore"), re.I | re.S)
        if title_match:
            title = _normalize_space(title_match.group(1))

    return LoadedDocument(title=title, text=_normalize_space(text), source_type="url", source=url)


def _load_text(path: Path) -> LoadedDocument:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return LoadedDocument(title=path.stem, text=_normalize_space(text), source_type=path.suffix.lstrip("."), source=str(path))


def _load_pdf(path: Path) -> LoadedDocument:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Install pypdf to ingest PDF files.") from exc

    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return LoadedDocument(title=path.stem, text=_normalize_space(text), source_type="pdf", source=str(path))


def _html_to_text(html: str) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        html = re.sub(r"<script.*?</script>", " ", html, flags=re.I | re.S)
        html = re.sub(r"<style.*?</style>", " ", html, flags=re.I | re.S)
        return re.sub(r"<[^>]+>", " ", html)

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return soup.get_text(" ")


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

