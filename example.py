"""Example usage of MdMemory."""

from pathlib import Path
from mdmemory import MdMemory


def create_llm_callback():
    """Create a simple LLM callback for demo purposes.

    This demonstrates how to create a callback that works with any LLM provider.
    """

    def llm_callback(messages: list) -> str:
        """
        LLM callback function.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            LLM response as string

        Example implementations:

        # Using LiteLLM:
        from litellm import completion
        response = completion(model="gpt-3.5-turbo", messages=messages)
        return response.choices[0].message.content

        # Using OpenAI directly:
        from openai import OpenAI
        client = OpenAI()
        response = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages)
        return response.choices[0].message.content

        # Using Claude:
        from anthropic import Anthropic
        client = Anthropic()
        response = client.messages.create(model="claude-3-sonnet", messages=messages)
        return response.content[0].text
        """
        # For this demo, return a simple mocked response
        return """{
            "action": "store",
            "recommended_path": "general_knowledge",
            "frontmatter": {
                "topic": "demo_topic",
                "summary": "A demonstration of MdMemory functionality",
                "tags": ["demo", "example"]
            },
            "optimize_suggested": false
        }"""

    return llm_callback


def main():
    """Run example."""
    # Initialize memory
    storage_path = Path("./example_knowledge_base")
    storage_path.mkdir(exist_ok=True)

    # Create LLM callback
    llm_callback = create_llm_callback()

    # Create MdMemory with the callback
    memory = MdMemory(
        llm_callback,
        str(storage_path),
        optimize_threshold=10,
    )

    print("📚 MdMemory Example\n")

    # Store some knowledge with explicit topics
    print("1️⃣ Storing knowledge items WITH explicit topics...")
    topic1 = memory.store(
        "user1",
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
        topic="python_functions",
    )
    print(f"   ✅ Stored as topic: {topic1}")

    topic2 = memory.store(
        "user1",
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
        topic="python_classes",
    )
    print(f"   ✅ Stored as topic: {topic2}")

    # Store knowledge WITHOUT explicit topic - LLM generates it
    print("\n1b️⃣ Storing knowledge WITHOUT explicit topic (LLM generates it)...")
    generated_topic1 = memory.store(
        "user1",
        """
Decorators are functions that modify other functions or classes.
They are a way to "wrap" a function or class with another function.
Common use cases include logging, authentication, validation, etc.
""",
    )
    print(f"   ✅ LLM generated topic: {generated_topic1}")

    generated_topic2 = memory.store(
        "user1",
        """
List comprehensions provide a concise way to create lists in Python.
Instead of using loops and append(), you can use a single line.
Example: [x*2 for x in range(5)] creates [0, 2, 4, 6, 8]
""",
    )
    print(f"   ✅ LLM generated topic: {generated_topic2}")

    # Retrieve knowledge tree
    print("\n2️⃣ Retrieving knowledge tree...")
    index = memory.retrieve("user1")
    print(index)

    # Get specific topics
    print("\n3️⃣ Getting specific topics...")
    if topic1:
        content = memory.get("user1", topic1)
        if content:
            print(f"\n   📌 {topic1}:")
            print(content[:150] + "...")

    if generated_topic1:
        content = memory.get("user1", generated_topic1)
        if content:
            print(f"\n   📌 {generated_topic1} (LLM-generated):")
            print(content[:150] + "...")

    # List all topics
    print("\n4️⃣ Listing all topics...")
    topics = memory.list_topics()
    for topic_id, path in topics.items():
        print(f"   - {topic_id}: {path}")

    print("\n✅ Example complete!")
    print(f"📂 Knowledge base stored at: {storage_path.absolute()}")


if __name__ == "__main__":
    main()
