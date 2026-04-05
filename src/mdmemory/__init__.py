"""MdMemory - Markdown-first, LLM-driven memory framework.

A Markdown-first, LLM-driven memory framework that organizes agent knowledge
into a hierarchical Knowledge Tree. It prioritizes context efficiency by using
a hierarchical folder structure and a "Hybrid Indexing" strategy, ensuring the
agent only loads what is necessary.

Core Features:
    - Human-Readable: Data stored as standard .md files on the filesystem
    - LLM-Organized: Uses LLM to automatically determine folder structure
    - Context-Aware: Hybrid indexing strategy keeps the root index compact
    - Efficient Navigation: Central index.md and .registry.json for direct access
    - Provider Agnostic: Works with any LLM provider via callbacks

Example Usage:
    >>> from mdmemory import MdMemory
    >>> memory = MdMemory()  # Uses defaults: LiteLLMCallback + "./MdMemory"
    >>> topic = memory.store("user1", "My knowledge content")
    >>> content = memory.get("user1", topic)
    >>> index = memory.retrieve("user1")
"""

__title__ = "mdmemory"
__version__ = "0.3.0"
__author__ = "Contributors"
__license__ = "MIT"
__copyright__ = "Copyright 2026 Contributors"
__description__ = (
    "Markdown-first, LLM-driven memory framework organized into a hierarchical Knowledge Tree"
)

from .core import (
    MdMemory,
    LLMCallback,
    LiteLLMCallback,
    OpenAICallback,
    AnthropicCallback,
)
from .models import FrontMatter, LLMResponse

__all__ = [
    "MdMemory",
    "LLMCallback",
    "LiteLLMCallback",
    "OpenAICallback",
    "AnthropicCallback",
    "FrontMatter",
    "LLMResponse",
    "__version__",
    "__title__",
    "__author__",
    "__license__",
]

# Optional ADK integration
try:
    from .adk import MdMemoryService

    __all__.append("MdMemoryService")
except ImportError:
    pass
