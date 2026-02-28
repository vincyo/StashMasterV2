"""Utilities for handling and normalizing lists of URLs.

This module provides helper functions used by various GUI components and import
scripts. The goal is to centralize logic for cleaning (removing empty lines and
duplicates) as well as merging URL lists while preferring one URL per domain and
optionally ordering core sources first.
"""
import re
from typing import List

CORE_DOMAINS = ["iafd.com", "freeones.com", "thenude.com", "babepedia.com"]


def clean_urls_list(urls: List[str]) -> List[str]:
    """Return a new list containing the given URLs with empties removed and
    duplicates discarded while preserving the original order.

    Leading/trailing whitespace is stripped from each URL. Comparison for
    duplicates is case‑sensitive on the full URL string.
    """
    seen = set()
    cleaned: List[str] = []
    for u in urls:
        u = u.strip()
        if not u:
            continue
        if u not in seen:
            seen.add(u)
            cleaned.append(u)
    return cleaned


def _extract_domain(url: str) -> str:
    """Return the domain part of a URL for deduplication purposes."""
    m = re.search(r'https?://(?:www\.)?([^/]+)', url.lower())
    return m.group(1) if m else url.lower()


def merge_urls_by_domain(base_urls: List[str], new_urls: List[str]) -> List[str]:
    """Merge two URL lists while preserving all distinct URLs.

    Historically this helper kept only one URL per domain, which could drop
    many valid profile pages. We now keep every distinct URL (full-string
    deduplication only) and preserve insertion order: ``base_urls`` first,
    then ``new_urls``.
    """
    final_urls: List[str] = []
    seen = set()

    for url in list(base_urls) + list(new_urls):
        u = (url or "").strip()
        if not u:
            continue
        if u in seen:
            continue
        seen.add(u)
        final_urls.append(u)

    return final_urls


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # prevent circular import at runtime
    from services.url_validator import URLCheckResult


def filter_live_urls(urls: List[str], results: list) -> List[str]:
    """Return a sublist of ``urls`` keeping only those not confirmed DEAD.

    ``results`` should be the list returned by ``URLValidator.validate_urls``.
    """
    from services.url_validator import URLStatus
    """Return a sublist of `urls` keeping only those whose corresponding
    validation results are not DEAD.

    The function assumes that ``results`` is in the same order as ``urls``
    (as produced by ``URLValidator.validate_urls``).  It is safe to pass the
    original list of URLs again; the helper will simply ignore any entries
    marked dead so the caller can overwrite the widget content.
    """
    from services.url_validator import URLStatus

    live: List[str] = []
    for url, res in zip(urls, results):
        if res.status != URLStatus.DEAD:
            live.append(url)
    return live
