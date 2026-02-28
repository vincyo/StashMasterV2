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
    """Merge two lists of URLs, keeping at most one URL per domain.

    The original ``base_urls`` are kept first; additional entries from
    ``new_urls`` are appended only if their domain does not already appear in
    ``base_urls``. Finally the combined list is sorted so that well‑known
    "core" domains appear first (iafd, FreeOnes, etc.).
    """
    final_urls: List[str] = []
    seen_domains = set()

    # preserve base list order
    for url in base_urls:
        domain = _extract_domain(url)
        seen_domains.add(domain)
        final_urls.append(url)

    for url in new_urls:
        domain = _extract_domain(url)
        if domain not in seen_domains:
            final_urls.append(url)
            seen_domains.add(domain)

    # deduplicate full URLs just in case
    # using dict.fromkeys preserves order
    deduped = list(dict.fromkeys(final_urls))

    # sort by core domains order
    def sort_key(u: str) -> int:
        ul = u.lower()
        for i, dom in enumerate(CORE_DOMAINS):
            if dom in ul:
                return i
        return len(CORE_DOMAINS)

    deduped.sort(key=sort_key)
    return deduped


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # prevent circular import at runtime
    from services.url_validator import URLCheckResult


def filter_live_urls(urls: List[str], results: list) -> List[str]:
    """Return a sublist of ``urls`` keeping only those whose corresponding
    validation results are not DEAD or ERROR.

    ``results`` should be the list returned by ``URLValidator.validate_urls``.
    """
    from services.url_validator import URLStatus
    """Return a sublist of `urls` keeping only those whose corresponding
    validation results are not DEAD or ERROR.

    The function assumes that ``results`` is in the same order as ``urls``
    (as produced by ``URLValidator.validate_urls``).  It is safe to pass the
    original list of URLs again; the helper will simply ignore any entries
    marked dead so the caller can overwrite the widget content.
    """
    from services.url_validator import URLStatus

    live: List[str] = []
    for url, res in zip(urls, results):
        if res.status not in (URLStatus.DEAD, URLStatus.ERROR):
            live.append(url)
    return live
