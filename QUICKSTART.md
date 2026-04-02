# MdMemory Quick Start

## Setup

### Install UV (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Clone and setup the project

```bash
git clone https://github.com/pvkarthikk/MdMemory.git
cd MdMemory
uv sync
```

## Running the Example

```bash
uv run example.py
```

## Running Tests

```bash
uv run --with pytest pytest tests/ -v
```

## Using MdMemory in Your Project

### 1. Install as a dependency

```bash
# Add to your project's pyproject.toml or install directly
pip install mdmemory
# or with uv:
uv add mdmemory
```

### 2. Basic Usage

```python
from mdmemory import MdMemory
from litellm import LiteLLM

# Initialize
llm = LiteLLM("gpt-3.5-turbo")
memory = MdMemory(llm, storage_path="./my_knowledge", optimize_threshold=20)

# Store knowledge
memory.store(
    "user123",
    "topic_id",
    "Your markdown content here..."
)

# Retrieve overview
index = memory.retrieve("user123")
print(index)

# Get specific topic
content = memory.get("user123", "topic_id")
print(content)

# List all topics
topics = memory.list_topics()
for topic_id, path in topics.items():
    print(f"{topic_id}: {path}")

# Delete a topic
memory.delete("user123", "topic_id")

# Optimize structure
memory.optimize("user123")
```

## Project Structure

```
MdMemory/
├── src/mdmemory/          # Main library code
│   ├── __init__.py        # Package exports
│   ├── core.py            # MdMemory main class
│   ├── models.py          # Pydantic models
│   ├── registry.py        # Path registry management
│   └── utils.py           # Utility functions
├── tests/                 # Test suite
│   ├── __init__.py
│   └── test_mdmemory.py   # Unit tests
├── example.py             # Example usage
├── pyproject.toml         # Project configuration
├── README.md              # Full documentation
├── QUICKSTART.md          # This file
├── spec.md                # Implementation specification
└── uv.lock                # Dependency lock file
```

## Development Commands with UV

### Code formatting
```bash
uv run --with black black src/ tests/
```

### Code linting
```bash
uv run --with ruff ruff check src/
```

### Type checking
```bash
uv run --with mypy mypy src/
```

### Run all checks
```bash
uv run --with black,ruff,mypy bash -c "black src/ tests/ && ruff check src/ && mypy src/"
```

## LLM Integration

MdMemory uses LiteLLM for flexible LLM provider support. You can use:

- OpenAI (GPT-3.5, GPT-4)
- Claude (Anthropic)
- Gemini (Google)
- Open-source models (Ollama, etc.)

Set your API keys as environment variables:

```bash
export OPENAI_API_KEY="sk-..."
# or
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Understanding the Storage Structure

After storing knowledge, you'll see:

```
knowledge_base/
├── .registry.json              # Mapping: topic_id -> file_path
├── index.md                    # Root knowledge index
└── general_knowledge/          # Auto-created category
    ├── index.md                # Category index
    ├── python_functions.md     # Knowledge file
    └── python_classes.md       # Knowledge file
```

- `.registry.json`: Enables fast lookups without scanning directories
- `index.md` files: Human-readable navigation and summaries
- Knowledge files: Standard Markdown with YAML frontmatter

## Next Steps

1. Read [spec.md](spec.md) for detailed implementation information
2. Check [README.md](README.md) for complete API documentation
3. Run `uv run example.py` to see MdMemory in action
4. Modify `example.py` to try different features

## Troubleshooting

### Issue: Import errors when running tests

**Solution:** Make sure you're using `uv run` which automatically activates the virtual environment:

```bash
uv run --with pytest pytest tests/ -v
```

### Issue: ModuleNotFoundError for mdmemory

**Solution:** Ensure the package is installed:

```bash
uv sync
```

### Issue: LLM API errors

**Solution:** 
1. Verify your API key is set correctly
2. Check your LiteLLM configuration
3. Try with the mock LLM in example.py first

## Contributing

1. Set up development environment: `uv sync`
2. Create a new branch for your feature
3. Make changes and run tests: `uv run --with pytest pytest tests/`
4. Format code: `uv run --with black black src/`
5. Submit a pull request

## License

MIT

---

For more information, see [README.md](README.md) and [spec.md](spec.md).
