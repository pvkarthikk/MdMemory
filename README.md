# MdMemory

A Markdown-first, LLM-driven memory framework that organizes agent knowledge into a hierarchical **Knowledge Tree**. Designed to be high-performance, asynchronous, and Model Context Protocol (MCP) compatible.

## Features

- **Asynchronous Core**: Built with `async/await` and `aiofiles` for non-blocking performance.
- **Human-Readable**: Data stored as standard `.md` files on the filesystem.
- **LLM-Organized**: Uses LLM to automatically determine folder structure and metadata.
- **MCP Native**: Built-in server support for Model Context Protocol (stdio/SSE).
- **Safe Concurrency**: Mandatory file locking via `portalocker` for registry and index integrity.
- **Scalable Optimization**: Sliding window batching prevents LLM token limit issues.
- **Native Search**: keyword-based filtering across topic IDs, summaries, and tags.
- **Recursive Indexing**: Automatic management of index files across deeply nested directories.

## Installation

```bash
pip install mdmemory
```

To include MCP server support:

```bash
pip install "mdmemory[mcp]"
```

## Quick Start

```python
import asyncio
from mdmemory import MdMemory

async def main():
    # Initialize MdMemory
    memory = MdMemory(
        model_name="gpt-3.5-turbo",
        model_api_key="your-api-key",
        storage_path="./knowledge_base"
    )

    # Store a memory (LLM automatically categorizes and generates metadata)
    topic = await memory.store(
        usr_id="user123",
        query="Decorators in Python are a powerful way to modify function behavior."
    )
    print(f"Stored as topic: {topic}")

    # Search memories
    results = await memory.search("user123", "Python decorators")
    for res in results:
        print(f"Found: {res['topic']} - {res['summary']}")

    # Retrieve specific topic
    content = await memory.get("user123", topic)
    print(content)

    # Optimize structure (triggers LLM-driven reorganization)
    await memory.optimize("user123")

if __name__ == "__main__":
    asyncio.run(main())
```

## MCP Server Integration

MdMemory can act as a managed memory backend for AI agents (like Claude Desktop) via the Model Context Protocol.

### Starting the Server

```bash
# Using stdio transport (default)
mdmemory-mcp --usr_id user123 --model gpt-4 --storage ./memory

# Using SSE transport
mdmemory-mcp --transport sse --host 0.0.0.0 --port 8000
```

### Exposed Capabilities
- **Tools**: `store_memory`, `search_memory`, `get_topic`, `delete_topic`, `optimize_structure`.
- **Resources**: `mdmemory://index`, `mdmemory://topic/{topic_id}`.
- **Prompts**: `summarize_knowledge`.

### Sample Configuration (Claude Desktop)

To use MdMemory with Claude Desktop, add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mdmemory": {
      "command": "python",
      "args": [
        "-m",
        "mdmemory.mcp",
        "--usr_id",
        "your_user_name",
        "--storage",
        "/absolute/path/to/memory"
      ],
      "env": {
        "MDMEMORY_MODEL": "gpt-4",
        "MDMEMORY_API_KEY": "your_api_key_here",
        "MDMEMORY_BASE_URL": "https://api.openai.com/v1"
      }
    }
  }
}
```

### SSE Configuration (Remote/Web)

To run the MCP server as a web service using Server-Sent Events (SSE):

```bash
mdmemory-mcp --transport sse --host 0.0.0.0 --port 8000
```

Example `claude_desktop_config.json` for connecting to a remote SSE server:

```json
{
  "mcpServers": {
    "mdmemory-remote": {
      "url": "http://your-server-ip:8000/sse"
    }
  }
}
```

## Directory Structure

```
storage_root/
├── .registry.json           # Global Path Map (Locked)
├── index.md                 # Root Knowledge Tree
└── /categories/             # Auto-created folders
    ├── coding/
    │   ├── index.md         # Sub-index
    │   └── python.md        # Knowledge file
    └── finance/
        └── taxes.md
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `model_name` | - | LLM model name (LiteLLM compatible) |
| `storage_path` | `./MdMemory` | Root directory for Markdown storage |
| `optimize_threshold` | `20` | Root index line count that triggers optimization |

## Development

### Running Tests
```bash
pytest tests/
```

### Requirements & Design
Detailed technical specifications are available in:
- [requirements.md](requirements.md)
- [design.md](design.md)

## License
MIT
