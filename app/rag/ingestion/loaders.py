from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class LoadedSection:
    title: str | None
    text: str
    position: int
    page_number: int | None = None
    heading_path: tuple[str, ...] = ()


@dataclass(frozen=True)
class LoadedDocument:
    title: str
    text: str
    source_type: str
    source: str
    source_id: str | None = None
    original_filename: str | None = None
    sections: tuple[LoadedSection, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)


def load_path(
    path: Path,
    *,
    source_id: str | None = None,
    source: str | None = None,
    title: str | None = None,
    original_filename: str | None = None,
) -> LoadedDocument:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(
            path,
            source_id=source_id,
            source=source,
            title=title,
            original_filename=original_filename,
        )
    if suffix in {".md", ".markdown", ".txt"}:
        return _load_text(
            path,
            source_id=source_id,
            source=source,
            title=title,
            original_filename=original_filename,
        )
    raise ValueError(f"Unsupported document type: {suffix}. Use PDF, Markdown, or TXT.")


def load_url(url: str) -> LoadedDocument:
    canonical_url = _canonicalize_url(url)
    _validate_public_url(canonical_url)
    request = Request(canonical_url, headers={"User-Agent": "GroundDesk/0.1"})
    with urlopen(request, timeout=20) as response:
        raw = response.read()
        content_type = response.headers.get("content-type", "")
    decoded = raw.decode("utf-8", errors="ignore")
    title = canonical_url.rstrip("/").split("/")[-1] or canonical_url

    if "html" in content_type or "<html" in decoded.lower():
        text, sections = _html_to_text(decoded)
        title_match = re.search(r"<title>(.*?)</title>", decoded, re.I | re.S)
        if title_match:
            title = _normalize_inline_space(title_match.group(1))
    else:
        text = _normalize_document_text(decoded)
        sections = (LoadedSection(title=None, text=text, position=0),)

    return LoadedDocument(
        title=title,
        text=text,
        source_type="url",
        source=canonical_url,
        source_id=f"url:{canonical_url}",
        sections=sections,
    )


def _load_text(
    path: Path,
    *,
    source_id: str | None,
    source: str | None,
    title: str | None,
    original_filename: str | None,
) -> LoadedDocument:
    text = _normalize_document_text(path.read_text(encoding="utf-8", errors="ignore"))
    sections = (
        _markdown_sections(text) if path.suffix.lower() in {".md", ".markdown"} else ()
    )
    if not sections:
        sections = (LoadedSection(title=None, text=text, position=0),)
    return LoadedDocument(
        title=title or path.stem,
        text=text,
        source_type=path.suffix.lstrip("."),
        source=source or str(path),
        source_id=source_id or f"file:{path.resolve()}",
        original_filename=original_filename or path.name,
        sections=sections,
    )


def _load_pdf(
    path: Path,
    *,
    source_id: str | None,
    source: str | None,
    title: str | None,
    original_filename: str | None,
) -> LoadedDocument:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Install pypdf to ingest PDF files.") from exc

    reader = PdfReader(str(path))
    page_text = [
        _normalize_document_text(page.extract_text() or "") for page in reader.pages
    ]
    sections = tuple(
        LoadedSection(
            title=f"Page {page_number}",
            text=text,
            position=page_number - 1,
            page_number=page_number,
        )
        for page_number, text in enumerate(page_text, start=1)
        if text
    )
    return LoadedDocument(
        title=title or path.stem,
        text="\n\n".join(text for text in page_text if text).strip(),
        source_type="pdf",
        source=source or str(path),
        source_id=source_id or f"file:{path.resolve()}",
        original_filename=original_filename or path.name,
        sections=sections,
    )


def _html_to_text(html: str) -> tuple[str, tuple[LoadedSection, ...]]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        html = re.sub(r"<script.*?</script>", " ", html, flags=re.I | re.S)
        html = re.sub(r"<style.*?</style>", " ", html, flags=re.I | re.S)
        text = _normalize_document_text(re.sub(r"<[^>]+>", " ", html))
        return text, (LoadedSection(title=None, text=text, position=0),)

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = _normalize_document_text(soup.get_text("\n"))
    sections: list[LoadedSection] = []
    current_title: str | None = None
    current_path: list[str] = []
    buffer: list[str] = []
    position = 0
    for node in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        value = _normalize_inline_space(node.get_text(" ", strip=True))
        if not value:
            continue
        if node.name and re.fullmatch(r"h[1-4]", node.name):
            if buffer:
                sections.append(
                    LoadedSection(
                        title=current_title,
                        text="\n\n".join(buffer),
                        position=position,
                        heading_path=tuple(current_path),
                    )
                )
                position += 1
                buffer = []
            level = int(node.name[1])
            current_path = current_path[: level - 1] + [value]
            current_title = value
            continue
        buffer.append(value)
    if buffer:
        sections.append(
            LoadedSection(
                title=current_title,
                text="\n\n".join(buffer),
                position=position,
                heading_path=tuple(current_path),
            )
        )
    return text, tuple(sections) or (LoadedSection(title=None, text=text, position=0),)


def _markdown_sections(text: str) -> tuple[LoadedSection, ...]:
    sections: list[LoadedSection] = []
    heading_path: list[str] = []
    current_title: str | None = None
    buffer: list[str] = []
    position = 0
    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
        if match:
            if buffer:
                sections.append(
                    LoadedSection(
                        title=current_title,
                        text="\n".join(buffer).strip(),
                        position=position,
                        heading_path=tuple(heading_path),
                    )
                )
                position += 1
                buffer = []
            level = len(match.group(1))
            heading = _normalize_inline_space(match.group(2))
            heading_path = heading_path[: level - 1] + [heading]
            current_title = heading
            continue
        buffer.append(line)
    if buffer:
        sections.append(
            LoadedSection(
                title=current_title,
                text="\n".join(buffer).strip(),
                position=position,
                heading_path=tuple(heading_path),
            )
        )
    return tuple(section for section in sections if section.text)


def _canonicalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Only absolute http(s) URLs can be ingested.")
    return urlunparse(parsed._replace(fragment=""))


def _validate_public_url(url: str) -> None:
    host = urlparse(url).hostname
    if not host:
        raise ValueError("URL host is required.")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve URL host: {host}") from exc
    for address in addresses:
        if not ipaddress.ip_address(address).is_global:
            raise ValueError("Only public URLs can be ingested.")


def _normalize_document_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _normalize_inline_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
