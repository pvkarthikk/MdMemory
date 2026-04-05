# MdMemory

A Markdown-first, LLM-driven memory framework that organizes agent knowledge into a hierarchical **Knowledge Tree**.

## Features

- **Human-Readable**: Data stored as standard `.md` files on the filesystem
- **LLM-Organized**: Uses LLM to automatically determine folder structure and organization
- **Context-Aware**: Hybrid indexing strategy keeps the root index compact
- **Efficient Navigation**: Central `index.md` and `.registry.json` Path Map for direct access
- **User-Scoped Optimization**: Each topic is tagged with a user ID, enabling per-user knowledge tree reorganization
- **Auto-Compression**: Root index automatically compresses into folder links when subdirectories reach 3+ files

## Installation

```bash
pip install mdmemory
```

Or with development dependencies:

```bash
pip install -e ".[dev]"
```

### Google ADK Integration

To use MdMemory as a memory service for Google ADK agents:

```bash
pip install mdmemory[adk]
```

## Quick Start

```python
from mdmemory import MdMemory

# Initialize MdMemory with your LLM configuration
memory = MdMemory(
    model_name="gpt-3.5-turbo",
    model_api_key="your-api-key",
    storage_path="./knowledge_base",
    optimize_threshold=20
)

# Store a memory WITH explicit topic
topic = memory.store(
    usr_id="user123",
    query="Decorators are functions that modify other functions...",
    topic="python_decorators"  # Optional - provide explicit topic
)

# Store a memory WITHOUT topic - LLM generates one automatically
generated_topic = memory.store(
    usr_id="user123",
    query="List comprehensions are concise ways to create lists in Python..."
    # topic parameter omitted - LLM will infer topic from content
)
print(f"Generated topic: {generated_topic}")

# Retrieve the knowledge tree
index = memory.retrieve("user123")
print(index)

# Get a specific topic
content = memory.get("user123", "python_decorators")
print(content)

# Delete a topic
memory.delete("user123", "python_decorators")

# List all topics
topics = memory.list_topics()
print(topics)

# Optimize structure
memory.optimize("user123")
```

## Directory Structure

```
storage_root/
├── .registry.json           # Global Path Map (Topic ID -> Physical Path)
├── index.md                 # Root Knowledge Tree
└── /categories/             # Auto-created folders
    ├── coding/
    │   ├── index.md         # Sub-index
    │   └── python.md        # Knowledge file
    └── finance/
        └── taxes.md
```

## Architecture

### Core Components

- **MdMemory**: Main class providing the public API
- **PathRegistry**: Manages `.registry.json` for topic ID -> file path mapping
- **FrontMatter**: Metadata attached to each knowledge file
- **LLMResponse**: Structured response from LLM decisions

### Key Concepts

#### Hybrid Indexing

- **Root `index.md`**: High-level overview of all knowledge
- **Sub-folder `index.md`**: Generated when folder exceeds `optimize_threshold`
- **Compression**: Parent index replaced with link to folder index when compressed

#### LLM Integration

The library queries the LLM for:

1. **Path Recommendation**: Where to store new knowledge
2. **Frontmatter Generation**: Metadata (summary, tags) for files
3. **Optimization Suggestions**: When and how to reorganize structure

#### User-Scoped Storage

Every stored topic automatically includes a `user_id` field in its frontmatter metadata. This enables:

- **Per-user optimization**: `optimize(usr_id)` only reorganizes topics belonging to that user
- **Multi-user support**: Multiple users can share the same storage path without interference
- **Frontmatter tracking**: User ID is persisted in each `.md` file's YAML frontmatter

#### Index Compression

When a subdirectory reaches 3+ markdown files, the root index automatically compresses individual entries into a single folder link:

```markdown
- **Coding/**: See [Coding index](coding/python/index.md)
```

This keeps the root index compact and navigable regardless of knowledge tree size.

### System Prompt

```
You are the MdMemory Librarian. Your goal is to maintain a clean, hierarchical 
Markdown Knowledge Tree. When storing data, choose a logical path. When optimizing, 
group related files into sub-directories to keep the root index under 50 lines.
```

## API Reference

### `__init__(model_name, model_api_key, model_base_url=None, storage_path="./MdMemory", optimize_threshold=20)`

Initialize MdMemory with LLM configuration.

**Parameters:**
- `model_name`: LLM model name (e.g., `"gpt-3.5-turbo"`, `"claude-3-sonnet"`, `"ollama/llama3"`)
- `model_api_key`: API key for the model provider
- `model_base_url` (optional): Base URL for the model API (for proxies, local models, etc.)
- `storage_path`: Root directory path for storing markdown files
- `optimize_threshold` (optional): Line count threshold for triggering auto-optimization (default: 20)

**Example:**
```python
# OpenAI
memory = MdMemory(model_name="gpt-3.5-turbo", model_api_key="sk-...")

# Anthropic Claude
memory = MdMemory(model_name="claude-3-sonnet-20240229", model_api_key="sk-ant-...")

# Local model via Ollama
memory = MdMemory(
    model_name="ollama/llama3",
    model_api_key="ollama",
    model_base_url="http://localhost:11434"
)
```

### `store(usr_id, query, topic=None) -> Optional[str]`

Store a new memory item.

**Parameters:**
- `usr_id`: User identifier
- `query`: Content to store (Markdown text)
- `topic` (optional): Topic identifier. If not provided, LLM will generate one from the query content

**Returns:** The topic ID that was used or generated, or None if storage failed

**Example:**
```python
# With explicit topic
topic = memory.store("user1", "Content here", topic="my_topic")

# With LLM-generated topic
topic = memory.store("user1", "Content here")  # LLM generates topic from content
```

### `retrieve(usr_id) -> str`

Get the root index (knowledge tree overview).

### `get(usr_id, topic) -> Optional[str]`

Get full content of a specific topic.

### `delete(usr_id, topic) -> bool`

Remove a topic from memory.

### `optimize(usr_id) -> None`

Reorganize knowledge tree structure for a specific user. Scans all topics belonging to `usr_id`, calls the LLM to suggest grouping related topics into subdirectories, moves files accordingly, and compresses the root index by replacing individual entries with folder links for directories with 3+ files.

**Parameters:**
- `usr_id`: User identifier (only topics with matching `user_id` in frontmatter will be optimized)

**Example:**
```python
# Optimize only user123's topics
memory.optimize("user123")
```

### `list_topics() -> Dict[str, str]`

List all topics in the registry.

---

## Google ADK Integration

MdMemory provides `MdMemoryService`, a drop-in implementation of Google ADK's `BaseMemoryService`. This lets your ADK agents use MdMemory's persistent, human-readable Markdown knowledge tree as their long-term memory backend.

### Setup

```python
from mdmemory import MdMemoryService

# Create the service (uses default storage path)
memory_service = MdMemoryService()

# Or with custom configuration
memory_service = MdMemoryService(
    storage_path="./agent_memory",
    optimize_threshold=20,
    llm_callback=my_llm_callback,  # optional
)
```

### Usage with ADK Runner

```python
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from mdmemory import MdMemoryService

memory_service = MdMemoryService(storage_path="./memory")
session_service = InMemorySessionService()

runner = Runner(
    agent=my_agent,
    app_name="my_app",
    session_service=session_service,
    memory_service=memory_service,
)
```

### How It Works

| ADK Method | MdMemory Behavior |
|------------|-------------------|
| `add_session_to_memory(session)` | Converts session events to Markdown, LLM generates semantic topic, stores as `.md` file |
| `add_events_to_memory(...)` | Appends new user/agent exchanges to existing session's Markdown file |
| `add_memory(...)` | Stores explicit `MemoryEntry` items as Markdown topics |
| `search_memory(query)` | Fast keyword search across frontmatter summaries; returns matching `MemoryEntry` objects |

### Search Performance

`search_memory` is optimized for speed:
1. Iterates the in-memory registry (O(1) dict lookup)
2. Reads only frontmatter (small YAML block) for filtering
3. Filters by `user_id` before reading full content
4. Keyword matches against topic name and summary
5. Only reads full Markdown content for actual matches

### Giving Your Agent Memory Tools

```python
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

agent = Agent(
    model="gemini-2.0-flash",
    name="memory_agent",
    instruction="You have access to long-term memory. Use it to recall past conversations.",
    tools=[PreloadMemoryTool()],
)
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
black src/
ruff check src/
mypy src/
```

## License

MIT

## Specification

See [spec.md](spec.md) for the full implementation specification.
