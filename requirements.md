# MdMemory Requirements Specification

## 1. Overview
MdMemory is a Markdown-first, LLM-driven memory framework designed to organize agent knowledge into a hierarchical **Knowledge Tree**. The primary goal is to provide a human-readable, persistent memory backend for AI agents.

## 2. Functional Requirements

| ID | Requirement Name | Description | Priority |
|:---|:---|:---|:---|
| **R1** | **Knowledge Storage** | | |
| R1.1 | Content Format | All memories MUST be stored as standard Markdown (`.md`) files. | Critical |
| R1.2 | Metadata | Each memory MUST include YAML frontmatter containing at least a topic ID, summary, and user ID. | Critical |
| R1.3 | Automatic Categorization | The system MUST use an LLM to automatically determine the logical storage path and generate metadata if not explicitly provided. | High |
| R1.4 | Topic Persistence | The system MUST maintain a mapping between logical Topic IDs and physical file paths to ensure consistent retrieval. | Critical |
| **R2** | **Knowledge Retrieval** | | |
| R2.1 | Topic Access | Users MUST be able to retrieve the full content of a topic using its Topic ID. | Critical |
| R2.2 | Knowledge Tree View | The system MUST provide a root index that gives an overview of all stored knowledge. | High |
| R2.3 | Multi-User Isolation | Retrieval and optimization MUST be scoped to specific User IDs. | High |
| R2.4 | Native Search | The system MUST support keyword search across topic IDs, summaries, and tags. | High |
| **R3** | **Structural Optimization** | | |
| R3.1 | Auto-Organization | The system SHOULD periodically reorganize the knowledge tree to keep it manageable. | Medium |
| R3.2 | Threshold Trigger | Optimization MUST be triggered when the root index exceeds a configurable line count (default: 20). | Medium |
| R3.3 | Index Compression | When a directory contains 3+ knowledge files, the root index MUST compress individual entries into a single folder link. | Medium |
| R3.4 | Scalable Optimization | The optimization process MUST use a sliding window/batching approach to stay within LLM token limits. | High |
| **R4** | **Model Context Protocol (MCP)** | | |
| R4.1 | Multi-Transport Support | The system MUST support both `stdio` and `SSE` transport protocols for MCP communication. | High |
| R4.2 | MCP Tools | The system MUST expose core functions (`store`, `search`, `get`, `delete`, `optimize`) as MCP Tools. | Critical |
| R4.3 | MCP Resources | The system MUST expose stored memories as MCP Resources using a `mdmemory://` URI scheme. | Medium |
| R4.4 | MCP Prompts | The system MUST provide pre-defined MCP Prompts for common memory interactions. | Low |
| R4.5 | Startup Configuration | The MCP server MUST allow setting the `usr_id` via environment variables or CLI arguments at startup. | High |

## 3. Non-Functional Requirements

| Category | ID | Requirement Description |
|:---|:---|:---|
| **Readability** | N1 | The storage structure and file contents MUST remain easily navigable and readable by a human using a standard file explorer or Markdown editor. |
| **Performance** | N2.1 | The system MUST use asynchronous I/O (`async/await`) for all file operations to ensure non-blocking execution. |
| | N2.2 | The system SHOULD load the topic registry into memory at startup for O(1) lookups. |
| **Reliability** | N3.1 | Every write operation MUST ensure that the physical file, the registry mapping, and the relevant index files are kept in sync. |
| | N3.2 | The system MUST provide a robust hash-based fallback mechanism for topic ID generation if the LLM fails. |
| | N3.3 | The system MUST implement mandatory file locking for registry and index updates to ensure data integrity in concurrent environments. |
| **Compatibility** | N4 | The system MUST support Python 3.9+ and be compatible with major OS platforms (Windows, Linux, macOS). |
