#!/usr/bin/env python3
"""
fix_paragraphs.py — Corrections de capitalisation et structure paragraphique.

BYM:
  1. Capitaliser le corps de définition après l'étymologie italique
  2. Séparer les références "voir" sur leur propre ligne

Smith:
  3. Ajouter \n\n avant les numéros inline (1), (2), (3)...
"""

import json
import re
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(r"C:\Users\caeng\OneDrive\Documents\A l'ombre du figuier\dictionnaire-biblique-main")
BYM_PATH = BASE / "uploads/dictionnaires/bym/bym-lexicon.entries.json"
SMITH_PATH = BASE / "uploads/dictionnaires/smith/smith.entries.json"

def load_json(path):
    raw = path.read_bytes()
    if raw[:3] == b'\xef\xbb\xbf':
        return json.loads(raw.decode('utf-8-sig'))
    return json.loads(raw.decode('utf-8'))

def save_json(path, data):
    text = json.dumps(data, ensure_ascii=False, indent=2)
    path.write_bytes(text.encode('utf-8'))

# ═══════════════════════════════════════════════════
# Load
# ═══════════════════════════════════════════════════
bym = load_json(BYM_PATH)
smith = load_json(SMITH_PATH)
print(f"BYM: {len(bym)} entrées")
print(f"Smith: {len(smith)} entrées")

# ═══════════════════════════════════════════════════
# BYM Phase 1: Capitaliser le corps après étymologie
# ═══════════════════════════════════════════════════
print("\n── BYM: Capitaliser corps après étymologie ──")

bym_cap_count = 0
bym_cap_examples = []

for entry in bym:
    d = entry.get("definition", "")
    if not d:
        continue

    # Pattern: etymology ends with "._" or "._\n" or just "_\n"
    # Then the body text follows, possibly after whitespace/newlines
    # We need to find the LAST closing italic marker that ends the etymology
    # and capitalize the first alpha char after it

    new_d = d
    changed = False

    # Strategy: find positions after "._" patterns followed by whitespace then lowercase
    # Common patterns:
    #   "...»._ \nlowercase..."
    #   "...»._\nlowercase..."
    #   "...»._ lowercase..."

    # Find all positions where italic etymology ends
    # Pattern: underscore followed by whitespace/newlines, then lowercase letter
    matches = list(re.finditer(r'(\._\s*\n\s*|\._\s+)', new_d))

    for m in matches:
        end_pos = m.end()
        if end_pos < len(new_d):
            char = new_d[end_pos]
            # Skip if it's a quote mark « (part of etymology continuation)
            if char == '«' or char == '_':
                continue
            if char.isalpha() and char.islower():
                new_d = new_d[:end_pos] + char.upper() + new_d[end_pos+1:]
                changed = True

    # Also handle: after closing italic that's not at end of etymology
    # Pattern: "_\n" followed by lowercase (single underscore closing italic mid-definition)
    # But only capitalize after the LAST italic section (etymology)

    if changed:
        entry["definition"] = new_d
        bym_cap_count += 1
        if len(bym_cap_examples) < 5:
            bym_cap_examples.append({
                "id": entry["id"], "mot": entry["mot"],
                "preview": new_d[:120]
            })

print(f"  Capitalisées: {bym_cap_count}")
for ex in bym_cap_examples:
    print(f"    {ex['mot']}: {ex['preview'][:80]}...")

# ═══════════════════════════════════════════════════
# BYM Phase 2: Séparer "voir" sur ligne propre
# ═══════════════════════════════════════════════════
print("\n── BYM: Séparer références 'voir' ──")

bym_voir_count = 0

for entry in bym:
    d = entry.get("definition", "")
    if not d:
        continue

    # Pattern: text ending with period/punctuation, then " voir " or ". voir "
    # But NOT if "voir" is already at start of a line
    # And NOT if it's inside a sentence (like "pour voir comment...")

    # Target: ". voir ex." or ". voir ge." or ". voir no." etc. at END of definition
    # These are bibliographic references

    # Match: after a period, space, then "voir" followed by a biblical reference pattern
    # Biblical refs: "ge.", "ex.", "lé.", "no.", "de.", "jo.", "ju.", "1 s.", "2 s.", etc.

    # Only separate if "voir" is clearly a bibliographic reference (followed by book abbreviation)
    bib_pattern = r'(?<=\.)\s+(voir\s+(?:[a-zéèêëàâäîïôöùûüç0-9]|[A-ZÉÈÊËÀÂÄÎÏÔÖÙÛÜÇ])[a-zéèêëàâäîïôöùûüç]*\.?\s+\d)'

    new_d = re.sub(bib_pattern, lambda m: '\n' + m.group(1).capitalize(), d)

    # Simpler approach: find ". voir " or ". Voir " followed by abbreviated book ref
    # at position where it's NOT already preceded by \n
    if new_d == d:
        # Try: period + space + "voir" + space + book abbreviation
        pattern = r'(\.) ((?:[Vv]oir)\s+(?:ge|ex|lé|no|de|jo|ju|ru|1\s*s|2\s*s|1\s*r|2\s*r|1\s*ch|2\s*ch|es|jé|éz|da|os|am|mi|na|ha|za|ma|mt|mr|mc|lu|jn|ac|ro|1\s*co|2\s*co|ga|ep|ph|col|1\s*th|2\s*th|1\s*ti|2\s*ti|ti|phm|hé|ja|1\s*pi|2\s*pi|1\s*jn|2\s*jn|3\s*jn|ap|ps)[\.\s])'

        new_d = re.sub(pattern, r'\1\n\2', d, flags=re.IGNORECASE)

    if new_d != d:
        # Ensure "voir" is capitalized at start of new line
        new_d = re.sub(r'\nvoir\s', lambda m: '\nVoir ', new_d)
        entry["definition"] = new_d
        bym_voir_count += 1

print(f"  Séparées: {bym_voir_count}")

# ═══════════════════════════════════════════════════
# Smith: Ajouter \n\n avant numéros inline
# ═══════════════════════════════════════════════════
print("\n── Smith: Ajouter paragraphes avant numéros inline ──")

smith_para_count = 0
smith_para_instances = 0

for entry in smith:
    d = entry.get("definition", "")
    if not d:
        continue

    # Pattern: inline numbered section — NOT preceded by \n
    # Match: non-newline char + space + (digit) where digit is 1-9
    # But avoid matching things like "en l'an (1)" mid-sentence
    # Target: clear section numbering (1), (2), (3)...

    # First check if entry has numbered sections at all
    if not re.search(r'\(\d+\)', d):
        continue

    # Find inline instances: preceded by space (not \n), followed by text
    # We want to add \n\n before (digit) when preceded by ". " or similar sentence-ending

    # Strategy: add \n\n before (N) when:
    #   - preceded by ". " or ".) " or text + space
    #   - NOT already preceded by \n
    #   - There are at least 2 numbered items (confirms it's a list, not a date)

    numbers_found = re.findall(r'\((\d+)\)', d)
    if len(numbers_found) < 2:
        continue

    # Check if they form a sequence (1, 2, 3...)
    nums = sorted(set(int(n) for n in numbers_found))
    if nums[0] != 1:
        continue

    new_d = d
    counter = [0]

    # Replace: space before (N) with \n\n, but NOT if already preceded by \n
    def add_para_before_number(match):
        before = match.group(1)
        number = match.group(2)
        # Don't add if already at start of line
        if before == '\n':
            return match.group(0)
        counter[0] += 1
        return f"{before}\n\n({number})"

    # Match: char + space + (digit)
    new_d = re.sub(r'(.)\s+\((\d+)\)', add_para_before_number, new_d)

    if counter[0] > 0:
        entry["definition"] = new_d
        smith_para_count += 1
        smith_para_instances += counter[0]

print(f"  Entrées modifiées: {smith_para_count}")
print(f"  Alinéas ajoutés: {smith_para_instances}")

# ═══════════════════════════════════════════════════
# Update definition_length
# ═══════════════════════════════════════════════════
for dataset in [bym, smith]:
    for entry in dataset:
        entry["definition_length"] = len(entry.get("definition", ""))

# ═══════════════════════════════════════════════════
# Save
# ═══════════════════════════════════════════════════
print("\n── Sauvegarde ──")
save_json(BYM_PATH, bym)
print(f"  {BYM_PATH.name}")
save_json(SMITH_PATH, smith)
print(f"  {SMITH_PATH.name}")

# ═══════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════
print("\n══════════════════════════════════════")
print("  RÉSUMÉ")
print("══════════════════════════════════════")
print(f"  BYM capitalisations:     {bym_cap_count}")
print(f"  BYM 'voir' séparés:      {bym_voir_count}")
print(f"  Smith alinéas ajoutés:   {smith_para_instances} dans {smith_para_count} entrées")
total = bym_cap_count + bym_voir_count + smith_para_count
print(f"  TOTAL entrées modifiées: {total}")
print("══════════════════════════════════════")
