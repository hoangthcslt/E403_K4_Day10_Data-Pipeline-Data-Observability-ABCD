from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import compact_join, normalize_whitespace, read_json, write_json

CROSSREF_API_URL = "https://api.crossref.org/works"

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 5
_INITIAL_BACKOFF_SECONDS = 1.0
_REQUEST_TIMEOUT_SECONDS = 30
_USER_AGENT = "day10-data-pipeline-lab/1.0 (educational use; +https://api.crossref.org)"

_TAG_RE = re.compile(r"<[^>]+>")
_PUBLISHED_DATE_KEYS = ("published", "published-print", "published-online", "issued", "created")


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_abstract(raw: str) -> str:
    if not raw:
        return ""
    return normalize_whitespace(_TAG_RE.sub(" ", raw))


def _format_authors(author_entries: list[dict]) -> list[str]:
    names: list[str] = []
    for entry in author_entries or []:
        given = normalize_whitespace(str(entry.get("given", "")))
        family = normalize_whitespace(str(entry.get("family", "")))
        full_name = compact_join([given, family], sep=" ")
        if not full_name:
            full_name = normalize_whitespace(str(entry.get("name", "")))
        if full_name:
            names.append(full_name)
    return names


def _date_from_parts(date_parts: list | None) -> str | None:
    if not date_parts:
        return None
    parts = date_parts[0] if isinstance(date_parts[0], list) else date_parts
    if not parts:
        return None
    year = parts[0]
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    try:
        return date(year, month, day).isoformat()
    except (TypeError, ValueError):
        return None


def _best_published_date(item: dict) -> str:
    for key in _PUBLISHED_DATE_KEYS:
        node = item.get(key)
        if isinstance(node, dict):
            parsed = _date_from_parts(node.get("date-parts"))
            if parsed:
                return parsed
    return ""


def _updated_date(item: dict, fallback_published: str) -> str:
    for key in ("indexed", "deposited"):
        node = item.get(key)
        if isinstance(node, dict) and node.get("date-time"):
            return str(node["date-time"])
    return fallback_published


def _find_pdf_url(links: list[dict]) -> str:
    for link in links or []:
        content_type = str(link.get("content-type", "")).lower()
        if "pdf" in content_type and link.get("URL"):
            return str(link["URL"])
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref `/works` payload thanh list PaperRecord."""
    items = (payload.get("message") or {}).get("items") or []
    records: list[PaperRecord] = []
    seen_ids: set[str] = set()

    for item in items:
        doi = normalize_whitespace(str(item.get("DOI", "")))
        titles = item.get("title") or []
        title = normalize_whitespace(titles[0]) if titles else ""

        if not doi or not title or doi in seen_ids:
            continue
        seen_ids.add(doi)

        summary = _clean_abstract(item.get("abstract", ""))
        authors = _format_authors(item.get("author") or [])
        categories = [normalize_whitespace(c) for c in (item.get("subject") or []) if normalize_whitespace(c)]
        primary_category = categories[0] if categories else "Uncategorized"

        published = _best_published_date(item)
        updated = _updated_date(item, published)

        abs_url = item.get("URL") or f"https://doi.org/{doi}"
        pdf_url = _find_pdf_url(item.get("link") or [])

        container_titles = item.get("container-title") or []
        comment = normalize_whitespace(container_titles[0]) if container_titles else ""

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def _request_with_retry(url: str, params: dict) -> dict:
    headers = {"User-Agent": _USER_AGENT}
    backoff = _INITIAL_BACKOFF_SECONDS
    last_error: Exception | None = None

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=_REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            last_error = exc
        else:
            if response.status_code == 200:
                return response.json()
            if response.status_code not in _RETRYABLE_STATUS_CODES:
                response.raise_for_status()
            last_error = requests.HTTPError(f"Crossref returned status {response.status_code}")
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    backoff = max(backoff, float(retry_after))
                except ValueError:
                    pass

        if attempt < _MAX_ATTEMPTS:
            time.sleep(backoff)
            backoff *= 2

    raise RuntimeError(f"Failed to fetch data from Crossref after {_MAX_ATTEMPTS} attempts: {last_error}")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi Crossref API, luu raw response, parse thanh records va luu raw records."""
    params = {
        "query.bibliographic": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    payload = _request_with_retry(CROSSREF_API_URL, params)
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    payload = read_json(path)
    return [PaperRecord(**item) for item in payload]
