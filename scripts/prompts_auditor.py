#!/usr/bin/env python3

from pathlib import Path

SPECIALISTS_DIR = Path("specialists")

REQUIRED_SECTIONS_FULL = [
    "### Role",
    "### Responsibilities",
    "### Fighter Lock and Subject Consistency",
    "### Use of Retrieved Context",
    "### Use of Memory",
    "### Hallucination Guard",
    "### Coordination with Other Specialists",
    "### Output Format (Hybrid Structured)"
]

REQUIRED_SECTIONS_DEBUG = [
    "### Role",
    "### Responsibilities",
    "### Output Format (Diagnostics)"
]

def audit_file(path: Path):
    text = path.read_text()
    issues = []

    is_debug = "DEBUG SPECIALIST" in text or "Diagnostics" in text
    required_sections = REQUIRED_SECTIONS_DEBUG if is_debug else REQUIRED_SECTIONS_FULL

    for section in required_sections:
        if section not in text:
            issues.append(f"Missing required section: '{section}'")

    if "###" not in text and "===" not in text:
        issues.append("No clear section headers")

    if len(text.split()) < 200 and not is_debug:
        issues.append("Prompt may be too short (<200 words)")

    return issues

def main():
    print("\n=== Specialist Prompt Audit Report ===\n")

    for file in SPECIALISTS_DIR.iterdir():
        if not file.name.endswith("_specialist.py"):
            continue
        if file.is_dir():
            continue

        issues = audit_file(file)

        print(f"[{file.name}]")
        if not issues:
            print("✓ All checks passed\n")
        else:
            for issue in issues:
                print(f"  ✗ {issue}")
            print()

    print("Audit complete.\n")

if __name__ == "__main__":
    main()
