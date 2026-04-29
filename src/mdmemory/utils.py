"""Utility functions for MdMemory."""

import json
import os
import hashlib
from pathlib import Path
from typing import Any, Dict, Tuple
import frontmatter as fm
import aiofiles
import portalocker
import asyncio


async def load_json_safe(filepath: Path) -> Dict[str, Any]:
    """Load JSON file with error handling and locking."""
    if not filepath.exists():
        return {}
    try:
        async with aiofiles.open(filepath, mode="r", encoding="utf-8") as f:
            # We use a thread for locking to avoid blocking the event loop
            def read_with_lock():
                with open(filepath, "r", encoding="utf-8") as lf:
                    portalocker.lock(lf, portalocker.LOCK_SH)
                    return json.load(lf)

            return await asyncio.to_thread(read_with_lock)
    except (json.JSONDecodeError, IOError, Exception) as e:
        print(f"Error loading {filepath}: {e}")
        return {}


async def save_json_safe(filepath: Path, data: Dict[str, Any]) -> bool:
    """Save JSON file with error handling and locking."""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)

        def write_with_lock():
            with open(filepath, "w", encoding="utf-8") as lf:
                portalocker.lock(lf, portalocker.LOCK_EX)
                json.dump(data, lf, indent=2, ensure_ascii=False)

        await asyncio.to_thread(write_with_lock)
        return True
    except (IOError, Exception) as e:
        print(f"Error saving {filepath}: {e}")
        return False


async def read_markdown_file(filepath: Path) -> Tuple[dict, str]:
    """Read Markdown file with frontmatter (async)."""
    if not filepath.exists():
        return {}, ""
    try:
        async with aiofiles.open(filepath, mode="r", encoding="utf-8") as f:
            content = await f.read()
            post = fm.loads(content)
            return post.metadata, post.content
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return {}, ""


async def write_markdown_file(filepath: Path, metadata: dict, content: str) -> bool:
    """Write Markdown file with frontmatter and locking."""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        post = fm.Post(content, **metadata)
        dumped = fm.dumps(post)

        def write_with_lock():
            with open(filepath, "w", encoding="utf-8") as lf:
                portalocker.lock(lf, portalocker.LOCK_EX)
                lf.write(dumped)

        await asyncio.to_thread(write_with_lock)
        return True
    except Exception as e:
        print(f"Error writing {filepath}: {e}")
        return False


def ensure_dir_exists(dirpath: Path) -> bool:
    """Ensure directory exists (sync is fine for this)."""
    try:
        dirpath.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {dirpath}: {e}")
        return False


def parse_topic_title(filename: str) -> str:
    """Convert filename (e.g., 'python.md') to title (e.g., 'Python')."""
    return filename.replace(".md", "").replace("_", " ").title()


async def line_count(filepath: Path) -> int:
    """Count lines in a file (async)."""
    try:
        count = 0
        async with aiofiles.open(filepath, mode="r", encoding="utf-8") as f:
            async for _ in f:
                count += 1
        return count
    except Exception:
        return 0


def generate_fallback_topic(query: str) -> str:
    """Generate a hash-based fallback topic ID."""
    clean_query = query.strip()[:100].lower()
    hash_part = hashlib.md5(query.encode()).hexdigest()[:8]
    prefix = "".join(e for e in clean_query[:20] if e.isalnum() or e == "_")
    if not prefix:
        prefix = "topic"
    return f"{prefix}_{hash_part}"
