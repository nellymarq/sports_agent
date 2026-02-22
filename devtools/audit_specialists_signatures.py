# devtools/audit_specialists_signatures.py
"""
Audits all specialists to ensure their async run_* functions accept:
    - user_input
    - history
    - retrieved_context
    - semantic_memory
    - episodic_memory

Run:
    python devtools/audit_specialists_signatures.py
"""

import ast
from pathlib import Path

SPECIALISTS_DIR = Path("specialists")


def audit_specialist(path: Path):
    source = path.read_text()
    tree = ast.parse(source)

    target_params = {
        "user_input",
        "history",
        "retrieved_context",
        "semantic_memory",
        "episodic_memory",
    }

    found_issues = []

    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("run_"):
            param_names = {arg.arg for arg in node.args.args}
            missing = target_params - param_names

            if missing:
                found_issues.append(
                    f"  - {node.name} is missing params: {', '.join(sorted(missing))}"
                )
            else:
                found_issues.append(f"  - {node.name} OK")

    if not found_issues:
        print(f"[{path.name}] No async run_* functions found.")
    else:
        print(f"[{path.name}]")
        for line in found_issues:
            print(line)
    print()


def main():
    if not SPECIALISTS_DIR.exists():
        print("No 'specialists' directory found.")
        return

    for file in sorted(SPECIALISTS_DIR.glob("*.py")):
        audit_specialist(file)


if __name__ == "__main__":
    main()
