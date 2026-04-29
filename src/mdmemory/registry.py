"""Registry management for MdMemory."""

from pathlib import Path
from typing import Optional, Dict
from .utils import load_json_safe, save_json_safe


class PathRegistry:
    """Manages the global path map (.registry.json)."""

    def __init__(self, registry_path: Path):
        """Initialize registry.

        Args:
            registry_path: Path to .registry.json file
        """
        self.registry_path = registry_path
        self._cache: Dict[str, str] = {}

    async def load(self) -> None:
        """Load registry from disk (async)."""
        self._cache = await load_json_safe(self.registry_path)

    def get(self, topic_id: str) -> Optional[str]:
        """Get physical path for a topic ID (sync from cache)."""
        return self._cache.get(topic_id)

    async def put(self, topic_id: str, path: str) -> bool:
        """Register a topic ID to a physical path.

        Args:
            topic_id: The topic identifier
            path: Relative path to the file

        Returns:
            True if successful
        """
        self._cache[topic_id] = path
        return await save_json_safe(self.registry_path, self._cache)

    async def delete(self, topic_id: str) -> bool:
        """Remove a topic from the registry.

        Args:
            topic_id: The topic identifier

        Returns:
            True if successful
        """
        if topic_id in self._cache:
            del self._cache[topic_id]
            return await save_json_safe(self.registry_path, self._cache)
        return True

    async def update_path(self, old_path: str, new_path: str) -> bool:
        """Update all references from old_path to new_path (for optimize)."""
        updated = False
        for topic_id, path in self._cache.items():
            if path == old_path:
                self._cache[topic_id] = new_path
                updated = True
        if updated:
            return await save_json_safe(self.registry_path, self._cache)
        return True

    def list_all(self) -> Dict[str, str]:
        """Return all mappings (sync from cache)."""
        return self._cache.copy()

    async def reload(self) -> bool:
        """Reload registry from disk (async)."""
        await self.load()
        return True
