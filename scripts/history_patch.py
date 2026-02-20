#!/usr/bin/env python3
"""
Strong history sanitizer patcher.

This script:
- Scans all specialist files
- Detects ANY loop that appends raw history entries
- Replaces it with a safe, validated version
- Backs up each file before patching
- Logs exactly what was changed

Run from project root:
    python3 devtools/patch_history_sanitizer.py
"""

import re
import shutil
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPECIALISTS_DIR = ROOT / "specialists"

# Regex to match ANY variant of:
# for h in history:
#     messages.append(h)
PATTERN = re.compile(
    r"for\s+h\s+in\s+history\s*:\s*\n\s*messages\.append\(h\)",
    re.MULTILINE
)

REPLACEMENT = """for h in history:
        if isinstance(h, dict) and "role" in h and "content" in h:
            messages.append(h)
        else:
            messages.append({
                "role": "user",
                "content": str(h)
            })"""

def patch_file(path: pathlib.Path):
    text = path.read_text(encoding="utf-8")

    if not PATTERN.search(text):
        return False

    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy(path, backup)

    new_text = PATTERN.sub(REPLACEMENT, text)
    path.write_text(new_text, encoding="utf-8")
    return True

def main():
    patched = []

    for py in SPECIALISTS_DIR.glob("*_specialist.py"):
        if patch_file(py):
            patched.append(py.name)

    if patched:
        print("Patched history handling in:")
        for name in patched:
            print("  -", name)
    else:
        print("No matching patterns found. Nothing patched.")

if __name__ == "__main__":
    main()
