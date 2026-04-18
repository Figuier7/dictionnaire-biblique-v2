#!/usr/bin/env python3
"""
Parse HebrewStrong.xml + BrownDriverBriggs.xml + LexicalIndex.xml
into a single enriched JSON file (English).

Output: hebrew-lexicon-en.json
Structure per entry:
{
  "strong": "H175",
  "hebrew": "אַהֲרוֹן",
  "xlit": "ʼAhărôwn",
  "pron": "a-har-one'",
  "pos": "n-pr-m",
  "lang": "heb",
  "source": "...",           # etymology from Strong's
  "definition_short": "...", # <meaning>/<def> from Strong's
  "definition_full": "...",  # flat text from BDB entry
  "usage": "...",            # from Strong's <usage>
  "bdb_id": "a.bn.ab",
  "twot": "35",
  "bdb_senses": [...],       # parsed sense tree from BDB
  "refs": ["Gen.1.1", ...],  # biblical refs from BDB
  "etymology": {...}         # from LexicalIndex
}
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

NS = "http://openscriptures.github.com/morphhb/namespace"
NS_MAP = {"os": NS}

BASE_DIR = Path(__file__).resolve().parent.parent / "HebrewLexicon-master"
STRONG_FILE = BASE_DIR / "HebrewStrong.xml"
BDB_FILE = BASE_DIR / "BrownDriverBriggs.xml"
LI_FILE = BASE_DIR / "LexicalIndex.xml"
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "hebrew-lexicon-en.json"


# ─── Utility: extract all text from an element, stripping sub-tags ───
def text_content(el):
    """Recursively extract all text from an element and its children."""
    if el is None:
        return ""
    parts = []
    if el.text:
        parts.append(el.text)
    for child in el:
        # For <w src="H6">6</w> → "6"
        # For <ref r="Gen.1.1">Gn 1:1</ref> → "Gn 1:1"
        # For <def>father</def> → "father"
        # For <foreign>...</foreign> → "..."
        parts.append(text_content(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts).strip()


def clean_text(s):
    """Normalize whitespace and clean up text."""
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s).strip()
    # Remove leading/trailing punctuation artifacts
    s = re.sub(r"^[;,.\s—–-]+", "", s)
    s = re.sub(r"[;,.\s—–-]+$", "", s)
    return s


# ─── 1. Parse Strong's ───
def parse_strongs():
    """Parse HebrewStrong.xml → dict keyed by Strong number (int)."""
    print("Parsing HebrewStrong.xml...")
    tree = ET.parse(str(STRONG_FILE))
    root = tree.getroot()
    entries = {}

    for entry in root.findall(f"{{{NS}}}entry"):
        eid = entry.get("id", "")  # e.g. "H175"
        if not eid.startswith("H"):
            continue
        num = int(eid[1:])

        w = entry.find(f"{{{NS}}}w")
        hebrew = w.text if w is not None and w.text else ""
        pos = w.get("pos", "") if w is not None else ""
        pron = w.get("pron", "") if w is not None else ""
        xlit = w.get("xlit", "") if w is not None else ""
        lang = w.get(f"{{{NS.replace('namespace','namespace')}}}lang", "")
        # Try xml:lang
        if not lang:
            lang = w.get("{http://www.w3.org/XML/1998/namespace}lang", "") if w is not None else ""

        source_el = entry.find(f"{{{NS}}}source")
        source_text = clean_text(text_content(source_el))

        meaning_el = entry.find(f"{{{NS}}}meaning")
        meaning_text = clean_text(text_content(meaning_el))

        # Extract <def> tags specifically from <meaning>
        defs = []
        if meaning_el is not None:
            for d in meaning_el.findall(f"{{{NS}}}def"):
                if d.text:
                    defs.append(d.text.strip())

        usage_el = entry.find(f"{{{NS}}}usage")
        usage_text = clean_text(text_content(usage_el))

        entries[num] = {
            "strong": eid,
            "hebrew": hebrew,
            "xlit": xlit,
            "pron": pron,
            "pos": pos,
            "lang": lang,
            "source": source_text,
            "definition_short": meaning_text,
            "defs": defs,  # individual <def> values
            "usage": usage_text,
        }

    print(f"  → {len(entries)} Strong entries parsed")
    return entries


# ─── 2. Parse LexicalIndex ───
def parse_lexical_index():
    """Parse LexicalIndex.xml → dict keyed by Strong number (int)."""
    print("Parsing LexicalIndex.xml...")
    tree = ET.parse(str(LI_FILE))
    root = tree.getroot()
    index = {}

    for part in root.findall(f"{{{NS}}}part"):
        part_lang = part.get("{http://www.w3.org/XML/1998/namespace}lang", "heb")

        for entry in part.findall(f"{{{NS}}}entry"):
            li_id = entry.get("id", "")

            w = entry.find(f"{{{NS}}}w")
            xlit_li = w.get("xlit", "") if w is not None else ""

            pos_el = entry.find(f"{{{NS}}}pos")
            pos_li = pos_el.text.strip() if pos_el is not None and pos_el.text else ""

            def_el = entry.find(f"{{{NS}}}def")
            def_li = def_el.text.strip() if def_el is not None and def_el.text else ""

            etym_el = entry.find(f"{{{NS}}}etym")
            etymology = {}
            if etym_el is not None:
                etymology["type"] = etym_el.get("type", "")
                etymology["root"] = etym_el.get("root", "")
                etymology["related"] = etym_el.text.strip() if etym_el.text else ""

            # Process xref(s) — there can be multiple
            for xref in entry.findall(f"{{{NS}}}xref"):
                strong_str = xref.get("strong", "")
                if not strong_str:
                    continue
                try:
                    strong_num = int(strong_str)
                except ValueError:
                    continue

                bdb_id = xref.get("bdb", "")
                twot = xref.get("twot", "")

                record = {
                    "li_id": li_id,
                    "xlit_li": xlit_li,
                    "pos_li": pos_li,
                    "def_li": def_li,
                    "bdb_id": bdb_id,
                    "twot": twot,
                    "etymology": etymology if etymology.get("type") else {},
                    "lang": part_lang,
                }

                # Keep first (most specific) match per Strong number
                if strong_num not in index:
                    index[strong_num] = record

    print(f"  → {len(index)} LexicalIndex entries with Strong refs")
    return index


# ─── 3. Parse BDB ───
def parse_sense(sense_el):
    """Recursively parse a BDB <sense> element into a dict."""
    sense = {}
    n = sense_el.get("n", "")
    if n:
        sense["n"] = n

    # Stem (Qal, Pi, Hiph, etc.)
    stem_el = sense_el.find(f"{{{NS}}}stem")
    if stem_el is not None and stem_el.text:
        sense["stem"] = stem_el.text.strip()

    # Aspect (Pf, Impf, Inf, Pt, etc.)
    asp_el = sense_el.find(f"{{{NS}}}asp")
    if asp_el is not None and asp_el.text:
        sense["aspect"] = asp_el.text.strip()

    # Definition
    def_el = sense_el.find(f"{{{NS}}}def")
    if def_el is not None:
        sense["def"] = clean_text(text_content(def_el))

    # All <def> tags in this sense level (not in sub-senses)
    defs = []
    for d in sense_el.findall(f"{{{NS}}}def"):
        t = clean_text(text_content(d))
        if t:
            defs.append(t)
    if defs:
        sense["defs"] = defs

    # Biblical references
    refs = []
    for ref in sense_el.findall(f"{{{NS}}}ref"):
        r = ref.get("r", "")
        if r:
            refs.append(r)
    if refs:
        sense["refs"] = refs

    # Full text content of this sense (for definition_full)
    sense["text"] = clean_text(text_content(sense_el))

    # Sub-senses
    sub_senses = []
    for child_sense in sense_el.findall(f"{{{NS}}}sense"):
        sub_senses.append(parse_sense(child_sense))
    if sub_senses:
        sense["senses"] = sub_senses

    return sense


def parse_bdb():
    """Parse BrownDriverBriggs.xml → dict keyed by BDB entry id."""
    print("Parsing BrownDriverBriggs.xml...")
    tree = ET.parse(str(BDB_FILE))
    root = tree.getroot()
    entries = {}

    for part in root.findall(f"{{{NS}}}part"):
        for section in part.findall(f"{{{NS}}}section"):
            for entry in section.findall(f"{{{NS}}}entry"):
                eid = entry.get("id", "")
                cite = entry.get("cite", "")
                entry_type = entry.get("type", "")
                mod = entry.get("mod", "")

                # Extract word
                w = entry.find(f"{{{NS}}}w")
                hebrew_bdb = text_content(w) if w is not None else ""

                # Extract POS
                pos_el = entry.find(f"{{{NS}}}pos")
                pos_bdb = clean_text(text_content(pos_el)) if pos_el is not None else ""

                # Extract top-level defs
                top_defs = []
                for d in entry.findall(f"{{{NS}}}def"):
                    t = clean_text(text_content(d))
                    if t:
                        top_defs.append(t)

                # Extract all references at entry level
                all_refs = []
                for ref in entry.iter(f"{{{NS}}}ref"):
                    r = ref.get("r", "")
                    if r:
                        all_refs.append(r)

                # Parse senses
                senses = []
                for sense_el in entry.findall(f"{{{NS}}}sense"):
                    senses.append(parse_sense(sense_el))

                # Full text of entry
                full_text = clean_text(text_content(entry))

                entries[eid] = {
                    "id": eid,
                    "cite": cite,
                    "type": entry_type,
                    "mod": mod,
                    "hebrew": hebrew_bdb,
                    "pos": pos_bdb,
                    "defs": top_defs,
                    "senses": senses,
                    "refs": list(dict.fromkeys(all_refs)),  # deduplicate, preserve order
                    "full_text": full_text,
                }

    print(f"  → {len(entries)} BDB entries parsed")
    return entries


# ─── 4. Fuse everything ───
def fuse_lexicon(strongs, li_index, bdb):
    """Fuse Strong's + LexicalIndex + BDB into enriched entries."""
    print("Fusing lexicon data...")
    result = []

    for num in sorted(strongs.keys()):
        s = strongs[num]
        li = li_index.get(num, {})

        entry = {
            "strong": s["strong"],
            "hebrew": s["hebrew"],
            "xlit": s["xlit"],
            "pron": s["pron"],
            "pos": s["pos"],
            "lang": s["lang"] or li.get("lang", "heb"),
            "source": s["source"],
            "definition_short": s["definition_short"],
            "defs_strong": s["defs"],
            "usage": s["usage"],
        }

        # Add LexicalIndex data
        if li:
            entry["bdb_id"] = li.get("bdb_id", "")
            entry["twot"] = li.get("twot", "")
            entry["li_id"] = li.get("li_id", "")
            entry["li_def"] = li.get("def_li", "")
            entry["li_pos"] = li.get("pos_li", "")
            if li.get("etymology"):
                entry["etymology"] = li["etymology"]
        else:
            entry["bdb_id"] = ""
            entry["twot"] = ""

        # Add BDB data
        bdb_id = entry.get("bdb_id", "")
        bdb_entry = bdb.get(bdb_id)
        if bdb_entry:
            entry["definition_full"] = bdb_entry["full_text"]
            entry["bdb_pos"] = bdb_entry["pos"]
            entry["bdb_defs"] = bdb_entry["defs"]
            entry["bdb_senses"] = bdb_entry["senses"]
            entry["bdb_refs"] = bdb_entry["refs"]
            entry["bdb_type"] = bdb_entry["type"]
            entry["bdb_cite"] = bdb_entry["cite"]
        else:
            entry["definition_full"] = ""
            entry["bdb_senses"] = []
            entry["bdb_refs"] = []

        result.append(entry)

    print(f"  → {len(result)} fused entries")
    matched = sum(1 for e in result if e.get("bdb_id"))
    print(f"  → {matched} entries linked to BDB via LexicalIndex")
    with_bdb = sum(1 for e in result if e.get("definition_full"))
    print(f"  → {with_bdb} entries with BDB content")

    return result


# ─── 5. Stats ───
def print_stats(lexicon):
    """Print statistics about the fused lexicon."""
    total = len(lexicon)
    with_bdb = sum(1 for e in lexicon if e.get("definition_full"))
    with_senses = sum(1 for e in lexicon if e.get("bdb_senses"))
    with_refs = sum(1 for e in lexicon if e.get("bdb_refs"))
    langs = defaultdict(int)
    for e in lexicon:
        langs[e.get("lang", "?")] += 1
    pos_counts = defaultdict(int)
    for e in lexicon:
        pos_counts[e.get("pos", "?")] += 1

    print("\n═══ Lexicon Statistics ═══")
    print(f"Total entries:        {total}")
    print(f"With BDB content:     {with_bdb} ({100*with_bdb/total:.1f}%)")
    print(f"With BDB senses:      {with_senses}")
    print(f"With biblical refs:   {with_refs}")
    print(f"\nLanguage distribution:")
    for lang, count in sorted(langs.items(), key=lambda x: -x[1]):
        print(f"  {lang}: {count}")
    print(f"\nTop POS tags:")
    for pos, count in sorted(pos_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"  {pos}: {count}")

    # Sample entry
    sample = next((e for e in lexicon if e["strong"] == "H1"), lexicon[0])
    print(f"\n═══ Sample Entry (H1) ═══")
    print(json.dumps(sample, ensure_ascii=False, indent=2)[:2000])


# ─── Main ───
def main():
    strongs = parse_strongs()
    li_index = parse_lexical_index()
    bdb = parse_bdb()
    lexicon = fuse_lexicon(strongs, li_index, bdb)
    print_stats(lexicon)

    # Write output
    print(f"\nWriting {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(lexicon, f, ensure_ascii=False, indent=2)

    size_mb = OUTPUT_FILE.stat().st_size / (1024 * 1024)
    print(f"  → {size_mb:.1f} MB written")
    print("Done!")


if __name__ == "__main__":
    main()
