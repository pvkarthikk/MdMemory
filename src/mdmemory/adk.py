"""Google ADK integration for MdMemory."""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Sequence

from google.adk.memory import BaseMemoryService
from google.adk.memory.memory_entry import MemoryEntry
from google.adk.memory.base_memory_service import SearchMemoryResponse
from google.genai import types

from .core import MdMemory
from .utils import read_markdown_file, write_markdown_file

if TYPE_CHECKING:
    from google.adk.events.event import Event
    from google.adk.sessions.session import Session


class MdMemoryService(BaseMemoryService):
    """MdMemory-backed implementation of ADK's BaseMemoryService.

    Stores ADK sessions as Markdown files organized by the MdMemory
    Knowledge Tree, enabling persistent, human-readable long-term memory.
    """

    def __init__(
        self,
        mdmemory: Optional[MdMemory] = None,
        storage_path: str = "./MdMemory",
        optimize_threshold: int = 20,
        llm_callback: Any = None,
    ):
        """Initialize MdMemoryService.

        Args:
            mdmemory: Existing MdMemory instance. If None, one is created.
            storage_path: Root path for storage (used if mdmemory is None).
            optimize_threshold: Line count threshold for triggering optimize.
            llm_callback: LLM callback for MdMemory (used if mdmemory is None).
        """
        if mdmemory is not None:
            self._memory = mdmemory
        else:
            self._memory = MdMemory(
                llm_callback=llm_callback,
                storage_path=storage_path,
                optimize_threshold=optimize_threshold,
            )
        # Cache: session_id -> topic for fast append lookups
        self._session_map: Dict[str, str] = {}

    def _session_to_markdown(self, session: Session) -> str:
        """Convert ADK session events to readable Markdown.

        Extracts only user/agent text exchanges, skipping function calls,
        responses, and other non-text events. Returns empty string if no
        text exchanges found.
        """
        exchanges = []
        for event in session.events:
            text = self._extract_text(event)
            if text:
                author = event.author
                exchanges.append(f"## {author.title()}\n{text}")

        if not exchanges:
            return ""

        lines = [
            f"# Session: {session.id}",
            f"App: {session.app_name}",
            "",
        ] + exchanges
        return "\n".join(lines)

    def _events_to_markdown(self, events: Sequence[Event]) -> str:
        """Convert a list of events to a Markdown snippet for appending."""
        lines = []
        for event in events:
            text = self._extract_text(event)
            if text:
                author = event.author
                lines.append(f"## {author.title()}")
                lines.append(text)
                lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _extract_text(event: Event) -> str:
        """Extract text content from an event, skipping non-text parts."""
        if not event.content or not event.content.parts:
            return ""
        texts = []
        for part in event.content.parts:
            if part.text:
                texts.append(part.text)
        return "\n".join(texts)

    def _resolve_session_topic(self, session_id: str) -> Optional[str]:
        """Find the topic for a session_id, populating cache if needed."""
        if session_id in self._session_map:
            return self._session_map[session_id]

        # Scan registry for matching session_id in frontmatter custom dict
        all_topics = self._memory.list_topics()
        for topic, relative_path in all_topics.items():
            file_path = self._memory.storage_path / relative_path
            if file_path.exists():
                meta, _ = read_markdown_file(file_path)
                custom = meta.get("custom", {})
                if isinstance(custom, dict) and custom.get("session_id") == session_id:
                    self._session_map[session_id] = topic
                    return topic
        return None

    async def add_session_to_memory(
        self,
        session: Session,
    ) -> None:
        """Store an ADK session as a Markdown topic in MdMemory.

        The LLM generates a semantic topic name from the session content.
        The session_id is stored in frontmatter custom dict for later lookup.
        """
        content = self._session_to_markdown(session)
        if not content.strip():
            return

        topic = self._memory.store(
            usr_id=session.user_id,
            query=content,
        )

        if topic:
            # Update frontmatter with session_id for fast lookup
            relative_path = self._memory.registry.get(topic)
            if relative_path:
                file_path = self._memory.storage_path / relative_path
                if file_path.exists():
                    meta, body = read_markdown_file(file_path)
                    if "custom" not in meta:
                        meta["custom"] = {}
                    meta["custom"]["session_id"] = session.id
                    meta["custom"]["app_name"] = session.app_name
                    write_markdown_file(file_path, meta, body)

            self._session_map[session.id] = topic

    async def add_events_to_memory(
        self,
        *,
        app_name: str,
        user_id: str,
        events: Sequence[Event],
        session_id: Optional[str] = None,
        custom_metadata: Optional[Mapping[str, object]] = None,
    ) -> None:
        """Add event deltas to an existing session's markdown file.

        Appends new user/agent exchanges to the existing topic.
        """
        if not events:
            return

        # Find existing topic for this session
        topic = None
        if session_id:
            topic = self._resolve_session_topic(session_id)

        if not topic:
            # No existing session found; create a new one
            snippet = self._events_to_markdown(events)
            if not snippet.strip():
                return
            topic = self._memory.store(
                usr_id=user_id,
                query=snippet,
            )
            if topic and session_id:
                self._session_map[session_id] = topic
            return

        # Append to existing file
        relative_path = self._memory.registry.get(topic)
        if not relative_path:
            return

        file_path = self._memory.storage_path / relative_path
        if not file_path.exists():
            return

        meta, content = read_markdown_file(file_path)

        new_content = self._events_to_markdown(events)
        if new_content.strip():
            content = content.rstrip() + "\n\n" + new_content

        meta["updated_at"] = datetime.now().isoformat()
        write_markdown_file(file_path, meta, content)

    async def add_memory(
        self,
        *,
        app_name: str,
        user_id: str,
        memories: Sequence[MemoryEntry],
        custom_metadata: Optional[Mapping[str, object]] = None,
    ) -> None:
        """Store explicit memory items as Markdown topics."""
        for entry in memories:
            text_parts = []
            if entry.content and entry.content.parts:
                for part in entry.content.parts:
                    if part.text:
                        text_parts.append(part.text)
            content = "\n".join(text_parts) if text_parts else str(entry)

            topic_hint = entry.custom_metadata.get("topic", entry.id or "memory_entry")
            self._memory.store(
                usr_id=user_id,
                query=content,
                topic=str(topic_hint),
            )

    async def search_memory(
        self,
        *,
        app_name: str,
        user_id: str,
        query: str,
    ) -> SearchMemoryResponse:
        """Search MdMemory topics by keyword matching.

        Fast approach:
        1. Iterate registry (dict lookup, O(1))
        2. Read only frontmatter for each topic (small YAML, fast)
        3. Filter by user_id
        4. Keyword match against summary + topic name
        5. For matches, read full content and build MemoryEntry
        """
        query_words = set(w.lower() for w in re.split(r"\W+", query) if len(w) > 1)
        if not query_words:
            return SearchMemoryResponse(memories=[])

        memories = []
        all_topics = self._memory.list_topics()

        for topic, relative_path in all_topics.items():
            file_path = self._memory.storage_path / relative_path
            if not file_path.exists():
                continue

            # Read frontmatter only (fast — small YAML block)
            meta, _ = read_markdown_file(file_path)

            # Filter by user_id
            if meta.get("user_id") != user_id:
                continue

            # Keyword match against summary and topic name
            searchable = f"{topic} {meta.get('summary', '')}".lower()
            if not any(w in searchable for w in query_words):
                continue

            # Match found — read full content
            _, full_content = read_markdown_file(file_path)

            # Build MemoryEntry
            timestamp = meta.get("updated_at") or meta.get("created_at")
            entry = MemoryEntry(
                content=types.Content(
                    role="user",
                    parts=[types.Part(text=full_content)],
                ),
                custom_metadata={
                    "topic": topic,
                    "summary": meta.get("summary", ""),
                    "tags": meta.get("tags", []),
                },
                id=topic,
                author=meta.get("user_id"),
                timestamp=timestamp,
            )
            memories.append(entry)

        return SearchMemoryResponse(memories=memories)
