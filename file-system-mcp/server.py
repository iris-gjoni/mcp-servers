import os
import glob
import shutil
import fnmatch
import logging
import sys
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("file-system-mcp")

mcp = FastMCP("Filesystem Server")

# Configuration
# By default, we restrict to the current working directory for safety,
# but this can be configured via env var to point to the large external codebase.
ROOT_DIR = os.path.abspath(os.environ.get("FS_ROOT", os.getcwd()))

if not os.path.exists(ROOT_DIR):
    logger.warning(f"Root directory {ROOT_DIR} does not exist. Creating it.")
    try:
        os.makedirs(ROOT_DIR)
    except Exception as e:
        logger.critical(f"Failed to create root directory {ROOT_DIR}: {e}")
        sys.exit(1)

def _is_safe_path(path: str) -> bool:
    """Ensure path is within ROOT_DIR."""
    # Resolve absolute paths
    try:
        abs_path = os.path.abspath(os.path.join(ROOT_DIR, path))
        abs_root = os.path.abspath(ROOT_DIR)
        return abs_path.startswith(abs_root)
    except Exception:
        return False

def _get_abs_path(path: str) -> str:
    return os.path.abspath(os.path.join(ROOT_DIR, path))

# --- Exploration Tools ---

@mcp.tool()
def list_directory(path: str = ".") -> str:
    """List contents of a directory with type information."""
    if not _is_safe_path(path):
        return "Error: Access denied."

    abs_path = _get_abs_path(path)
    if not os.path.exists(abs_path):
        return "Error: Path does not exist."

    if not os.path.isdir(abs_path):
        return "Error: Path is not a directory."

    items = []
    try:
        with os.scandir(abs_path) as it:
            for entry in it:
                type_str = "DIR " if entry.is_dir() else "FILE"
                items.append(f"{type_str} {entry.name}")
    except Exception as e:
        logger.error(f"Error listing directory {path}: {e}")
        return f"Error listing directory: {e}"

    return "\n".join(sorted(items))

@mcp.tool()
def get_file_info(path: str) -> str:
    """Get size and modification time of a file."""
    if not _is_safe_path(path):
        return "Error: Access denied."

    abs_path = _get_abs_path(path)
    if not os.path.exists(abs_path):
        return "Error: File not found."

    try:
        stats = os.stat(abs_path)
        size_mb = stats.st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(stats.st_mtime).isoformat()
        return f"Size: {stats.st_size} bytes ({size_mb:.2f} MB)\nModified: {mtime}"
    except Exception as e:
        logger.error(f"Error getting info for {path}: {e}")
        return f"Error getting info: {e}"

# --- Reading Tools ---

@mcp.tool()
def read_file(path: str, start_line: int = 1, end_line: int = -1) -> str:
    """
    Read content of a file. Supports line ranges (1-based).
    If end_line is -1, reads to the end.
    """
    if not _is_safe_path(path):
        return "Error: Access denied."

    abs_path = _get_abs_path(path)
    if not os.path.isfile(abs_path):
        return "Error: Not a file."

    try:
        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        total_lines = len(lines)
        if start_line < 1: start_line = 1
        if end_line == -1 or end_line > total_lines: end_line = total_lines

        # Adjust for 0-based indexing
        selected_lines = lines[start_line-1 : end_line]
        content = "".join(selected_lines)

        return f"--- File: {path} ({start_line}-{end_line}/{total_lines}) ---\n{content}"
    except Exception as e:
        logger.error(f"Error reading file {path}: {e}")
        return f"Error reading file: {e}"

@mcp.tool()
def search_files(path: str = ".", pattern: str = "*") -> str:
    """Find files by glob pattern (e.g. *.py)."""
    if not _is_safe_path(path):
        return "Error: Access denied."

    abs_path = _get_abs_path(path)
    results = []
    try:
        # Using glob with recursive=True if pattern contains **
        search_pattern = os.path.join(abs_path, pattern)
        recursive = "**" in pattern

        files = glob.glob(search_pattern, recursive=recursive)

        # Filter to ensure they are within root (glob might follow symlinks)
        valid_files = [f for f in files if _is_safe_path(os.path.relpath(f, ROOT_DIR))]

        # Return relative paths
        results = [os.path.relpath(f, ROOT_DIR) for f in valid_files]
    except Exception as e:
        logger.error(f"Error searching files in {path}: {e}")
        return f"Error searching files: {e}"

    return "\n".join(results[:100]) + ("\n... (truncated)" if len(results) > 100 else "")

@mcp.tool()
def grep_search(query: str, path: str = ".") -> str:
    """
    Search for a string content within files in a directory (recursive).
    Returns file paths and matching lines.
    """
    if not _is_safe_path(path):
        return "Error: Access denied."

    abs_path = _get_abs_path(path)
    results = []

    try:
        # Walk through directory
        for root, dirs, files in os.walk(abs_path):
            for file in files:
                file_path = os.path.join(root, file)

                # Skip binary or large files check could go here

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            if query in line:
                                rel_path = os.path.relpath(file_path, ROOT_DIR)
                                results.append(f"{rel_path}:{i+1}: {line.strip()}")
                                if len(results) >= 50: # Limit results
                                    return "\n".join(results) + "\n... (limit reached)"
                except:
                    continue # Skip unreadable files

    except Exception as e:
        logger.error(f"Error during grep in {path}: {e}")
        return f"Error during grep: {e}"

    return "\n".join(results) if results else "No matches found."

# --- Manipulation Tools ---

@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Create or overwrite a file."""
    if not _is_safe_path(path):
        return "Error: Access denied."

    abs_path = _get_abs_path(path)
    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Wrote to file {path}")
        return f"Successfully wrote to {path}"
    except Exception as e:
        logger.error(f"Error writing file {path}: {e}")
        return f"Error writing file: {e}"

@mcp.tool()
def replace_in_file(path: str, old_text: str, new_text: str) -> str:
    """Replace a specific string in a file."""
    if not _is_safe_path(path):
        return "Error: Access denied."

    abs_path = _get_abs_path(path)
    if not os.path.isfile(abs_path):
        return "Error: File not found."

    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if old_text not in content:
            return "Error: old_text not found in file."

        new_content = content.replace(old_text, new_text)

        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        logger.info(f"Replaced text in {path}")
        return f"Successfully replaced text in {path}"
    except Exception as e:
        logger.error(f"Error replacing text in {path}: {e}")
        return f"Error replacing text: {e}"

@mcp.tool()
def create_directory(path: str) -> str:
    """Create a new directory."""
    if not _is_safe_path(path):
        return "Error: Access denied."

    abs_path = _get_abs_path(path)
    try:
        os.makedirs(abs_path, exist_ok=True)
        logger.info(f"Created directory {path}")
        return f"Created directory {path}"
    except Exception as e:
        logger.error(f"Error creating directory {path}: {e}")
        return f"Error creating directory: {e}"

@mcp.tool()
def move_file(source: str, destination: str) -> str:
    """Move or rename a file."""
    if not _is_safe_path(source) or not _is_safe_path(destination):
        return "Error: Access denied."

    abs_src = _get_abs_path(source)
    abs_dest = _get_abs_path(destination)

    try:
        os.makedirs(os.path.dirname(abs_dest), exist_ok=True)
        shutil.move(abs_src, abs_dest)
        logger.info(f"Moved {source} to {destination}")
        return f"Moved {source} to {destination}"
    except Exception as e:
        logger.error(f"Error moving file {source} to {destination}: {e}")
        return f"Error moving file: {e}"

if __name__ == "__main__":
    logger.info(f"Filesystem Server running on root: {ROOT_DIR}")
    mcp.run()
