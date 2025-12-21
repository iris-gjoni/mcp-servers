# Task State MCP Server

A Model Context Protocol (MCP) server for managing task state. This server allows you to create, list, update, and delete tasks, persisting them in a SQLite database.

## Tools

- `add_task(description: str, priority: str = "medium", tags: str = "") -> str`: Add a new task with optional priority and tags.
- `list_tasks(status: Optional[str] = None, tag: Optional[str] = None) -> str`: List tasks, optionally filtered by status or tag.
- `update_task(task_id: int, status: Optional[str] = None, priority: Optional[str] = None, tags: Optional[str] = None) -> str`: Update a task's status, priority, or tags.
- `delete_task(task_id: int) -> str`: Delete a task by ID.

## Configuration

- `TASK_DB_FILE`: Path to the SQLite database file (default: `tasks.db`).

## Usage

Run the server:

```bash
python server.py
```

