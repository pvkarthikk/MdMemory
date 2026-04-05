"""Tests for MdMemory."""

import json
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
    """Mock LLM callback for testing."""

    def __call__(self, messages: list) -> str:
        """Mock LLM callback that parses messages and returns JSON response."""
        topic = "generated_topic"

        if messages:
            content = messages[0].get("content", "")
            if '"topic"' in content:
                import re

                match = re.search(r'"topic":\s*"([^"]+)"', content)
                if match:
                    topic_value = match.group(1)
                    if not topic_value.startswith("NOT_PROVIDED"):
                        topic = topic_value

            if "Action: optimize" in content:
                return json.dumps(
                    {
                        "action": "optimize",
                        "recommended_path": "",
                        "frontmatter": {"topic": "", "summary": "", "tags": []},
                        "optimize_suggested": True,
                        "reason": json.dumps(
                            [
                                {
                                    "topic": "python_basics",
                                    "new_path": "coding/python",
                                    "summary": "Python basics",
                                },
                                {
                                    "topic": "python_functions",
                                    "new_path": "coding/python",
                                    "summary": "Python functions",
                                },
                                {
                                    "topic": "python_classes",
                                    "new_path": "coding/python",
                                    "summary": "Python classes",
                                },
                            ]
                        ),
                    }
                )

        return json.dumps(
            {
                "action": "store",
                "recommended_path": "test",
                "frontmatter": {"topic": topic, "summary": "test summary", "tags": []},
                "optimize_suggested": False,
            }
        )


class OptimizeMockLLM:
    """Mock LLM that returns specific move operations for optimize testing."""

    def __init__(self, moves: list = None):
        self.moves = moves or []

    def __call__(self, messages: list) -> str:
        content = messages[0].get("content", "") if messages else ""

        if "Action: optimize" in content:
            return json.dumps(
                {
                    "action": "optimize",
                    "recommended_path": "",
                    "frontmatter": {"topic": "", "summary": "", "tags": []},
                    "optimize_suggested": True,
                    "reason": json.dumps(self.moves),
                }
            )

        topic = "generated_topic"
        if '"topic"' in content:
            import re

            match = re.search(r'"topic":\s*"([^"]+)"', content)
            if match:
                topic_value = match.group(1)
                if not topic_value.startswith("NOT_PROVIDED"):
                    topic = topic_value

        return json.dumps(
            {
                "action": "store",
                "recommended_path": "root",
                "frontmatter": {"topic": topic, "summary": "test summary", "tags": []},
                "optimize_suggested": False,
            }
        )


@pytest.fixture
def temp_storage():
    """Temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def memory(temp_storage):
    """MdMemory instance with temp storage."""
    llm_callback = MockLLM()
    return MdMemory(llm_callback, str(temp_storage), optimize_threshold=5)


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

        file_path = memory.storage_path / "test" / f"{result}.md"
        assert file_path.exists()

    def test_store_with_provided_topic(self, memory):
        """Test storing with explicit topic parameter."""
        result = memory.store("user1", "Python decorators content", topic="python_decorators")
        assert result == "python_decorators"

        file_path = memory.storage_path / "test" / "python_decorators.md"
        assert file_path.exists()

    def test_store_with_generated_topic(self, memory):
        """Test storing without topic - system generates one."""
        query = "Python functions are reusable blocks of code"
        result = memory.store("user1", query)
        assert result is not None
        assert isinstance(result, str)

        topics = memory.list_topics()
        assert result in topics

    def test_store_includes_user_id(self, memory):
        """Test that store includes user_id in frontmatter."""
        topic = memory.store("user42", "Content for user 42")
        assert topic is not None

        relative_path = memory.registry.get(topic)
        file_path = memory.storage_path / relative_path
        metadata, _ = read_markdown_file(file_path)
        assert metadata.get("user_id") == "user42"

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

    def test_optimize_reorganizes_files(self, temp_storage):
        """Test that optimize moves files to new directories."""
        moves = [
            {"topic": "python_basics", "new_path": "coding/python", "summary": "Python basics"},
            {
                "topic": "python_functions",
                "new_path": "coding/python",
                "summary": "Python functions",
            },
        ]
        llm = OptimizeMockLLM(moves=moves)
        memory = MdMemory(llm, str(temp_storage), optimize_threshold=2)

        # Store topics at root level
        memory.store("user1", "Python basics content", topic="python_basics")
        memory.store("user1", "Python functions content", topic="python_functions")

        # Force root index to exceed threshold
        memory._append_to_index(memory.root_index_path, "extra_topic_1", "Extra 1")
        memory._append_to_index(memory.root_index_path, "extra_topic_2", "Extra 2")
        memory._append_to_index(memory.root_index_path, "extra_topic_3", "Extra 3")

        # Run optimize
        memory.optimize("user1")

        # Verify files were moved
        new_file_1 = memory.storage_path / "coding" / "python" / "python_basics.md"
        new_file_2 = memory.storage_path / "coding" / "python" / "python_functions.md"
        assert new_file_1.exists()
        assert new_file_2.exists()

        # Verify registry updated
        assert "coding" in memory.registry.get("python_basics")
        assert "coding" in memory.registry.get("python_functions")

    def test_optimize_filters_by_user_id(self, temp_storage):
        """Test that optimize only processes topics for the given user."""
        moves = [
            {"topic": "user1_topic", "new_path": "coding/python", "summary": "User 1 topic"},
        ]
        llm = OptimizeMockLLM(moves=moves)
        memory = MdMemory(llm, str(temp_storage), optimize_threshold=2)

        # Store topics for different users
        memory.store("user1", "User 1 content", topic="user1_topic")
        memory.store("user2", "User 2 content", topic="user2_topic")

        # Force threshold
        memory._append_to_index(memory.root_index_path, "extra_1", "Extra 1")
        memory._append_to_index(memory.root_index_path, "extra_2", "Extra 2")
        memory._append_to_index(memory.root_index_path, "extra_3", "Extra 3")

        # Optimize for user1 only
        memory.optimize("user1")

        # user1_topic should be moved
        new_file = memory.storage_path / "coding" / "python" / "user1_topic.md"
        assert new_file.exists()

        # user2_topic should still be at root
        user2_path = memory.registry.get("user2_topic")
        assert user2_path is not None
        assert "coding" not in user2_path

    def test_compress_root_index(self, temp_storage):
        """Test root index compression when folder has 3+ files."""
        llm = OptimizeMockLLM(
            moves=[
                {"topic": "topic_a", "new_path": "coding/python", "summary": "Topic A"},
                {"topic": "topic_b", "new_path": "coding/python", "summary": "Topic B"},
                {"topic": "topic_c", "new_path": "coding/python", "summary": "Topic C"},
            ]
        )
        memory = MdMemory(llm, str(temp_storage), optimize_threshold=2)

        # Store 3 topics
        memory.store("user1", "Content A", topic="topic_a")
        memory.store("user1", "Content B", topic="topic_b")
        memory.store("user1", "Content C", topic="topic_c")

        # Force threshold
        memory._append_to_index(memory.root_index_path, "extra_1", "Extra 1")
        memory._append_to_index(memory.root_index_path, "extra_2", "Extra 2")
        memory._append_to_index(memory.root_index_path, "extra_3", "Extra 3")

        memory.optimize("user1")

        # Verify root index contains folder link
        _, root_content = read_markdown_file(memory.root_index_path)
        assert "Coding" in root_content
        assert "coding/python/index.md" in root_content


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

    def test_frontmatter_user_id(self):
        """Test FrontMatter with user_id."""
        fm = FrontMatter(topic="test", summary="Test", user_id="user42")
        assert fm.user_id == "user42"

    def test_frontmatter_default_user_id(self):
        """Test FrontMatter default user_id is None."""
        fm = FrontMatter(topic="test", summary="Test")
        assert fm.user_id is None


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

    def test_llm_response_with_reason(self):
        """Test LLMResponse with reason field."""
        frontmatter = FrontMatter(topic="test", summary="summary")
        response = LLMResponse(
            action="optimize",
            recommended_path="",
            frontmatter=frontmatter,
            optimize_suggested=True,
            reason='[{"topic": "a", "new_path": "coding"}]',
        )
        assert response.action == "optimize"
        assert "topic" in response.reason
