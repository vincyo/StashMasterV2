#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ConfigManager - Gestion de la configuration globale
"""

import json
import os
from typing import Dict, Any

class ConfigManager:
    """Gère la lecture et l'écriture de la configuration (config.json)"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_defaults()
        self.load()

    def _load_defaults(self) -> Dict[str, Any]:
        return {
            "stash_url": "http://localhost:9999",
            "stash_api_key": "",
            "database_path": "H:/Stash/stash-go.sqlite",
            "ollama_url": "http://localhost:11434/api/generate",
            "performer_bio_length": 3000,
            "theme": "dark"
        }

    def load(self):
        """Charge la configuration depuis le fichier JSON"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    self.config.update(user_config)
            except Exception as e:
                print(f"Erreur lors du chargement de la config: {e}")

    def save(self):
        """Sauvegarde la configuration actuelle"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de la config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        self.config[key] = value
        self.save()
