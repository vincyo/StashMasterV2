"""
GroupPhase2Merger — Associe les URLs scrapées aux scènes Stash par index.

Stratégie de matching :
  1. Exact sur scene_index (numéro de scène dans le DVD)
  2. Fallback : comparaison de titre normalisé
"""


class GroupPhase2Merger:

    def merge(
        self,
        stash_scenes: list[dict],
        scraped_scene_urls: dict[int, dict[str, str]]
    ) -> list[dict]:
        """
        Associe les URLs scrapées à chaque scène Stash.

        Args:
            stash_scenes:       liste de scènes DB (scene_id, scene_index, scene_title, existing_urls)
            scraped_scene_urls: {scene_index: {"data18": url, "adultdvdempire": url}}

        Returns:
            Liste de dicts enrichis avec "new_urls" et "status"
        """
        result = []

        for scene in stash_scenes:
            scene_id    = scene["scene_id"]
            scene_index = scene.get("scene_index")
            scene_title = scene.get("scene_title", f"Scène {scene_id}")
            existing    = scene.get("existing_urls", [])

            # Chercher par index exact
            new_urls = scraped_scene_urls.get(scene_index, {})

            # Filtrer les URLs déjà présentes
            truly_new = {
                src: url for src, url in new_urls.items()
                if url and url not in existing
            }

            # Déterminer le statut
            if not new_urls:
                status = "no_match"
            elif not truly_new:
                status = "already_present"
            elif existing:
                status = "partial"
            else:
                status = "new"

            result.append({
                "scene_id":      scene_id,
                "scene_index":   scene_index,
                "scene_title":   scene_title,
                "existing_urls": existing,
                "new_urls":      truly_new,
                "status":        status,
            })

        return result
