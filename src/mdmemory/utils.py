"""Utility functions for MdMemory."""

import json
import os
from pathlib import Path
from typing import Any, Dict
import frontmatter as fm


def load_json_safe(filepath: Path) -> Dict[str, Any]:
    """Load JSON file with error handling."""
    if not filepath.exists():
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading {filepath}: {e}")
        return {}


def save_json_safe(filepath: Path, data: Dict[str, Any]) -> bool:
    """Save JSON file with error handling."""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Error saving {filepath}: {e}")
        return False


def read_markdown_file(filepath: Path) -> tuple[dict, str]:
    """Read Markdown file with frontmatter.

    Returns (frontmatter_dict, content)
    """
    if not filepath.exists():
        return {}, ""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            post = fm.load(f)
        return post.metadata, post.content
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return {}, ""


def write_markdown_file(filepath: Path, metadata: dict, content: str) -> bool:
    """Write Markdown file with frontmatter."""
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        post = fm.Post(content, **metadata)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(fm.dumps(post))
        return True
    except Exception as e:
        print(f"Error writing {filepath}: {e}")
        return False


def ensure_dir_exists(dirpath: Path) -> bool:
    """Ensure directory exists."""
    try:
        dirpath.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {dirpath}: {e}")
        return False


def parse_topic_title(filename: str) -> str:
    """Convert filename (e.g., 'python.md') to title (e.g., 'Python')."""
    return filename.replace(".md", "").replace("_", " ").title()


def line_count(filepath: Path) -> int:
    """Count lines in a file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0
