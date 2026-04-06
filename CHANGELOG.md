# Changelog

All notable changes to MdMemory will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2026-04-06

### Fixed
- Made model api key as optional

## [0.3.0] - 2026-04-05

### Breaking Changes
- **Removed callback pattern**: `llm_callback` parameter removed from `MdMemory.__init__`
- **Removed callback classes**: `LLMCallback`, `LiteLLMCallback`, `OpenAICallback`, `AnthropicCallback` removed
- `MdMemory.__init__` now requires `model_name` and `model_api_key` parameters directly

### Added
- Direct LiteLLM integration: `MdMemory` now uses `litellm.completion()` internally
- `model_name`, `model_api_key`, `model_base_url` parameters for LLM configuration
- `litellm` added as a required dependency

### Changed
- Simplified initialization: no callback boilerplate needed
- `MdMemoryService` updated to use new `model_name`/`model_api_key` params

## [0.2.0] - 2023-04-04

### Fixed
- removed litellm deps 
- update litellm callback to have api and url base for ease of use

## [0.1.0] - 2026-04-02

### Added
- Initial release of MdMemory
- Markdown-first, LLM-driven memory framework with hierarchical Knowledge Tree
- Hybrid indexing strategy with root and sub-indexes
- Path registry system for efficient topic lookup
- Full CRUD operations: store, retrieve, get, delete
- Auto-optimization of knowledge tree structure
- Comprehensive unit tests (15 tests)
- Full documentation in README and QUICKSTART

### Features
- Human-readable Markdown storage on filesystem
- LLM-organized automatic folder structure
- Context-aware hybrid indexing
- Efficient JSON registry for direct access
- Support for explicit and LLM-generated topic IDs
- Frontmatter metadata for each knowledge item
- Optional automatic tree optimization

## [Unreleased]

### Added
- User-scoped optimization: `optimize(usr_id)` now only reorganizes topics belonging to the specified user
- `user_id` field added to `FrontMatter` model for per-user topic tracking
- Automatic index compression: root index replaces individual entries with folder links when subdirectories reach 3+ files
- `_apply_optimization()`: moves files to LLM-recommended directories and updates registry/indexes
- `_compress_root_index()`: recursively walks directory tree to find qualifying folders and compresses root index
- **Google ADK Integration**: `MdMemoryService` implementing ADK's `BaseMemoryService`
  - `add_session_to_memory()`: converts ADK sessions to Markdown topics with LLM-generated semantic names
  - `add_events_to_memory()`: appends event deltas to existing session files with fast session-id caching
  - `add_memory()`: stores explicit `MemoryEntry` items as Markdown topics
  - `search_memory()`: fast keyword matching across frontmatter summaries with user_id filtering
- Optional `adk` dependency group: `pip install mdmemory[adk]`
- Conditional export of `MdMemoryService` in `__init__.py`

### Changed
- `store()` now persists `user_id` in frontmatter metadata for all stored topics
- `_get_llm_decision()` prompt updated for "optimize" action to return move operations as JSON array in `reason` field
- `_prune_from_indexes()` now uses regex for proper line removal instead of naive string replacement
- `optimize()` scans registry, filters topics by `usr_id` via frontmatter, and calls LLM with user-specific context

### Fixed
- `usr_id` parameter was previously unused; now properly tracked and utilized in optimization

### Planned
- Advanced search and filtering capabilities
- Export/import functionality
- Version history and reverting
- Collaboration features
- Semantic/vector search for `search_memory()`
