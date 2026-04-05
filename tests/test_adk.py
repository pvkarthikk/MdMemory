"""Tests for MdMemoryService (Google ADK integration)."""

import tempfile
from pathlib import Path

import pytest
from google.adk.memory.memory_entry import MemoryEntry
from google.adk.memory.base_memory_service import SearchMemoryResponse
from google.adk.sessions.session import Session
from google.adk.events.event import Event
from google.genai import types

from mdmemory import MdMemory
from mdmemory.adk import MdMemoryService
from mdmemory.utils import read_markdown_file


def _make_event(author: str, text: str) -> Event:
    """Create a minimal ADK Event with text content."""
    return Event(
        author=author,
        content=types.Content(
            role="user" if author == "user" else "model",
            parts=[types.Part(text=text)],
        ),
    )


def _make_session(
    session_id: str,
    app_name: str,
    user_id: str,
    events: list[Event] | None = None,
) -> Session:
    """Create a minimal ADK Session."""
    return Session(
        id=session_id,
        app_name=app_name,
        user_id=user_id,
        events=events or [],
    )


class MockLLM:
    """Mock LLM callback for testing."""

    def __call__(self, messages: list) -> str:
        import json
        import re

        content = messages[0].get("content", "") if messages else ""
        topic = "session_memory"
        summary = "session memory"

        if '"topic"' in content:
            match = re.search(r'"topic":\s*"([^"]+)"', content)
            if match:
                topic_value = match.group(1)
                if not topic_value.startswith("NOT_PROVIDED"):
                    topic = topic_value

        if "Python decorators" in content:
            topic = "python_decorators"
            summary = "Python decorators tutorial"
        elif "Machine learning" in content:
            topic = "machine_learning"
            summary = "Machine learning basics"
        elif "Cooking recipes" in content:
            topic = "cooking_recipes"
            summary = "Cooking recipes collection"
        elif "Python basics" in content:
            topic = "python_basics"
            summary = "Python basics tutorial"
        elif "Initial message" in content:
            topic = "initial_conversation"
            summary = "Initial conversation"
        elif "Hello world" in content:
            topic = "greeting"
            summary = "Hello world greeting"
        elif "Test content" in content:
            topic = "test_content"
            summary = "Test content"
        elif "User prefers" in content:
            topic = "user_preference"
            summary = "User preferences"
        elif "Orphan event" in content:
            topic = "orphan_events"
            summary = "Orphan events"

        return json.dumps(
            {
                "action": "store",
                "recommended_path": "memory",
                "frontmatter": {
                    "topic": topic,
                    "summary": summary,
                    "tags": [],
                },
                "optimize_suggested": False,
            }
        )


@pytest.fixture
def temp_storage():
    """Temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mdmemory(temp_storage):
    """MdMemory instance with temp storage."""
    return MdMemory(MockLLM(), str(temp_storage), optimize_threshold=100)


@pytest.fixture
def memory_service(mdmemory):
    """MdMemoryService instance."""
    return MdMemoryService(mdmemory=mdmemory)


class TestMdMemoryServiceInit:
    """Test MdMemoryService initialization."""

    def test_init_with_mdmemory(self, mdmemory):
        """Test initializing with existing MdMemory instance."""
        service = MdMemoryService(mdmemory=mdmemory)
        assert service._memory is mdmemory

    def test_init_creates_mdmemory(self, temp_storage):
        """Test initializing creates MdMemory internally."""
        service = MdMemoryService(
            storage_path=str(temp_storage),
            llm_callback=MockLLM(),
        )
        assert service._memory is not None
        assert service._memory.root_index_path.exists()


class TestAddSessionToMemory:
    """Test add_session_to_memory."""

    async def test_stores_session_as_topic(self, memory_service):
        """Test that a session is stored as a markdown topic."""
        session = _make_session(
            session_id="sess_001",
            app_name="test_app",
            user_id="user1",
            events=[
                _make_event("user", "What is Python?"),
                _make_event("agent", "Python is a programming language."),
            ],
        )

        await memory_service.add_session_to_memory(session)

        # Should have stored the session
        topics = memory_service._memory.list_topics()
        assert len(topics) >= 1

        # Session should be cached
        assert "sess_001" in memory_service._session_map

    async def test_empty_session_not_stored(self, memory_service):
        """Test that empty sessions are not stored."""
        session = _make_session(
            session_id="sess_empty",
            app_name="test_app",
            user_id="user1",
            events=[],
        )

        await memory_service.add_session_to_memory(session)

        topics = memory_service._memory.list_topics()
        assert len(topics) == 0

    async def test_session_content_includes_exchanges(self, memory_service):
        """Test that stored topic contains user/agent exchanges."""
        session = _make_session(
            session_id="sess_002",
            app_name="test_app",
            user_id="user1",
            events=[
                _make_event("user", "Hello world"),
                _make_event("agent", "Hi there"),
            ],
        )

        await memory_service.add_session_to_memory(session)

        topic = memory_service._session_map.get("sess_002")
        assert topic is not None

        relative_path = memory_service._memory.registry.get(topic)
        file_path = memory_service._memory.storage_path / relative_path
        _, content = read_markdown_file(file_path)

        assert "Hello world" in content
        assert "Hi there" in content
        assert "User" in content
        assert "Agent" in content

    async def test_session_id_stored_in_frontmatter(self, memory_service):
        """Test that session_id is persisted in frontmatter custom dict."""
        session = _make_session(
            session_id="sess_003",
            app_name="test_app",
            user_id="user1",
            events=[_make_event("user", "Test content")],
        )

        await memory_service.add_session_to_memory(session)

        topic = memory_service._session_map.get("sess_003")
        relative_path = memory_service._memory.registry.get(topic)
        file_path = memory_service._memory.storage_path / relative_path
        meta, _ = read_markdown_file(file_path)

        assert meta.get("custom", {}).get("session_id") == "sess_003"
        assert meta.get("custom", {}).get("app_name") == "test_app"


class TestAddEventsToMemory:
    """Test add_events_to_memory."""

    async def test_appends_to_existing_session(self, memory_service):
        """Test that events are appended to existing session topic."""
        session = _make_session(
            session_id="sess_append",
            app_name="test_app",
            user_id="user1",
            events=[_make_event("user", "Initial message")],
        )
        await memory_service.add_session_to_memory(session)

        topic_before = memory_service._session_map.get("sess_append")
        relative_path = memory_service._memory.registry.get(topic_before)
        file_path = memory_service._memory.storage_path / relative_path
        _, content_before = read_markdown_file(file_path)

        # Add more events
        new_events = [
            _make_event("user", "Follow up question"),
            _make_event("agent", "Follow up answer"),
        ]
        await memory_service.add_events_to_memory(
            app_name="test_app",
            user_id="user1",
            events=new_events,
            session_id="sess_append",
        )

        _, content_after = read_markdown_file(file_path)
        assert "Initial message" in content_after
        assert "Follow up question" in content_after
        assert "Follow up answer" in content_after
        assert len(content_after) > len(content_before)

    async def test_creates_new_topic_if_session_not_found(self, memory_service):
        """Test that events create new topic if session_id not found."""
        events = [
            _make_event("user", "Orphan event"),
        ]
        await memory_service.add_events_to_memory(
            app_name="test_app",
            user_id="user1",
            events=events,
            session_id="nonexistent_session",
        )

        topics = memory_service._memory.list_topics()
        assert len(topics) >= 1

    async def test_empty_events_not_stored(self, memory_service):
        """Test that empty event list does nothing."""
        await memory_service.add_events_to_memory(
            app_name="test_app",
            user_id="user1",
            events=[],
            session_id="sess_001",
        )

        topics = memory_service._memory.list_topics()
        assert len(topics) == 0


class TestAddMemory:
    """Test add_memory."""

    async def test_stores_explicit_memory_items(self, memory_service):
        """Test storing explicit MemoryEntry items."""
        entries = [
            MemoryEntry(
                content=types.Content(
                    role="user",
                    parts=[types.Part(text="User prefers dark mode")],
                ),
                custom_metadata={"topic": "user_preference"},
                id="mem_001",
            ),
        ]

        await memory_service.add_memory(
            app_name="test_app",
            user_id="user1",
            memories=entries,
        )

        topics = memory_service._memory.list_topics()
        assert len(topics) >= 1


class TestSearchMemory:
    """Test search_memory."""

    async def test_search_returns_matching_topics(self, memory_service):
        """Test that search returns topics with keyword matches."""
        session = _make_session(
            session_id="sess_search",
            app_name="test_app",
            user_id="user1",
            events=[
                _make_event("user", "Python decorators tutorial"),
                _make_event("agent", "Decorators wrap functions"),
            ],
        )
        await memory_service.add_session_to_memory(session)

        result = await memory_service.search_memory(
            app_name="test_app",
            user_id="user1",
            query="Python decorators",
        )

        assert isinstance(result, SearchMemoryResponse)
        assert len(result.memories) >= 1

    async def test_search_filters_by_user_id(self, memory_service):
        """Test that search only returns memories for the given user."""
        session1 = _make_session(
            session_id="sess_user1",
            app_name="test_app",
            user_id="user1",
            events=[_make_event("user", "Python basics")],
        )
        session2 = _make_session(
            session_id="sess_user2",
            app_name="test_app",
            user_id="user2",
            events=[_make_event("user", "Python basics")],
        )

        await memory_service.add_session_to_memory(session1)
        await memory_service.add_session_to_memory(session2)

        # Search as user1
        result1 = await memory_service.search_memory(
            app_name="test_app",
            user_id="user1",
            query="Python",
        )

        # Search as user2
        result2 = await memory_service.search_memory(
            app_name="test_app",
            user_id="user2",
            query="Python",
        )

        # Each user should only see their own memories
        for mem in result1.memories:
            assert mem.author == "user1"
        for mem in result2.memories:
            assert mem.author == "user2"

    async def test_search_no_matches(self, memory_service):
        """Test search returns empty list when no matches."""
        session = _make_session(
            session_id="sess_nomatch",
            app_name="test_app",
            user_id="user1",
            events=[_make_event("user", "Cooking recipes")],
        )
        await memory_service.add_session_to_memory(session)

        result = await memory_service.search_memory(
            app_name="test_app",
            user_id="user1",
            query="quantum physics",
        )

        assert len(result.memories) == 0

    async def test_search_empty_query(self, memory_service):
        """Test search with empty query returns empty."""
        result = await memory_service.search_memory(
            app_name="test_app",
            user_id="user1",
            query="",
        )

        assert len(result.memories) == 0

    async def test_search_memory_entry_content(self, memory_service):
        """Test that returned MemoryEntry has proper content."""
        session = _make_session(
            session_id="sess_content",
            app_name="test_app",
            user_id="user1",
            events=[
                _make_event("user", "Machine learning basics"),
                _make_event("agent", "ML is a subset of AI"),
            ],
        )
        await memory_service.add_session_to_memory(session)

        result = await memory_service.search_memory(
            app_name="test_app",
            user_id="user1",
            query="Machine learning",
        )

        assert len(result.memories) >= 1
        entry = result.memories[0]
        assert entry.content is not None
        assert entry.content.parts is not None
        assert len(entry.content.parts) >= 1
        assert "Machine learning" in entry.content.parts[0].text
