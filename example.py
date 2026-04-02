"""Example usage of MdMemory."""

from pathlib import Path
from mdmemory import MdMemory


class SimpleLLM:
    """Simple LLM mock for demo purposes."""

    def completion(self, **kwargs):
        """Return a simple response."""

        class MockChoice:
            class MockMessage:
                content = """{
                    "action": "store",
                    "recommended_path": "general_knowledge",
                    "frontmatter": {
                        "topic": "demo_topic",
                        "summary": "A demonstration of MdMemory functionality",
                        "tags": ["demo", "example"]
                    },
                    "optimize_suggested": false
                }"""

            message = MockMessage()

        class MockResponse:
            choices = [MockChoice()]

        return MockResponse()


def main():
    """Run example."""
    # Initialize memory
    storage_path = Path("./example_knowledge_base")
    storage_path.mkdir(exist_ok=True)

    llm = SimpleLLM()
    memory = MdMemory(llm, str(storage_path), optimize_threshold=10)

    print("📚 MdMemory Example\n")

    # Store some knowledge
    print("1️⃣ Storing knowledge items...")
    memory.store(
        "user1",
        "python_functions",
        """
# Python Functions

Functions are reusable blocks of code that perform specific tasks.

## Syntax
```python
def function_name(parameters):
    # function body
    return value
```

## Key Points
- Use `def` keyword to define functions
- Parameters are optional
- Functions return values using `return` statement
""",
    )

    memory.store(
        "user1",
        "python_classes",
        """
# Python Classes

Classes are blueprints for creating objects.

## Syntax
```python
class ClassName:
    def __init__(self):
        pass
```

## Key Points
- Use `class` keyword
- `__init__` is the constructor
- `self` refers to the instance
""",
    )

    # Retrieve knowledge tree
    print("\n2️⃣ Retrieving knowledge tree...")
    index = memory.retrieve("user1")
    print(index)

    # Get specific topic
    print("\n3️⃣ Getting specific topic (python_functions)...")
    content = memory.get("user1", "python_functions")
    if content:
        print(content[:200] + "...")

    # List all topics
    print("\n4️⃣ Listing all topics...")
    topics = memory.list_topics()
    for topic_id, path in topics.items():
        print(f"   - {topic_id}: {path}")

    print("\n✅ Example complete!")
    print(f"📂 Knowledge base stored at: {storage_path.absolute()}")


if __name__ == "__main__":
    main()
