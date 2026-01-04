import os
import glob
import logging
import sys
import numpy as np
from mcp.server.fastmcp import FastMCP
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("documentation-mcp")

# Initialize FastMCP server
mcp = FastMCP("Documentation Server")

# Configuration
script_dir = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.abspath(os.environ.get("DOCS_DIR", os.path.join(script_dir, "docs")))
REPO_MAP_DIR = os.path.abspath(os.path.join(script_dir, "..", "repo-map"))
MODEL_NAME = "all-MiniLM-L6-v2"

# Global state for the index
doc_index = []
doc_embeddings = None
model = None

def load_model():
    global model
    if model is None:
        logger.info(f"Loading model {MODEL_NAME}...")
        model = SentenceTransformer(MODEL_NAME)
        logger.info("Model loaded.")

def index_docs():
    global doc_index, doc_embeddings, model

    load_model()

    logger.info(f"Indexing documents in {DOCS_DIR}...")
    files = glob.glob(os.path.join(DOCS_DIR, "**/*.md"), recursive=True)

    new_index = []
    texts = []

    for fpath in files:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
                # Simple chunking could be added here, but for now we index the whole file or first N chars
                # For better semantic search, we might want to split by headers.
                # Here we just use the filename and content for the embedding.

                rel_path = os.path.relpath(fpath, DOCS_DIR)

                # Create a representation for embedding
                # We include the path and the content
                text_to_embed = f"Path: {rel_path}\nContent: {content[:1000]}"

                new_index.append({
                    "path": rel_path,
                    "full_path": fpath,
                    "preview": content[:200] + "..."
                })
                texts.append(text_to_embed)
        except Exception as e:
            logger.error(f"Error reading {fpath}: {e}")

    if not texts:
        logger.info("No documents found.")
        doc_index = []
        doc_embeddings = None
        return

    logger.info(f"Encoding {len(texts)} documents...")
    embeddings = model.encode(texts)

    # Normalize for cosine similarity
    norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
    doc_embeddings = embeddings / norm
    doc_index = new_index
    logger.info("Indexing complete.")

@mcp.tool()
def refresh_index():
    """Re-scans the documentation directory and updates the semantic index."""
    index_docs()
    return f"Indexed {len(doc_index)} documents."

@mcp.tool()
def search_docs(query: str, top_k: int = 5) -> str:
    """
    Semantically search the documentation for the given query.
    Returns a list of matching files with a short preview.
    """
    global doc_embeddings, doc_index, model

    if not doc_index:
        index_docs()
        if not doc_index:
            return "No documentation found to search."

    # Encode query
    query_vec = model.encode([query])
    query_norm = np.linalg.norm(query_vec, axis=1, keepdims=True)
    query_vec = query_vec / query_norm

    # Calculate similarity
    similarities = cosine_similarity(query_vec, doc_embeddings)[0]

    # Get top k
    top_indices = np.argsort(similarities)[::-1][:top_k]

    results = []
    for idx in top_indices:
        score = similarities[idx]
        doc = doc_index[idx]
        results.append(f"[{score:.2f}] {doc['path']}\nPreview: {doc['preview']}\n")

    return "\n---\n".join(results)

@mcp.tool()
def get_full_doc(path: str) -> str:
    """
    Retrieve the full content of a documentation file.
    The path should be one returned by search_docs.
    """
    # Security check to prevent directory traversal
    safe_path = os.path.normpath(os.path.join(DOCS_DIR, path))
    if not safe_path.startswith(os.path.abspath(DOCS_DIR)):
        return "Error: Access denied. Path is outside documentation directory."

    try:
        with open(safe_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Error: File not found."
    except Exception as e:
        logger.error(f"Error reading file {path}: {e}")
        return f"Error reading file: {str(e)}"

@mcp.tool()
def get_repo_map(project_name: str) -> str:
    """
    Retrieve the repo map for a given project by finding the corresponding .md file in the repo-map directory.
    Traverses the file structure to find the file named {project_name}.md.
    """
    logger.info(f"Searching for repo map for project: {project_name}")
    logger.info(f"REPO_MAP_DIR: {REPO_MAP_DIR}")
    files = glob.glob(os.path.join(REPO_MAP_DIR, "**/*.md"), recursive=True)
    logger.info(f"Files found: {files}")
    for f in files:
        basename = os.path.basename(f)
        logger.info(f"Checking file: {f}, basename: {basename}")
        if basename == f"{project_name}.md":
            logger.info(f"Match found: {f}")
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    content = file.read()
                    logger.info(f"Content length: {len(content)}")
                    return content
            except Exception as e:
                logger.error(f"Error reading {f}: {e}")
                return f"Error reading file: {str(e)}"
    logger.info(f"No repo map found for project {project_name}")
    return f"No repo map found for project {project_name}"

if __name__ == "__main__":
    # Ensure docs dir exists
    if not os.path.exists(DOCS_DIR):
        logger.info(f"Creating documentation directory: {DOCS_DIR}")
        os.makedirs(DOCS_DIR)
        # Create a dummy readme
        with open(os.path.join(DOCS_DIR, "README.md"), "w") as f:
            f.write("# Documentation\n\nThis is the root of the documentation.")

    # Initial index
    try:
        index_docs()
    except Exception as e:
        logger.warning(f"Warning: Initial indexing failed: {e}")

    mcp.run()
