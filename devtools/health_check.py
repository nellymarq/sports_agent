# === UNIVERSAL DEVTOOLS HEADER ===
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# === END UNIVERSAL DEVTOOLS HEADER ===

import os

def run(cmd):
    print(f"\n=== Running: {cmd} ===")
    os.system(cmd)

if __name__ == "__main__":
    print("\n=== FULL PROJECT HEALTH CHECK ===\n")

    # Run devtools checks
    run("python3 devtools/check_tree.py")
    run("python3 devtools/validate_imports.py")

    # Run full pytest suite
    run("pytest -q")

    print("\n=== HEALTH CHECK COMPLETE ===")
