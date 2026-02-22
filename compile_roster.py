# -*- coding: utf-8 -*-
# compile_roster.py
# Reads male_fighters.json + female_fighters.json and generates data/compiled/fighter_roster_data.py

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from fighter_utils import FighterRecord, DIVISIONS, _normalize

RAW_MALE = Path("data/raw/male_fighters.json")
RAW_FEMALE = Path("data/raw/female_fighters.json")
OUT_PY = Path("data/compiled/fighter_roster_data.py")


# ---------------- Division normalization ----------------

DIVISION_NAME_MAP: Dict[str, str] = {
    "heavyweight": "mens_heavyweight",
    "light heavyweight": "mens_light_heavyweight",
    "middleweight": "mens_middleweight",
    "welterweight": "mens_welterweight",
    "lightweight": "mens_lightweight",
    "featherweight": "mens_featherweight",
    "bantamweight": "mens_bantamweight",
    "flyweight": "mens_flyweight",
    "women's strawweight": "womens_strawweight",
    "women's flyweight": "womens_flyweight",
    "women's bantamweight": "womens_bantamweight",
    "women's featherweight": "womens_featherweight",
}


def normalize_division(raw: str) -> str:
    if not raw:
        return ""

    key = raw.strip().lower()

    # Normalize ALL apostrophe variants
    for bad in ["’", "‘", "ʼ", "ʹ", "′", "`", "´"]:
        key = key.replace(bad, "'")

    # Normalize female division variants
    key = key.replace("women’s", "women's")
    key = key.replace("womens", "women's")
    key = key.replace("woman's", "women's")
    key = key.replace("female", "women's")

    # Remove double spaces
    key = re.sub(r"\s+", " ", key)

    # Normalize weight class words
    key = key.replace("fly weight", "flyweight")
    key = key.replace("bantam weight", "bantamweight")
    key = key.replace("feather weight", "featherweight")
    key = key.replace("light heavy weight", "light heavyweight")
    key = key.replace("middle weight", "middleweight")
    key = key.replace("welter weight", "welterweight")
    key = key.replace("light weight", "lightweight")
    key = key.replace("heavy weight", "heavyweight")

    # Handle abbreviations
    if key in ["w flyweight", "women's fly"]:
        key = "women's flyweight"
    if key in ["w bantamweight", "women's bantam"]:
        key = "women's bantamweight"
    if key in ["w strawweight", "women's straw"]:
        key = "women's strawweight"

    # Final lookup
    for k, v in DIVISION_NAME_MAP.items():
        if k in key:
            return v

    return ""


# ---------------- Helpers ----------------

def is_champion(name: str) -> bool:
    return "(c" in name.lower()


def clean_name(name: str) -> str:
    name = re.sub(r"\(c.*?\)", "", name, flags=re.IGNORECASE)
    name = name.replace("(c)", "")
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def parse_height_to_inches(height: str) -> int | None:
    if not height:
        return None
    m = re.search(r"(\d+)\s*ft\s*(\d+)\s*in", height)
    if not m:
        return None
    feet = int(m.group(1))
    inches = int(m.group(2))
    return feet * 12 + inches


def parse_record(record: str) -> str | None:
    if not record:
        return None
    return record.strip()


def build_aliases(name: str) -> List[str]:
    parts = name.split()
    aliases: List[str] = []
    lower_full = name.lower()
    aliases.append(lower_full)
    if len(parts) >= 2:
        first = parts[0].lower()
        last = parts[-1].lower()
        aliases.append(first)
        aliases.append(last)
        aliases.append(f"{first} {last}")
    return sorted(set(aliases))


def build_nicknames(nickname: str) -> List[str]:
    if not nickname:
        return []
    nick = nickname.strip()
    if not nick:
        return []
    return [nick.lower()]


# ---------------- Load & validate raw JSON ----------------

def load_raw() -> List[dict]:
    male = json.loads(RAW_MALE.read_text(encoding="utf-8"))
    female = json.loads(RAW_FEMALE.read_text(encoding="utf-8"))
    return male + female


def validate_raw(raw: List[dict]) -> None:
    errors = 0
    seen_names = set()

    for i, row in enumerate(raw, start=1):
        name = (row.get("name") or "").strip()
        div = (row.get("division") or "").strip()

        if not name:
            print(f"[ERROR] Entry {i}: missing name")
            errors += 1

        norm_name = _normalize(name)
        if norm_name in seen_names:
            print(f"[ERROR] Entry {i}: duplicate name '{name}'")
            errors += 1
        seen_names.add(norm_name)

        norm_div = normalize_division(div)
        if not norm_div:
            print(f"[ERROR] Entry {i}: cannot normalize division '{div}'")
            errors += 1
        elif norm_div not in DIVISIONS:
            print(f"[ERROR] Entry {i}: normalized division '{norm_div}' not in DIVISIONS")
            errors += 1

    if errors:
        raise ValueError(f"Validation failed with {errors} error(s)")
    print("[OK] Raw JSON validation passed.")


# ---------------- Build FighterRecord structures ----------------

def build_structures(raw: List[dict]):
    division_roster = {d: [] for d in DIVISIONS}
    nickname_map = {}
    alias_map = {}
    last_name_index = {}

    for row in raw:
        raw_name = (row.get("name") or "").strip()
        raw_div = (row.get("division") or "").strip()
        raw_nick = (row.get("nickname") or "") or ""
        raw_record = (row.get("mma_record") or "") or ""
        raw_height = (row.get("height") or "") or ""

        is_champ = is_champion(raw_name)
        name = clean_name(raw_name)
        division = normalize_division(raw_div)

        aliases = build_aliases(name)
        nicknames = build_nicknames(raw_nick)
        height_in = parse_height_to_inches(raw_height)
        record = parse_record(raw_record)

        fighter = FighterRecord(
            canonical_name=name,
            division=division,
            aliases=aliases,
            nicknames=nicknames,
            is_champion=is_champ,
            ufc_id=None,
            rank=None,
            reach_in=None,
            height_in=height_in,
            stance=None,
            dob=None,
            record=record,
            metadata={
                "country": row.get("country"),
                "age": row.get("age"),
            },
        )

        division_roster[division].append(fighter)

        for n in nicknames:
            nickname_map[n] = fighter

        for a in aliases:
            alias_map[a] = fighter

        parts = name.split()
        if parts:
            last = _normalize(parts[-1])
            last_name_index.setdefault(last, []).append(fighter)

    return division_roster, nickname_map, alias_map, last_name_index


# ---------------- Serialization ----------------

def serialize_fighter(f: FighterRecord) -> str:
    import json

    def q(s):
        return "None" if s is None else json.dumps(s)

    def qlist(lst):
        return "[" + ", ".join(json.dumps(x) for x in lst) + "]"

    return (
        "FighterRecord("
        f"canonical_name={q(f.canonical_name)}, "
        f"division={q(f.division)}, "
        f"aliases={qlist(f.aliases)}, "
        f"nicknames={qlist(f.nicknames)}, "
        f"is_champion={f.is_champion}, "
        f"ufc_id={q(f.ufc_id)}, "
        f"rank={f.rank}, "
        f"reach_in={f.reach_in}, "
        f"height_in={f.height_in}, "
        f"stance={q(f.stance)}, "
        f"dob={q(f.dob)}, "
        f"record={q(f.record)}, "
        f"metadata={json.dumps(f.metadata)}"
        ")"
    )


def write_output(division_roster, nickname_map, alias_map, last_name_index):
    lines = []
    lines.append("# -*- coding: utf-8 -*-")
    lines.append("from fighter_utils import FighterRecord\n")

    lines.append("DIVISION_ROSTER = {")
    for div, fighters in division_roster.items():
        lines.append(f"    '{div}': [")
        for f in fighters:
            lines.append(f"        {serialize_fighter(f)},")
        lines.append("    ],")
    lines.append("}\n")

    lines.append("NICKNAME_MAP = {")
    for nick, f in nickname_map.items():
        lines.append(f"    {json.dumps(nick)}: {serialize_fighter(f)},")
    lines.append("}\n")

    lines.append("ALIAS_MAP = {")
    for alias, f in alias_map.items():
        lines.append(f"    {json.dumps(alias)}: {serialize_fighter(f)},")
    lines.append("}\n")

    lines.append("LAST_NAME_INDEX = {")
    for last, fighters in last_name_index.items():
        lines.append(f"    {json.dumps(last)}: [")
        for f in fighters:
            lines.append(f"        {serialize_fighter(f)},")
        lines.append("    ],")
    lines.append("}\n")

    OUT_PY.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Wrote {OUT_PY}")


def main():
    raw = load_raw()
    validate_raw(raw)
    div_roster, nick_map, alias_map, last_index = build_structures(raw)
    write_output(div_roster, nick_map, alias_map, last_index)


if __name__ == "__main__":
    main()
