import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_FULL_PATH = ROOT / "specialists" / "template" / "specialist_template_full.py"
TEMPLATE_DEBUG_PATH = ROOT / "specialists" / "template" / "specialist_template_debug.py"
DEFINITIONS_PATH = ROOT / "specialists" / "spec_definitions.json"
OUTPUT_DIR = ROOT / "specialists"


def load_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_definitions():
    return json.loads(DEFINITIONS_PATH.read_text(encoding="utf-8"))


def generate_specialist(template: str, spec: dict) -> str:
    domain_focus_items = spec.get("domain_focus", []) or []
    domain_focus_text = "\n".join(f"- {item}" for item in domain_focus_items) or "- (diagnostic role)"

    func_name = f"run_{spec['specialist_key']}_specialist"
    optional_section_title = spec.get("optional_section_title", "Additional Insights")

    return (
        template
        .replace("TEMPLATE SPECIALIST", spec["name"])
        .replace("[EDIT THIS LIST PER SPECIALIST]", domain_focus_text)
        .replace("Optional Section", optional_section_title)
        .replace("FUNCTION_NAME", func_name)
    )


def write_specialist(filename: str, content: str):
    path = OUTPUT_DIR / filename
    path.write_text(content, encoding="utf-8")
    print(f"[OK] Wrote {path}")


def main():
    definitions = load_definitions()

    template_full = load_template(TEMPLATE_FULL_PATH)
    template_debug = load_template(TEMPLATE_DEBUG_PATH)

    for spec in definitions:
        template_type = spec.get("template_type", "full")
        template = template_debug if template_type == "debug" else template_full

        content = generate_specialist(template, spec)
        write_specialist(spec["filename"], content)


if __name__ == "__main__":
    main()
