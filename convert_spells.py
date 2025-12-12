import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).parent
INPUT = ROOT / "all-spells.json"
OUTPUT_DIR = ROOT / "spell-output"



def strip_markup(text: str) -> str:
    if not text:
        return ""

    # Pattern matches {@cmd text|source} and captures the visible text part.
    pattern = re.compile(r"\{@[^\s}]+\s+([^|}]+)(?:\|[^}]*)?}")

    # Replace each markup instance with just the inner display text.
    return pattern.sub(lambda m: m.group(1), text)

LEVEL_NAMES = {
    0: "Cantrip",
    1: "1stLevel",
    2: "2ndLevel",
    3: "3rdLevel",
    4: "4thLevel",
    5: "5thLevel",
    6: "6thLevel",
    7: "7thLevel",
    8: "8thLevel",
    9: "9thLevel",
}


def format_time(spell):
    t = (spell.get("time") or [{}])[0]
    number = t.get("number")
    unit = t.get("unit", "").lower()
    if unit == "action":
        code = "A"
    elif unit == "bonus action":
        code = "BA"
    elif unit == "reaction":
        code = "R"
    elif unit == "minute":
        code = "Min"
    elif unit == "hour":
        code = "Hr"
    else:
        code = unit or "?"
    return f"{number}{code}" if number else code


def format_range(spell):
    r = spell.get("range") or {}
    dist = r.get("distance") or {}
    rtype = r.get("type")
    dtype = dist.get("type")
    amount = dist.get("amount")

    if dtype == "self":
        return "Self"
    if dtype == "touch":
        return "Touch"
    if dtype == "feet" and amount:
        return f"{amount} ft."
    return rtype or "Unknown"


def format_components(spell):
    comps = spell.get("components") or {}
    parts = []
    material_detail = None
    if comps.get("v"):
        parts.append("V")
    if comps.get("s"):
        parts.append("S")
    m = comps.get("m")
    if m:
        parts.append("M*")
        try:
            material_detail = strip_markup(m['text'])
        except (KeyError, TypeError):
            material_detail = strip_markup(str(m))
    return ", ".join(parts) or "None", material_detail


def format_duration(spell):
    d = (spell.get("duration") or [{}])[0]
    dtype = d.get("type")
    if dtype == "instant":
        return "Instant", False
    if dtype == "permanent":
        return "Permanent", False
    if dtype == "timed":
        dur = d.get("duration") or {}
        amount = dur.get("amount")
        unit = dur.get("type", "").lower()
        if unit == "round":
            unit_name = "Round" if amount == 1 else "Rounds"
        elif unit == "minute":
            unit_name = "Minute" if amount == 1 else "Minutes"
        elif unit == "hour":
            unit_name = "Hour" if amount == 1 else "Hours"
        else:
            unit_name = unit
        text = f"{amount} {unit_name}" if amount else unit_name
        conc = bool(d.get("concentration"))
        return text, conc
    return "Unknown", False


def is_ritual(spell):
    meta = spell.get("meta") or {}
    return bool(meta.get("ritual"))


def is_upcastable(spell):
    return bool(spell.get("entriesHigherLevel"))


def build_tags(spell):
    tags = ["Spell"]
    level = spell.get("level", 0)
    tags.append(LEVEL_NAMES.get(level, f"Level{level}"))
    if is_ritual(spell):
        tags.append("Ritual")
    if is_upcastable(spell):
        tags.append("Upcastable")
    return tags


def spell_to_markdown(spell) -> str:
    tags = build_tags(spell)
    time_str = format_time(spell)
    range_str = format_range(spell)
    comp_str, material_detail = format_components(spell)
    duration_str, conc = format_duration(spell)
    ritual_flag = "Yes" if is_ritual(spell) else "No"
    conc_flag = "Yes" if conc else "No"

    entries = spell.get("entries") or []

    def flatten_entries(items):
        parts = []
        for it in items:
            if isinstance(it, str):
                parts.append(it)
            elif isinstance(it, dict) and it.get("type") == "entries":
                inner = it.get("entries") or []
                parts.extend(flatten_entries(inner))
        return parts

    flat_entries = flatten_entries(entries)
    desc_text = "\n\n".join(strip_markup(e) for e in flat_entries)

    lines = ["---", "tags:"]
    for t in tags:
        lines.append(f"  - {t}")
    lines.extend([
        f"Time: {time_str}",
        f"range: {range_str}",
        f"Components: {comp_str}",
        f"Duration: {duration_str}",
        f"Concentration: {conc_flag}",
        f"Ritual: {ritual_flag}",
        "---",
        desc_text.strip(),
    ])

    if material_detail:
        lines.append("")
        lines.append(f"* {material_detail}")

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    with INPUT.open("r", encoding="utf-8") as f:
        spells = json.load(f)

    for spell in spells:
        name = spell.get("name", "unnamed")
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "-", name).strip("-") or "spell"
        md = spell_to_markdown(spell)
        out_path = OUTPUT_DIR / f"{safe_name}.md"
        with out_path.open("w", encoding="utf-8") as outf:
            outf.write(md)


if __name__ == "__main__":
    main()
