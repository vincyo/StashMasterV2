"""
GroupPhase1Merger — Fusionne les métadonnées DVD/Group scrapées avec la DB.
"""

GROUP_FIELDS = {
    "Title": "name",
    "Aliases": "aliases",
    "Date": "date",
    "Studio": "studio",
    "Director": "director",
    "Duration": "duration",
    "Description": "description",
    "Tags": "tags",
    "URLs": "urls",
}

class GroupPhase1Merger:
    def merge(self, db_data: dict, scraped_results: list[dict], checked_fields: list[str]) -> dict:
        result = {}
        for field in checked_fields:
            db_key = GROUP_FIELDS.get(field)
            if not db_key: continue
            
            db_val = db_data.get(db_key)
            if field == "Studio" and db_data.get("studio_name"):
                db_val = db_data["studio_name"]

            scraped_vals = {}
            for r in scraped_results:
                val = r.get(db_key.replace("name", "title") if db_key == "name" else db_key)
                if val:
                    scraped_vals[r["_source"]] = val
            
            if not scraped_vals:
                status = "empty"
                suggestion = db_val
            elif not db_val:
                status = "new"
                suggestion = self._pick_best(scraped_vals)
            else:
                # Priorité Data18 : si data18 est présent et diffère de DB, c'est un conflit (même si d'autres sources matchent)
                data18_val = scraped_vals.get("data18")
                if data18_val and str(data18_val).lower().strip() != str(db_val).lower().strip():
                    status = "conflict"
                    suggestion = data18_val
                elif self._matches(db_val, scraped_vals):
                    status = "confirmed"
                    suggestion = db_val
                else:
                    status = "conflict"
                    suggestion = self._pick_best(scraped_vals)

            result[field] = {
                "status": status,
                "db_value": db_val,
                "scraped_values": scraped_vals,
                "suggestion": suggestion
            }
        return result

    def _matches(self, db_val, scraped_vals):
        db_s = str(db_val).lower().strip()
        for v in scraped_vals.values():
            if str(v).lower().strip() == db_s:
                return True
        return False

    def _pick_best(self, scraped_vals):
        # Priorité simple : data18 > iafd_dvd > adultdvdempire
        for src in ["data18", "iafd_dvd", "adultdvdempire"]:
            if src in scraped_vals:
                return scraped_vals[src]
        return list(scraped_vals.values())[0]
