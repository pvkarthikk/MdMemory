"""Tests for MdMemory."""

import tempfile
from pathlib import Path

import pytest

from mdmemory import MdMemory, FrontMatter, LLMResponse
from mdmemory.registry import PathRegistry
from mdmemory.utils import (
    load_json_safe,
    save_json_safe,
    read_markdown_file,
    write_markdown_file,
)


class MockLLM:
    """Mock LLM for testing."""

    def completion(self, **kwargs):
        """Mock completion method that parses the context."""
        # Extract messages to determine the topic
        messages = kwargs.get("messages", [])
        topic = "generated_topic"

        if messages:
            content = messages[0].get("content", "")
            # Try to extract topic from context
            if '"topic"' in content:
                import re
                match = re.search(r'"topic":\s*"([^"]+)"', content)
                if match:
                    topic_value = match.group(1)
                    if not topic_value.startswith("NOT_PROVIDED"):
                        topic = topic_value

        class MockChoice:
            class MockMessage:
                def __init__(self, t):
                    self.content = f"""{{
"action": "store",
"recommended_path": "test",
"frontmatter": {{
    "topic": "{t}",
    "summary": "test summary",
    "tags": []
}},
"optimize_suggested": false
}}"""

            message = MockMessage(topic)

        class MockResponse:
            choices = [MockChoice()]

        return MockResponse()


@pytest.fixture
def temp_storage():
    """Temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def memory(temp_storage):
    """MdMemory instance with temp storage."""
    llm = MockLLM()
    return MdMemory(llm, str(temp_storage), optimize_threshold=5)


class TestRegistry:
    """Test PathRegistry."""

    def test_registry_put_get(self, temp_storage):
        """Test registry put and get."""
        registry_path = temp_storage / ".registry.json"
        registry = PathRegistry(registry_path)

        registry.put("topic1", "path/to/topic1.md")
        assert registry.get("topic1") == "path/to/topic1.md"

    def test_registry_delete(self, temp_storage):
        """Test registry delete."""
        registry_path = temp_storage / ".registry.json"
        registry = PathRegistry(registry_path)

        registry.put("topic1", "path/to/topic1.md")
        registry.delete("topic1")
        assert registry.get("topic1") is None


class TestUtils:
    """Test utility functions."""

    def test_write_and_read_markdown(self, temp_storage):
        """Test writing and reading markdown files."""
        file_path = temp_storage / "test.md"
        metadata = {"title": "Test", "tags": ["a", "b"]}
        content = "# Test\n\nThis is a test."

        write_markdown_file(file_path, metadata, content)
        read_meta, read_content = read_markdown_file(file_path)

        assert read_meta["title"] == "Test"
        assert "Test" in read_content

    def test_json_safe_operations(self, temp_storage):
        """Test safe JSON operations."""
        json_path = temp_storage / "test.json"
        data = {"key": "value", "nested": {"inner": 123}}

        save_json_safe(json_path, data)
        loaded = load_json_safe(json_path)

        assert loaded == data


class TestMdMemory:
    """Test MdMemory core functionality."""

    def test_init_creates_structure(self, memory, temp_storage):
        """Test initialization creates necessary files."""
        assert memory.root_index_path.exists()
        assert memory.registry_path.exists()

    def test_store_creates_file(self, memory):
        """Test storing a memory item."""
        result = memory.store("user1", "Python is a programming language...")
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

        # Check file exists (MockLLM returns "test" as path)
        file_path = memory.storage_path / "test" / f"{result}.md"
        assert file_path.exists()

    def test_store_with_provided_topic(self, memory):
        """Test storing with explicit topic parameter."""
        result = memory.store("user1", "Python decorators content", topic="python_decorators")
        assert result == "python_decorators"

        # Check file exists
        file_path = memory.storage_path / "test" / "python_decorators.md"
        assert file_path.exists()

    def test_store_with_generated_topic(self, memory):
        """Test storing without topic - system generates one."""
        query = "Python functions are reusable blocks of code"
        result = memory.store("user1", query)
        assert result is not None
        assert isinstance(result, str)

        # Verify it was registered in the registry
        topics = memory.list_topics()
        assert result in topics

    def test_retrieve_root_index(self, memory):
        """Test retrieving root index."""
        memory.store("user1", "Test content")
        index = memory.retrieve("user1")
        assert isinstance(index, str)
        assert len(index) > 0

    def test_get_topic(self, memory):
        """Test getting a specific topic."""
        topic = memory.store("user1", "My topic content")
        assert topic is not None
        content = memory.get("user1", topic)
        assert content is not None
        assert "My topic content" in content

    def test_delete_topic(self, memory):
        """Test deleting a topic."""
        topic = memory.store("user1", "This will be deleted")
        assert topic is not None
        result = memory.delete("user1", topic)
        assert result is True

        content = memory.get("user1", topic)
        assert content is None

    def test_list_topics(self, memory):
        """Test listing all topics."""
        topic1 = memory.store("user1", "Content 1")
        topic2 = memory.store("user1", "Content 2")
        assert topic1 is not None
        assert topic2 is not None
        topics = memory.list_topics()
        assert topic1 in topics
        assert topic2 in topics


class TestFrontMatter:
    """Test FrontMatter model."""

    def test_frontmatter_creation(self):
        """Test creating FrontMatter."""
        fm = FrontMatter(
            topic="test_topic",
            summary="Test summary",
            tags=["python", "learning"],
        )
        assert fm.topic == "test_topic"
        assert len(fm.tags) == 2

    def test_frontmatter_default_tags(self):
        """Test FrontMatter with default tags."""
        fm = FrontMatter(topic="test", summary="Test")
        assert fm.tags == []


class TestLLMResponse:
    """Test LLMResponse model."""

    def test_llm_response_creation(self):
        """Test creating LLMResponse."""
        frontmatter = FrontMatter(topic="test", summary="summary")
        response = LLMResponse(
            action="store",
            recommended_path="coding/python",
            frontmatter=frontmatter,
            optimize_suggested=True,
        )
        assert response.action == "store"
        assert response.optimize_suggested is True
