"""
AdultEmpireDVDExtractor — Source secondaire (P2).
Extrait aussi les URLs de clips/scènes pour la Phase 2.
"""
import re
from services.extractors.dvd.base_dvd import BaseExtractorDVD


class AdultEmpireDVDExtractor(BaseExtractorDVD):
    SOURCE_NAME = "adultdvdempire"

    # Cookie requis pour accès
    COOKIES = "ageConfirmed=true"

    def _fetch_tree(self, url: str):
        """Override pour injecter le cookie age."""
        cached = self.cache.get(url)
        if cached:
            from lxml import html as lxml_html
            return lxml_html.fromstring(cached)
        try:
            import subprocess
            from lxml import html as lxml_html
            result = subprocess.run(
                ["curl", "-sL", "--max-time", "15",
                 "-H", f"Cookie: {self.COOKIES}", url],
                capture_output=True, timeout=20
            )
            html = result.stdout.decode("utf-8", errors="replace")
            if html and len(html) > 500:
                self.cache.set(url, html)
                return lxml_html.fromstring(html)
        except Exception as e:
            print(f"[adultdvdempire] Fetch error: {e}")
        return None

    def search_urls(self, title: str, studio: str = "") -> list[str]:
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        return [
            f"https://www.adultdvdempire.com/{slug}.html",
            f"https://www.adultdvdempire.com/dvd/{slug}/",
        ]

    def extract_from_url(self, url: str) -> dict:
        data = self._empty_result(url)
        tree = self._fetch_tree(url)
        if tree is None:
            return data

        data["title"] = (self._get_text(tree, '//h1[@class="title"]/text()') or 
                        self._get_text(tree, '//h1/text()'))

        data["studio"] = self._get_text(tree, '//a[contains(@href,"/studio/")]/text()')

        # Date — format "Sep 22 2008"
        data["date"] = (self._get_text(tree, '//li[contains(text(),"Released")]/text()') or 
                       self._get_text(tree, '//*[contains(@class,"release-date")]/text()'))

        # Duration — format "1 hrs. 55 mins."
        data["duration_raw"] = (self._get_text(tree, '//li[contains(text(),"Run Time")]/text()') or 
                                self._get_text(tree, '//*[contains(@class,"run-time")]/text()'))

        data["director"] = self._get_text(tree, '//a[contains(@href,"/director/")]/text()')

        # Synopsis — strip "Show More"
        desc_nodes = tree.xpath('//*[contains(@class,"synopsis")]//text()')
        if desc_nodes:
            desc = " ".join(t.strip() for t in desc_nodes if t.strip()
                            and "show more" not in t.lower())
            data["description"] = desc[:2000] or None

        # Covers
        data["front_cover_url"] = (self._get_text(tree, '//img[contains(@class,"cover-front")]/@src') or 
                                   self._get_text(tree, '//div[@id="front-cover"]//img/@src'))
        data["back_cover_url"]  = (self._get_text(tree, '//img[contains(@class,"cover-back")]/@src') or 
                                   self._get_text(tree, '//div[@id="back-cover"]//img/@src'))

        # ── PHASE 2 : extraction URLs scènes via liens /clip/ ───
        clip_links = tree.xpath('//a[contains(@href, "/clip/")]/@href')
        seen = set()
        for i, href in enumerate(clip_links):
            if href in seen:
                continue
            seen.add(href)
            scene_url = href if href.startswith("http") else f"https://www.adultdvdempire.com{href}"
            data["scenes"].append({
                "index": i + 1,
                "title": None,
                "url_adultdvdempire": scene_url,
            })

        return data
