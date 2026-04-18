#!/usr/bin/env python3
"""
fix_bym_post_punct_caps.py — Capitalise les lettres minuscules après ponctuation
de fin de phrase et après retour à la ligne dans BYM.

Règles :
  1. ". X" → ". X majuscule" (si le point n'est pas une abréviation biblique)
  2. "\nX"  → "\nX majuscule" (début de paragraphe/section)
  3. "! X" / "? X" → majuscule
  4. ";\nX" / ".\nX" → majuscule

Exclusions :
  - Abréviations bibliques (ge. ex. mt. jn. etc.)
  - Intérieur de guillemets « ... »
  - Références "Voir ..."
  - Chiffres
  - Mots immédiatement après "\nVoir" (c'est une référence, pas une phrase)
"""

import json
import re
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(r"C:\Users\caeng\OneDrive\Documents\A l'ombre du figuier\dictionnaire-biblique-main")
BYM_PATH = BASE / "uploads" / "dictionnaires" / "bym" / "bym-lexicon.entries.json"

raw = BYM_PATH.read_bytes()
has_bom = raw[:3] == b'\xef\xbb\xbf'
bym = json.loads(raw.decode('utf-8-sig') if has_bom else raw.decode('utf-8'))
print(f"BYM: {len(bym)} entrées chargées\n")

# ══════════════════════════════════════════════════
# Abréviations bibliques (le point n'est pas fin de phrase)
# ══════════════════════════════════════════════════
ABBREVIATIONS = {
    # Livres AT
    'ge', 'ex', 'lé', 'lév', 'no', 'de', 'jos', 'jas', 'jug', 'jg', 'ru',
    # Livres NT
    'mt', 'mr', 'mc', 'lu', 'jn', 'ac', 'ro', 'ga', 'ép', 'éph', 'ep',
    'ph', 'col', 'ti', 'tt', 'hé', 'ja', 'pi', 'phm', 'jud', 'ap',
    # Livres groupés
    'co', 'th', 'r', 's', 'chr',
    # Autres livres AT
    'ps', 'pr', 'ec', 'ct', 'es', 'jé', 'la', 'éz', 'da', 'os',
    'joë', 'am', 'ab', 'jon', 'mi', 'na', 'ha', 'so', 'ag', 'za',
    'mal', 'esd', 'né',
    # Abréviations courantes
    'av', 'env', 'cf', 'ch', 'v', 'ss', 'etc', 'vol', 'p',
    'c.-à-d', 'p. ex', 'chap', 'nb', 'bym',
}

# Lettres minuscules accentuées
LC = r'a-zàâéèêëïîôùûüçæœ'

def word_before_period(text, pos):
    """Extract the word immediately before position `pos` in text."""
    segment = text[max(0, pos - 25):pos].rstrip()
    m = re.search(r"([\w.'\-]+)$", segment)
    return m.group(1).lower() if m else ''

def inside_guillemets(text, pos):
    """Check if position is inside « ... »."""
    before = text[:pos]
    return before.count('«') > before.count('»')

def is_voir_line(text, pos):
    """Check if the line starting at pos is a 'Voir' reference line."""
    end = min(len(text), pos + 15)
    segment = text[pos:end].lower().lstrip()
    return segment.startswith('voir ')

def is_after_verse_ref(text, pos):
    """Check if period at pos follows a verse reference like '3:17'."""
    before = text[max(0, pos - 10):pos]
    return bool(re.search(r'\d+:\d+$', before.rstrip()))

# ══════════════════════════════════════════════════
# PHASE 1: ". lowercase" → ". Uppercase"
# ══════════════════════════════════════════════════
print("── Phase 1: Capitalisation après \". \" ──")

p1_count = 0
p1_entries = 0

for entry in bym:
    d = entry.get("definition", "")
    if not d:
        continue

    chars = list(d)
    changed = False

    for m in re.finditer(r'\.( )([' + LC + r'])', d):
        period_pos = m.start()       # position of "."
        char_pos = m.start(2)        # position of lowercase letter

        # Skip abbreviations
        wb = word_before_period(d, period_pos)
        # Remove trailing period from word
        wb_clean = wb.rstrip('.')
        if wb_clean in ABBREVIATIONS:
            continue
        if len(wb_clean) <= 1 and not wb_clean.isdigit():
            continue

        # Skip ordinals: 1er. 2e.
        if re.search(r'\d+(er|e|ème)$', wb_clean):
            continue

        # Skip inside guillemets
        if inside_guillemets(d, period_pos):
            continue

        # Skip if "Voir" line context
        after = d[char_pos:char_pos + 10].lower()
        if after.startswith('voir '):
            # "Voir" should itself be capitalized, so actually proceed
            pass

        chars[char_pos] = d[char_pos].upper()
        changed = True
        p1_count += 1

    if changed:
        entry["definition"] = ''.join(chars)
        p1_entries += 1

print(f"  {p1_count} capitalisations dans {p1_entries} entrées")

# ══════════════════════════════════════════════════
# PHASE 2: "\nlowercase" → "\nUppercase"
# (début de paragraphe/section après retour à la ligne)
# ══════════════════════════════════════════════════
print("\n── Phase 2: Capitalisation après retour à la ligne ──")

p2_count = 0
p2_entries = 0

for entry in bym:
    d = entry.get("definition", "")
    if not d:
        continue

    chars = list(d)
    changed = False

    for m in re.finditer(r'\n([' + LC + r'])', d):
        char_pos = m.start(1)

        # Skip if this is a continuation inside guillemets
        if inside_guillemets(d, char_pos):
            continue

        # Skip reference lines that start with verse-like patterns
        # e.g., "\nge. 49:1-28." — these are wrapped references
        after = d[char_pos:min(len(d), char_pos + 8)].lower()
        # Skip if it's a biblical book abbreviation
        first_word = re.match(r'([a-zéèàç]+)', after)
        if first_word and first_word.group(1) in ABBREVIATIONS:
            continue

        # Skip if preceded by opening line with ":" or "," (list continuation)
        before_newline = d[max(0, char_pos - 2):char_pos]
        # If it's just a wrapped line (not a new sentence), skip
        # Heuristic: if the line before ends with a comma, it's continuation
        line_before_end = d[max(0, char_pos - 40):char_pos - 1].rstrip()
        if line_before_end and line_before_end[-1] == ',':
            continue

        # Check if the word after \n is "et" or "ou" (conjunction continuation)
        if after.startswith('et ') or after.startswith('ou '):
            continue

        chars[char_pos] = d[char_pos].upper()
        changed = True
        p2_count += 1

    if changed:
        entry["definition"] = ''.join(chars)
        p2_entries += 1

print(f"  {p2_count} capitalisations dans {p2_entries} entrées")

# ══════════════════════════════════════════════════
# PHASE 3: "! lowercase" / "? lowercase" → majuscule
# ══════════════════════════════════════════════════
print("\n── Phase 3: Capitalisation après \"!\" et \"?\" ──")

p3_count = 0
p3_entries = 0

for entry in bym:
    d = entry.get("definition", "")
    if not d:
        continue

    chars = list(d)
    changed = False

    for m in re.finditer(r'[!?][ \n]([' + LC + r'])', d):
        char_pos = m.start(1)

        if inside_guillemets(d, char_pos):
            continue

        chars[char_pos] = d[char_pos].upper()
        changed = True
        p3_count += 1

    if changed:
        entry["definition"] = ''.join(chars)
        p3_entries += 1

print(f"  {p3_count} capitalisations dans {p3_entries} entrées")

# ══════════════════════════════════════════════════
# Update definition_length
# ══════════════════════════════════════════════════
for entry in bym:
    entry["definition_length"] = len(entry.get("definition", ""))

# ══════════════════════════════════════════════════
# Save
# ══════════════════════════════════════════════════
text = json.dumps(bym, ensure_ascii=False, indent=2)
if has_bom:
    BYM_PATH.write_bytes(b'\xef\xbb\xbf' + text.encode('utf-8'))
else:
    BYM_PATH.write_bytes(text.encode('utf-8'))
print(f"\n  Sauvegardé: {BYM_PATH.name}")

# ══════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════
total = p1_count + p2_count + p3_count
total_entries = len(set(
    [e['id'] for e in bym if any(c.isupper() for c in 'placeholder')]
))  # just use sums
print(f"\n══════════════════════════════════════════════")
print(f"  RÉSUMÉ — MAJUSCULES APRÈS PONCTUATION BYM")
print(f"══════════════════════════════════════════════")
print(f"  Phase 1 — Après \". \":      {p1_count} ({p1_entries} entrées)")
print(f"  Phase 2 — Après \"\\n\":      {p2_count} ({p2_entries} entrées)")
print(f"  Phase 3 — Après \"!\" / \"?\":  {p3_count} ({p3_entries} entrées)")
print(f"  ──────────────────────────────────────────")
print(f"  TOTAL:  {total} capitalisations")
print(f"══════════════════════════════════════════════")
