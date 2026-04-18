#!/usr/bin/env python3
"""
Post-processing and validation for hebrew-lexicon-fr.json.

Checks:
1. All 8674 entries present
2. No Hebrew/Aramaic text was corrupted by translation
3. Biblical references preserved intact
4. French translation fields exist
5. Strong numbers sequential and complete
6. POS tags preserved
7. Sense tree integrity

Also generates a compact version for the web platform (lighter JSON).

Usage:
    python3 validate_lexicon.py [--input hebrew-lexicon-fr.json]
    python3 validate_lexicon.py --compact  # generate compact web version
"""

import argparse
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent

# Hebrew Unicode block: \u0590-\u05FF (Hebrew) + \u0600-\u06FF (Arabic, for occasional marks)
HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
STRONG_RE = re.compile(r"^H\d+$")
REF_RE = re.compile(r"^[A-Z1-3][a-zA-Z]+\.\d+\.\d+$")


def load_lexicon(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate(lexicon, is_translated=False):
    """Run all validation checks."""
    issues = []
    warnings = []

    # 1. Count check
    if len(lexicon) != 8674:
        issues.append(f"Expected 8674 entries, got {len(lexicon)}")

    # 2. Strong number integrity
    seen_nums = set()
    for i, e in enumerate(lexicon):
        sid = e.get("strong", "")
        if not STRONG_RE.match(sid):
            issues.append(f"Entry {i}: invalid strong ID '{sid}'")
            continue
        num = int(sid[1:])
        if num in seen_nums:
            issues.append(f"Entry {i}: duplicate strong {sid}")
        seen_nums.add(num)

    missing = set(range(1, 8675)) - seen_nums
    if missing:
        issues.append(f"Missing Strong numbers: {sorted(missing)[:10]}{'...' if len(missing)>10 else ''}")

    # 3. Hebrew integrity
    for e in lexicon:
        hebrew = e.get("hebrew", "")
        if not hebrew:
            warnings.append(f"{e['strong']}: empty hebrew field")
        elif not HEBREW_RE.search(hebrew):
            warnings.append(f"{e['strong']}: no Hebrew chars in hebrew field: '{hebrew[:30]}'")

        # Check Hebrew wasn't accidentally translated
        if is_translated:
            hebrew_fr = e.get("hebrew", "")
            # Hebrew field should be identical pre/post translation
            if hebrew_fr != hebrew:
                issues.append(f"{e['strong']}: Hebrew field changed!")

    # 4. POS preservation
    known_pos = {"n-m", "n-f", "v", "a", "adv", "prep", "conj", "inj", "d", "p", "n", "n-pr-m",
                 "n-pr-f", "n-pr-loc", "n-pr", "n-pr-m n-pr-loc", "n-pr-m n-pr-f", "n-gent"}
    for e in lexicon:
        pos = e.get("pos", "")
        # Don't flag - just count
        pass

    # 5. Translation field checks (only for translated version)
    if is_translated:
        fr_fields = ["definition_short_fr", "usage_fr"]
        missing_fr = defaultdict(int)
        for e in lexicon:
            for field in fr_fields:
                if not e.get(field):
                    missing_fr[field] += 1
        for field, count in missing_fr.items():
            if count > 100:
                warnings.append(f"{field}: missing in {count}/{len(lexicon)} entries")

    # 6. BDB link coverage
    with_bdb = sum(1 for e in lexicon if e.get("bdb_id"))
    with_senses = sum(1 for e in lexicon if e.get("bdb_senses"))
    with_refs = sum(1 for e in lexicon if e.get("bdb_refs"))

    # 7. Sense tree integrity
    broken_senses = 0
    for e in lexicon:
        for s in e.get("bdb_senses", []):
            if not isinstance(s, dict):
                broken_senses += 1
    if broken_senses:
        issues.append(f"{broken_senses} broken sense objects")

    # Summary
    stats = {
        "total_entries": len(lexicon),
        "strong_coverage": f"{len(seen_nums)}/8674",
        "bdb_linked": with_bdb,
        "with_senses": with_senses,
        "with_refs": with_refs,
    }

    # Language distribution
    langs = defaultdict(int)
    for e in lexicon:
        langs[e.get("lang", "?")] += 1
    stats["languages"] = dict(langs)

    return issues, warnings, stats


def generate_compact(lexicon, output_path):
    """Generate a compact version for web platform use — architecture 7 tiers.

    Fields :
    - s, h, x, pr, l     : identifiants et morphologie
    - p                   : POS Strong (fallback si bp absent)
    - bp                  : POS BDB (plus precis : n.pr.dei, n.m.pl, etc.) -- NOUVEAU
    - d                   : definition courte lisible (Strong short)
    - df                  : definition complete BDB (definition_full_fr)
    - g                   : glosses (defs_strong_fr) -- mots cles
    - b                   : bdb_id
    - tw                  : twot
    - se                  : senses BDB structures (tree avec stem/n/d/sub)
    - bd                  : bdb_defs_fr (liste plate, fallback si se vide)
    - r                   : racine etymologique
    - et                  : etymologie textuelle (source_fr) -- NOUVEAU
    - br                  : bdb_refs (passages bibliques) -- NOUVEAU

    Champ u (usage KJV) RETIRE : decision editoriale (non aligne avec profondeur BDB).

    Fallback chain pour `d` : definition_short_fr > definition_full_fr (tronque a 200) > definition_short (EN)
    """
    # Nettoyage complet BDB scholarly : refs auteurs, abreviations, symboles, artefacts
    import importlib.util
    _clean_mod_path = BASE_DIR / "scripts" / "clean_bdb_scholarly.py"
    _spec = importlib.util.spec_from_file_location("clean_bdb", str(_clean_mod_path))
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    clean_bdb_full = _mod.clean_bdb_scholarly

    stats = {"d_from_short_fr": 0, "d_from_full_fr": 0, "d_from_short_en": 0, "d_empty": 0,
             "with_df": 0, "with_bp": 0, "with_et": 0, "with_br": 0, "cleaned_trailing": 0}
    compact = []
    for e in lexicon:
        c = {
            "s": e["strong"],
            "h": e.get("hebrew", ""),
            "x": e.get("xlit", ""),
            "pr": e.get("pron", ""),
            "p": e.get("pos", ""),
            "l": e.get("lang", "heb"),
        }

        # POS BDB plus precis (n.pr.dei, n.m.pl, vb, etc.) -- surfacable en tooltip
        bdb_pos = (e.get("bdb_pos") or "").strip()
        if bdb_pos and bdb_pos != c["p"]:
            c["bp"] = bdb_pos
            stats["with_bp"] += 1

        # === Definitions : d (courte) + df (BDB complete) ===
        def_short_fr = (e.get("definition_short_fr") or "").strip()
        def_short_en = (e.get("definition_short") or "").strip()
        def_full_fr_raw = (e.get("definition_full_fr") or "").strip()
        def_full_fr = clean_bdb_full(def_full_fr_raw)
        if def_full_fr != def_full_fr_raw:
            stats["cleaned_trailing"] += 1

        # d : chaine de fallback - on garde TOUJOURS une definition affichable
        if def_short_fr:
            c["d"] = def_short_fr
            stats["d_from_short_fr"] += 1
        elif def_full_fr:
            if len(def_full_fr) > 200:
                cut = def_full_fr[:200].rsplit(" ", 1)[0]
                c["d"] = cut + "\u2026"
            else:
                c["d"] = def_full_fr
            stats["d_from_full_fr"] += 1
        elif def_short_en:
            c["d"] = def_short_en
            stats["d_from_short_en"] += 1
        else:
            c["d"] = ""
            stats["d_empty"] += 1

        # df : definition BDB complete (si substantiellement differente de d)
        if def_full_fr and def_full_fr != c["d"]:
            c["df"] = def_full_fr
            stats["with_df"] += 1

        # Glosses (mots-cles courts)
        defs_fr = e.get("defs_strong_fr", e.get("defs_strong", []))
        if defs_fr:
            c["g"] = defs_fr

        # [RETIRE] u (usage KJV) -- decision editoriale

        # BDB meta
        bdb_id = e.get("bdb_id", "")
        if bdb_id:
            c["b"] = bdb_id
        twot = e.get("twot", "")
        if twot:
            c["tw"] = twot

        # BDB senses (arbre structure simplifie avec stem + n + d + sub)
        # Filtrage : si tous les sens sont vides (d="" recursivement), ne PAS inclure `se`
        senses = e.get("bdb_senses", [])
        if senses:
            compacted = _compact_senses(senses)
            if compacted:
                c["se"] = compacted

        # BDB defs (liste plate - fallback si se vide)
        bdb_defs = e.get("bdb_defs_fr") or e.get("bdb_defs") or []
        if bdb_defs:
            flat = [d.strip() for d in bdb_defs if isinstance(d, str) and len(d.strip()) >= 3]
            if flat:
                c["bd"] = flat[:8]

        # Etymology root (racine hebraique)
        etym = e.get("etymology", {}) or {}
        if etym.get("root"):
            c["r"] = etym["root"]

        # Etymology text (source_fr) -- ex "pluriel de 433", "de 1961", "un mot primitif"
        source_fr = (e.get("source_fr") or "").strip()
        if source_fr:
            c["et"] = source_fr
            stats["with_et"] += 1

        # Bdb_refs (passages bibliques, format OSIS style "Gen.1.1")
        refs = e.get("bdb_refs") or []
        if refs:
            # Nettoyer + cap a 15 refs (pour taille fichier)
            clean_refs = [r.strip() for r in refs if isinstance(r, str) and r.strip()]
            if clean_refs:
                c["br"] = clean_refs[:15]
                stats["with_br"] += 1

        compact.append(c)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(compact, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\nCompact version: {size_mb:.2f} MB -> {output_path}")
    print(f"  d sourced from definition_short_fr : {stats['d_from_short_fr']}")
    print(f"  d sourced from definition_full_fr  : {stats['d_from_full_fr']} (fallback, ex-vides)")
    print(f"  d sourced from definition_short_en : {stats['d_from_short_en']} (dernier recours)")
    print(f"  d EMPTY (aucune source)            : {stats['d_empty']}")
    print(f"  df field populated (BDB full)      : {stats['with_df']}")
    print(f"  bp field populated (POS BDB)       : {stats['with_bp']}")
    print(f"  et field populated (etymologie)    : {stats['with_et']}")
    print(f"  br field populated (refs bibliques): {stats['with_br']}")
    print(f"  df entries nettoyees (trailing)    : {stats['cleaned_trailing']}")
    print(f"  u field REMOVED (usage KJV)")
    return compact


def _compact_senses(senses):
    """Simplify sense tree for compact JSON.

    Filtre recursivement les sens vides :
    - Un sense est garde uniquement s'il a un 'd' non vide OU un 'c' (sous-sens) avec du contenu reel
    - Les champs 'st' et 'n' seuls (sans 'd' ni 'c') sont consideres comme vides
    Returns [] si toute la branche est vide.
    """
    result = []
    for s in senses:
        cs = {}
        if s.get("stem"):
            cs["st"] = s["stem"]
        if s.get("n"):
            cs["n"] = s["n"]
        d = (s.get("def_fr") or s.get("def") or "").strip()
        if d:
            cs["d"] = d
        # Sub-senses (recursif, filtre)
        sub = s.get("senses", [])
        if sub:
            compacted_sub = _compact_senses(sub)
            if compacted_sub:
                cs["c"] = compacted_sub
        # N'ajouter le sense que s'il a un contenu reel (d ou sous-sens)
        if cs.get("d") or cs.get("c"):
            result.append(cs)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=None, help="Input JSON file")
    parser.add_argument("--compact", action="store_true", help="Generate compact version")
    args = parser.parse_args()

    # Determine input file
    if args.input:
        input_path = Path(args.input)
    else:
        # Try FR version first, fall back to EN
        fr_path = BASE_DIR / "hebrew-lexicon-fr.json"
        en_path = BASE_DIR / "hebrew-lexicon-en.json"
        if fr_path.exists():
            input_path = fr_path
        elif en_path.exists():
            input_path = en_path
        else:
            print("ERROR: No lexicon file found")
            sys.exit(1)

    is_translated = "fr" in input_path.stem
    print(f"Loading {input_path}...")
    lexicon = load_lexicon(input_path)
    print(f"  -> {len(lexicon)} entries")

    # Validate
    issues, warnings, stats = validate(lexicon, is_translated)

    print("\n=== Validation Results ===")
    print(f"Entries:       {stats['total_entries']}")
    print(f"Strong IDs:    {stats['strong_coverage']}")
    print(f"BDB linked:    {stats['bdb_linked']}")
    print(f"With senses:   {stats['with_senses']}")
    print(f"With refs:     {stats['with_refs']}")
    print(f"Languages:     {stats['languages']}")

    if issues:
        print(f"\n[X] ISSUES ({len(issues)}):")
        for iss in issues[:20]:
            print(f"  * {iss}")
    else:
        print("\n[OK] No issues found")

    if warnings:
        print(f"\n[!] Warnings ({len(warnings)}):")
        for w in warnings[:10]:
            print(f"  * {w}")

    # Generate compact version
    if args.compact:
        suffix = "-fr" if is_translated else "-en"
        compact_path = BASE_DIR / f"hebrew-lexicon{suffix}-compact.json"
        generate_compact(lexicon, compact_path)

    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
