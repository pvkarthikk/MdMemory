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
    - Provider Agnostic: Uses LiteLLM to support any LLM provider via model_name

Example Usage:
    >>> from mdmemory import MdMemory
    >>> memory = MdMemory(model_name="gpt-3.5-turbo", model_api_key="your-key")
    >>> topic = memory.store("user1", "My knowledge content")
    >>> content = memory.get("user1", topic)
    >>> index = memory.retrieve("user1")
"""

__title__ = "mdmemory"
__version__ = "0.4.1"
__author__ = "Contributors"
__license__ = "MIT"
__copyright__ = "Copyright 2026 Contributors"
__description__ = (
    "Markdown-first, LLM-driven memory framework organized into a hierarchical Knowledge Tree"
)

from .core import MdMemory
from .models import FrontMatter, LLMResponse

# Optional MCP integration
try:
    from .mcp import MdMemoryMCPServer
    __mcp_available__ = True
except ImportError:
    __mcp_available__ = False

__all__ = [
    "MdMemory",
    "FrontMatter",
    "LLMResponse",
    "__version__",
    "__title__",
    "__author__",
    "__license__",
]

if __mcp_available__:
    __all__.append("MdMemoryMCPServer")

