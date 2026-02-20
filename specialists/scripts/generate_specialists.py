import os

SPECIALISTS = [
    "style",
    "form",
    "sentiment",
    "weightcut",
    "metadata",
    "pace",
    "grappling",
    "scramble",
    "fightiq",
    "damage",
    "gameplan",
    "judging",
    "knowledge",
    "general"
]

template = open("specialists/_template.py").read()

for name in SPECIALISTS:
    code = template.replace("{NAME}", name)
    with open(f"specialists/{name}_specialist.py", "w") as f:
        f.write(code)

print("All specialists regenerated.")
