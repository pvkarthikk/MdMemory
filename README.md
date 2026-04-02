# MdMemory

A Markdown-first, LLM-driven memory framework that organizes agent knowledge into a hierarchical **Knowledge Tree**.

## Features

- **Human-Readable**: Data stored as standard `.md` files on the filesystem
- **LLM-Organized**: Uses LLM to automatically determine folder structure and organization
- **Context-Aware**: Hybrid indexing strategy keeps the root index compact
- **Efficient Navigation**: Central `index.md` and `.registry.json` Path Map for direct access

## Installation

```bash
pip install mdmemory
```

Or with development dependencies:

```bash
pip install -e ".[dev]"
```

## Quick Start

```python
from mdmemory import MdMemory
from litellm import LiteLLM

# Initialize with LiteLLM
llm = LiteLLM("gpt-3.5-turbo")
memory = MdMemory(llm, storage_path="./knowledge_base", optimize_threshold=20)

# Store a memory
memory.store(
    usr_id="user123",
    topic="python_decorators",
    query="Decorators are functions that modify other functions..."
)

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
3. **Optimization Suggestions**: When to reorganize structure

### System Prompt

```
You are the MdMemory Librarian. Your goal is to maintain a clean, hierarchical 
Markdown Knowledge Tree. When storing data, choose a logical path. When optimizing, 
group related files into sub-directories to keep the root index under 50 lines.
```

## API Reference

### `__init__(llm, storage_path, optimize_threshold=20)`

Initialize MdMemory with an LLM instance and storage location.

### `store(usr_id, topic, query) -> bool`

Store a new memory item.

### `retrieve(usr_id) -> str`

Get the root index (knowledge tree overview).

### `get(usr_id, topic) -> Optional[str]`

Get full content of a specific topic.

### `delete(usr_id, topic) -> bool`

Remove a topic from memory.

### `optimize(usr_id) -> None`

Reorganize knowledge tree structure.

### `list_topics() -> Dict[str, str]`

List all topics in the registry.

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
