import os
import pathlib

def create_context_files(base_dir: str, output_dir: str, max_depth: int = 2, whitelist: list = None, blacklist: list = None):
    """
    Generates a single context file containing contents of all files up to a specified depth,
    respecting whitelist and blacklist patterns.

    Args:
        base_dir: The root directory to start traversing from.
        output_dir: The directory where the context file will be saved.
        max_depth: The maximum depth of subdirectories to traverse.
        whitelist: A list of patterns to include (takes precedence over blacklist).
        blacklist: A list of patterns to exclude.
    """
    base_path = pathlib.Path(base_dir)
    output_path = pathlib.Path(output_dir)

    # Create the output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # Create a single context file
    context_file_path = output_path / "context.md"

    # Initialize list to hold all file contents
    all_file_contents = []

    # Normalize whitelist and blacklist to Path objects for easier comparison
    if whitelist:
        whitelist = [pathlib.Path(p) for p in whitelist]
    if blacklist:
        blacklist = [pathlib.Path(p) for p in blacklist]

    # Process each depth level
    for current_depth in range(1, max_depth + 1):
        print(f"Processing directories at depth: {current_depth}")
        for dir_path in base_path.glob("*/" * current_depth):
            if dir_path.is_dir():
                # Skip hidden directories (those starting with .) at any level
                dir_relative = dir_path.relative_to(base_path)
                if any(part.startswith('.') for part in dir_relative.parts):
                    print(f"  Skipping hidden directory: {dir_path}")
                    continue
                
                print(f"  Processing directory: {dir_path}")

                for file_path in dir_path.rglob("*"):  # rglob for recursive within this dir
                    if file_path.is_file():
                        # Added skip check for system directories unlikely to hold key business context files
                        relative_parts = file_path.relative_to(base_path).parts
                        if any(part in {'.venv', '__pycache__', '.git', 'context', 'blog_automation.egg-info'} for part in relative_parts):
                            continue

                        # Whitelist check (takes precedence)
                        if whitelist:
                            whitelisted = False
                            for pattern in whitelist:
                                if file_path.match(str(pattern)):
                                    whitelisted = True
                                    break
                            if not whitelisted:
                                continue  # Skip this file

                        # Blacklist check
                        if blacklist:
                            blacklisted = False
                            for pattern in blacklist:
                                if file_path.match(str(pattern)):
                                    blacklisted = True
                                    break
                            if blacklisted:
                                continue  # Skip this file
                        
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                file_content = f.read()

                            # Append file content with Markdown formatting
                            all_file_contents.append(f"## File: {file_path.relative_to(base_path)}\n\n```\n{file_content}\n```\n")

                        except Exception as e:
                            print(f"    Error reading file {file_path}: {e}")
                            all_file_contents.append(f"## File: {file_path.relative_to(base_path)}\n\nCould not read file content.\n")

    # Write all contents to a single context file
    try:
        with open(context_file_path, "w", encoding="utf-8") as context_file:
            context_file.write("\n".join(all_file_contents))
        print(f"Generated context file: {context_file_path}")
    except Exception as e:
        print(f"Error writing context file {context_file_path}: {e}")


if __name__ == "__main__":
    base_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up two levels
    context_directory = os.path.join(base_directory, "context")

    print(f"Base directory: {base_directory}")
    print(f"Output context directory: {context_directory}")

    # Example usage with whitelist and blacklist
    whitelist = ["*.py", "*.md"]  # Only include Python and Markdown files
    blacklist = [
        "*/venv/*",
        "*/.venv/*",         # Added pattern to exclude ".venv" directories
        "*__pycache__*",
        "*/.git/*",
        "blog_automation.egg-info",
        "*/context/*"
    ] # Exclude venv, __pycache__, .git, and context directories

    create_context_files(base_directory, context_directory, whitelist=whitelist, blacklist=blacklist)
