#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database - Service d'interaction avec la base de données Stash (SQLite)
"""

import os
import sqlite3
import re
import threading
from typing import Dict, List, Optional, Any

class StashDatabase:
    """Gère les requêtes vers stash-go.sqlite"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        # réinitialiser toute connexion existante pour ce thread (nouvelle base)
        try:
            if hasattr(self._thread_conn, 'conn'):
                self._thread_conn.conn.close()
                self._thread_conn.conn = None
        except Exception:
            pass

    # utiliser connexion thread-local pour éviter les erreurs sqlite cross-thread
    _thread_conn = threading.local()

    def _get_connection(self):
        """Retourne une connexion SQLite spécifique au thread courant."""
        conn = getattr(self._thread_conn, 'conn', None)
        if conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._thread_conn.conn = conn
        else:
            # Vérifie que la connexion n'est pas fermée
            try:
                conn.cursor()
            except Exception:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                self._thread_conn.conn = conn
        return conn

    def _close_conn(self):
        """Ferme proprement la connexion thread-local et la réinitialise."""
        conn = getattr(self._thread_conn, 'conn', None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._thread_conn.conn = None

    def get_performer_metadata(self, performer_id: str) -> Optional[Dict]:
        """Récupère les métadonnées actuelles d'un performer"""
        if not os.path.exists(self.db_path):
            print(f"Erreur: Base de données non trouvée à {self.db_path}")
            return None
            
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Performer de base
            cur.execute("SELECT * FROM performers WHERE id=?", (performer_id,))
            row = cur.fetchone()
            if not row:
                return None
                
            data = dict(row)
            
            # Aliases
            cur.execute("SELECT alias FROM performer_aliases WHERE performer_id=?", (performer_id,))
            data['aliases'] = [r['alias'] for r in cur.fetchall()]
            
            # URLs
            cur.execute("SELECT url FROM performer_urls WHERE performer_id=?", (performer_id,))
            data['urls'] = [r['url'] for r in cur.fetchall()]
            
            # Tags
            query = """
                SELECT t.name 
                FROM tags t
                JOIN performers_tags pt ON pt.tag_id = t.id
                WHERE pt.performer_id = ?
            """
            cur.execute(query, (performer_id,))
            data['tags'] = [r['name'] for r in cur.fetchall()]
            
            # Trivia/Awards (si stockés dans performers ou tables dédiées)
            # Dans la BDD Stash standard, trivia et awards ne sont pas des colonnes natives de 'performers'
            # mais souvent stockées dans 'details' ou via des plugins.
            # Mapping des champs spécifiques UI
            data['career_start'] = data.get('career_length', '')
            data['details'] = data.get('details', '')

            # Custom Fields (lecture étendue + mapping des alias vers clés UI)
            cur.execute("SELECT field, value FROM performer_custom_fields WHERE performer_id=?", (performer_id,))
            custom_rows = cur.fetchall()
            data['custom_fields'] = {}

            custom_map = {
                'birthplace': 'birthplace',
                'place of birth': 'birthplace',
                'dob': 'birthdate',
                'date of birth': 'birthdate',
                'awards': 'awards',
                'trivia': 'trivia',
                'trivia fr': 'trivia',
                'tattoos': 'tattoos',
                'tattoos fr': 'tattoos',
                'piercings': 'piercings',
                'piercings fr': 'piercings',
                'official website': 'website',
                'website': 'website',
                'instagram': 'instagram',
                'onlyfans': 'onlyfans',
                'tiktok': 'tiktok',
                'youtube': 'youtube',
                'twitch': 'twitch',
                'imdb': 'imdb',
                'twitter': 'twitter',
                'facebook': 'facebook',
                'biography': 'details',
                'bio': 'details',
            }

            for cfield in custom_rows:
                field_raw = str(cfield['field'] or '').strip()
                value_raw = str(cfield['value'] or '').strip()
                if not field_raw:
                    continue

                fname = field_raw.lower()
                data['custom_fields'][field_raw] = value_raw

                ui_key = custom_map.get(fname)
                if not ui_key:
                    continue

                # Priorité : si la clé n'est pas déjà remplie, on prend le custom field
                # ou si la valeur actuelle est vide.
                existing = data.get(ui_key)
                if existing is None or str(existing).strip() == '':
                    data[ui_key] = value_raw

            # Fallback: certains setups utilisent la colonne 'disambiguation' comme lieu de naissance
            if not data.get('birthplace') and data.get('disambiguation'):
                data['birthplace'] = data.get('disambiguation')

            # --- Nettoyage des dates ---
            # Stash stocke les dates NULL comme "0001-01-01" — on les efface
            NULL_DATES = {'0001-01-01', '0001-01-01T00:00:00Z', '0001-01-01 00:00:00+00:00', ''}
            for date_col in ('birthdate', 'death_date'):
                raw = str(data.get(date_col, '') or '').strip()
                if raw in NULL_DATES:
                    data[date_col] = ''
                elif 'T' in raw:
                    # Tronquer "1988-06-02T00:00:00Z" → "1988-06-02"
                    data[date_col] = raw.split('T')[0]

            # Mapper death_date → deathdate (clé utilisée dans le UI field_vars)
            data['deathdate'] = data.get('death_date', '')

            return data
        except Exception as e:
            print(f"Erreur lors de la lecture DB: {e}")
            return None

    def get_all_performers(self) -> List[Dict]:
        """Récupère tous les performers pour une liste de sélection"""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM performers ORDER BY name")
            return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            print(f"Erreur get_all_performers: {e}")
            return []

    def get_group_metadata(self, group_id: str) -> Optional[Dict]:
        """Récupère les métadonnées d'un groupe (DVD)"""
        if not os.path.exists(self.db_path): return None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM groups WHERE id=?", (group_id,))
            row = cur.fetchone()
            if not row:
                return None
            data = dict(row)
            
            # Studio (dans Stash 'groups' a souvent une colonne studio_id)
            if data.get('studio_id'):
                cur.execute("SELECT name FROM studios WHERE id=?", (data['studio_id'],))
                s_row = cur.fetchone()
                if s_row: data['studio_name'] = s_row['name']
            
            return data
        except Exception as e:
            print(f"Erreur get_group_metadata: {e}")
            return None

    def get_all_groups(self) -> List[Dict]:
        """Récupère tous les groupes pour une liste de sélection"""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM groups ORDER BY name")
            return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            print(f"Erreur get_all_groups: {e}")
            return []

    def save_performer_metadata(self, performer_id: str, updates: Dict):
        """Met à jour le performer dans Stash"""
        if not os.path.exists(self.db_path):
            return
            
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # 1. Mise à jour de la table performers
            # On ne met à jour que ce qui est fourni
            fields_to_update = []
            values = []
            
            # Mapping UI keys -> DB columns
            mapping = {
                'name': 'name',
                'birthdate': 'birthdate',
                'birthplace': 'disambiguation', # Faute de mieux si birthplace absent
                'ethnicity': 'ethnicity',
                'country': 'country',
                'eye_color': 'eye_color',
                'hair_color': 'hair_color',
                'height': 'height',
                'weight': 'weight',
                'measurements': 'measurements',
                'fake_tits': 'fake_tits',
                'details': 'details',
                'deathdate': 'death_date',
                'tattoos': 'tattoos',
                'piercings': 'piercings',
                'career_start': 'career_length'
            }
            
            for ui_key, db_col in mapping.items():
                if ui_key in updates:
                    fields_to_update.append(f"{db_col}=?")
                    values.append(updates[ui_key])
            
            if fields_to_update:
                query = f"UPDATE performers SET {', '.join(fields_to_update)} WHERE id=?"
                values.append(performer_id)
                cur.execute(query, tuple(values))
            
            # 2. Mise à jour des aliases
            if 'aliases' in updates:
                aliases_in = updates['aliases']
                if isinstance(aliases_in, str):
                    new_aliases = [a.strip() for a in re.split(r'[,\n\r]+', aliases_in) if a.strip()]
                elif isinstance(aliases_in, list):
                    new_aliases = [str(a).strip() for a in aliases_in if str(a).strip()]
                else:
                    new_aliases = [str(aliases_in).strip()] if str(aliases_in).strip() else []

                # Fusion automatique: conserve les aliases existants + ajoute les nouveaux (sans doublons)
                existing_aliases: List[str] = []
                try:
                    cur.execute("SELECT alias FROM performer_aliases WHERE performer_id=?", (performer_id,))
                    existing_aliases = [r['alias'] for r in cur.fetchall() if r.get('alias')]
                except Exception:
                    existing_aliases = []

                def dedupe_keep_order(items: List[str]) -> List[str]:
                    out: List[str] = []
                    seen = set()
                    for it in items:
                        it = str(it).strip()
                        if not it:
                            continue
                        k = it.casefold()
                        if k in seen:
                            continue
                        seen.add(k)
                        out.append(it)
                    return out

                merged_aliases = dedupe_keep_order(existing_aliases + new_aliases)

                cur.execute("DELETE FROM performer_aliases WHERE performer_id=?", (performer_id,))
                for alias in merged_aliases:
                    cur.execute(
                        "INSERT INTO performer_aliases (performer_id, alias) VALUES (?, ?)",
                        (performer_id, alias),
                    )

            # 2bis. Mise à jour des tags
            if 'tags' in updates:
                # 1. Supprimer les anciens liens
                cur.execute("DELETE FROM performers_tags WHERE performer_id=?", (performer_id,))
                
                tags_raw = updates['tags']
                if isinstance(tags_raw, str):
                    tag_list = [t.strip() for t in re.split(r'[,\n\r]+', tags_raw) if t.strip()]
                else:
                    tag_list = tags_raw
                
                for tag_name in tag_list:
                    # 2. Trouver ou créer le tag
                    cur.execute("SELECT id FROM tags WHERE name=?", (tag_name,))
                    tag_row = cur.fetchone()
                    if tag_row:
                        tag_id = tag_row['id']
                    else:
                        cur.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
                        tag_id = cur.lastrowid
                    
                    # 3. Lier le performer au tag
                    cur.execute("INSERT INTO performers_tags (performer_id, tag_id) VALUES (?, ?)", (performer_id, tag_id))
            
            # 3. Mise à jour des champs personnalisés (Custom Fields)
            # On identifie les champs qui doivent aller dans performer_custom_fields
            custom_map = {
                'birthplace': 'Birthplace',
                'awards': 'Awards',
                'trivia': 'Trivia',
                'trivia_fr': 'Trivia FR',
                'tattoos_fr': 'Tattoos FR',
                'piercings_fr': 'Piercings FR',
                'website': 'Official Website',
                'instagram': 'Instagram',
                'onlyfans': 'OnlyFans',
                'tiktok': 'TikTok',
                'youtube': 'YouTube',
                'twitch': 'Twitch',
                'imdb': 'IMDb',
                'twitter': 'Twitter',
                'facebook': 'Facebook'
            }
            # Note: Si l'utilisateur veut DOB en custom field, on peut l'ajouter ici
            
            for ui_key, custom_name in custom_map.items():
                if ui_key in updates:
                    val = str(updates[ui_key]).strip()
                    # Delete existing and re-insert
                    cur.execute("DELETE FROM performer_custom_fields WHERE performer_id=? AND field=?", (performer_id, custom_name))
                    if val:
                        cur.execute("INSERT INTO performer_custom_fields (performer_id, field, value) VALUES (?, ?, ?)", 
                                   (performer_id, custom_name, val))

            # 4. Mise à jour des URLs (Discovery)
            if 'discovered_urls' in updates:
                cur.execute("DELETE FROM performer_urls WHERE performer_id=?", (performer_id,))
                urls = updates['discovered_urls']
                if isinstance(urls, str):
                    urls = [u.strip() for u in re.split(r'[,\n\r\s]+', urls) if u.strip()]
                # Dédupe en conservant l'ordre, et attribue une position (colonne NOT NULL dans Stash)
                cleaned_urls = []
                seen = set()
                for u in urls or []:
                    u = str(u).strip()
                    if not u or u in seen:
                        continue
                    seen.add(u)
                    cleaned_urls.append(u)

                for pos, url in enumerate(cleaned_urls):
                    cur.execute(
                        "INSERT INTO performer_urls (performer_id, position, url) VALUES (?, ?, ?)",
                        (performer_id, pos, url),
                    )

            # 5. Propagation des Tags vers les Scènes (Optionnel mais demandé)
            if 'tags' in updates:
                self._propagate_tags_to_scenes(cur, performer_id, tag_list if 'tag_list' in locals() else [])

            conn.commit()
            return True
        except Exception as e:
            print(f"Erreur lors de la sauvegarde DB: {e}")
            try:
                self._get_connection().rollback()
            except Exception:
                pass
            self._close_conn()
            return False

    def _propagate_tags_to_scenes(self, cur, performer_id: str, tag_names: List[str]):
        """Propage les tags d'un performer vers toutes ses scènes"""
        if not tag_names:
            return

        def table_exists(table_name: str) -> bool:
            try:
                row = cur.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
                    (table_name,),
                ).fetchone()
                return bool(row)
            except Exception:
                return False

        # Certaines variantes de schéma Stash n'ont pas ces tables.
        if not table_exists("scenes_tags"):
            return

        link_table = None
        if table_exists("scenes_performers"):
            link_table = "scenes_performers"
        elif table_exists("performers_scenes"):
            link_table = "performers_scenes"
        else:
            return
            
        # 1. Récupérer les IDs des tags
        tag_ids = []
        for name in tag_names:
            cur.execute("SELECT id FROM tags WHERE name=?", (name,))
            row = cur.fetchone()
            if row:
                tag_ids.append(row['id'])
        
        if not tag_ids:
            return

        # 2. Trouver toutes les scènes du performer
        try:
            cur.execute(f"SELECT scene_id FROM {link_table} WHERE performer_id=?", (performer_id,))
            scene_ids = [r['scene_id'] for r in cur.fetchall()]
        except sqlite3.OperationalError:
            return
        except Exception:
            return
        
        for scene_id in scene_ids:
            for tag_id in tag_ids:
                # 3. Vérifier si le lien existe déjà pour éviter les doublons
                try:
                    cur.execute("SELECT 1 FROM scenes_tags WHERE scene_id=? AND tag_id=?", (scene_id, tag_id))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO scenes_tags (scene_id, tag_id) VALUES (?, ?)", (scene_id, tag_id))
                except sqlite3.OperationalError:
                    return
                except Exception:
                    return
    def save_group_metadata(self, group_id: str, updates: Dict):
        """Met à jour un groupe dans Stash"""
        if not os.path.exists(self.db_path): return False
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            fields = []
            values = []
            mapping = {
                'name': 'name',
                'date': 'date',
                'details': 'details',
                'director': 'director',
                'duration': 'duration', # Stash utilise souvent des secondes ou string
                'rating': 'rating'
            }
            
            for k, v in mapping.items():
                if k in updates:
                    fields.append(f"{v}=?")
                    values.append(updates[k])
            
            if fields:
                query = f"UPDATE groups SET {', '.join(fields)} WHERE id=?"
                values.append(group_id)
                cur.execute(query, tuple(values))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Erreur save_group_metadata: {e}")
            self._close_conn()
            return False

    def get_scene_metadata(self, scene_id: str) -> Optional[Dict]:
        """Récupère les métadonnées d'une scène"""
        if not os.path.exists(self.db_path): return None
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM scenes WHERE id=?", (scene_id,))
            row = cur.fetchone()
            if not row:
                return None
            
            data = dict(row)
            
            # Tags
            cur.execute("""
                SELECT t.name FROM tags t
                JOIN scenes_tags st ON st.tag_id = t.id
                WHERE st.scene_id = ?
            """, (scene_id,))
            data['tags'] = [r['name'] for r in cur.fetchall()]
            
            # Performers
            link_table = None
            try:
                row = cur.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='scenes_performers' LIMIT 1"
                ).fetchone()
                if row:
                    link_table = "scenes_performers"
                else:
                    row2 = cur.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='performers_scenes' LIMIT 1"
                    ).fetchone()
                    if row2:
                        link_table = "performers_scenes"
            except Exception:
                link_table = None

            if link_table:
                cur.execute(
                    f"""
                    SELECT p.name FROM performers p
                    JOIN {link_table} sp ON sp.performer_id = p.id
                    WHERE sp.scene_id = ?
                    """,
                    (scene_id,),
                )
                data['performers'] = [r['name'] for r in cur.fetchall()]
            else:
                data['performers'] = []
            
            # Studio
            if data.get('studio_id'):
                cur.execute("SELECT name FROM studios WHERE id=?", (data['studio_id'],))
                s_row = cur.fetchone()
                if s_row: data['studio'] = s_row['name']
            
            return data
        except Exception as e:
            print(f"Erreur get_scene_metadata: {e}")
            return None

    def save_scene_metadata(self, scene_id: str, updates: Dict) -> bool:
        """Met à jour une scène dans Stash"""
        if not os.path.exists(self.db_path): return False
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            fields = []
            values = []
            mapping = {
                'title': 'title',
                'details': 'details',
                'date': 'date',
                'code': 'code',
                'rating': 'rating'
            }
            
            for k, v in mapping.items():
                if k in updates:
                    fields.append(f"{v}=?")
                    values.append(updates[k])
            
            if fields:
                query = f"UPDATE scenes SET {', '.join(fields)} WHERE id=?"
                values.append(scene_id)
                cur.execute(query, tuple(values))
            
            # Tags & Performers (sync complexe si besoin, mais on reste simple ici pour le moment)
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Erreur save_scene_metadata: {e}")
            self._close_conn()
            return False

    def get_scenes_for_group(self, group_id: str) -> List[Dict]:
        """Récupère les scènes rattachées à un groupe"""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            query = """
                SELECT s.id, s.title
                FROM scenes s
                JOIN groups_scenes gs ON gs.scene_id = s.id
                WHERE gs.group_id = ?
            """
            cur.execute(query, (group_id,))
            return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            print(f"Erreur get_scenes_for_group: {e}")
            return []

    def add_scene_url(self, scene_id: str, url: str) -> bool:
        """Ajoute une URL à une scène si elle n'existe pas déjà"""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            
            # Vérifier si l'URL existe déjà
            cur.execute("SELECT 1 FROM scene_urls WHERE scene_id=? AND url=?", (scene_id, url))
            if cur.fetchone():
                return True
                
            cur.execute("INSERT INTO scene_urls (scene_id, url) VALUES (?, ?)", (scene_id, url))
            conn.commit()
            return True
        except Exception as e:
            print(f"Erreur add_scene_url: {e}")
            return False
