# === UNIVERSAL DEVTOOLS HEADER ===
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# === END UNIVERSAL DEVTOOLS HEADER ===

import pkgutil
import importlib

def validate_package(package_name):
    print(f"\nValidating imports in package: {package_name}")
    try:
        package = importlib.import_module(package_name)
    except Exception as e:
        print(f"  ✘ Could not import package '{package_name}': {e}")
        return

    if not hasattr(package, "__path__"):
        print("  ✔ Single module imported successfully")
        return

    for _, module_name, _ in pkgutil.walk_packages(package.__path__, package_name + "."):
        try:
            importlib.import_module(module_name)
            print(f"  ✔ {module_name}")
        except Exception as e:
            print(f"  ✘ {module_name} — ERROR: {e}")

if __name__ == "__main__":
    print("=== Import Validation ===")

    validate_package("specialists")
    validate_package("tools")
    validate_package("router_agent")
    validate_package("supervisor")
    validate_package("orchestrator")
    validate_package("coordinator_agent")
    validate_package("critic_agent")

    print("\nDone.")
