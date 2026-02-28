import sqlite3

DB_PATH = r"H:\Stash\stash-go.sqlite"

class PerformerDB:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def get_performer_by_id(self, performer_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM performers WHERE id=?", (performer_id,))
        row = cur.fetchone()
        if not row:
            return None
        data = dict(row)
        # Extraire les alias
        try:
            cur.execute("SELECT alias FROM performer_aliases WHERE performer_id=?", (performer_id,))
            aliases_rows = cur.fetchall()
            aliases = [r['alias'] for r in aliases_rows]
            print(f"DEBUG: Found aliases for ID {performer_id}: {aliases}")
        except Exception as e:
            print(f"DEBUG: Error fetching aliases: {e}")
            aliases = []
        data["aliases"] = aliases
        # Extraire les URLs
        try:
            cur.execute("SELECT url FROM performer_urls WHERE performer_id=?", (performer_id,))
            urls_rows = cur.fetchall()
            urls = [r['url'] for r in urls_rows]
            data["urls"] = urls
        except Exception as e:
            print(f"DEBUG: Error fetching URLs: {e}")
            data["urls"] = []

        # Extraire les tags
        try:
            # Jointure avec la table tags pour obtenir les noms
            query = """
                SELECT t.name 
                FROM tags t
                JOIN performers_tags pt ON pt.tag_id = t.id
                WHERE pt.performer_id = ?
            """
            cur.execute(query, (performer_id,))
            tags_rows = cur.fetchall()
            tags = [r['name'] for r in tags_rows]
            data["tags"] = tags
        except Exception as e:
            print(f"DEBUG: Error fetching tags: {e}")
            data["tags"] = []

        # Extraire la biographie (détails)
        data["bio"] = data.get("details", "")

        return data

    def get_performer_context(self, performer_id):
        """Extraire le contexte Stash complet d'un performer."""
        cur = self.conn.cursor()
        ctx = {"groups": [], "studios": [], "collaborators": [], "scene_count": 0}

        # Nombre de scènes
        try:
            cur.execute(
                "SELECT COUNT(*) as cnt FROM performers_scenes WHERE performer_id=?",
                (performer_id,),
            )
            row = cur.fetchone()
            ctx["scene_count"] = row["cnt"] if row else 0
        except Exception:
            pass

        # Groups (DVDs) via performers_scenes → groups_scenes → groups
        try:
            cur.execute(
                """
                SELECT DISTINCT g.name
                FROM groups g
                JOIN groups_scenes gs ON gs.group_id = g.id
                JOIN performers_scenes ps ON ps.scene_id = gs.scene_id
                WHERE ps.performer_id = ?
                ORDER BY g.name
                """,
                (performer_id,),
            )
            ctx["groups"] = [r["name"] for r in cur.fetchall()]
        except Exception:
            pass

        # Studios via scenes
        try:
            cur.execute(
                """
                SELECT DISTINCT st.name
                FROM studios st
                JOIN scenes s ON s.studio_id = st.id
                JOIN performers_scenes ps ON ps.scene_id = s.id
                WHERE ps.performer_id = ?
                ORDER BY st.name
                """,
                (performer_id,),
            )
            ctx["studios"] = [r["name"] for r in cur.fetchall()]
        except Exception:
            pass

        # Top collaborateurs
        try:
            cur.execute(
                """
                SELECT p2.name, COUNT(*) as cnt
                FROM performers_scenes ps1
                JOIN performers_scenes ps2 ON ps1.scene_id = ps2.scene_id
                JOIN performers p2 ON p2.id = ps2.performer_id
                WHERE ps1.performer_id = ? AND ps2.performer_id != ?
                GROUP BY p2.id
                ORDER BY cnt DESC
                LIMIT 20
                """,
                (performer_id, performer_id),
            )
            ctx["collaborators"] = [
                {"name": r["name"], "count": r["cnt"]} for r in cur.fetchall()
            ]
        except Exception:
            pass

        return ctx

    def get_known_performers(self):
        """Retourne une liste de tous les noms de performers connus."""
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM performers ORDER BY name")
        rows = cur.fetchall()
        return [r['name'] for r in rows]

    def close(self):
        self.conn.close()

    def inject_performer_metadata(self, performer_id: int, updates: dict) -> None:
        """
        Met à jour les champs Phase 2 d'un performer.
        Gère : details, tattoos, piercings, awards, trivia, tags, urls.
        """
        cur = self.conn.cursor()

        # Champs texte directs
        DIRECT = {"details", "tattoos", "piercings", "trivia", "death_date", "awards"}
        direct = {k: v for k, v in updates.items() if k in DIRECT and v is not None}
        if direct:
            set_clause = ", ".join(f"{k}=?" for k in direct)
            vals = list(direct.values()) + [performer_id]
            cur.execute(
                f"UPDATE performers SET {set_clause}, updated_at=datetime('now') WHERE id=?",
                vals
            )

        # URLs → table performer_urls
        for url in updates.get("urls", []):
            cur.execute(
                "SELECT COUNT(*) FROM performer_urls WHERE performer_id=? AND url=?",
                (performer_id, url)
            )
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "SELECT COALESCE(MAX(position),-1)+1 FROM performer_urls WHERE performer_id=?",
                    (performer_id,)
                )
                pos = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO performer_urls (performer_id, position, url) VALUES (?,?,?)",
                    (performer_id, pos, url)
                )

        # Tags → table performers_tags (get-or-create)
        for tag_name in updates.get("tags", []):
            cur.execute("SELECT id FROM tags WHERE name=?", (tag_name,))
            row = cur.fetchone()
            tag_id = row[0] if row else None
            if not tag_id:
                cur.execute(
                    "INSERT INTO tags (name, created_at, updated_at, ignore_auto_tag) "
                    "VALUES (?,datetime('now'),datetime('now'),0)",
                    (tag_name,)
                )
                tag_id = cur.lastrowid
            cur.execute(
                "SELECT COUNT(*) FROM performers_tags WHERE performer_id=? AND tag_id=?",
                (performer_id, tag_id)
            )
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO performers_tags (performer_id, tag_id) VALUES (?,?)",
                    (performer_id, tag_id)
                )

        self.conn.commit()

class GroupDB:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def get_group_by_id(self, group_id):
        cur = self.conn.cursor()
        cur.execute("SELECT g.*, s.name as studio_name FROM groups g LEFT JOIN studios s ON g.studio_id = s.id WHERE g.id=?", (group_id,))
        row = cur.fetchone()
        if not row:
            return None
        data = dict(row)

        # Extraire les URLs
        try:
            cur.execute("SELECT url FROM group_urls WHERE group_id=?", (group_id,))
            urls_rows = cur.fetchall()
            urls = [r['url'] for r in urls_rows]
            data["urls"] = urls
        except Exception as e:
            print(f"DEBUG: Error fetching group URLs: {e}")
            data["urls"] = []

        # Extraire les tags (Étiquettes)
        try:
            query = """
                SELECT t.name 
                FROM tags t
                JOIN groups_tags gt ON gt.tag_id = t.id
                WHERE gt.group_id = ?
            """
            cur.execute(query, (group_id,))
            tags_rows = cur.fetchall()
            tags = [r['name'] for r in tags_rows]
            data["tags"] = tags
        except Exception as e:
            print(f"DEBUG: Error fetching group tags: {e}")
            data["tags"] = []

        return data

    def get_group_scenes(self, group_id: int) -> list[dict]:
        """
        Récupère les scènes associées à un groupe, y compris leurs URLs.
        """
        cur = self.conn.cursor()
        query = """
            SELECT
                s.id AS scene_id,
                gs.scene_index,
                s.title AS scene_title,
                GROUP_CONCAT(su.url) AS existing_urls
            FROM
                groups_scenes gs
            JOIN
                scenes s ON gs.scene_id = s.id
            LEFT JOIN
                scene_urls su ON s.id = su.scene_id
            WHERE
                gs.group_id = ?
            GROUP BY
                s.id, gs.scene_index, s.title
            ORDER BY
                gs.scene_index
        """
        cur.execute(query, (group_id,))
        rows = cur.fetchall()
        
        scenes = []
        for row in rows:
            scene = dict(row)
            scene['existing_urls'] = scene['existing_urls'].split(',') if scene['existing_urls'] else []
            scenes.append(scene)
        return scenes

    def inject_scene_urls(self, scene_urls_to_inject: list[dict]) -> None:
        """
        Injecte les URLs de scènes dans la base de données.
        Args:
            scene_urls_to_inject: Liste de dicts avec {'scene_id': int, 'url': str, 'source': str}
        """
        cur = self.conn.cursor()
        for item in scene_urls_to_inject:
            scene_id = item['scene_id']
            url = item['url']
            
            # Vérifier si l'URL existe déjà pour cette scène
            cur.execute(
                "SELECT COUNT(*) FROM scene_urls WHERE scene_id=? AND url=?",
                (scene_id, url)
            )
            if cur.fetchone()[0] == 0:
                cur.execute(
                    "INSERT INTO scene_urls (scene_id, url) VALUES (?,?)",
                    (scene_id, url)
                )
        self.conn.commit()


    def close(self):
        self.conn.close()
