"""Core MdMemory implementation."""

import json
import os
import re
import shutil
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import litellm
import frontmatter as fm

from .models import FrontMatter, LLMResponse
from .registry import PathRegistry
from .utils import (
    ensure_dir_exists,
    parse_topic_title,
    read_markdown_file,
    save_json_safe,
    write_markdown_file,
    generate_fallback_topic,
    line_count,
)


class MdMemory:
    """Markdown-first, LLM-driven memory framework."""

    SYSTEM_PROMPT = """You are the MdMemory Librarian. Your goal is to maintain a clean, hierarchical Markdown Knowledge Tree. When storing data, choose a logical path. When optimizing, group related files into sub-directories to keep the root index under {threshold} lines. Always return JSON containing: `action`, `recommended_path`, `frontmatter`, and `optimize_suggested`."""

    def __init__(
        self,
        model_name: str,
        model_api_key: Optional[str] = None,
        model_base_url: Optional[str] = None,
        storage_path: str = "./MdMemory",
        optimize_threshold: int = 20,
    ):
        """Initialize MdMemory."""
        self._model_name = model_name
        self._model_api_key = model_api_key
        self._model_base_url = model_base_url
        self.storage_path = Path(storage_path)
        self.optimize_threshold = optimize_threshold

        # Initialize storage structure
        ensure_dir_exists(self.storage_path)

        # Load or create registry
        self.registry_path = self.storage_path / ".registry.json"
        self.registry = PathRegistry(self.registry_path)

        # Initialize root index path
        self.root_index_path = self.storage_path / "index.md"
        self._registry_loaded = False

    async def _ensure_initialized(self) -> None:
        """Ensure registry and root index are loaded/created."""
        if not self._registry_loaded:
            if not self.registry_path.exists():
                await save_json_safe(self.registry_path, {})
            await self.registry.load()
            if not self.root_index_path.exists():
                await self._init_root_index()
            self._registry_loaded = True

    async def _init_root_index(self) -> None:
        """Initialize the root index.md."""
        metadata = {
            "title": "MdMemory Root Index",
            "created_at": datetime.now().isoformat(),
        }
        content = "# Knowledge Tree\n\nWelcome to MdMemory. This is the root index.\n\n"
        await write_markdown_file(self.root_index_path, metadata, content)

    async def _call_llm(self, messages: list) -> str:
        """Call LiteLLM directly (async)."""
        kwargs = {
            "model": self._model_name,
            "messages": messages,
        }
        if self._model_base_url:
            kwargs["api_base"] = self._model_base_url
        if self._model_api_key:
            kwargs["api_key"] = self._model_api_key

        response = await litellm.acompletion(**kwargs)
        return response.choices[0].message.content

    async def _get_llm_decision(self, action: str, context: Dict[str, Any]) -> Optional[LLMResponse]:
        """Call LLM for organizational decisions."""
        try:
            system_prompt = self.SYSTEM_PROMPT.format(threshold=self.optimize_threshold)
            if action == "optimize":
                prompt = f"""
{system_prompt}

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
{system_prompt}

Action: {action}
Context: {json.dumps(context, indent=2)}

Please respond with a JSON object containing:
- action: The action being performed
- recommended_path: The logical folder path (e.g., "coding/python")
- frontmatter: Object with topic, summary, tags
- optimize_suggested: Boolean indicating if optimization is needed
"""

            messages = [{"role": "user", "content": prompt}]
            response_text = await self._call_llm(messages)

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

    async def store(self, usr_id: str, query: str, topic: Optional[str] = None) -> Optional[str]:
        """Store a memory item (async)."""
        await self._ensure_initialized()

        # Prepare context for LLM
        context = {"query": query, "user_id": usr_id}
        if topic:
            context["topic"] = topic
        else:
            context["topic"] = (
                "NOT_PROVIDED - Please generate a concise topic ID from the query content"
            )

        # Call LLM to determine folder path and frontmatter
        llm_response = await self._get_llm_decision("store", context)

        if not llm_response:
            # Fallback: use provided topic or generate hash-based one
            if topic:
                used_topic = topic
                recommended_path = "uncategorized"
            else:
                used_topic = generate_fallback_topic(query)
                recommended_path = "uncategorized"

            frontmatter = FrontMatter(
                topic=used_topic,
                summary=query[:100].strip(),
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
        success = await write_markdown_file(file_path, metadata, query)

        if success:
            # Update registry
            relative_path = str(file_path.relative_to(self.storage_path))
            await self.registry.put(used_topic, relative_path)

            # Update parent index
            await self._update_index_for_path(recommended_path, used_topic, frontmatter.summary)

            # Check if optimization is needed
            if llm_response and llm_response.optimize_suggested:
                await self.optimize(usr_id)

            return used_topic

        return None

    async def search(self, usr_id: str, query: str) -> List[Dict[str, Any]]:
        """Search topics by keyword matching (async).
        
        Matches against topic name, summary, and tags.
        """
        await self._ensure_initialized()
        query_words = set(w.lower() for w in re.split(r"\W+", query) if len(w) > 1)
        if not query_words:
            return []

        results = []
        all_topics = self.registry.list_all()

        for topic, relative_path in all_topics.items():
            file_path = self.storage_path / relative_path
            if not file_path.exists():
                continue

            meta, _ = await read_markdown_file(file_path)

            if meta.get("user_id") != usr_id:
                continue

            # Keyword match against topic, summary, and tags
            tags_str = " ".join(meta.get("tags", []))
            searchable = f"{topic} {meta.get('summary', '')} {tags_str}".lower()
            
            if any(w in searchable for w in query_words):
                results.append({
                    "topic": topic,
                    "summary": meta.get("summary", ""),
                    "tags": meta.get("tags", []),
                    "updated_at": meta.get("updated_at"),
                    "path": relative_path
                })
        
        return sorted(results, key=lambda x: x.get("updated_at", ""), reverse=True)

    async def _update_index_for_path(self, folder_path: str, topic: str, summary: str) -> None:
        """Update the appropriate index file for a folder."""
        parts = folder_path.strip("/").split("/") if folder_path and folder_path != "." else []

        # Update root index if storing directly
        if not parts:
            await self._append_to_index(self.root_index_path, topic, summary)
        else:
            # Create/update sub-index
            sub_index_path = self.storage_path / folder_path / "index.md"
            ensure_dir_exists(sub_index_path.parent)

            if not sub_index_path.exists():
                metadata = {"title": f"Index: {folder_path.replace('/', ' > ')}"}
                content = f"# {folder_path.replace('/', ' > ')}\n\n"
                await write_markdown_file(sub_index_path, metadata, content)

            await self._append_to_index(sub_index_path, topic, summary)

    async def _append_to_index(self, index_path: Path, topic: str, summary: str) -> None:
        """Append an entry to an index file."""
        metadata, content = await read_markdown_file(index_path)
        topic_title = parse_topic_title(topic)
        new_entry = f"- **{topic_title}**: {summary}\n"

        if new_entry not in content:
            content = content.rstrip() + "\n" + new_entry
            await write_markdown_file(index_path, metadata, content)

    async def retrieve(self, usr_id: str) -> str:
        """Retrieve the root index (knowledge tree overview)."""
        await self._ensure_initialized()
        _, content = await read_markdown_file(self.root_index_path)
        return content

    async def get(self, usr_id: str, topic: str) -> Optional[str]:
        """Get full content of a specific topic."""
        await self._ensure_initialized()
        relative_path = self.registry.get(topic)
        if not relative_path:
            return None

        file_path = self.storage_path / relative_path
        if not file_path.exists():
            return None

        metadata, content = await read_markdown_file(file_path)

        # Return frontmatter + content
        post = fm.Post(content, **metadata)
        return fm.dumps(post)

    async def delete(self, usr_id: str, topic: str) -> bool:
        """Delete a topic from memory."""
        await self._ensure_initialized()
        relative_path = self.registry.get(topic)
        if not relative_path:
            return False

        file_path = self.storage_path / relative_path
        try:
            if file_path.exists():
                file_path.unlink()
            await self.registry.delete(topic)

            # Recursive pruning from all indices
            await self._prune_from_indexes(topic, file_path)

            return True
        except Exception as e:
            print(f"Error deleting {topic}: {e}")
            return False

    async def _prune_from_indexes(self, topic: str, file_path: Path) -> None:
        """Remove topic from all relevant index files recursively."""
        topic_title = parse_topic_title(topic)
        pattern = re.compile(rf"- \*\*{re.escape(topic_title)}\*\*: .+\n?")

        current_dir = file_path.parent
        while current_dir.resolve() != self.storage_path.parent.resolve():
            index_path = current_dir / "index.md"
            if index_path.exists():
                metadata, content = await read_markdown_file(index_path)
                new_content = pattern.sub("", content).strip()
                if not new_content or new_content.strip() == f"# {current_dir.name.replace('_', ' ').title()}":
                     # If index is now empty (just title), maybe delete it? 
                     # For now, just write empty or keep header.
                     await write_markdown_file(index_path, metadata, new_content + "\n")
                else:
                    await write_markdown_file(index_path, metadata, new_content + "\n")
            
            if current_dir.resolve() == self.storage_path.resolve():
                break
            current_dir = current_dir.parent

    async def optimize(self, usr_id: str) -> None:
        """Optimize the knowledge tree structure using sliding window batches."""
        await self._ensure_initialized()
        
        # Check root index threshold
        count = await line_count(self.root_index_path)
        if count <= self.optimize_threshold:
            return

        # Filter topics by usr_id
        user_topics = []
        all_topics = self.registry.list_all()
        for topic, relative_path in all_topics.items():
            file_path = self.storage_path / relative_path
            if file_path.exists():
                fm_meta, _ = await read_markdown_file(file_path)
                if fm_meta.get("user_id") == usr_id:
                    parent_dir = str(Path(relative_path).parent)
                    if parent_dir == ".":
                        parent_dir = "(root)"
                    user_topics.append({
                        "topic": topic,
                        "current_path": parent_dir,
                        "summary": fm_meta.get("summary", ""),
                    })

        if not user_topics:
            return

        # Sliding Window Optimization: Process in batches of 50 to avoid token limits
        batch_size = 50
        for i in range(0, len(user_topics), batch_size):
            batch = user_topics[i : i + batch_size]
            context = {
                "user_topics": batch,
                "batch_index": (i // batch_size) + 1,
                "total_batches": (len(user_topics) + batch_size - 1) // batch_size,
                "threshold": self.optimize_threshold,
            }

            llm_response = await self._get_llm_decision("optimize", context)
            if llm_response:
                await self._apply_optimization(llm_response)

        await self._compress_root_index()

    async def _apply_optimization(self, llm_response: LLMResponse) -> None:
        """Apply optimization recommendations from LLM."""
        try:
            moves = json.loads(llm_response.reason or "[]")
        except json.JSONDecodeError:
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
            await self.registry.put(topic, new_relative)

            # Prune from all indices recursively
            await self._prune_from_indexes(topic, old_file)

            # Update/create new sub-index
            await self._update_index_for_path(new_path, topic, summary)

    async def _compress_root_index(self) -> None:
        """Compress root index by replacing sub-folder entries with folder links."""
        metadata, content = await read_markdown_file(self.root_index_path)

        compressible_dirs = []
        for dirpath, _, _ in sorted(os.walk(str(self.storage_path))):
            dir_path = Path(dirpath)
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

        lines = content.strip().split("\n")
        header_lines = []
        for line in lines:
            if line.startswith("- "):
                break
            header_lines.append(line)

        new_lines = header_lines + [""]

        processed_top_levels = set()
        for dirpath in compressible_dirs:
            top_level = dirpath.split("/")[0].split("\\")[0]
            if top_level in processed_top_levels:
                continue
            
            title = top_level.replace("_", " ").title()
            index_link = f"{dirpath}/index.md".replace("\\", "/")
            new_lines.append(f"- **{title}/**: See [{title} index]({index_link})")
            processed_top_levels.add(top_level)

        metadata["updated_at"] = datetime.now().isoformat()
        await write_markdown_file(self.root_index_path, metadata, "\n".join(new_lines))

    def list_topics(self) -> Dict[str, str]:
        """List all topics in the registry."""
        return self.registry.list_all()
