import os
import sqlite3
import logging
import sys
from datetime import datetime
from typing import Optional
from mcp.server.fastmcp import FastMCP

# Configure logging to stderr to avoid interfering with MCP protocol on stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("task-state-mcp")

mcp = FastMCP("Task State Server")

# Configuration
# Ensure we use an absolute path for the database
DB_FILE = os.path.abspath(os.environ.get("TASK_DB_FILE", "tasks.db"))

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        # Ensure directory exists
        db_dir = os.path.dirname(DB_FILE)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logger.info(f"Created directory for database: {db_dir}")

        conn = get_db_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'todo',
                priority TEXT DEFAULT 'medium',
                tags TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migration for existing tables (idempotent)
        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'medium'")
        except sqlite3.OperationalError:
            pass # Column likely exists

        try:
            conn.execute("ALTER TABLE tasks ADD COLUMN tags TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass # Column likely exists

        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {DB_FILE}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

VALID_PRIORITIES = {'low', 'medium', 'high'}
VALID_STATUSES = {'todo', 'in_progress', 'done'}

@mcp.tool()
def add_task(description: str, priority: str = "medium", tags: str = "") -> str:
    """
    Add a new task.
    priority: low, medium, high
    tags: comma-separated strings (e.g. "bug,ui")
    """
    if priority not in VALID_PRIORITIES:
        return f"Error: Invalid priority '{priority}'. Must be one of: {', '.join(VALID_PRIORITIES)}"

    try:
        conn = get_db_connection()
        cursor = conn.execute(
            "INSERT INTO tasks (description, priority, tags) VALUES (?, ?, ?)",
            (description, priority, tags)
        )
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"Added task {task_id}")
        return f"Task added with ID: {task_id}"
    except Exception as e:
        logger.error(f"Error adding task: {e}")
        return f"Error adding task: {str(e)}"

@mcp.tool()
def list_tasks(status: Optional[str] = None, tag: Optional[str] = None) -> str:
    """List tasks, optionally filtered by status or tag."""
    try:
        conn = get_db_connection()
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        if tag:
            query += " AND tags LIKE ?"
            params.append(f"%{tag}%")

        query += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, created_at DESC"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "No tasks found."

        result = []
        for row in rows:
            tags_display = f" [{row['tags']}]" if row['tags'] else ""
            result.append(f"[{row['id']}] {row['status'].upper()} ({row['priority']}){tags_display}: {row['description']}")
        return "\n".join(result)
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return f"Error listing tasks: {str(e)}"

@mcp.tool()
def update_task(task_id: int, status: Optional[str] = None, priority: Optional[str] = None, tags: Optional[str] = None) -> str:
    """Update a task's status, priority, or tags."""
    if status and status not in VALID_STATUSES:
         return f"Error: Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}"

    if priority and priority not in VALID_PRIORITIES:
        return f"Error: Invalid priority '{priority}'. Must be one of: {', '.join(VALID_PRIORITIES)}"

    try:
        conn = get_db_connection()

        updates = []
        params = []

        if status:
            updates.append("status = ?")
            params.append(status)
        if priority:
            updates.append("priority = ?")
            params.append(priority)
        if tags is not None:
            updates.append("tags = ?")
            params.append(tags)

        if not updates:
            return "No updates specified."

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(task_id)

        sql = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"

        cursor = conn.execute(sql, params)
        row_count = cursor.rowcount
        conn.commit()
        conn.close()

        if row_count > 0:
            logger.info(f"Updated task {task_id}")
            return f"Task {task_id} updated."
        else:
            return f"Task {task_id} not found."
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        return f"Error updating task: {str(e)}"

@mcp.tool()
def delete_task(task_id: int) -> str:
    """Delete a task by ID."""
    try:
        conn = get_db_connection()
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        row_count = cursor.rowcount
        conn.commit()
        conn.close()

        if row_count > 0:
            logger.info(f"Deleted task {task_id}")
            return f"Task {task_id} deleted."
        else:
            return f"Task {task_id} not found."
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}")
        return f"Error deleting task: {str(e)}"

if __name__ == "__main__":
    try:
        init_db()
        mcp.run()
    except Exception as e:
        logger.critical(f"Server failed to start: {e}")
        sys.exit(1)
