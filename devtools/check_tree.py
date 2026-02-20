# === UNIVERSAL DEVTOOLS HEADER ===
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# === END UNIVERSAL DEVTOOLS HEADER ===

import os

def print_tree(start_path, prefix=""):
    files = sorted(os.listdir(start_path))
    for i, name in enumerate(files):
        path = os.path.join(start_path, name)
        connector = "└── " if i == len(files) - 1 else "├── "
        print(prefix + connector + name)
        if os.path.isdir(path):
            extension = "    " if i == len(files) - 1 else "│   "
            print_tree(path, prefix + extension)

if __name__ == "__main__":
    print_tree(".")
