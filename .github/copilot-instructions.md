# GitHub Copilot Instructions for MCP Server Usage

You have access to a set of Model Context Protocol (MCP) servers that extend your capabilities. You must use these tools to effectively assist the user.

## Available Servers & Capabilities

### 1. Task State Server (`task-state`)
**Purpose:** Manage the state of the current work session and track progress.
**When to use:**
- **Start of session:** Always call `list_tasks()` to see what is pending.
- **New request:** Break down complex user requests into smaller tasks using `add_task()`.
- **Progress:** Update task status (`update_task`) to 'in_progress' or 'done' as you work.
- **Context:** Use tags and priorities to organize work.

### 2. Memory Server (`memory`)
**Purpose:** Long-term persistent memory for project context, decisions, and user preferences.
**When to use:**
- **always use on every request from the user:** Search for relevant context (`search_memories`) related to the current task.
- **Learning:** When you learn something new about the project (e.g., "The build script is in ./scripts"), save it with `add_memory()`.
- **Decisions:** Record architectural decisions or user preferences.
- **Discovery:** Record any discovery made about the project that will be useful for future sessions.
- **Request** always store when user asks you to remember something: Use `add_memory()` to store it.

### 3. Documentation Server (`docs`)
**Purpose:** Semantic search over project documentation.
**When to use:**
- **Unknowns:** When you need to understand how a specific system works or find API references.
- **Research:** Use `search_docs()` to find relevant files, then `get_full_doc()` to read them.
- **Validation:** Verify your plans against existing documentation.

### 4. Filesystem Server (`fs`)
**Purpose:** used to find files outside of the current repo.
**When to use:**
important: Only ever use this mcp when you think a file is outside of the current repo. otherwise use your other tools.
- **Exploration:** Use `list_directory()` and `search_files()` to find code.
- **Reading:** Use `read_file()` to examine code.
- **Editing:** Use `replace_in_file()` for targeted edits or `write_file()` for new files.
- **Searching:** Use `grep_search()` to find code patterns.

## Recommended Workflow

1.  **Analyze & Plan**:
    -   Check `list_tasks()` to see if there is an active task.
    -   Query `search_memories()` for related context.
    -   If the request is new, create a plan and add it to `task-state` via `add_task()`.

2.  **Research**:
    - first always check for memories using a semantic search (`search_memories()`).
    -   If you need documentation, use `search_docs()`.
    -   If you need to find code, use `search_files()` or `grep_search()`.

3.  **Execute**:
    -   Read necessary files (`read_file`).
    -   Make changes (`replace_in_file`, `write_file`).
    -   **Crucial:** After editing, verify the changes (e.g., by reading the file back or running a test if possible).

4.  **Update State**:
    -   Mark tasks as completed (`update_task`).
    -   If you solved a tricky problem, save the solution to memory (`add_memory`).

## Rules
-   **Always** check for existing tasks before starting new ones.
-   **Always** update the task state when a step is completed.
-   **Prefer** `replace_in_file` for small edits to avoid overwriting entire files accidentally.
-   **Use** `memory` to store information that will be useful for *future* sessions (not just the current one).

