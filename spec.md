# Specification: MdMemory Library (Phase 1)

## 1. Overview
`MdMemory` is a Markdown-first, LLM-driven memory framework that organizes agent knowledge into a **Knowledge Tree**. It prioritizes context efficiency by using a hierarchical folder structure and a "Hybrid Indexing" strategy, ensuring the agent only loads what is necessary.

### Core Philosophy
* **Human-Readable:** Data is stored as standard `.md` files on the local filesystem.
* **LLM-Organized:** The LLM decides where files go and when the tree needs reorganization.
* **Context-Aware:** Uses a central `index.md` for high-level navigation and a `.registry.json` (Path Map) for direct access.

---

## 2. Directory Structure
```text
/storage_root/
├── .registry.json           # Global Path Map (Topic ID -> Physical Path)
├── index.md                 # Root Knowledge Tree (Summaries & Links)
└── /categories/             # Dynamically created by LLM
    ├── coding/
    │   ├── index.md         # Sub-index for the coding branch
    │   └── python.md        # Actual knowledge leaf
    └── finance/
        └── taxes.md
```

---

## 3. API Definition

```python
class MdMemory:
    def __init__(self, llm: LiteLlm, storage_path: str, optimize_threshold: int = 20):
        """
        Initializes the memory. 
        - Loads the .registry.json.
        - Checks if index.md is 'heavy' and triggers optimize if needed.
        """
        pass

    def store(self, usr_id: str, topic: str, query: str) -> bool:
        """
        1. Calls LLM with 'System Prompt' to determine the best folder path and generate frontmatter.
        2. Saves content to `{storage_path}/{path}/{topic}.md`.
        3. Updates .registry.json with the new mapping.
        4. Appends a 1-sentence summary to the parent folder's index.md.
        5. If LLM flag 'optimize_suggested' is True, calls self.optimize().
        """
        pass

    def retrieve(self, usr_id: str) -> str:
        """
        Returns the content of the root index.md. 
        The agent uses this to 'browse' the memory tree.
        """
        pass

    def get(self, usr_id: str, topic: str) -> str:
        """
        1. Looks up the topic in .registry.json to find the physical path.
        2. Returns the full content (Frontmatter + Markdown) of the file.
        """
        pass

    def delete(self, usr_id: str, topic: str) -> bool:
        """
        Removes the file, updates the registry, and prunes the index.md.
        """
        pass

    def optimize(self, usr_id: str):
        """
        The 'Librarian' function:
        1. Analyzes the current index.md via LLM.
        2. If a folder is too large, LLM proposes a sub-folder structure.
        3. Physically moves files and updates .registry.json.
        4. Generates/Updates sub-indexes for newly created folders.
        5. Compresses the parent index.md to show only folder summaries.
        """
        pass
```

---

## 4. LLM Interaction Logic

### System Prompt for `LiteLlm`
The library must use this prompt for all organizational decisions:
> "You are the MdMemory Librarian. Your goal is to maintain a clean, hierarchical Markdown Knowledge Tree. When storing data, choose a logical path. When optimizing, group related files into sub-directories to keep the root index under 50 lines. Always return JSON containing: `path`, `summary`, `tags`, and `optimize_suggested`."

### Expected LLM Response Format (JSON)
```json
{
  "action": "store",
  "recommended_path": "coding/python/frameworks",
  "frontmatter": {
    "topic": "topic_id",
    "summary": "Brief description...",
    "tags": ["tag1", "tag2"]
  },
  "optimize_suggested": false
}
```

---

## 5. Implementation Details

### The Global Path Map (`.registry.json`)
A simple key-value store to decouple Topic IDs from their physical location.
* **Key:** `topic_id`
* **Value:** `relative/path/to/file.md`

### The Hybrid Indexing Strategy
* **Root `index.md`:** Contains top-level folders and standalone files. 
* **Sub-folder `index.md`:** Generated only when a folder exceeds the `optimize_threshold`. 
* **Compression:** When a folder is sub-indexed, the parent `index.md` removes the individual file links and replaces them with a single link to the folder's index.

### Auto-Refactor Logic
During `optimize()`, the LLM should cluster files.
* *Input:* List of file summaries in a "Heavy" folder.
* *Output:* "Move files [A, B, C] to new folder 'Sub-Category X'".
* *Action:* Python `shutil.move` is called, and the `.registry.json` is updated immediately to prevent broken links.

---

### Logic Checklist for the Developer:
- [ ] Ensure `LiteLlm` calls are asynchronous if possible for performance.
- [ ] Implement file-locking for the `.registry.json` to prevent corruption during concurrent `store` calls.
- [ ] Use `frontmatter` Python library for easy parsing of `.md` files.
