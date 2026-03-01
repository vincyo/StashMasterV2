#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BioGenerator - Service de génération de biographies
"""

import os
import re
import json
import urllib.request
import urllib.error
import requests
import gc
from typing import Dict, List, Optional

GEMINI_MODEL   = "gemini-2.0-flash"
GEMINI_API_URL = ("https://generativelanguage.googleapis.com/v1beta/models"
                  "/{model}:generateContent?key={key}")

SYSTEM_PROMPT_BIO = """Tu es un rédacteur expert pour une base de données de films pour adultes.
Ton objectif est de rédiger une biographie structurée et professionnelle en FRANÇAIS (Québec) pour l'artiste, basée sur les faits fournis ET sur tes connaissances personnelles sur cet artiste.

STRUCTURE OBLIGATOIRE (7 sections, dans cet ordre) :

### [Nom] : [Sous-titre accrocheur]

**Introduction** — 2-3 phrases : identité complète, date et lieu de naissance, année début de carrière, pseudonymes principaux.

**📅 Origines et Premiers Pas** — 3-4 phrases : origines culturelles, vie avant l'industrie, entrée dans l'industrie, ambition.

**🏆 Carrière et Filmographie** — 4-5 phrases : studios partenaires, diversité des rôles, évolution, apogée, constance qualitative. Enrichis avec des faits réels si tu les connais.

**💡 Faits Marquants & Personnalité** — 3-4 phrases : personnalité, vie privée, loisirs, anecdotes notables. Utilise les trivia fournis.

**👗 Apparence et Style** — 3-4 phrases : description physique complète en prose (cheveux, mensurations, origines, tatouages/piercings), style scénique.

**🏆 Prix et Distinctions** — 3-4 phrases : cérémonies et victoires spécifiques intégrées en prose, jamais en liste.

**Conclusion rapide** — 2 phrases : bilan, héritage, avenir.

RÈGLES ABSOLUES :
- ZÉRO liste à puces — uniquement paragraphes en prose fluide
- Mesures/taille/poids intégrés naturellement dans la prose d'Apparence
- Prix intégrés en phrase, JAMAIS sous forme année-catégorie
- Français professionnel et soutenu, avec une touche québécoise
- Utiliser ABSOLUTEMENT toutes les données fournies
- Tu peux enrichir avec tes propres connaissances sur l'artiste (studios réels, prix connus, etc.)
- Ne pas mentionner que tu es une IA
- Longueur cible : 2800 à 3500 caractères
"""


class BioGenerator:
    """Générateur de biographies avec Gemini (recherche web) et Ollama (local)"""

    def __init__(self, ollama_url: str = "http://localhost:11434/api/generate"):
        self.ollama_url = ollama_url
        # GPU settings for Ollama generation
        self.ollama_num_gpu = int(os.getenv("OLLAMA_NUM_GPU", "999"))
        self.ollama_num_thread = int(os.getenv("OLLAMA_NUM_THREAD", "8"))
        self.gemini_key = self._load_gemini_key()
        self.gemini_search_enabled = True
        self._gemini_disabled = False
        self._gemini_warned_search_disabled = False
        self._gemini_warned_disabled = False
        self._interview_cache: Dict[str, str] = {}
        if self.gemini_key:
            print("[BioGenerator] Clé Gemini chargée — génération Google avec IA activée.")
        else:
            print("[BioGenerator] Pas de clé Gemini — génération Google en mode template.")
        print(f"[OLLAMA] Options GPU actives: num_gpu={self.ollama_num_gpu}, num_thread={self.ollama_num_thread}")

    def _get_interview_context(self, performer_name: str, metadata: Dict) -> str:
        """Construit un contexte compact depuis les URLs d'interviews.

        Objectif: enrichir la génération de bio avec des infos biographiques fiables
        (Q/R, parcours, anecdotes). Limité pour éviter de ralentir le workflow.
        """
        urls = metadata.get("urls") or []
        if isinstance(urls, str):
            urls = [u.strip() for u in re.split(r"[\s,\n\r]+", urls) if u.strip()]
        if not isinstance(urls, list) or not urls:
            return ""

        try:
            from services.interview_extractor import is_interview_url, extract_interview_text
        except Exception:
            return ""

        interview_urls = [u for u in urls if isinstance(u, str) and is_interview_url(u)]
        if not interview_urls:
            return ""

        # Limites conservatrices
        max_pages = 2
        max_chars = 2500

        chunks: List[str] = []
        used = 0
        for u in interview_urls[:max_pages]:
            u = u.strip()
            if not u:
                continue

            if u in self._interview_cache:
                text = self._interview_cache[u]
            else:
                title, text_raw = extract_interview_text(u)
                text = ""
                if text_raw:
                    header = f"SOURCE INTERVIEW: {u}"
                    if title:
                        header += f"\nTITRE: {title.strip()}"
                    text = (header + "\n" + text_raw.strip()).strip()
                self._interview_cache[u] = text

            if not text:
                continue

            remaining = max_chars - used
            if remaining <= 0:
                break
            if len(text) > remaining:
                text = text[:remaining]
            chunks.append(text)
            used += len(text) + 2

        combined = "\n\n".join(chunks).strip()
        if combined:
            print(f"[BioGenerator] Contexte interviews ajouté ({len(combined)} chars) — {performer_name}")
        return combined

    def _ollama_request(self, model: str, prompt: str, timeout: int = 360) -> Optional[str]:
        """Call Ollama with GPU-preferred options and safe fallback."""
        payload_gpu = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "15m",
            "options": {
                "num_gpu": self.ollama_num_gpu,
                "num_thread": self.ollama_num_thread,
            }
        }

        try:
            response = requests.post(self.ollama_url, json=payload_gpu, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                text = data.get('response', '')
                if text:
                    print(f"[OLLAMA] Génération OK (GPU demandé) — model={model}")
                    return text
            else:
                print(f"[OLLAMA] Réponse non-200 avec options GPU: {response.status_code}")
        except Exception as e:
            print(f"[OLLAMA] Erreur appel GPU, fallback CPU/auto: {e}")

        # Fallback sans options explicites
        try:
            payload_fallback = {
                "model": model,
                "prompt": prompt,
                "stream": False,
            }
            response = requests.post(self.ollama_url, json=payload_fallback, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                text = data.get('response', '')
                if text:
                    print(f"[OLLAMA] Génération OK (fallback) — model={model}")
                    return text
            return None
        except Exception as e:
            print(f"[OLLAMA] Erreur fallback: {e}")
            return None

    def clear_runtime_caches(self, model: str = "dolphin-mistral:7b") -> bool:
        """Clear Python runtime cache and ask Ollama to unload model from RAM/VRAM."""
        ok = True
        try:
            gc.collect()
        except Exception:
            ok = False

        # Ask Ollama to unload model from memory cache
        try:
            unload_payload = {
                "model": model,
                "prompt": "",
                "stream": False,
                "keep_alive": 0,
            }
            resp = requests.post(self.ollama_url, json=unload_payload, timeout=30)
            if resp.status_code == 200:
                print(f"[OLLAMA] Cache modèle déchargé: {model}")
            else:
                ok = False
                print(f"[OLLAMA] Échec clear cache modèle ({resp.status_code})")
        except Exception as e:
            ok = False
            print(f"[OLLAMA] Erreur clear cache: {e}")

        return ok

    def _load_gemini_key(self) -> Optional[str]:
        """Cherche .gemini_key à la racine du projet."""
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        for path in [os.path.join(root, ".gemini_key"), r"F:\Nouveau dossier\.gemini_key"]:
            if os.path.exists(path):
                try:
                    key = open(path, 'r').read().strip()
                    if key:
                        return key
                except Exception:
                    pass
        return None

    def _call_gemini(self, user_prompt: str, use_search: bool = True) -> Optional[str]:
        """Appelle Gemini 2.0 Flash, avec grounding Google Search si use_search=True."""
        if not self.gemini_key or self._gemini_disabled:
            return None

        do_search = bool(use_search and self.gemini_search_enabled)
        url = GEMINI_API_URL.format(model=GEMINI_MODEL, key=self.gemini_key)
        payload: Dict = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT_BIO}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.75,
                "maxOutputTokens": 1500,
            },
        }
        if do_search:
            # Grounding Google Search : Gemini va chercher sur le web pour enrichir la bio
            payload["tools"] = [{"google_search": {}}]

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            return text.strip()
        except urllib.error.HTTPError as e:
            # 401/403 arrivent souvent quand l'API key n'a pas les droits pour le grounding google_search.
            code = getattr(e, "code", None)

            # Si le grounding est activé et qu'on reçoit 403/401, on retente une fois sans search.
            if code in (401, 403) and do_search:
                self.gemini_search_enabled = False
                if not self._gemini_warned_search_disabled:
                    self._gemini_warned_search_disabled = True
                    print("[GEMINI] 403/401 avec google_search — retry sans search et grounding désactivé pour la session.")
                return self._call_gemini(user_prompt, use_search=False)

            # Si même sans search on est en 401/403, on désactive Gemini pour éviter le spam.
            if code in (401, 403):
                self._gemini_disabled = True
                if not self._gemini_warned_disabled:
                    self._gemini_warned_disabled = True
                    print("[GEMINI] 403/401 persistant — Gemini désactivé pour la session (clé/droits à vérifier).")
                return None

            print(f"[GEMINI] Erreur HTTP {code} : {e}")
            return None
        except Exception as e:
            print(f"[GEMINI] Erreur : {e}")
            return None

    def clean_awards_with_gemini(self, raw_awards: str) -> str:
        """
        Utilise Gemini pour nettoyer et formater les awards.
        Fallback sur regex si Gemini échoue ou prend trop de temps.
        """
        if not raw_awards or not raw_awards.strip():
            return ""
        
        # Si pas de clé Gemini, utiliser fallback immédiatement
        if not self.gemini_key:
            from utils.normalizer import clean_awards_field
            return clean_awards_field(raw_awards)
        
        prompt = f"""Nettoie et formate cette liste d'awards de performer adulte.

RÈGLES :
1. Une ligne par award, format : "ANNÉE ORGANISATION - Catégorie (Film si mentionné) [Winner/Nominee]"
2. Organisations reconnues : AVN Award, XBIZ Award, XRCO Award, NightMoves Award, Spank Bank Award, PornHub Award
3. Supprimer TOUTES les phrases de prose/bio (ex: "she has been", "she was also", "including", etc.)
4. Séparer les awards collés (ex: "Awards2015 Nominee: Cat1 Nominee: Cat2" → 2 lignes distinctes)
5. Nettoyer les caractères UTF-8 mal encodés (Ã‚â€, etc.)
6. Si l'année ou l'organisation manque, tenter de l'inférer du contexte

TEXTE BRUT :
{raw_awards[:3000]}

Retourne UNIQUEMENT la liste nettoyée, une ligne par award, sans explication."""

        try:
            cleaned = self._call_gemini(prompt, use_search=False)
            if cleaned and len(cleaned) > 20:  # Validation minimale
                return cleaned
        except Exception as e:
            print(f"[GEMINI] Erreur nettoyage awards : {e}")
        
        # Fallback sur regex
        from utils.normalizer import clean_awards_field
        return clean_awards_field(raw_awards)



    def _summarize_awards(self, awards_raw: str) -> str:
        """Convertit une liste d'awards nettoyés en une phrase de prose."""
        if not awards_raw or not awards_raw.strip():
            return ""
        lines = [l.strip() for l in awards_raw.splitlines() if l.strip()]
        ceremonies = set()
        wins = []
        nom_count = 0
        
        for line in lines:
            # Ignorer les lignes vides ou trop courtes
            if len(line) < 5:
                continue
            
            # Pattern pour nouveau format: "2015 AVN Award - Category [Status]"
            m = re.match(r'^(\d{4})\s+([A-Za-z\s]+Award)\s*-\s*(.+?)\s*(?:\[(Winner|Nominee)\])?$', line, re.I)
            if m:
                year, org, category, status = m.groups()
                ceremonies.add(org.strip())
                
                # Nettoyer la catégorie (retirer œuvre entre parenthèses pour le résumé)
                category = re.sub(r'\s*\([^)]+\)', '', category).strip()
                
                if status and 'winner' in status.lower():
                    wins.append(f"{category} ({year})")
                else:
                    nom_count += 1
            
            # Ancien format pour compatibilité : "2015 - Nominee: Category"
            else:
                old_m = re.match(r'^(\d{4})\s*[-–]\s*(Winner|Nominee)\s*:\s*(.+)$', line, re.I)
                if old_m:
                    year, status, category = old_m.groups()
                    category = re.sub(r'\s*\([^)]+\)', '', category).strip()
                    if 'winner' in status.lower():
                        wins.append(f"{category} ({year})")
                    else:
                        nom_count += 1
        
        if not ceremonies and not wins and nom_count == 0:
            return ""
        
        cer_str = " et ".join(sorted(ceremonies)) if ceremonies else "plusieurs cérémonies de l'industrie"
        parts = []
        
        if wins:
            win_str = ", ".join(wins[:3])
            if len(wins) > 3:
                win_str += f" et {len(wins)-3} autre(s) trophée(s)"
            parts.append(f"remportant notamment {win_str}")
        
        if nom_count:
            parts.append(f"cumulant plus de {nom_count} nomination(s)")
        
        detail = ", ".join(parts)
        if detail:
            return f"Son talent a été salué aux {cer_str}, {detail}."
        return f"Son talent a été reconnu par de multiples distinctions aux {cer_str}."


    def _prose_appearance(self, measurements: str, height: str, weight: str,
                          hair_color: str, ethnicity: str,
                          tattoos: str, piercings: str) -> str:
        """Rédige la section apparence sous forme de prose."""
        parts = []
        if hair_color and hair_color not in ('[couleur]', 'Non disponible'):
            parts.append(f"Sa chevelure {hair_color.lower()} encadre un visage expressif")
        if measurements and measurements not in ('[mesures]', 'Non disponible'):
            parts.append(f"sa silhouette est mise en valeur par des mensurations de {measurements}")
        if height and height not in ('[taille]', 'Non disponible'):
            h = str(height).replace('cm', '').strip()
            parts.append(f"une stature de {h} cm")
        if weight and weight not in ('[poids]', 'Non disponible'):
            w = str(weight).replace('kg', '').strip()
            parts.append(f"un poids de {w} kg")
        prose = ""
        if parts:
            prose = ". ".join(p.capitalize() for p in parts) + "."

        body_art = []
        tat = str(tattoos).strip()
        if tat and tat.lower() not in ('none', 'information non disponible', '[mesures]', ''):
            # Condenser une liste multi-lignes en une courte mention
            tat_lines = [l.strip() for l in tat.splitlines() if l.strip()]
            if len(tat_lines) > 2:
                body_art.append(f"plusieurs tatouages ornent son corps")
            elif len(tat_lines) > 0:
                body_art.append(f"elle arbore {tat_lines[0].lower()}")
        pier = str(piercings).strip()
        if pier and pier.lower() not in ('none', 'information non disponible', ''):
            body_art.append(f"des piercings {pier.lower()}")
        if body_art:
            prose += " " + " et ".join(body_art).capitalize() + "."
        return prose.strip()

    def _prose_trivia(self, trivia: str) -> str:
        """Condense une liste de faits trivia en prose fluide."""
        if not trivia or not trivia.strip():
            return ""
        lines = [l.strip().rstrip('.') for l in trivia.splitlines() if l.strip()]
        if len(lines) == 1:
            return lines[0] + "."
        selected = lines[:3]
        if len(selected) == 1:
            return selected[0] + "."
        return ". ".join(selected) + "."

    def _prose_bio_raw(self, bio_raw: str, performer_name: str) -> str:
        """Extrait 2-3 phrases pertinentes du bio_raw scrappé pour enrichir la section carrière."""
        if not bio_raw or not bio_raw.strip():
            return ""
        # Garder les phrases qui contiennent des infos de carrière (studios, années, prix...)
        sentences = re.split(r'(?<=[.!?])\s+', bio_raw.strip())
        keywords = re.compile(
            r'\b(studio|brazzers|evil angel|digital|mofos|naughty|reality|\d{4}|'
            r'award|avn|xbiz|carrière|career|film|scène|scene|travaill|work|'
            r'collaborate|nomm|nomin|won|remport|gagn)\b', re.I)
        relevant = [s.strip() for s in sentences if keywords.search(s) and len(s) > 40]
        if not relevant:
            # fallback : prendre les 2 premières phrases non vides
            relevant = [s.strip() for s in sentences if len(s.strip()) > 40][:2]
        return ' '.join(relevant[:3])
        if len(lines) == 1:
            return lines[0] + "."
        # Garder les 3 premiers faits max, les joindre en prose
        selected = lines[:3]
        if len(selected) == 1:
            return selected[0] + "."
        return ". ".join(selected) + "."

    def generate_google_bio(self, performer_name: str, metadata: Dict) -> str:
        """Génère une bio via Gemini 2.0 Flash (avec recherche web) si clé dispo, sinon template local."""
        # Données brutes
        birthdate    = metadata.get('birthdate')    or ''
        birthplace   = metadata.get('birthplace')   or metadata.get('country') or ''
        career_start = metadata.get('career_start') or ''
        if not career_start and metadata.get('career_length'):
            career_start = str(metadata['career_length']).split('-')[0].strip()
        aliases      = metadata.get('aliases') or []
        ethnicity    = metadata.get('ethnicity')    or ''
        height       = metadata.get('height')       or ''
        weight       = metadata.get('weight')       or ''
        measurements = metadata.get('measurements') or ''
        hair_color   = metadata.get('hair_color')   or ''
        tattoos      = metadata.get('tattoos')      or ''
        piercings    = metadata.get('piercings')    or ''
        trivia       = metadata.get('trivia')       or ''
        awards_raw   = metadata.get('awards') or metadata.get('awards_summary') or ''
        bio_raw      = metadata.get('bio_raw') or metadata.get('details', '')
        stash_bio    = metadata.get('stash_bio', '')  # Bio déjà présente dans Stash

        interviews_ctx = metadata.get('interviews') or ''
        if not interviews_ctx:
            interviews_ctx = self._get_interview_context(performer_name, metadata)
            if interviews_ctx:
                metadata['interviews'] = interviews_ctx
        if isinstance(aliases, str):
            aliases = [a.strip() for a in re.split(r'[,\n]', aliases) if a.strip()]
        alias_str = ', '.join(aliases) if aliases else performer_name

        # Essai Gemini (avec Google Search grounding)
        if self.gemini_key:
            lines = [
                f"Rédige une biographie complète en français (Québec) pour : {performer_name}",
                "",
                "DONNÉES FACTUELLES DISPONIBLES :",
            ]
            if birthdate:    lines.append(f"- Date de naissance : {birthdate}")
            if birthplace:   lines.append(f"- Lieu de naissance : {birthplace}")
            if career_start: lines.append(f"- Début de carrière : {career_start}")
            cl = metadata.get('career_length')
            if cl:           lines.append(f"- Années d'activité : {cl}")
            if alias_str != performer_name: lines.append(f"- Pseudonymes : {alias_str}")
            if ethnicity:    lines.append(f"- Ethnicité : {ethnicity}")
            if hair_color:   lines.append(f"- Cheveux : {hair_color}")
            if measurements: lines.append(f"- Mensurations : {measurements}")
            if height:       lines.append(f"- Taille : {height} cm")
            if weight:       lines.append(f"- Poids : {weight} kg")
            if tattoos:      lines.append(f"- Tatouages : {tattoos}")
            if piercings:    lines.append(f"- Piercings : {piercings}")
            if trivia:       lines.append(f"\nTrivia :\n{trivia[:800]}")
            if awards_raw:   lines.append(f"\nAwards :\n{awards_raw[:1200]}")
            if bio_raw:      lines.append(f"\nBio scrapée :\n{bio_raw[:1000]}")
            if interviews_ctx:
                lines.append(f"\nInterviews (extraits) :\n{interviews_ctx[:2500]}")
            if stash_bio and stash_bio != bio_raw:
                lines.append(f"\nBio actuelle dans Stash (à améliorer/enrichir) :\n{stash_bio[:1200]}")
            lines += [
                "",
                "Tu peux enrichir avec tes connaissances réelles (studios, prix vérifiables, faits publics).",
                "Respecte la structure en 7 sections définie dans le système.",
            ]
            print(f"[GEMINI] Génération bio pour {performer_name} (avec recherche web)...")
            result = self._call_gemini("\n".join(lines), use_search=True)
            if result:
                print(f"[GEMINI] Bio générée ({len(result)} caractères)")
                return result
            print("[GEMINI] Échec — repli sur template local.")

        # Repli template local
        print(f"[BIO] Génération template local pour {performer_name}")
        awards_prose     = self._summarize_awards(awards_raw)
        trivia_prose     = self._prose_trivia(trivia)
        appearance_prose = self._prose_appearance(
            measurements, height, weight, hair_color, ethnicity, tattoos, piercings)
        career_enrich    = self._prose_bio_raw(bio_raw or stash_bio, performer_name)
        bd  = birthdate    or '[date de naissance]'
        bp  = birthplace   or '[lieu]'
        cs  = career_start or '[année de début]'
        eth = ethnicity    or '[origine]'

        intro = (
            f"Née le {bd} à {bp}, {performer_name} est une personnalité respectée du monde du "
            f"divertissement adulte. Dès son entrée remarquée en {cs}, elle a su s'imposer par "
            f"son charisme et son énergie. Connue sous les noms de {alias_str}, elle a navigué "
            f"avec succès dans une industrie compétitive."
        )
        origines = (
            f"Issue d'une culture {eth}, {performer_name} a passé ses premières années dans la "
            f"région de {bp}. Son engagement dès {cs} témoigne d'une volonté farouche de réussir."
        )
        carriere = (
            "Sa carrière est jalonnée de succès et de collaborations avec les leaders de l'industrie."
            + (" " + career_enrich if career_enrich else "")
        )
        faits = (
            f"En dehors des plateaux, {performer_name} cultive un univers personnel riche."
            + (" " + trivia_prose if trivia_prose else "")
        )
        apparence = (
            f"Sa beauté distinctive, reflet de ses origines {eth}, est l'un de ses traits les plus remarquables. "
            + appearance_prose
        )
        prix = awards_prose or "Ses efforts ont été couronnés par de nombreuses nominations et récompenses."
        conclusion = (
            f"En résumé, {performer_name} est une véritable icône de son temps. "
            "Son influence perdurera, laissant une trace indélébile dans l'histoire du divertissement moderne."
        )

        tmpl = "\n\n".join([
            f"### {performer_name} : Une Carrière d'Excellence et un Parcours Inspirant",
            f"**Introduction**\n{intro}",
            f"**📅 Origines et Premiers Pas**\n{origines}",
            f"**🏆 Carrière et Filmographie**\n{carriere}",
            f"**💡 Faits Marquants & Personnalité**\n{faits}",
            f"**👗 Apparence et Style**\n{apparence}",
            f"**🏆 Prix et Distinctions**\n{prix}",
            f"**Conclusion**\n{conclusion}",
        ])
        if len(tmpl) > 3500:
            tmpl = tmpl[:3497] + "..."
        return tmpl

    def generate_ollama_bio(self, performer_name: str, metadata: Dict, custom_prompt: str = "", model: str = "dolphin-mistral:7b") -> Optional[str]:
        """Génère une bio avec Ollama en intégrant des directives personnalisées"""
        try:
            # Variables pour les f-strings des prompts
            ethnicity   = metadata.get('ethnicity', 'Non disponible')
            hair_color  = metadata.get('hair_color', 'Non disponible')
            measurements= metadata.get('measurements', 'Non disponible')
            height      = metadata.get('height', 'Non disponible')
            weight      = metadata.get('weight', 'Non disponible')
            career_start= metadata.get('career_start', 'Non disponible')

            # Construction des infos de base
            aliases_str = (', '.join(metadata.get('aliases', []))
                           if isinstance(metadata.get('aliases'), list)
                           else metadata.get('aliases', ''))
            info_str = f"""
            - Nom : {performer_name}
            - Aliases / Pseudonymes : {aliases_str}
            - Date de naissance : {metadata.get('birthdate', 'Non disponible')}
            - Lieu de naissance : {metadata.get('birthplace', 'Non disponible')}
            - Ethnicité : {ethnicity}
            - Début de carrière : {career_start}
            - Carrière (années) : {metadata.get('career_length', 'Non disponible')}
            - Mensurations : {measurements}
            - Taille : {height} cm
            - Poids : {weight} kg
            - Couleur de cheveux : {hair_color}
            - Tatouages : {metadata.get('tattoos', 'Non disponible')}
            - Piercings : {metadata.get('piercings', 'Non disponible')}
            """
            
            # Ajout de contexte riche si présent
            extra_context = ""
            if metadata.get('trivia'):
                extra_context += f"\nFaits marquants (Trivia) :\n{metadata['trivia']}"
            bio_source = metadata.get('bio_raw') or metadata.get('details', '')
            if bio_source:
                extra_context += f"\nBio source scrappée :\n{bio_source}"
            if metadata.get('awards'):
                extra_context += f"\nRécompenses (brut) :\n{metadata['awards']}"

            interviews_ctx = metadata.get('interviews') or ''
            if not interviews_ctx:
                interviews_ctx = self._get_interview_context(performer_name, metadata)
                if interviews_ctx:
                    metadata['interviews'] = interviews_ctx
            if interviews_ctx:
                extra_context += f"\n\nInterviews (extraits) :\n{interviews_ctx}"

            if custom_prompt:
                prompt = f"""Tu es un rédacteur expert en biographies pour l'industrie du divertissement adulte.

OBJECTIF : Rédiger une biographie de 2800 à 3200 caractères pour {performer_name}.
Directives personnalisées : {custom_prompt}

STRUCTURE OBLIGATOIRE (7 sections, dans cet ordre) :

### {performer_name} : [sous-titre accrocheur basé sur les données]

**Introduction** — 2-3 phrases : identité complète, date et lieu de naissance, année début de carrière, pseudonymes principaux.

**📅 Origines et Premiers Pas** — 3-4 phrases : origines culturelles ({ethnicity}), vie privée discrois, âge/contexte au début de carrière ({career_start}), ambition.

**🏆 Carrière et Filmographie** — 4-5 phrases : studios partenaires, diversité des rôles, évolution, apogée, constance qualitative.

**💡 Faits Marquants & Personnalité** — 3-4 phrases : personnalité, approche professionnelle, mystère/discroistion sur la vie privée, anecdotes des trivia si piscine.

**👗 Apparence et Style** — 3-4 phrases : description physique complète en prose (cheveux {hair_color}, origines {ethnicity}, {measurements}, {height}cm, {weight}kg, tatouages, piercings), style scénique.

**🏆 Prix et Distinctions** — 3-4 phrases : cérémonies et victoires spécifiques intégrées en prose, jamais en liste.

**Conclusion rapide** — 2 phrases : bilan, héritage, avenir.

RÈGLES ABSOLUES :
- ZÉRO liste à puces — uniquement paragraphes en prose fluide
- Mesures/taille/poids intégrés naturellement dans la prose d'Apparence
- Prix intégrés en phrase, JAMAIS sous forme année-catégorie
- Français professionnel et soutenu, avec une touche québécoise si pertinent
- Utiliser ABSOLUMENT toutes les données fournies ci-dessous
- Ne pas mentionner que tu es une IA

DONNÉES FACTUELLES :
{info_str}
{extra_context}

Réponds UNIQUEMENT avec le texte de la biographie, sans préambule ni commentaire."""
            else:
                prompt = f"""Tu es un rédacteur expert en biographies pour l'industrie du divertissement adulte.

OBJECTIF : Rédiger une biographie complète de 2800 à 3200 caractères pour {performer_name}.

MODÈLE DE STRUCTURE à suivre (7 sections) :

### {performer_name} : [sous-titre accrocheur]

**Introduction** — Née le [date] à [lieu], [nom] a marqué l'industrie dès [année]. Reconnue pour [traits], elle a rapidement acquis une notoriété significative. Ses alias [liste] ont contribué à forger une image polyvalente.

**📅 Origines et Premiers Pas** — Origines [ethnie], vie privée discroistion, entrée dans l'industrie en [année] à [age] ans.

**🏆 Carrière et Filmographie** — Studios, collaborations, diversité des rôles, apogée, longuitévité.

**💡 Faits Marquants & Personnalité** — Personnalité authentique, vie privée, loisirs si connus, anecdotes.

**👗 Apparence et Style** — Description physique intégrée en prose (cheveux, mensurations, style).

**🏆 Prix et Distinctions** — Nominations/victoires citées en phrases, jamais en liste.

**Conclusion rapide** — Bilan et héritage.

RÈGLES ABSOLUES :
- ZÉRO liste à puces — prose fluide uniquement
- Tous les chiffres (mesures, années, taille) intégrés naturellement dans les phrases
- Français professionnel, touche québécoise bienveille
- Utiliser TOUTES les données fournies ci-dessous
- Ne pas mentionner l'IA

DONNÉES FACTUELLES COMPLÈTES :
{info_str}
{extra_context}

Réponds UNIQUEMENT avec le texte de la biographie, sans préambule."""
            
            return self._ollama_request(model=model, prompt=prompt, timeout=360)
        except requests.exceptions.ReadTimeout:
            print("[OLLAMA] Timeout dépassé (360s) — essayez un modèle plus léger.")
            return None
        except Exception as e:
            print(f"Erreur Ollama (generation): {e}")
            return None

    def refine_bio(self, current_bio: str, custom_prompt: str, model: str = "dolphin-mistral:7b") -> Optional[str]:
        """Raffine ou fusionne une bio existante selon des directives IA"""
        try:
            prompt = f"""Tu es un éditeur expert en biographies pour l'industrie du divertissement adulte.
Modifie le texte suivant en appliquant STRICTEMENT ces directives : {custom_prompt}

RÈGLES :
- CONSERVER la structure 7 sections
- ZÉRO liste à puces, prose fluide uniquement
- Français professionnel
- Ne pas mentionner l'IA

Texte actuel :
---
{current_bio}
---

Renvoie UNIQUEMENT la biographie modifiée, sans commentaires."""
            
            return self._ollama_request(model=model, prompt=prompt, timeout=360)
        except requests.exceptions.ReadTimeout:
            print("[OLLAMA] Timeout dépassé (360s) lors du raffinement.")
            return None
        except Exception as e:
            print(f"Erreur Ollama (refinement): {e}")
            return None

    def translate_qc(self, text: str, field_name: str = "", model: str = "dolphin-mistral:7b") -> str:
        """Traduit un texte spécifique en Français/QC avec Ollama."""
        if not text or text.lower() == 'none' or len(text.strip()) < 2:
            return text
            
        try:
            prompt = f"""Traduis le texte suivant (champ '{field_name}') en Français (style Québécois/QC) de manière naturelle. 
            Si c'est déjà en français, améliore le style.
            Texte à traduire : {text}
            Renvoie UNIQUEMENT la traduction, sans commentaires."""
            
            result = self._ollama_request(model=model, prompt=prompt, timeout=60)
            if result:
                result = result.strip()
                return result if result else text
        except Exception as e:
            print(f"[OLLAMA] Erreur traduction {field_name}: {e}")
        return text

    def translate_google(self, text: str, target_lang: str = "fr") -> str:
        """Traduit un texte via l'API Google Translate gratuite (gtx)."""
        if not text or text.lower() == 'none' or len(text.strip()) < 2:
            return text
            
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={text}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # La structure est [[["trad", "orig", ...], ...]]
                translated = "".join([part[0] for part in data[0] if part[0]])
                return translated
        except Exception as e:
            print(f"[GOOGLE] Erreur traduction : {e}")
        return text

    def translate_hybrid(self, text: str, field_name: str = "") -> str:
        """Tente Google Translate, bascule sur Ollama si échec ou contenu vide."""
        def _is_advice_noise(src: str, candidate: str, fld: str) -> bool:
            if not candidate:
                return True
            low = candidate.lower()
            markers = [
                "cette phrase est déjà en français", "cette phrase est deja en francais",
                "pour améliorer le style", "pour ameliorer le style",
                "je vous recommande", "par exemple", "il est préférable", "il est preferable",
                "si le style québécois", "si le style quebecois",
                "1.", "2.", "3."
            ]
            if any(m in low for m in markers):
                return True

            # Si sortie beaucoup plus longue que l'entrée sur body-art, c'est souvent du commentaire
            fld_low = (fld or "").lower()
            if fld_low in ("tatouages", "tattoos", "piercings") and len(candidate) > max(120, int(len(src) * 2.2)):
                return True

            return False

        # On tente Google d'abord (recommandation utilisateur pour contenu peu explicite)
        res = self.translate_google(text)
        
        # Si Google échoue ou si le résultat est suspect (trop court par rapport à l'original)
        # ou si on veut forcer le style QC via Ollama
        if not res or res == text or len(res) < len(text) * 0.3:
            res = self.translate_qc(text, field_name)

        # Garde-fou contre les réponses "conseils" au lieu d'une traduction
        if _is_advice_noise(text, res, field_name):
            return text

        return res
