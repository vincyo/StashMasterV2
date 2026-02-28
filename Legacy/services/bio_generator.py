"""
BioGenerator — Génère une bio professionnelle via IA à partir des données V2.
Utilise Gemini (API REST) ou Ollama (fallback local).
"""
import os
import json
import urllib.request

GEMINI_MODEL = "gemini-2.0-flash"  # Flash = moins cher, suffisant
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

SYSTEM_PROMPT = """Tu es un rédacteur expert pour une base de données de films pour adultes.
Ton objectif est de rédiger une biographie structurée et professionnelle en FRANÇAIS (Québec) pour l'artiste, basée sur les faits fournis.

Respecte scrupuleusement le format suivant (avec les émojis et le gras) :

### [Nom] : [Titre accrocheur]

**Introduction**
[Paragraphe introductif : identité, dates clés, pseudonymes, résumé de carrière.]

**📅 Origines et Premiers Pas**
[Détails sur les origines, la jeunesse, et l'entrée dans l'industrie.]

**🏆 Carrière et Filmographie**
[Parcours professionnel, studios majeurs, évolution, scènes notables.]

**💡 Faits Intéressants & Vie Personnelle**
[Vie hors caméra, personnalité, anecdotes, réseaux sociaux.]

**👗 Apparence et Style**
[Attributs physiques, style, tatouages, piercings.]

**🏆 Prix et Distinctions**
[Récompenses et nominations. Si aucune, mentionner la popularité.]

**Conclusion rapide**
[Phrase de conclusion sur l'héritage de l'artiste.]

Règles impératives :
- N'invente AUCUN fait. Base-toi uniquement sur les données fournies (contexte Stash, données scrapées).
- Si une information est manquante pour une section, rédige une phrase générale ou passe brièvement, mais garde la section.
- Tu DOIS inclure TOUTES les 7 sections (Introduction, Origines, Carrière, Faits, Apparence, Prix, Conclusion).
- Le ton doit être informatif, fluide et agréable à lire (style encyclopédique/journalistique).
- Utilise le français standard du Québec.
"""


class BioGenerator:
    def __init__(self, gemini_key: str | None = None, ollama_url: str = "http://localhost:11434"):
        self.gemini_key = gemini_key or self._load_gemini_key()
        self.ollama_url = ollama_url

    def _load_gemini_key(self) -> str | None:
        # Chercher le .gemini_key à la racine du projet
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        key_path = os.path.join(project_root, ".gemini_key")

        if os.path.exists(key_path):
            with open(key_path, 'r') as f:
                return f.read().strip()
        
        # Fallback pour le chemin d'origine si nécessaire (peut être retiré plus tard)
        legacy_path = r"F:\V2\.gemini_key"
        if os.path.exists(legacy_path):
             with open(legacy_path, 'r') as f:
                return f.read().strip()

        return None

    def build_context_from_v2(
        self,
        db_data: dict,
        stash_ctx: dict,
        scraped_results: list[dict],
        merged_data: dict,
        checked_fields: list[str],
    ) -> dict:
        """
        Construit le contexte de génération depuis les données V2.
        
        Args:
            db_data:         données DB du performer (V2 PerformerDB)
            stash_ctx:       contexte Stash (scènes, studios, collabs)
            scraped_results: résultats bruts des extracteurs Phase 2
            merged_data:     résultats fusionnés Phase2Merger
            checked_fields:  champs cochés par l'utilisateur
        """
        ctx = {
            "name":      db_data.get("name", "Unknown"),
            "birthdate": db_data.get("birthdate") if "Birthdate" in checked_fields else None,
            "details":   db_data.get("details"),
            "mini_bios": [],
            "trivia":    [],
            "scene_count":    stash_ctx.get("scene_count", 0),
            "studios":        stash_ctx.get("studios", [])[:10],
            "collaborators":  [c["name"] for c in stash_ctx.get("collaborators", [])[:5]],
            "awards":         [],
            "socials":        [],
            "career_length":  None,
        }

        # Bios scrapées (Details)
        if "Details" in checked_fields:
            for src, bio_text in merged_data.get("details", {}).get("by_source", {}).items():
                if bio_text and len(bio_text) > 50:
                    ctx["mini_bios"].append(f"[{src.upper()}] {bio_text[:600]}")

        # Détection "Infos limitées" : Si aucune bio textuelle n'est trouvée, on autorise plus de specs techniques
        limited_info_mode = (len(ctx["mini_bios"]) == 0)

        # Helper pour récupérer une valeur (DB > Merged/Scraped)
        def get_val(key):
            v = db_data.get(key)
            if not v and isinstance(merged_data, dict):
                v = merged_data.get(key)
            
            # Fallback : Chercher dans les résultats bruts du scraping
            if not v and scraped_results:
                for res in scraped_results:
                    if res.get(key):
                        v = res.get(key)
                        break
            return v

        # Career Length (Phase 1)
        if "Career Length" in checked_fields:
            val = get_val("career_length")
            if val: ctx["career_length"] = val

        # 1. Origines & Apparence de base (Toujours utile pour la narration)
        base_specs = []
        if "Ethnicity" in checked_fields:
            val = get_val("ethnicity")
            if val: base_specs.append(f"Ethnicity: {val}")
        if "Country" in checked_fields:
            val = get_val("country")
            if val: base_specs.append(f"Country: {val}")
        if "Hair Color" in checked_fields:
            val = get_val("hair_color")
            if val:
                if isinstance(val, list):
                    val = val[0] if val else ""
                val = str(val).split(",")[0].strip() # Garder couleur principale
                if val: base_specs.append(f"Hair: {val}")
        if "Eye Color" in checked_fields:
            val = get_val("eye_color")
            if val: base_specs.append(f"Eyes: {val}")
        
        if base_specs:
            ctx["trivia"].append("Appearance/Origins: " + ", ".join(base_specs))

        # 2. Specs Techniques (Seulement si infos limitées pour éviter l'effet "fiche technique")
        specs = []
        tech_map = {
            "Height":       ("height", "Height"),
            "Weight":       ("weight", "Weight"),
            "Measurements": ("measurements", "Measurements"),
            "Fake Tits":    ("fake_tits", "Fake Tits"),
        }
        
        if limited_info_mode:
            for field, (db_key, label) in tech_map.items():
                if field in checked_fields and db_data.get(db_key):
                    specs.append(f"{label}: {db_data[db_key]}")
                if field in checked_fields:
                    val = get_val(db_key)
                    if val: specs.append(f"{label}: {val}")
            
            if specs:
                ctx["trivia"].append("Physical Stats (Use to flesh out bio if needed): " + ", ".join(specs))

        # Awards (depuis merged_data)
        if "Awards" in checked_fields:
            awards = merged_data.get("awards", {}).get("merged", [])
            if awards:
                ctx["awards"] = awards  # Stocker la liste complète pour le prompt

        # Aliases
        if "Aliases" in checked_fields and db_data.get("aliases"):
            aliases = db_data["aliases"]
            if isinstance(aliases, list):
                aliases = ", ".join(aliases)
            ctx["trivia"].append(f"Aliases: {aliases}")

        # URLs (Socials)
        if "URLs" in checked_fields:
            urls_data = merged_data.get("urls", {}).get("merged", {})
            # Filtrer pour ne garder que les réseaux sociaux principaux
            social_keys = ["twitter", "instagram", "onlyfans", "facebook", "tiktok"]
            found_socials = []
            for k, v in urls_data.items():
                if any(s in k.lower() for s in social_keys):
                    # On envoie "Twitter: http..." pour que l'IA puisse extraire le handle si elle veut
                    found_socials.append(f"{k} ({v})")
            if found_socials:
                ctx["socials"] = found_socials

        return ctx

    def build_prompt(self, ctx: dict) -> str:
        """Construit le prompt utilisateur depuis le contexte."""
        parts = [f"Performer: {ctx['name']}"]

        if ctx.get("birthdate"):
            parts.append(f"Born: {ctx['birthdate']}")

        if ctx.get("career_length"):
            parts.append(f"Years Active: {ctx['career_length']}")

        if ctx.get("trivia"):
            parts.append("\nKnown facts:")
            parts.extend(f"  - {t}" for t in ctx["trivia"])

        if ctx.get("scene_count"):
            parts.append(f"\nStash scenes: {ctx['scene_count']}")

        if ctx.get("studios"):
            parts.append(f"Studios worked with: {', '.join(ctx['studios'][:8])}")

        if ctx.get("collaborators"):
            parts.append(f"Frequent collaborators: {', '.join(ctx['collaborators'])}")

        if ctx.get("awards"):
            parts.append("\nAwards & Nominations:")
            # On envoie les 20 premiers pour donner de la matière à la section 'Prix'
            parts.append("; ".join(ctx["awards"][:20]))

        if ctx.get("socials"):
            parts.append(f"\nSocial Media: {', '.join(ctx['socials'])}")

        if ctx.get("mini_bios"):
            parts.append("\nSource bios for reference:")
            for bio in ctx["mini_bios"][:3]:  # max 3 sources
                parts.append(f"  {bio}")

        if ctx.get("details"):
            parts.append(f"\nCurrent Stash bio: {ctx['details'][:400]}")

        parts.append("\nRédige la biographie en français (Québec) selon le modèle.")
        return "\n".join(parts)

    def generate(self, ctx: dict) -> str | None:
        """Génère la bio. Essaie Gemini d'abord, Ollama en fallback."""
        prompt = self.build_prompt(ctx)

        if self.gemini_key:
            result = self._call_gemini(prompt)
            if result:
                return result.strip()

        return self._call_ollama(prompt)

    def _call_gemini(self, user_prompt: str) -> str | None:
        url = GEMINI_API_URL.format(model=GEMINI_MODEL, key=self.gemini_key)
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 300,
            }
        }
        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=data,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                result = json.loads(resp.read())
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"[BioGenerator] Gemini error: {e}")
            return None

    def _call_ollama(self, user_prompt: str, model: str = "dolphin-llama3") -> str | None:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 300}
        }
        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f"{self.ollama_url}/api/chat", data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
            return result["message"]["content"]
        except Exception as e:
            print(f"[BioGenerator] Ollama error: {e}")
            return None
