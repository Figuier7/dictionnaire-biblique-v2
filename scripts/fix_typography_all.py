#!/usr/bin/env python3
"""
fix_typography_all.py — Applique toutes les corrections typographiques auditees.

Phases :
  A1  Capitaliser definitions Smith debutant par minuscule (650)
  A2  (See X) -> (Voir X) dans Easton (67)
  A3  i.e. -> c.-a-d. / e.g. -> p. ex. dans Easton (54)
  A5  Normaliser U+2011 -> U+002D dans Easton + concepts (173)
  A6  Supprimer doubles espaces BYM + Smith (29)
  A7  Capitaliser definitions Easton debutant par minuscule (5)
  A8  Retirer point final des mot Easton (8)
  A9  Labels concepts ALL CAPS -> casse titre (sauf YHWH) (15)
  A10 display_titles.secondary ALL CAPS -> casse titre (10)
  S1  label_fr BYM ALL CAPS -> casse titre (437)
  S2  Aliases concepts ALL CAPS -> casse titre (61)
  S3  Decompacter mot BYM (12)
  S4  NBSP dans guillemets BYM (423)
  M1  Corriger 3 entrees BYM tronquees

Produit : rapport de corrections dans work/reports/typography-fix-report.json
"""

import json
import re
import sys
import io
import os
from pathlib import Path
from datetime import datetime

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(r"C:\Users\caeng\OneDrive\Documents\A l'ombre du figuier\dictionnaire-biblique-main")
BYM_PATH = BASE / "uploads/dictionnaires/bym/bym-lexicon.entries.json"
EASTON_PATH = BASE / "uploads/dictionnaires/easton/easton.entries.json"
SMITH_PATH = BASE / "uploads/dictionnaires/smith/smith.entries.json"
CONCEPTS_PATH = BASE / "uploads/dictionnaires/concepts.json"
REPORT_PATH = BASE / "work/reports/typography-fix-report.json"

report = {}

def load_json(path):
    """Load JSON with BOM handling."""
    raw = path.read_bytes()
    if raw[:3] == b'\xef\xbb\xbf':
        text = raw.decode('utf-8-sig')
    else:
        text = raw.decode('utf-8')
    return json.loads(text)

def save_json(path, data, use_bom=False):
    """Save JSON preserving encoding convention."""
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if use_bom:
        path.write_bytes(b'\xef\xbb\xbf' + text.encode('utf-8'))
    else:
        path.write_bytes(text.encode('utf-8'))

def smart_title(s):
    """Convert ALL CAPS to title case, handling accented chars and apostrophes.
    'JÉRUSALEM' -> 'Jérusalem', 'SHIM\\'ON' -> 'Shim\\'on', 'BAR-TALMAÏ' -> 'Bar-Talmaï'
    """
    if not s or not s.strip():
        return s
    # Split on hyphens, title each part
    parts = s.split('-')
    result_parts = []
    for part in parts:
        if not part:
            result_parts.append(part)
            continue
        # Split on apostrophes
        subparts = part.split("'")
        titled_subs = []
        for i, sub in enumerate(subparts):
            if not sub:
                titled_subs.append(sub)
                continue
            titled_subs.append(sub[0].upper() + sub[1:].lower() if len(sub) > 1 else sub[0].upper())
        result_parts.append("'".join(titled_subs))
    return '-'.join(result_parts)

def smart_title_phrase(s):
    """Title case for multi-word phrases. First word capitalized, rest lowercase
    except proper nouns. Used for BYM label_fr."""
    if not s or not s.strip():
        return s
    # For single words, use smart_title
    if ' ' not in s:
        return smart_title(s)
    # For phrases: capitalize first word, lowercase rest
    words = s.split(' ')
    result = []
    for i, w in enumerate(words):
        if not w:
            result.append(w)
            continue
        if i == 0:
            result.append(smart_title(w))
        else:
            # Keep prepositions/articles lowercase, capitalize nouns
            lower_w = w.lower() if w.isupper() else w
            # But re-apply smart_title for hyphenated words
            if '-' in w and w.isupper():
                lower_w = smart_title(w)
                # Actually for label_fr, lowercase all except first word
                lower_w = w[0].upper() + w[1:].lower() if len(w) > 1 else w[0].upper()
            elif w.isupper() and len(w) > 1:
                lower_w = w[0].lower() + w[1:].lower()
            result.append(lower_w)
    return ' '.join(result)


# ─────────────────────────────────────────────────
# Load all files
# ─────────────────────────────────────────────────
print("Chargement des fichiers...")
bym = load_json(BYM_PATH)
easton = load_json(EASTON_PATH)
smith = load_json(SMITH_PATH)

# concepts.json uses BOM
concepts_raw = CONCEPTS_PATH.read_bytes()
concepts_has_bom = concepts_raw[:3] == b'\xef\xbb\xbf'
concepts = load_json(CONCEPTS_PATH)

print(f"  BYM: {len(bym)} entrees")
print(f"  Easton: {len(easton)} entrees")
print(f"  Smith: {len(smith)} entrees")
print(f"  Concepts: {len(concepts)} concepts")

# ─────────────────────────────────────────────────
# A1: Capitaliser definitions Smith debutant par minuscule
# ─────────────────────────────────────────────────
print("\n── A1: Capitaliser definitions Smith ──")
a1_count = 0
a1_examples = []
for entry in smith:
    d = entry.get("definition", "")
    if not d:
        continue
    first_char = d[0]
    # Skip if starts with paren (etymology marker)
    if first_char in '(_«':
        continue
    if first_char.islower():
        entry["definition"] = d[0].upper() + d[1:]
        a1_count += 1
        if len(a1_examples) < 5:
            a1_examples.append({"id": entry["id"], "mot": entry["mot"], "old": d[:40], "new": entry["definition"][:40]})
print(f"  Corrige: {a1_count}")
report["A1_smith_capitalize"] = {"count": a1_count, "examples": a1_examples}

# ─────────────────────────────────────────────────
# A2: (See X) -> (Voir X) dans Easton
# ─────────────────────────────────────────────────
print("\n── A2: (See X) -> (Voir X) dans Easton ──")

# Translation map for known concept names in See references
see_translations = {
    "PAUL": "PAUL", "TABERNACLE": "TABERNACLE", "FAITH": "FOI",
    "AZAZEL": "AZAZEL", "HAURAN": "HAURAN", "ARGOB": "ARGOB",
    "BETHABARA": "BETHABARA", "GIBEON": "GABAON", "APOCRYPHA": "APOCRYPHES",
    "VERSION": "VERSION", "THORNS": "EPINES", "ABEL": "ABEL",
    "CANE": "ROSEAU", "PHILIP": "PHILIPPE", "CHURCH": "EGLISE",
    "DISPENSATION": "DISPENSATION", "MAHANEH-DAN": "MAHANEH-DAN",
    "WATCHES": "VEILLES", "NOAH": "NOE", "CHALDEA": "CHALDEE",
    "WHALE": "BALEINE", "DARIC": "DARIQUE", "ITHAMAR": "ITHAMAR",
    "BANQUET": "BANQUET", "PHYLACTERY": "PHYLACTERE",
    "VULTURE": "VAUTOUR", "MOABITE STONE": "PIERRE MOABITE",
    "OAK": "CHENE", "ON": "ON", "HAGAR": "AGAR",
    "LUZ": "LUZ", "BETHEL": "BETHEL", "SABBATH": "SHABBAT",
    "NINEVEH": "NINIVE", "FURNACE": "FOURNAISE", "PRIEST": "SACRIFICATEUR",
    "FALL": "CHUTE", "DRESS": "VETEMENT", "MARTHA": "MARTHE",
    "HEZEKIAH": "EZECHIAS", "JERUSALEM": "JERUSALEM",
    "NUMBERING THE PEOPLE": "RECENSEMENT DU PEUPLE",
    "DIVINATION": "DIVINATION", "HEBRON": "HEBRON",
    "TEIL-TREE": "TEREBINTHE", "GABBATHA": "GABBATHA",
    "NEBO": "NEBO", "VALLEY": "VALLEE", "PALACE": "PALAIS",
    "DÉCRETS D'ELOHIM": "DÉCRETS D'ELOHIM", "ELECTION": "ELECTION",
    "BIBLE": "BIBLE", "CLAUDIA": "CLAUDIA", "EZRA": "ESDRAS",
    "ATONEMENT": "EXPIATION", "DAVID": "DAVID", "ASP": "ASPIC",
    "BRASS": "AIRAIN", "EN-ROGEL": "EN-ROGEL", "ARMS": "ARMES",
    "SOLOMON": "SALOMON", "THUMMIM": "THUMMIM",
    "CROWN OF THORNS": "COURONNE D'EPINES",
    "ATONEMENT, DAY OF": "JOUR DES EXPIATIONS",
    "GALATIANS, EPISTLE TO": "EPITRE AUX GALATES",
    "MATTHEW, GOSPEL OF": "EVANGILE DE MATTHIEU",
    "JOASH [5.]": "JOAS",
}

a2_count = 0
a2_examples = []

def replace_see(match):
    """Replace (See X) with (Voir X), translating if possible."""
    content = match.group(1).strip().rstrip('.')
    # Try translation
    translated = see_translations.get(content, content)
    return f"(Voir {translated})"

for entry in easton:
    d = entry.get("definition", "")
    if "(See " not in d:
        continue
    new_d = re.sub(r'\(See\s+([^)]+)\)', replace_see, d)
    if new_d != d:
        entry["definition"] = new_d
        a2_count += 1
        if len(a2_examples) < 5:
            a2_examples.append({"id": entry["id"], "mot": entry["mot"]})

print(f"  Corrige: {a2_count}")
report["A2_easton_see_voir"] = {"count": a2_count, "examples": a2_examples}

# ─────────────────────────────────────────────────
# A3: i.e. -> c.-a-d. / e.g. -> p. ex. dans Easton
# ─────────────────────────────────────────────────
print("\n── A3: i.e./e.g. -> c.-a-d./p. ex. ──")
a3_count = 0
a3_examples = []
for entry in easton:
    d = entry.get("definition", "")
    new_d = d
    # Replace i.e. with c.-à-d. (careful not to match mid-word)
    new_d = re.sub(r'\bi\.e\.\b', 'c.-à-d.', new_d)
    new_d = re.sub(r'\bi\.e\.,', 'c.-à-d.,', new_d)
    # Replace e.g. with p. ex.
    new_d = re.sub(r'\be\.g\.\b', 'p. ex.', new_d)
    new_d = re.sub(r'\be\.g\.,', 'p. ex.,', new_d)
    if new_d != d:
        entry["definition"] = new_d
        a3_count += 1
        if len(a3_examples) < 5:
            a3_examples.append({"id": entry["id"], "mot": entry["mot"]})

print(f"  Corrige: {a3_count}")
report["A3_easton_ie_eg"] = {"count": a3_count, "examples": a3_examples}

# ─────────────────────────────────────────────────
# A5: Normaliser U+2011 -> U+002D dans Easton + concepts
# ─────────────────────────────────────────────────
print("\n── A5: Normaliser U+2011 -> U+002D ──")
a5_easton = 0
for entry in easton:
    for field in ["mot", "label_fr", "definition"]:
        val = entry.get(field, "")
        if '\u2011' in val:
            entry[field] = val.replace('\u2011', '-')
            if field == "definition":
                a5_easton += 1

a5_concepts = 0
for concept in concepts:
    for field in ["label", "concept_id"]:
        val = concept.get(field, "")
        if '\u2011' in val:
            concept[field] = val.replace('\u2011', '-')
            a5_concepts += 1
    # Also check display_titles
    dt = concept.get("display_titles", {})
    for k in ["primary", "secondary"]:
        val = dt.get(k, "")
        if '\u2011' in val:
            dt[k] = val.replace('\u2011', '-')
    # Check aliases
    aliases = concept.get("aliases", [])
    concept["aliases"] = [a.replace('\u2011', '-') if isinstance(a, str) and '\u2011' in a else a for a in aliases]

print(f"  Easton: {a5_easton} definitions")
print(f"  Concepts: {a5_concepts} labels")
report["A5_normalize_u2011"] = {"easton_definitions": a5_easton, "concepts": a5_concepts}

# ─────────────────────────────────────────────────
# A6: Supprimer doubles espaces BYM + Smith
# ─────────────────────────────────────────────────
print("\n── A6: Supprimer doubles espaces ──")
a6_bym = 0
for entry in bym:
    d = entry.get("definition", "")
    new_d = re.sub(r'  +', ' ', d)
    if new_d != d:
        entry["definition"] = new_d
        a6_bym += 1

a6_smith = 0
for entry in smith:
    d = entry.get("definition", "")
    new_d = re.sub(r'  +', ' ', d)
    if new_d != d:
        entry["definition"] = new_d
        a6_smith += 1

print(f"  BYM: {a6_bym}")
print(f"  Smith: {a6_smith}")
report["A6_double_spaces"] = {"bym": a6_bym, "smith": a6_smith}

# ─────────────────────────────────────────────────
# A7: Capitaliser definitions Easton debutant par minuscule
# ─────────────────────────────────────────────────
print("\n── A7: Capitaliser definitions Easton ──")
a7_count = 0
a7_ids = []
for entry in easton:
    d = entry.get("definition", "")
    if not d:
        continue
    if d[0].islower():
        entry["definition"] = d[0].upper() + d[1:]
        a7_count += 1
        a7_ids.append(entry["id"])

print(f"  Corrige: {a7_count} — {a7_ids}")
report["A7_easton_capitalize"] = {"count": a7_count, "ids": a7_ids}

# ─────────────────────────────────────────────────
# A8: Retirer point final des mot Easton
# ─────────────────────────────────────────────────
print("\n── A8: Retirer point final des mot Easton ──")
a8_count = 0
a8_entries = []
for entry in easton:
    mot = entry.get("mot", "")
    if mot.endswith('.'):
        old_mot = mot
        entry["mot"] = mot.rstrip('.')
        entry["label_fr"] = entry["label_fr"].rstrip('.') if entry.get("label_fr", "").endswith('.') else entry.get("label_fr", "")
        a8_count += 1
        a8_entries.append({"id": entry["id"], "old": old_mot, "new": entry["mot"]})

print(f"  Corrige: {a8_count}")
report["A8_easton_trailing_dot"] = {"count": a8_count, "entries": a8_entries}

# ─────────────────────────────────────────────────
# A9: Labels concepts ALL CAPS -> casse titre (sauf YHWH)
# ─────────────────────────────────────────────────
print("\n── A9: Labels concepts ALL CAPS -> casse titre ──")
KEEP_UPPER = {"YHWH"}  # By editorial convention
a9_count = 0
a9_entries = []
for concept in concepts:
    label = concept.get("label", "")
    if not label:
        continue
    # Check if ALL CAPS (at least 2 alpha chars, all uppercase)
    alpha_chars = [c for c in label if c.isalpha()]
    if len(alpha_chars) >= 2 and all(c.isupper() for c in alpha_chars):
        if label in KEEP_UPPER:
            continue
        old_label = label
        new_label = smart_title(label)
        concept["label"] = new_label
        a9_count += 1
        a9_entries.append({"concept_id": concept["concept_id"], "old": old_label, "new": new_label})

print(f"  Corrige: {a9_count}")
for e in a9_entries:
    print(f"    {e['old']} -> {e['new']}")
report["A9_concepts_labels_caps"] = {"count": a9_count, "entries": a9_entries}

# ─────────────────────────────────────────────────
# A10: display_titles.secondary ALL CAPS -> casse titre
# ─────────────────────────────────────────────────
print("\n── A10: display_titles.secondary ALL CAPS ──")
a10_count = 0
a10_entries = []
for concept in concepts:
    dt = concept.get("display_titles", {})
    sec = dt.get("secondary", "")
    if not sec:
        continue
    alpha_chars = [c for c in sec if c.isalpha()]
    if len(alpha_chars) >= 2 and all(c.isupper() for c in alpha_chars):
        if sec in KEEP_UPPER:
            continue
        old = sec
        dt["secondary"] = smart_title(sec)
        a10_count += 1
        a10_entries.append({"concept_id": concept["concept_id"], "old": old, "new": dt["secondary"]})
    # Also fix primary if ALL CAPS
    pri = dt.get("primary", "")
    if pri:
        alpha_p = [c for c in pri if c.isalpha()]
        if len(alpha_p) >= 2 and all(c.isupper() for c in alpha_p) and pri not in KEEP_UPPER:
            dt["primary"] = smart_title(pri)

print(f"  Corrige: {a10_count}")
report["A10_concepts_secondary_caps"] = {"count": a10_count, "entries": a10_entries}

# ─────────────────────────────────────────────────
# S1: label_fr BYM ALL CAPS -> casse titre
# ─────────────────────────────────────────────────
print("\n── S1: label_fr BYM ALL CAPS -> casse titre ──")
s1_count = 0
s1_examples = []
for entry in bym:
    label = entry.get("label_fr", "")
    if not label:
        continue
    # Remove soft hyphens for checking
    clean = label.replace('\u00ad', '')
    alpha_chars = [c for c in clean if c.isalpha()]
    if len(alpha_chars) >= 2 and all(c.isupper() for c in alpha_chars):
        old = label
        new_label = smart_title_phrase(label)
        entry["label_fr"] = new_label
        s1_count += 1
        if len(s1_examples) < 10:
            s1_examples.append({"id": entry["id"], "old": old, "new": new_label})

print(f"  Corrige: {s1_count}")
report["S1_bym_label_caps"] = {"count": s1_count, "examples": s1_examples}

# ─────────────────────────────────────────────────
# S2: Aliases concepts ALL CAPS -> casse titre
# ─────────────────────────────────────────────────
print("\n── S2: Aliases concepts ALL CAPS -> casse titre ──")
s2_count = 0
s2_entries = []
for concept in concepts:
    aliases = concept.get("aliases", [])
    changed = False
    new_aliases = []
    for alias in aliases:
        if not isinstance(alias, str):
            new_aliases.append(alias)
            continue
        alpha_chars = [c for c in alias if c.isalpha()]
        if len(alpha_chars) >= 2 and all(c.isupper() for c in alpha_chars) and alias not in KEEP_UPPER:
            new_alias = smart_title(alias)
            new_aliases.append(new_alias)
            changed = True
            s2_entries.append({"concept_id": concept["concept_id"], "old": alias, "new": new_alias})
        else:
            new_aliases.append(alias)
    if changed:
        concept["aliases"] = new_aliases
        s2_count += 1

print(f"  Concepts touches: {s2_count}, aliases converties: {len(s2_entries)}")
report["S2_concepts_aliases_caps"] = {"concepts_touched": s2_count, "aliases_converted": len(s2_entries), "examples": s2_entries[:15]}

# ─────────────────────────────────────────────────
# S3: Decompacter mot BYM
# ─────────────────────────────────────────────────
print("\n── S3: Decompacter mot BYM ──")

DECOMPACT_MAP = {
    "ARBREDELACONNAISSANCEDECEQUIESTBONOUMAUVAIS": "ARBRE DE LA CONNAISSANCE DE CE QUI EST BON OU MAUVAIS",
    "BLASPHÈMECONTRELESAINTESPRIT": "BLASPHÈME CONTRE LE SAINT-ESPRIT",
    "BLASPHÈMECONTRELESAINT\u00adESPRIT": "BLASPHÈME CONTRE LE SAINT-ESPRIT",
    "CHEMINDESHABBAT": "CHEMIN DES SHABBAT",
    "GRANDETRIBULATION": "GRANDE TRIBULATION",
    "IMPOSITIONDESMAINS": "IMPOSITION DES MAINS",
    "MONTDESOLIVIERS": "MONT DES OLIVIERS",
    "MYSTÈREDELAVIOLATIONDELATORAH": "MYSTÈRE DE LA VIOLATION DE LA TORAH",
    "NOUVELLENAISSANCE": "NOUVELLE NAISSANCE",
    "VIOLATIONDELATORAH": "VIOLATION DE LA TORAH",
    "ESPRITIMPUR": "ESPRIT IMPUR",
    "HÉRODEANTIPAS": "HÉRODE ANTIPAS",
}

s3_count = 0
s3_entries = []
for entry in bym:
    mot = entry.get("mot", "")
    # Clean soft hyphens for matching
    mot_clean = mot.replace('\u00ad', '')
    if mot_clean in DECOMPACT_MAP:
        old_mot = mot
        new_mot = DECOMPACT_MAP[mot_clean]
        entry["mot"] = new_mot
        # Also fix label_fr if it was the same compacted form
        label = entry.get("label_fr", "")
        label_clean = label.replace('\u00ad', '')
        if label_clean.upper() == mot_clean or label_clean == mot_clean:
            entry["label_fr"] = smart_title_phrase(new_mot)
        s3_count += 1
        s3_entries.append({"id": entry["id"], "old": old_mot, "new": new_mot, "label_fr": entry["label_fr"]})

print(f"  Corrige: {s3_count}")
for e in s3_entries:
    print(f"    {e['old']} -> {e['new']} (label_fr: {e['label_fr']})")
report["S3_bym_decompact"] = {"count": s3_count, "entries": s3_entries}

# ─────────────────────────────────────────────────
# S4: Ajouter NBSP dans guillemets BYM
# ─────────────────────────────────────────────────
print("\n── S4: NBSP dans guillemets BYM ──")
NBSP = '\u00a0'
s4_count = 0
for entry in bym:
    d = entry.get("definition", "")
    if '«' not in d and '»' not in d:
        continue
    new_d = d
    # « followed by normal space -> « + NBSP
    new_d = re.sub(r'«\s', f'«{NBSP}', new_d)
    # Normal space before » -> NBSP + »
    new_d = re.sub(r'\s»', f'{NBSP}»', new_d)
    # « not followed by any space -> add NBSP
    new_d = re.sub(r'«(?!\s|' + NBSP + ')', f'«{NBSP}', new_d)
    # » not preceded by any space -> add NBSP before
    new_d = re.sub(r'(?<!\s|' + NBSP + ')»', f'{NBSP}»', new_d)
    if new_d != d:
        entry["definition"] = new_d
        s4_count += 1

print(f"  Corrige: {s4_count}")
report["S4_bym_nbsp_guillemets"] = {"count": s4_count}

# ─────────────────────────────────────────────────
# M1: Corriger 3 entrees BYM tronquees
# ─────────────────────────────────────────────────
print("\n── M1: Corriger entrees BYM tronquees ──")
m1_count = 0
m1_entries = []

TRUNCATED_FIXES = {
    "LIANCE": {
        "mot": "ARCHE DE L'ALLIANCE",
        "label_fr": "Arche de l'alliance"
    },
    "NAISSANCED": {
        "mot": "NAISSANCE D'EN HAUT",
        "label_fr": "Naissance d'en haut"
    },
    "ROYAUMED": {
        "mot": "ROYAUME D'ELOHÎM",
        "label_fr": "Royaume d'Elohîm"
    },
}

for entry in bym:
    mot = entry.get("mot", "")
    if mot in TRUNCATED_FIXES:
        fix = TRUNCATED_FIXES[mot]
        old_mot = mot
        old_label = entry.get("label_fr", "")
        entry["mot"] = fix["mot"]
        entry["label_fr"] = fix["label_fr"]
        m1_count += 1
        m1_entries.append({"id": entry["id"], "old_mot": old_mot, "new_mot": fix["mot"], "old_label": old_label, "new_label": fix["label_fr"]})

print(f"  Corrige: {m1_count}")
for e in m1_entries:
    print(f"    {e['old_mot']} -> {e['new_mot']}")
report["M1_bym_truncated"] = {"count": m1_count, "entries": m1_entries}

# ─────────────────────────────────────────────────
# Update definition_length fields
# ─────────────────────────────────────────────────
print("\n── Mise a jour definition_length ──")
for dataset in [bym, easton, smith]:
    for entry in dataset:
        d = entry.get("definition", "")
        entry["definition_length"] = len(d)

# ─────────────────────────────────────────────────
# Save all files
# ─────────────────────────────────────────────────
print("\n── Sauvegarde ──")
save_json(BYM_PATH, bym)
print(f"  {BYM_PATH.name} sauvegarde")

save_json(EASTON_PATH, easton)
print(f"  {EASTON_PATH.name} sauvegarde")

save_json(SMITH_PATH, smith)
print(f"  {SMITH_PATH.name} sauvegarde")

save_json(CONCEPTS_PATH, concepts, use_bom=concepts_has_bom)
print(f"  {CONCEPTS_PATH.name} sauvegarde (BOM={concepts_has_bom})")

# ─────────────────────────────────────────────────
# Save report
# ─────────────────────────────────────────────────
report["meta"] = {
    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "files_modified": [
        str(BYM_PATH),
        str(EASTON_PATH),
        str(SMITH_PATH),
        str(CONCEPTS_PATH),
    ]
}

save_json(REPORT_PATH, report)
print(f"\n  Rapport: {REPORT_PATH}")

# ─────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────
print("\n══════════════════════════════════════")
print("  RESUME DES CORRECTIONS")
print("══════════════════════════════════════")
print(f"  A1  Smith definitions capitalisees:     {a1_count}")
print(f"  A2  Easton (See)->(Voir):               {a2_count}")
print(f"  A3  Easton i.e./e.g.:                   {a3_count}")
print(f"  A5  U+2011 normalises:                  {a5_easton + a5_concepts}")
print(f"  A6  Doubles espaces:                    {a6_bym + a6_smith}")
print(f"  A7  Easton def capitalisees:            {a7_count}")
print(f"  A8  Easton mot point final:             {a8_count}")
print(f"  A9  Concepts labels ALL CAPS:           {a9_count}")
print(f"  A10 Concepts secondary ALL CAPS:        {a10_count}")
print(f"  S1  BYM label_fr ALL CAPS:              {s1_count}")
print(f"  S2  Concepts aliases ALL CAPS:          {len(s2_entries)}")
print(f"  S3  BYM mot decompactes:                {s3_count}")
print(f"  S4  BYM NBSP guillemets:                {s4_count}")
print(f"  M1  BYM tronques:                       {m1_count}")
total = a1_count + a2_count + a3_count + a5_easton + a5_concepts + a6_bym + a6_smith + a7_count + a8_count + a9_count + a10_count + s1_count + len(s2_entries) + s3_count + s4_count + m1_count
print(f"  ──────────────────────────────────")
print(f"  TOTAL corrections:                      {total}")
print("══════════════════════════════════════")
