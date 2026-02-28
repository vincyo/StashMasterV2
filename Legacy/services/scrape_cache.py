"""
Cache en mémoire des résultats de scraping pour éviter le double
appel réseau entre Phase 1 et Phase 2.
"""


class ScrapeCache:
    """
    Cache class-level partagé entre toutes les instances.
    Stocke les résultats de scraping par URL.
    """
    _data: dict[str, dict] = {}

    @classmethod
    def set(cls, url: str, data: dict):
        """Stocker le résultat de scraping pour une URL."""
        cls._data[url] = data

    @classmethod
    def get(cls, url: str) -> dict | None:
        """Récupérer le résultat de scraping pour une URL, ou None."""
        return cls._data.get(url)

    @classmethod
    def has(cls, url: str) -> bool:
        """Vérifier si une URL est en cache."""
        return url in cls._data

    @classmethod
    def clear(cls):
        """Vider tout le cache."""
        cls._data.clear()

    @classmethod
    def size(cls) -> int:
        """Nombre d'entrées en cache."""
        return len(cls._data)
