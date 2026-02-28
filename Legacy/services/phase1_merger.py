"""
Phase1Merger — Compare les données scrapées avec la DB pour les champs Phase 1.
Identifie les confirmations et les conflits.
Gère la fusion et la normalisation des ALIAS.
"""

# Ordre de priorité des sources pour les champs simples
SOURCE_PRIORITY = ["iafd", "freeones", "babepedia", "thenude"]

# Champs Phase 1 avec leur clé DB
PHASE1_FIELDS = {
    "Name": "name",
    "Aliases": "aliases",
    "Birthdate": "birthdate",
    "Deathdate": "death_date",
    "Country": "country",
    "Ethnicity": "ethnicity",
    "Hair Color": "hair_color",
    "Eye Color": "eye_color",
    "Height": "height",
    "Weight": "weight",
    "Measurements": "measurements",
    "Fake Tits": "fake_tits",
    "Career Length": "career_length",
}


class Phase1Merger:
    def merge(self, db_data: dict, scraped_results: list[dict], 
              checked_fields: list[str]) -> dict:
        """
        Fusionner les données pour les champs cochés.
        Logique spéciale pour les ALIASES.
        """
        result = {}
        
        for field_name in checked_fields:
            db_key = PHASE1_FIELDS.get(field_name)
            if not db_key:
                continue

            # --- Logique spéciale pour les ALIASES ---
            if db_key == 'aliases':
                result[field_name] = self._merge_aliases(db_data, scraped_results)
                continue

            # --- Logique générale pour les autres champs ---
            db_value = self._normalize_value(db_data.get(db_key))
            
            scraped_values = {}
            for r in scraped_results:
                source = r.get("_source", "?")
                val = self._normalize_value(r.get(db_key))
                if val:
                    scraped_values[source] = val
            
            if not scraped_values:
                result[field_name] = self._build_result("empty", db_value, scraped_values, db_value)
            elif not db_value:
                suggestion = self._pick_best(scraped_values)
                result[field_name] = self._build_result("new", None, scraped_values, suggestion)
            elif self._matches_any(db_value, scraped_values):
                result[field_name] = self._build_result("confirmed", db_value, scraped_values, db_value)
            else:
                suggestion = self._pick_best(scraped_values)
                result[field_name] = self._build_result("conflict", db_value, scraped_values, suggestion)
        
        return result

    def _normalize_alias(self, alias: str) -> str | None:
        """Normalise une chaîne d'alias (lowercase, strip)."""
        if not isinstance(alias, str):
            return None
        normalized = alias.lower().strip()
        return normalized if normalized else None

    def _merge_aliases(self, db_data: dict, scraped_results: list[dict]) -> dict:
        """Fusionne, normalise et dédoublonne les alias de toutes les sources."""
        db_key = 'aliases'
        db_aliases = db_data.get(db_key) or []
        
        final_aliases = set()
        
        # 1. Ajouter les alias de la DB
        for alias in db_aliases:
            norm_alias = self._normalize_alias(alias)
            if norm_alias:
                final_aliases.add(norm_alias)
        
        # 2. Ajouter les alias des sources scrapées
        scraped_values_dict = {}
        for r in scraped_results:
            source_name = r.get('_source', '?')
            source_aliases = r.get(db_key)
            if source_aliases:
                scraped_values_dict[source_name] = source_aliases
                for alias in source_aliases:
                    norm_alias = self._normalize_alias(alias)
                    if norm_alias:
                        final_aliases.add(norm_alias)
        
        # 3. Déterminer le statut de la fusion
        db_set = {self._normalize_alias(a) for a in db_aliases if self._normalize_alias(a)}
        status = "empty"
        if final_aliases:
            if not db_set:
                status = "new"
            elif db_set == final_aliases:
                status = "confirmed"
            else:
                status = "conflict"  # 'conflict' indique qu'il y a des changements/ajouts

        # 4. Construire le résultat final pour l'UI
        return self._build_result(
            status,
            db_value=", ".join(sorted(list(db_set))),
            scraped_values={k: ", ".join(v) for k, v in scraped_values_dict.items()},
            suggestion=", ".join(sorted(list(final_aliases)))
        )

    def _build_result(self, status, db_value, scraped_values, suggestion):
        """Helper pour construire le dictionnaire de résultat."""
        return {
            "status": status,
            "db_value": db_value,
            "scraped_values": scraped_values,
            "suggestion": suggestion,
        }

    def _normalize_value(self, val) -> str | None:
        """Normaliser une valeur simple pour comparaison."""
        if val is None:
            return None
        # Ne gère plus les listes ici, elles sont traitées par _merge_aliases
        val = str(val).strip()
        return val if val else None

    def _matches_any(self, db_value: str, scraped_values: dict) -> bool:
        """Vérifier si la valeur DB correspond à au moins une source."""
        db_lower = db_value.lower().strip()
        for val in scraped_values.values():
            if val and val.lower().strip() == db_lower:
                return True
        return False

    def _pick_best(self, scraped_values: dict) -> str:
        """Choisir la meilleure valeur selon la priorité des sources."""
        for source in SOURCE_PRIORITY:
            if source in scraped_values and scraped_values[source]:
                return scraped_values[source]
        # Fallback : première valeur non-None
        for val in scraped_values.values():
            if val:
                return val
        return ""
