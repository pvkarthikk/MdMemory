"""Data models for MdMemory."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FrontMatter(BaseModel):
    """Frontmatter metadata for Markdown files."""

    topic: str
    summary: str
    tags: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    custom: Dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Expected response from LLM for organizational decisions."""

    action: str  # "store", "optimize", etc.
    recommended_path: str
    frontmatter: FrontMatter
    optimize_suggested: bool = False
    reason: Optional[str] = None
