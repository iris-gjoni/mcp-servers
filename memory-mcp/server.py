import os
import sqlite3
import uuid
import logging
import sys
from datetime import datetime
from typing import Optional
import numpy as np
from mcp.server.fastmcp import FastMCP

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("memory-mcp")

# Conditional import for semantic search dependencies
try:
    from sentence_transformers import SentenceTransformer
    HAS_SEMANTIC_SEARCH = True
except ImportError:
    HAS_SEMANTIC_SEARCH = False
    logger.warning("sentence-transformers not found. Semantic search disabled.")

mcp = FastMCP("Memory Server")

# Configuration
MEMORY_FILE = os.path.abspath(os.environ.get("MEMORY_FILE", "memory.db"))
MODEL_NAME = "all-MiniLM-L6-v2"

# Global state
model = None

def get_db_connection():
    conn = sqlite3.connect(MEMORY_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        # Ensure directory exists
        db_dir = os.path.dirname(MEMORY_FILE)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logger.info(f"Created directory for database: {db_dir}")

        conn = get_db_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                embedding BLOB
            )
        """)
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {MEMORY_FILE}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def load_model():
    global model
    if HAS_SEMANTIC_SEARCH and model is None:
        logger.info(f"Loading model {MODEL_NAME}...")
        model = SentenceTransformer(MODEL_NAME)
        logger.info("Model loaded.")

def get_embedding(text: str) -> Optional[bytes]:
    if not HAS_SEMANTIC_SEARCH:
        return None
    load_model()
    embedding = model.encode([text])[0]
    return embedding.tobytes()

def decode_embedding(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)

@mcp.tool()
def add_memory(content: str) -> str:
    """Add a new memory."""
    try:
        memory_id = str(uuid.uuid4())
        embedding = get_embedding(content)

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO memories (id, content, embedding) VALUES (?, ?, ?)",
            (memory_id, content, embedding)
        )
        conn.commit()
        conn.close()
        logger.info(f"Added memory {memory_id}")
        return f"Memory added with ID: {memory_id}"
    except Exception as e:
        logger.error(f"Error adding memory: {e}")
        return f"Error adding memory: {str(e)}"

@mcp.tool()
def list_memories(limit: int = 10) -> str:
    """List recent memories."""
    try:
        conn = get_db_connection()
        cursor = conn.execute("SELECT id, content, created_at FROM memories ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "No memories found."

        result = []
        for row in rows:
            result.append(f"[{row['created_at']}] {row['id']}: {row['content']}")
        return "\n".join(result)
    except Exception as e:
        logger.error(f"Error listing memories: {e}")
        return f"Error listing memories: {str(e)}"

@mcp.tool()
def search_memories(query: str, limit: int = 5) -> str:
    """Search memories semantically (if available) or by keyword."""
    try:
        if HAS_SEMANTIC_SEARCH:
            load_model()
            query_embedding = model.encode([query])[0]

            conn = get_db_connection()
            cursor = conn.execute("SELECT id, content, created_at, embedding FROM memories WHERE embedding IS NOT NULL")
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return "No memories with embeddings found."

            memories = []
            embeddings = []

            for row in rows:
                memories.append(row)
                embeddings.append(decode_embedding(row['embedding']))

            if not embeddings:
                 return "No embeddings found."

            embeddings_matrix = np.vstack(embeddings)

            # Cosine similarity
            # Normalize query
            query_norm = np.linalg.norm(query_embedding)
            if query_norm > 0:
                query_embedding = query_embedding / query_norm

            # Normalize docs
            doc_norms = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)
            # Avoid division by zero
            doc_norms[doc_norms == 0] = 1
            embeddings_matrix = embeddings_matrix / doc_norms

            similarities = np.dot(embeddings_matrix, query_embedding)

            # Get top k
            top_indices = np.argsort(similarities)[::-1][:limit]

            results = []
            for idx in top_indices:
                score = similarities[idx]
                row = memories[idx]
                results.append(f"[{score:.2f}] {row['created_at']} - {row['content']}")

            return "\n".join(results)

        else:
            # Fallback to simple LIKE search
            conn = get_db_connection()
            cursor = conn.execute("SELECT id, content, created_at FROM memories WHERE content LIKE ? ORDER BY created_at DESC LIMIT ?", (f"%{query}%", limit))
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return "No matching memories found."

            result = []
            for row in rows:
                result.append(f"{row['created_at']} - {row['content']}")
            return "\n".join(result)
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        return f"Error searching memories: {str(e)}"

@mcp.tool()
def delete_memory(memory_id: str) -> str:
    """Delete a memory by ID."""
    try:
        conn = get_db_connection()
        cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        row_count = cursor.rowcount
        conn.commit()
        conn.close()

        if row_count > 0:
            logger.info(f"Deleted memory {memory_id}")
            return f"Memory {memory_id} deleted."
        else:
            return f"Memory {memory_id} not found."
    except Exception as e:
        logger.error(f"Error deleting memory {memory_id}: {e}")
        return f"Error deleting memory: {str(e)}"

if __name__ == "__main__":
    try:
        init_db()
        mcp.run()
    except Exception as e:
        logger.critical(f"Server failed to start: {e}")
        sys.exit(1)
