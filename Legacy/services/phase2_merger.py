"""
Phase2Merger — fusionne les résultats de scraping Phase 2
en données prêtes pour l'interface de résolution.
"""


class Phase2Merger:
    """
    Fusionne les résultats de scraping Phase 2 en données prêtes
    pour l'interface Phase2MergeDialog.
    
    Chaque champ a sa propre stratégie de fusion.
    """

    def merge(self, db_data: dict, scraped_results: list[dict]) -> dict:
        """
        Fusionner les données DB + scraping pour tous les champs Phase 2.
        
        Args:
            db_data: Données actuelles du performer depuis Stash DB
            scraped_results: Liste de dicts retournés par les extracteurs
            
        Returns:
            Dict avec les résultats fusionnés par champ
        """
        return {
            "awards":    self._merge_awards(db_data, scraped_results),
            "trivia":    self._merge_trivia(db_data, scraped_results),
            "details":   self._merge_details(db_data, scraped_results),
            "tattoos":   self._merge_body_art("tattoos", db_data, scraped_results),
            "piercings": self._merge_body_art("piercings", db_data, scraped_results),
            "tags":      self._merge_tags(db_data, scraped_results),
            "urls":      self._merge_urls(db_data, scraped_results),
        }

    # ── AWARDS ────────────────────────────────────────────────────

    def _merge_awards(self, db, scraped):
        """
        IAFD = source primaire (liste structurée).
        Autres sources = regex fallback depuis bio/trivia.
        Résultat : union dédupliquée, IAFD en premier.
        """
        seen = set()
        result = []

        # 1. IAFD en premier (plus fiable)
        for r in scraped:
            if r.get("_source") == "iafd":
                for award in (r.get("awards") or []):
                    key = award.lower().strip()
                    if key not in seen:
                        seen.add(key)
                        result.append(award)

        # 2. Autres sources en déduplication
        for r in scraped:
            if r.get("_source") != "iafd":
                for award in (r.get("awards") or []):
                    key = award.lower().strip()
                    if key not in seen:
                        seen.add(key)
                        result.append(award)

        return {
            "db_value":  db.get("awards", []),
            "merged":    result,
            "sources":   {r["_source"]: r.get("awards", []) for r in scraped},
            "strategy":  "union_iafd_first"
        }

    # ── TRIVIA ────────────────────────────────────────────────────

    def _merge_trivia(self, db, scraped):
        """
        FreeOnes "Additional Information" est la meilleure source.
        TheNude bios studio = contexte supplémentaire.
        Babepedia peut avoir quelques lignes.
        → Proposer les 3 séparément pour que l'utilisateur choisisse/combine.
        """
        by_source = {}
        for r in scraped:
            trivia = r.get("trivia")
            if trivia:
                by_source[r["_source"]] = trivia

        # Sélection automatique par priorité
        best = None
        TRIVIA_PRIORITY = ["freeones", "thenude", "babepedia"]
        for src in TRIVIA_PRIORITY:
            if src in by_source:
                best = by_source[src]
                break

        return {
            "db_value":   db.get("trivia"),
            "by_source":  by_source,
            "suggestion": best,
            "strategy":   "best_source_priority"
        }

    # ── BIO / DETAILS ──────────────────────────────────────────────

    def _merge_details(self, db, scraped):
        """
        FreeOnes = bio narrative la plus complète.
        TheNude = bios studio (contexte professionnel).
        Babepedia = court texte.
        → Option 1 : FreeOnes seule
        → Option 2 : Toutes sources concaténées (séparateurs clairs)
        → Option 3 : DB actuelle
        """
        by_source = {}
        for r in scraped:
            detail = r.get("details")
            if detail and len(detail) > 50:
                by_source[r["_source"]] = detail

        # Construire option "fusion" ordonnée
        DETAIL_ORDER = ["freeones", "babepedia", "thenude", "boobpedia"]
        fused_parts = []
        for src in DETAIL_ORDER:
            if src in by_source:
                fused_parts.append(f"[Source: {src.upper()}]\n{by_source[src]}")

        fused = "\n\n---\n\n".join(fused_parts) if fused_parts else None

        return {
            "db_value":  db.get("details"),
            "by_source": by_source,
            "fused":     fused,
            "strategy":  "user_choice"
        }

    # ── TATTOOS / PIERCINGS ────────────────────────────────────────

    def _merge_body_art(self, field: str, db, scraped):
        """
        Hiérarchie : IAFD/FreeOnes (structuré) > Babepedia/TheNude (flat).
        Union dédupliquée par (position, description).
        Les entrées position="multiple" ne sont gardées que si aucune
        entrée structurée n'existe pour ce champ.
        """
        structured = []
        flat = []
        seen = set()

        QUALITY_ORDER = ["iafd", "freeones", "thenude", "babepedia"]
        for source in QUALITY_ORDER:
            for r in scraped:
                if r.get("_source") != source:
                    continue
                for item in (r.get(field) or []):
                    pos  = (item.get("position") or "").lower().strip()
                    desc = (item.get("description") or "").lower().strip()
                    key  = f"{pos}|{desc}"
                    if key in seen:
                        continue
                    seen.add(key)
                    if pos == "multiple":
                        flat.append(item)
                    else:
                        structured.append(item)

        # Utiliser flat uniquement si aucune entrée structurée
        merged = structured if structured else flat

        return {
            "db_value":  db.get(field, ""),
            "merged":    merged,
            "sources":   {r["_source"]: r.get(field, []) for r in scraped},
            "strategy":  "structured_priority"
        }

    # ── TAGS ──────────────────────────────────────────────────────

    def _merge_tags(self, db, scraped):
        """
        Union de toutes les sources, déduplification insensible à la casse.
        """
        seen = set()
        merged = []
        for r in scraped:
            for tag in (r.get("tags") or []):
                key = tag.lower().strip()
                if key and key not in seen:
                    seen.add(key)
                    merged.append(tag.strip().title())
        merged.sort()
        return {
            "db_value": db.get("tags", []),
            "merged":   merged,
            "sources":  {r["_source"]: r.get("tags", []) for r in scraped},
            "strategy": "union_all"
        }

    # ── URLs ──────────────────────────────────────────────────────

    def _merge_urls(self, db, scraped):
        """
        Agréger databases + social_media de toutes les sources.
        Priorité : freeones > iafd > babepedia > thenude (pour ordre d'affichage).
        """
        URL_PRIORITY = ["freeones", "iafd", "babepedia", "thenude", "boobpedia"]
        merged = {}
        for source in reversed(URL_PRIORITY):
            for r in scraped:
                if r.get("_source") != source:
                    continue
                for key, url in (r.get("urls") or {}).items():
                    if url:
                        merged[key] = url
        return {
            "db_value": db.get("urls", []),
            "merged":   merged,
            "strategy": "priority_merge"
        }
