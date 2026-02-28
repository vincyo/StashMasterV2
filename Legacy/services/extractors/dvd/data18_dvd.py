"""
Data18DVDExtractor — Source prioritaire (P1) pour les métadonnées group.
Extrait aussi les URLs de scènes individuelles pour la Phase 2.
"""
import re
from services.extractors.dvd.base_dvd import BaseExtractorDVD


class Data18DVDExtractor(BaseExtractorDVD):
    SOURCE_NAME = "data18"

    def search_urls(self, title: str, studio: str = "") -> list[str]:
        """Génère des URLs candidates data18 pour un titre DVD."""
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        candidates = [
            f"https://www.data18.com/movies/{slug}",
            f"https://www.data18.com/content/{slug}",
            f"https://www.data18.com/movies/{slug}-dvd",
        ]
        
        # RESTAURATION DE LA RECHERCHE ACTIVE
        # Le site data18.com a un endpoint de recherche qui peut retourner une liste de résultats
        try:
            search_query = title.strip().replace(' ', '+')
            search_url = f"https://www.data18.com/search?k={search_query}"
            
            tree = self._fetch_tree(search_url)
            if tree is not None:
                # Récupérer tous les liens qui ressemblent à des films/DVDs
                # Pattern: /movies/ID-titre ou /content/ID-titre
                links = tree.xpath('//a[contains(@href, "/movies/")]/@href')
                links += tree.xpath('//a[contains(@href, "/content/")]/@href')
                
                # Aussi chercher dans les blocs gen11/gen12 typiques de data18
                links += tree.xpath('//div[contains(@class,"gen")]//a/@href')

                for link in links:
                    # Filtrer les faux positifs (scenes, tags, sites, etc.)
                    if any(x in link for x in ["/scenes/", "/tags/", "/sites/", "/pornstars/", "/studios/"]):
                        continue
                        
                    full_link = link if link.startswith("http") else f"https://www.data18.com{link}"
                    
                    # Éviter les doublons
                    if full_link not in candidates:
                        # Priorité : insérer au début si le titre est très proche (TODO)
                        # Pour l'instant on ajoute à la fin
                        candidates.append(full_link)
        except Exception as e:
            print(f"[Data18] Search error: {e}")

        return candidates

    def extract_from_url(self, url: str) -> dict:
        data = self._empty_result(url)
        tree = self._fetch_tree(url)
        if tree is None:
            return data

        # Titre
        data["title"] = self._get_text(tree, '//h1[@itemprop="name"]/text()') or \
                        self._get_text(tree, '//h1/text()')

        # Date — plusieurs fallbacks
        date_raw = self._get_text(tree, '//span[contains(text(),"Release")]/following-sibling::text()[1]')
        if not date_raw:
            date_raw = self._get_text(tree, '//div[@class="gen-wrap"]//span[contains(@class,"date")]/text()')
        data["date"] = date_raw

        # Studio
        data["studio"] = self._get_text(tree, '//a[@itemprop="publisher"]/text()') or \
                         self._get_text(tree, '//span[@itemprop="publisher"]/text()')

        # Director
        data["director"] = self._get_text(tree, '//span[@itemprop="director"]/text()')

        # Duration — format [HH:MM:SS]
        dur = self._get_text(tree, '//span[@itemprop="duration"]/text()') or \
              self._get_text(tree, '//*[contains(text(),"Run Time")]/following-sibling::text()[1]')
        data["duration_raw"] = dur

        # Description / Synopsis
        desc_nodes = tree.xpath('//div[@class="boxdesc"]//text()')
        if desc_nodes:
            desc = " ".join(t.strip() for t in desc_nodes if t.strip())
            # Couper avant <ul> ou <br><br>
            data["description"] = desc[:2000] if desc else None

        # Covers
        data["front_cover_url"] = self._get_text(tree, '//img[@id="frontbox"]/@src') or \
                                   self._get_text(tree, '//img[contains(@alt,"front")]/@src')
        data["back_cover_url"]  = self._get_text(tree, '//img[@id="backbox"]/@src') or \
                                   self._get_text(tree, '//img[contains(@alt,"back")]/@src')

        # Tags — 3 listes : categories, themes, genres
        tags = []
        for xpath in [
            '//a[contains(@href,"/categories/")]/text()',
            '//a[contains(@href,"/themes/")]/text()',
            '//a[contains(@href,"/genres/")]/text()',
        ]:
            tags += [t.strip() for t in tree.xpath(xpath) if t.strip()]
        data["tags"] = list(dict.fromkeys(tags))  # dédupliqué, ordre préservé

        # ── PHASE 2 : extraction URLs scènes individuelles ──────
        # data18 liste les scènes avec des liens /content/SCENE_ID
        scene_links = tree.xpath('//div[contains(@class,"scene")]//a[contains(@href,"/content/")]/@href')
        if not scene_links:
            scene_links = tree.xpath('//a[contains(@href,"/content/") and contains(@href,"/scene")]/@href')

        for i, href in enumerate(scene_links):
            scene_url = href if href.startswith("http") else f"https://www.data18.com{href}"
            data["scenes"].append({
                "index": i + 1,
                "title": None,      # sera enrichi si besoin
                "url_data18": scene_url,
            })

        return data
