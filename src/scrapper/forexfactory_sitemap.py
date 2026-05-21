"""Helpers to fetch and parse ForexFactory sitemap-index and child sitemaps.

This module provides lightweight utilities intended to be used by a Flask
route. It intentionally keeps network calls small and provides parsing helpers
that can be unit-tested without network access.
"""
from datetime import date, datetime
import logging

import cloudscraper
from defusedxml import ElementTree as ET

logger = logging.getLogger(__name__)

SITEMAP_INDEX_URL = "https://www.forexfactory.com/sitemap-index.xml"


def _safe_parse_date(text):
    """Parse a date string from sitemap <lastmod> into a date object.

    Accepts ISO-like strings (YYYY-MM-DD or full datetime). Returns None on
    parse failure.
    """
    if not text:
        return None
    try:
        # Try full ISO first
        dt = datetime.fromisoformat(text)
        return dt.date()
    except Exception:
        try:
            # Fallback: take first 10 chars (YYYY-MM-DD)
            return date.fromisoformat(text[:10])
        except Exception:
            return None


def parse_sitemap_index(xml_text):
    """Return list of child sitemap URLs found in sitemap-index XML text."""
    root = ET.fromstring(xml_text)
    urls = []
    # Handle namespace if present (xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    # Try with namespace first, fallback to no namespace
    sitemaps = root.findall(".//ns:sitemap", namespace)
    if not sitemaps:
        sitemaps = root.findall(".//sitemap")

    for sitemap_el in sitemaps:
        # Try with namespace, fallback without
        loc = sitemap_el.find("ns:loc", namespace)
        if loc is None:
            loc = sitemap_el.find("loc")
        if loc is not None and loc.text:
            urls.append(loc.text.strip())
    return urls


def parse_child_sitemap(xml_text):
    """Return list of dicts: {"url": str, "lastmod": date_or_None} from child sitemap XML."""
    root = ET.fromstring(xml_text)
    results = []
    # Handle namespace if present
    namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    # Try with namespace first, fallback to no namespace
    urls = root.findall(".//ns:url", namespace)
    if not urls:
        urls = root.findall(".//url")

    for url_el in urls:
        # Try with namespace, fallback without
        loc = url_el.find("ns:loc", namespace)
        if loc is None:
            loc = url_el.find("loc")

        lastmod_el = url_el.find("ns:lastmod", namespace)
        if lastmod_el is None:
            lastmod_el = url_el.find("lastmod")

        lastmod = (
            _safe_parse_date(lastmod_el.text.strip())
            if lastmod_el is not None and lastmod_el.text
            else None
        )
        if loc is not None and loc.text:
            results.append({"url": loc.text.strip(), "lastmod": lastmod})
    return results


def fetch_url_text(url, timeout=10):
    """Fetch a URL and return response text. Raises RuntimeError on failure."""
    scraper = cloudscraper.create_scraper()
    try:
        resp = scraper.get(url, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        logger.exception("Failed to fetch sitemap URL: %s", url)
        raise RuntimeError(f"Failed to get URL {url}: {e}")
    return resp.text


def get_sitemap_urls(
    start_date=None, end_date=None, limit=None, offset=0, max_pages=10
):
    """Fetch sitemap-index and child sitemaps and return paginated results.

    start_date/end_date: date or None
    limit: int or None, offset: int
    max_pages: maximum number of child sitemaps to fetch (safety)
    """
    # Step 1: get sitemap index
    idx_text = fetch_url_text(SITEMAP_INDEX_URL)
    child_urls = parse_sitemap_index(idx_text)

    records = []
    pages = 0
    for child in child_urls:
        if pages >= max_pages:
            break
        try:
            child_text = fetch_url_text(child)
            child_records = parse_child_sitemap(child_text)
            for r in child_records:
                lm = r.get("lastmod")
                if start_date and lm and lm < start_date:
                    continue
                if end_date and lm and lm > end_date:
                    continue
                records.append(r)
        except Exception:
            logger.exception("Failed to fetch/parse child sitemap: %s", child)
        pages += 1

    # Deduplicate by URL while preserving order
    seen = set()
    deduped = []
    for r in records:
        u = r.get("url")
        if u in seen:
            continue
        seen.add(u)
        deduped.append(r)

    total = len(deduped)

    # Apply offset
    if offset and offset > 0:
        if offset >= total:
            paged = []
        else:
            paged = deduped[offset:]
    else:
        paged = deduped[:]

    # Apply limit
    if limit is not None:
        paged = paged[:limit]

    return {"total": total, "offset": offset, "limit": limit, "results": paged}
