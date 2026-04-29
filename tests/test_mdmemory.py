"""Tests for MdMemory."""

import json
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from mdmemory import MdMemory, FrontMatter, LLMResponse
from mdmemory.registry import PathRegistry
from mdmemory.utils import (
    load_json_safe,
    save_json_safe,
    read_markdown_file,
    write_markdown_file,
    generate_fallback_topic,
)


def _make_mock_response_sync(content: str) -> MagicMock:
    """Create a mock response object."""
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message = MagicMock()
    mock.choices[0].message.content = content
    return mock


def _mock_llm(messages: list) -> str:
    """Default mock LLM logic for store actions."""
    content = messages[0].get("content", "")
    topic = "generated_topic"

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


@pytest.fixture
def temp_storage():
    """Temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
async def memory(temp_storage):
    """MdMemory instance with temp storage."""
    with patch(
        "mdmemory.core.litellm.acompletion",
        new_callable=AsyncMock
    ) as mock_ac:
        mock_ac.side_effect = lambda **kw: _make_mock_response_sync(_mock_llm(kw.get("messages", [])))
        mem = MdMemory(
            model_name="gpt-3.5-turbo",
            model_api_key="test-key",
            storage_path=str(temp_storage),
            optimize_threshold=5,
        )
        yield mem


class TestRegistry:
    """Test PathRegistry."""

    @pytest.mark.asyncio
    async def test_registry_put_get(self, temp_storage):
        """Test registry put and get."""
        registry_path = temp_storage / ".registry.json"
        registry = PathRegistry(registry_path)
        await registry.load()

        await registry.put("topic1", "path/to/topic1.md")
        assert registry.get("topic1") == "path/to/topic1.md"

    @pytest.mark.asyncio
    async def test_registry_delete(self, temp_storage):
        """Test registry delete."""
        registry_path = temp_storage / ".registry.json"
        registry = PathRegistry(registry_path)
        await registry.load()

        await registry.put("topic1", "path/to/topic1.md")
        await registry.delete("topic1")
        assert registry.get("topic1") is None


class TestUtils:
    """Test utility functions."""

    @pytest.mark.asyncio
    async def test_write_and_read_markdown(self, temp_storage):
        """Test writing and reading markdown files."""
        file_path = temp_storage / "test.md"
        metadata = {"title": "Test", "tags": ["a", "b"]}
        content = "# Test\n\nThis is a test."

        await write_markdown_file(file_path, metadata, content)
        read_meta, read_content = await read_markdown_file(file_path)

        assert read_meta["title"] == "Test"
        assert "Test" in read_content

    @pytest.mark.asyncio
    async def test_json_safe_operations(self, temp_storage):
        """Test safe JSON operations."""
        json_path = temp_storage / "test.json"
        data = {"key": "value", "nested": {"inner": 123}}

        await save_json_safe(json_path, data)
        loaded = await load_json_safe(json_path)

        assert loaded == data

    def test_fallback_topic_generation(self):
        """Test hash-based fallback topic ID."""
        q1 = "Hello World"
        q2 = "Hello World!"
        t1 = generate_fallback_topic(q1)
        t2 = generate_fallback_topic(q2)
        assert t1 != t2
        assert "hello" in t1


class TestMdMemory:
    """Test MdMemory core functionality."""

    @pytest.mark.asyncio
    async def test_init_creates_structure(self, memory, temp_storage):
        """Test initialization creates necessary files."""
        await memory._ensure_initialized()
        assert memory.root_index_path.exists()
        assert memory.registry_path.exists()

    @pytest.mark.asyncio
    async def test_store_creates_file(self, memory):
        """Test storing a memory item."""
        result = await memory.store("user1", "Python is a programming language...")
        assert result is not None
        assert isinstance(result, str)

        file_path = memory.storage_path / "test" / f"{result}.md"
        assert file_path.exists()

    @pytest.mark.asyncio
    async def test_store_with_provided_topic(self, memory):
        """Test storing with explicit topic parameter."""
        result = await memory.store("user1", "Python decorators content", topic="python_decorators")
        assert result == "python_decorators"

        file_path = memory.storage_path / "test" / "python_decorators.md"
        assert file_path.exists()

    @pytest.mark.asyncio
    async def test_search_functionality(self, memory):
        """Test keyword search."""
        await memory.store("user1", "Python is great", topic="python_intro")
        await memory.store("user1", "Cooking is fun", topic="cooking_fun")
        
        results = await memory.search("user1", "Python")
        assert len(results) == 1
        assert results[0]["topic"] == "python_intro"

    @pytest.mark.asyncio
    async def test_recursive_pruning(self, memory):
        """Test recursive index pruning on delete."""
        # Store in nested path
        with patch("mdmemory.core.litellm.acompletion", new_callable=AsyncMock) as mock_ac:
            mock_ac.side_effect = lambda **kw: _make_mock_response_sync(json.dumps({
                "action": "store",
                "recommended_path": "a/b/c",
                "frontmatter": {"topic": "deep_topic", "summary": "deep", "tags": []},
                "optimize_suggested": False,
            }))
            await memory.store("user1", "Deep content", topic="deep_topic")
        
        # Verify indices created
        assert (memory.storage_path / "a" / "b" / "c" / "index.md").exists()
        
        # Delete
        await memory.delete("user1", "deep_topic")
        
        # Verify entry removed from nested index
        _, content = await read_markdown_file(memory.storage_path / "a" / "b" / "c" / "index.md")
        assert "deep_topic" not in content

    @pytest.mark.asyncio
    async def test_optimize_batching(self, temp_storage):
        """Test optimize uses sliding window batches."""
        async def mock_async_side_effect(**kwargs):
            content = kwargs["messages"][0]["content"]
            if "batch_index" in content:
                return _make_mock_response_sync(json.dumps({
                    "action": "optimize",
                    "recommended_path": "",
                    "frontmatter": {"topic": "", "summary": "", "tags": []},
                    "optimize_suggested": True,
                    "reason": "[]"
                }))
            return _make_mock_response_sync(_mock_llm(kwargs["messages"]))

        with patch("mdmemory.core.litellm.acompletion", new_callable=AsyncMock) as mock_ac:
            mock_ac.side_effect = mock_async_side_effect
            memory = MdMemory(
                model_name="gpt-3.5-turbo",
                model_api_key="test-key",
                storage_path=str(temp_storage),
                optimize_threshold=2,
            )
            # Store 5 topics
            for i in range(5):
                await memory.store("user1", f"Content {i}", topic=f"topic_{i}")
            
            await memory.optimize("user1")
            
        # Success if no crash
