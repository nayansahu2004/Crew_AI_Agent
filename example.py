

import os

folder_path = r"E:\Programming\Crew_AI_Agent"

EXCLUDE_FOLDERS = {
    "node_modules",
    "__pycache__",
}

for root, dirs, files in os.walk(folder_path):

    # Exclude folders starting with "." and explicitly excluded folders
    dirs[:] = [
        d for d in dirs
        if not d.startswith(".")
        and d not in EXCLUDE_FOLDERS
    ]

    level = root.replace(folder_path, "").count(os.sep)
    indent = "    " * level

    print(f"{indent}{os.path.basename(root)}/")

    # Keep ALL files, including .env and .gitignore
    for file in files:
        print(f"{indent}    {file}")