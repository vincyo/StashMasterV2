import re
from typing import Iterable, Optional, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from services.scrapers import HEADERS, _fetch_with_curl


def is_interview_url(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        domain = (parsed.netloc or "").lower().replace("www.", "")
        path = (parsed.path or "").lower()
    except Exception:
        return False

    if "interview" in domain:
        return True

    if re.search(r"/(?:interview|interviews)(?:/|_|-)", path, re.I):
        return True

    # Domain hints where interviews are common
    if (domain == "barelist.com" or domain.endswith(".barelist.com")) and "interview" in url.lower():
        return True
    if domain.endswith("adultdvdtalk.com") and ("interview" in domain or "interview" in url.lower()):
        return True

    return False


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def extract_interview_text(url: str, timeout: int = 15) -> Tuple[str, str]:
    """Fetch and extract a readable interview text from a page.

    Returns (title, text). Both may be empty strings if extraction fails.
    """
    html = ""
    try:
        resp = requests.get(
            url,
            headers={**HEADERS, "Accept": "text/html,application/xhtml+xml"},
            timeout=timeout,
            allow_redirects=True,
        )
        if resp.status_code == 200:
            html = resp.text or ""
        elif resp.status_code == 403:
            # Anti-bot: tenter curl, souvent plus permissif
            html = _fetch_with_curl(url) or (resp.text or "")
        else:
            return "", ""
    except Exception:
        # Dernier recours: curl
        html = _fetch_with_curl(url) or ""

    if not html.strip():
        return "", ""

    try:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        title = ""
        if soup.title and soup.title.get_text():
            title = _clean_text(soup.title.get_text())

        # Try common content containers
        candidates = []
        selectors = [
            "article",
            "main",
            "#content",
            ".content",
            ".entry-content",
            ".post-content",
            ".post",
        ]
        for sel in selectors:
            node = soup.select_one(sel)
            if node:
                candidates.append(node)

        node = candidates[0] if candidates else soup.body
        if not node:
            return title, ""

        def _is_boilerplate(tl: str) -> bool:
            return any(
                x in tl
                for x in (
                    "cookies",
                    "privacy policy",
                    "terms of use",
                    "sign up",
                    "subscribe",
                    "accept cookies",
                    "cloudflare",
                    "checking your browser",
                )
            )

        # Prefer paragraphs and list items; keep some structure
        lines = []
        for el in node.find_all(["h1", "h2", "h3", "p", "li"]):
            t = _clean_text(el.get_text(" "))
            if not t or len(t) < 20:
                continue
            tl = t.lower()
            if _is_boilerplate(tl):
                continue
            lines.append(t)

        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        # Fallback: some pages have non-standard markup or anti-bot wrappers
        if len(text) < 200:
            raw = soup.get_text("\n")
            raw_lines = []
            for ln in (raw or "").splitlines():
                ln = _clean_text(ln)
                if not ln or len(ln) < 40:
                    continue
                tl = ln.lower()
                if _is_boilerplate(tl):
                    continue
                raw_lines.append(ln)
                if len(raw_lines) >= 60:
                    break
            text = "\n".join(raw_lines).strip()

        return title, text
    except Exception:
        return "", ""


def build_interview_context(urls: Iterable[str], max_pages: int = 2, max_chars: int = 2500) -> str:
    """Build a compact context block from interview pages.

    - Limits pages to avoid slowdowns.
    - Trims total chars to keep prompts reasonable.
    """
    if not urls:
        return ""

    picked = []
    for u in urls:
        if not isinstance(u, str):
            continue
        u = u.strip()
        if not u:
            continue
        if is_interview_url(u):
            picked.append(u)
        if len(picked) >= max_pages:
            break

    if not picked:
        return ""

    chunks = []
    for u in picked:
        title, text = extract_interview_text(u)
        if not text:
            continue
        # Keep it compact
        text = text[: max(0, max_chars)]
        header = f"SOURCE INTERVIEW: {u}"
        if title:
            header += f"\nTITRE: {title}"
        chunks.append(header + "\n" + text)

    combined = "\n\n".join(chunks).strip()
    if len(combined) > max_chars:
        combined = combined[:max_chars]
    return combined
