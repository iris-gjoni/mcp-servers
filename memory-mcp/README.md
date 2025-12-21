# Memory MCP Server

A Model Context Protocol (MCP) server that provides memory storage and retrieval capabilities with semantic search.

## Features

- **Persistent Storage**: Uses SQLite to store memories.
- **Semantic Search**: Uses `sentence-transformers` to enable semantic search over memories.
- **Tools**:
  - `add_memory(content)`: Store a new memory.
  - `list_memories(limit)`: List recent memories.
  - `search_memories(query, limit)`: Search memories by content (semantic or keyword).
  - `delete_memory(memory_id)`: Delete a memory.

## Dependencies

- `mcp`
- `numpy`
- `sentence-transformers` (optional, for semantic search)
- `scikit-learn` (optional, for cosine similarity if not using numpy directly, though the code uses numpy)

## Configuration

- `MEMORY_FILE`: Path to the SQLite database file (default: `memory.db`).

