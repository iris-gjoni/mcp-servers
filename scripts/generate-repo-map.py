import os
import sys

def generate_md_tree(root_dir='.', output_file='file_structure.md'):
    """
    Generates a Markdown file with the recursive file structure starting from the given root directory.
    Includes the root folder name at the top level.
    """
    root_base = os.path.basename(os.path.abspath(root_dir)) or '.'  # Get the name of the root folder
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# File Structure\n\n")
        # Start with the root folder
        f.write(f"- {root_base}/\n")
        for root, dirs, files in os.walk(root_dir):
            # Calculate indentation level relative to root_dir
            rel_root = os.path.relpath(root, root_dir)
            level = rel_root.count(os.sep) if rel_root != '.' else 0
            indent = '  ' * (level + 1)  # +1 because we started with root at level 0
            # Write subdirectories (but os.walk handles recursion, so we write files here)
            # Actually, for dirs, we need to write them as we encounter
            if level > 0:  # Skip writing the root again
                dir_name = os.path.basename(root)
                f.write(f"{indent}- {dir_name}/\n")
            subindent = '  ' * (level + 2)
            for file in sorted(files):  # Sort for consistency
                f.write(f"{subindent}- {file}\n")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, 'file_structure.md')
    root_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    generate_md_tree(root_dir, output_file)
