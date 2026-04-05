"""Core MdMemory implementation."""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import litellm

from .models import FrontMatter, LLMResponse
from .registry import PathRegistry
from .utils import (
    ensure_dir_exists,
    parse_topic_title,
    read_markdown_file,
    save_json_safe,
    write_markdown_file,
)


class MdMemory:
    """Markdown-first, LLM-driven memory framework."""

    SYSTEM_PROMPT = """You are the MdMemory Librarian. Your goal is to maintain a clean, hierarchical Markdown Knowledge Tree. When storing data, choose a logical path. When optimizing, group related files into sub-directories to keep the root index under 50 lines. Always return JSON containing: `action`, `recommended_path`, `frontmatter`, and `optimize_suggested`."""

    def __init__(
        self,
        model_name: str,
        model_api_key: str,
        model_base_url: Optional[str] = None,
        storage_path: str = "./MdMemory",
        optimize_threshold: int = 20,
    ):
        """Initialize MdMemory.

        Args:
            model_name: LLM model name (e.g., "gpt-3.5-turbo", "claude-3-sonnet")
            model_api_key: API key for the model provider
            model_base_url: Base URL for the model API (optional, for proxies/local models)
            storage_path: Root path for storage (default: ./MdMemory)
            optimize_threshold: Line count threshold for triggering optimize
        """
        self._model_name = model_name
        self._model_api_key = model_api_key
        self._model_base_url = model_base_url
        self.storage_path = Path(storage_path)
        self.optimize_threshold = optimize_threshold

        # Initialize storage structure
        ensure_dir_exists(self.storage_path)

        # Load or create registry
        self.registry_path = self.storage_path / ".registry.json"
        if not self.registry_path.exists():
            save_json_safe(self.registry_path, {})
        self.registry = PathRegistry(self.registry_path)

        # Initialize root index
        self.root_index_path = self.storage_path / "index.md"
        if not self.root_index_path.exists():
            self._init_root_index()

    def _init_root_index(self) -> None:
        """Initialize the root index.md."""
        metadata = {
            "title": "MdMemory Root Index",
            "created_at": datetime.now().isoformat(),
        }
        content = "# Knowledge Tree\n\nWelcome to MdMemory. This is the root index.\n\n"
        write_markdown_file(self.root_index_path, metadata, content)

    def _call_llm(self, messages: list) -> str:
        """Call LiteLLM directly.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            LLM response as string
        """
        kwargs = {
            "model": self._model_name,
            "api_key": self._model_api_key,
            "messages": messages,
        }
        if self._model_base_url:
            kwargs["api_base"] = self._model_base_url

        response = litellm.completion(**kwargs)
        return response.choices[0].message.content

    def _get_llm_decision(self, action: str, context: Dict[str, str]) -> Optional[LLMResponse]:
        """Call LLM for organizational decisions.

        Args:
            action: The action type ("store", "optimize", etc.)
            context: Context dict for the LLM

        Returns:
            LLMResponse or None if error
        """
        try:
            if action == "optimize":
                prompt = f"""
{self.SYSTEM_PROMPT}

Action: {action}
Context: {json.dumps(context, indent=2)}

Analyze the current structure and suggest reorganization to group related topics into subdirectories.

Please respond with a JSON object containing:
- action: "optimize"
- recommended_path: "" (leave empty for optimize action)
- frontmatter: {{}} (leave empty for optimize action)
- optimize_suggested: true
- reason: A JSON array of move operations, e.g.:
  [{{"topic": "python_basics", "new_path": "coding/python", "summary": "Python basics"}}, ...]
"""
            else:
                prompt = f"""
{self.SYSTEM_PROMPT}

Action: {action}
Context: {json.dumps(context, indent=2)}

Please respond with a JSON object containing:
- action: The action being performed
- recommended_path: The logical folder path (e.g., "coding/python")
- frontmatter: Object with topic, summary, tags
- optimize_suggested: Boolean indicating if optimization is needed
"""

            messages = [{"role": "user", "content": prompt}]
            response_text = self._call_llm(messages)

            # Try to extract JSON from response
            try:
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    response_json = json.loads(json_match.group())
                    return LLMResponse(**response_json)
            except (json.JSONDecodeError, ValueError):
                pass

            return None
        except Exception as e:
            print(f"LLM call error: {e}")
            return None

    def store(self, usr_id: str, query: str, topic: Optional[str] = None) -> Optional[str]:
        """Store a memory item.

        Args:
            usr_id: User ID
            query: The content to store
            topic: Topic identifier (optional - LLM will generate if not provided)

        Returns:
            The topic ID that was used/generated, or None if failed
        """
        # Prepare context for LLM
        context = {"query": query, "user_id": usr_id}
        if topic:
            context["topic"] = topic
        else:
            context["topic"] = (
                "NOT_PROVIDED - Please generate a concise topic ID from the query content"
            )

        # Call LLM to determine folder path and frontmatter
        llm_response = self._get_llm_decision("store", context)

        if not llm_response:
            # Fallback: use provided topic or generate simple one from query
            if topic:
                used_topic = topic
                recommended_path = "uncategorized"
            else:
                used_topic = query[:30].replace(" ", "_").replace("\n", "_").lower()
                recommended_path = "uncategorized"

            frontmatter = FrontMatter(
                topic=used_topic,
                summary=query[:100],
                tags=[],
                created_at=datetime.now().isoformat(),
            )
        else:
            used_topic = llm_response.frontmatter.topic
            recommended_path = llm_response.recommended_path
            frontmatter = llm_response.frontmatter

        # Set timestamps and user_id
        frontmatter.created_at = datetime.now().isoformat()
        frontmatter.updated_at = datetime.now().isoformat()
        frontmatter.user_id = usr_id

        # Create file path
        folder_path = self.storage_path / recommended_path
        ensure_dir_exists(folder_path)
        file_path = folder_path / f"{used_topic}.md"

        # Write the file
        metadata = frontmatter.model_dump()
        success = write_markdown_file(file_path, metadata, query)

        if success:
            # Update registry
            relative_path = str(file_path.relative_to(self.storage_path))
            self.registry.put(used_topic, relative_path)

            # Update parent index
            self._update_index_for_path(recommended_path, used_topic, frontmatter.summary)

            # Check if optimization is needed
            if llm_response and llm_response.optimize_suggested:
                self.optimize(usr_id)

            return used_topic

        return None

    def _update_index_for_path(self, folder_path: str, topic: str, summary: str) -> None:
        """Update the appropriate index file for a folder.

        Args:
            folder_path: Relative folder path (e.g., "coding/python")
            topic: Topic name
            summary: One-line summary
        """
        parts = folder_path.split("/")

        # Update root index if storing directly
        if len(parts) == 1:
            self._append_to_index(self.root_index_path, topic, summary)
        else:
            # Create/update sub-index
            sub_index_path = self.storage_path / folder_path / "index.md"
            ensure_dir_exists(sub_index_path.parent)

            if not sub_index_path.exists():
                metadata = {"title": f"Index: {folder_path.replace('/', ' > ')}"}
                content = f"# {folder_path.replace('/', ' > ')}\n\n"
                write_markdown_file(sub_index_path, metadata, content)

            self._append_to_index(sub_index_path, topic, summary)

    def _append_to_index(self, index_path: Path, topic: str, summary: str) -> None:
        """Append an entry to an index file.

        Args:
            index_path: Path to the index file
            topic: Topic name
            summary: One-line summary
        """
        metadata, content = read_markdown_file(index_path)
        topic_title = parse_topic_title(topic)
        new_entry = f"- **{topic_title}**: {summary}\n"

        if new_entry not in content:
            content += new_entry
            write_markdown_file(index_path, metadata, content)

    def retrieve(self, usr_id: str) -> str:
        """Retrieve the root index (knowledge tree overview).

        Args:
            usr_id: User ID

        Returns:
            Content of root index.md
        """
        metadata, content = read_markdown_file(self.root_index_path)
        return content

    def get(self, usr_id: str, topic: str) -> Optional[str]:
        """Get full content of a specific topic.

        Args:
            usr_id: User ID
            topic: Topic identifier

        Returns:
            Full content (frontmatter + markdown) or None if not found
        """
        relative_path = self.registry.get(topic)
        if not relative_path:
            return None

        file_path = self.storage_path / relative_path
        if not file_path.exists():
            return None

        metadata, content = read_markdown_file(file_path)

        # Return frontmatter + content
        import frontmatter as fm

        post = fm.Post(content, **metadata)
        return fm.dumps(post)

    def delete(self, usr_id: str, topic: str) -> bool:
        """Delete a topic from memory.

        Args:
            usr_id: User ID
            topic: Topic identifier

        Returns:
            True if successful
        """
        relative_path = self.registry.get(topic)
        if not relative_path:
            return False

        file_path = self.storage_path / relative_path
        try:
            if file_path.exists():
                file_path.unlink()
            self.registry.delete(topic)

            # Update index files
            self._prune_from_indexes(topic, file_path)

            return True
        except Exception as e:
            print(f"Error deleting {topic}: {e}")
            return False

    def _prune_from_indexes(self, topic: str, file_path: Path) -> None:
        """Remove topic from all relevant index files.

        Args:
            topic: Topic identifier
            file_path: File path (to find parent folders)
        """
        topic_title = parse_topic_title(topic)
        pattern = re.compile(rf"- \*\*{re.escape(topic_title)}\*\*: .+\n?")

        # Update parent folder index if exists
        parent_index = file_path.parent / "index.md"
        if parent_index.exists():
            metadata, content = read_markdown_file(parent_index)
            new_content = pattern.sub("", content).strip()
            if new_content:
                write_markdown_file(parent_index, metadata, new_content)

        # Also check root index
        if self.root_index_path.exists():
            metadata, content = read_markdown_file(self.root_index_path)
            new_content = pattern.sub("", content).strip()
            if new_content:
                write_markdown_file(self.root_index_path, metadata, new_content)

    def optimize(self, usr_id: str) -> None:
        """Optimize the knowledge tree structure.

        Args:
            usr_id: User ID
        """
        # Analyze root index
        metadata, content = read_markdown_file(self.root_index_path)
        lines = content.strip().split("\n")

        if len(lines) <= self.optimize_threshold:
            return

        # Filter topics by usr_id
        user_topics = []
        all_topics = self.registry.list_all()
        for topic, relative_path in all_topics.items():
            file_path = self.storage_path / relative_path
            if file_path.exists():
                fm_meta, _ = read_markdown_file(file_path)
                if fm_meta.get("user_id") == usr_id:
                    parent_dir = str(Path(relative_path).parent)
                    if parent_dir == ".":
                        parent_dir = "(root)"
                    user_topics.append(
                        {
                            "topic": topic,
                            "current_path": parent_dir,
                            "summary": fm_meta.get("summary", ""),
                        }
                    )

        if not user_topics:
            return

        # Call LLM to suggest optimization
        context = {
            "user_topics": user_topics,
            "total_root_lines": len(lines),
            "threshold": self.optimize_threshold,
        }

        llm_response = self._get_llm_decision("optimize", context)

        if llm_response:
            self._apply_optimization(llm_response)
            self._compress_root_index()

    def _apply_optimization(self, llm_response: LLMResponse) -> None:
        """Apply optimization recommendations from LLM.

        Args:
            llm_response: LLM response with optimization suggestions.
                The `reason` field should be a JSON array of move operations:
                [{"topic": "...", "new_path": "...", "summary": "..."}, ...]
        """
        try:
            moves = json.loads(llm_response.reason or "[]")
        except json.JSONDecodeError:
            print("Optimization: could not parse LLM move recommendations")
            return

        for move in moves:
            topic = move.get("topic")
            new_path = move.get("new_path")
            summary = move.get("summary", "")

            if not topic or not new_path:
                continue

            old_relative = self.registry.get(topic)
            if not old_relative:
                continue

            old_file = self.storage_path / old_relative
            if not old_file.exists():
                continue

            # Create new directory
            new_dir = self.storage_path / new_path
            ensure_dir_exists(new_dir)

            # Move file
            new_file = new_dir / old_file.name
            shutil.move(str(old_file), str(new_file))

            # Update registry
            new_relative = str(new_file.relative_to(self.storage_path))
            self.registry.put(topic, new_relative)

            # Prune old index entry
            self._prune_from_indexes(topic, old_file)

            # Update/create new sub-index
            self._update_index_for_path(new_path, topic, summary)

    def _compress_root_index(self) -> None:
        """Compress root index by replacing sub-folder entries with folder links.

        Only compresses folders that have 3+ markdown files (excluding index.md).
        Walks the directory tree recursively to find qualifying directories.
        """
        metadata, content = read_markdown_file(self.root_index_path)

        # Walk directory tree to find directories with index.md and 3+ md files
        compressible_dirs = []
        for dirpath, dirnames, filenames in sorted(os.walk(str(self.storage_path))):
            dir_path = Path(dirpath)
            # Skip root and hidden dirs
            if dir_path == self.storage_path:
                continue
            if any(part.startswith(".") for part in dir_path.relative_to(self.storage_path).parts):
                continue

            sub_index = dir_path / "index.md"
            if sub_index.exists():
                md_files = [f for f in dir_path.glob("*.md") if f.name != "index.md"]
                if len(md_files) >= 3:
                    relative = dir_path.relative_to(self.storage_path)
                    compressible_dirs.append(str(relative))

        if not compressible_dirs:
            return

        # Rebuild root index: keep header + non-list lines, replace individual entries with folder links
        lines = content.strip().split("\n")
        header_lines = []
        for line in lines:
            if line.startswith("- "):
                break
            header_lines.append(line)

        new_lines = header_lines + [""]

        for dirpath in compressible_dirs:
            # Use the first segment as the top-level category name
            top_level = dirpath.split("/")[0].split("\\")[0]
            title = top_level.replace("_", " ").title()
            index_link = f"{dirpath}/index.md".replace("\\", "/")
            new_lines.append(f"- **{title}/**: See [{title} index]({index_link})")

        metadata["updated_at"] = datetime.now().isoformat()
        write_markdown_file(self.root_index_path, metadata, "\n".join(new_lines))

    def list_topics(self) -> Dict[str, str]:
        """List all topics in the registry.

        Returns:
            Dictionary of topic ID -> path mappings
        """
        return self.registry.list_all()
