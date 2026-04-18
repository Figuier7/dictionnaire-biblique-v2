#!/usr/bin/env python3
"""
fix_smith_paragraphs.py — Insère des sauts de paragraphe (\n\n) dans les
définitions longues de Smith qui n'en ont pas.

Algorithme :
  1. Pour chaque entrée > 400 chars sans \n\n existant :
  2. Parcourir le texte et repérer les frontières de phrase (". [A-Z]")
  3. Quand on a accumulé >= MIN_BLOCK chars depuis le dernier saut,
     insérer \n\n à la prochaine frontière de phrase éligible
  4. Préférer couper après une référence biblique entre parenthèses :
     ") Nouvelle phrase" ou ") —" ou après "etc."

Règles de prudence :
  - Ne pas couper à l'intérieur de parenthèses ou guillemets
  - Ne pas couper au milieu d'une phrase
  - Ne pas couper si le bloc restant serait trop court (< 100 chars)
  - Respecter les paragraphes existants
"""

import json
import re
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(r"C:\Users\caeng\OneDrive\Documents\A l'ombre du figuier\dictionnaire-biblique-main")
SMITH_PATH = BASE / "uploads" / "dictionnaires" / "smith" / "smith.entries.json"

raw = SMITH_PATH.read_bytes()
has_bom = raw[:3] == b'\xef\xbb\xbf'
smith = json.loads(raw.decode('utf-8-sig') if has_bom else raw.decode('utf-8'))
print(f"Smith: {len(smith)} entrées chargées\n")

# ══════════════════════════════════════════════════
# Paramètres
# ══════════════════════════════════════════════════
MIN_BLOCK = 350       # Minimum chars before we look for a break point
IDEAL_BLOCK = 500     # Ideal block size — prefer breaks near this length
MIN_TAIL = 80         # Don't break if remainder would be < this
MIN_ENTRY_LEN = 400   # Only process entries longer than this

# ══════════════════════════════════════════════════
# Détection des frontières de phrase
# ══════════════════════════════════════════════════

# Sentence-ending patterns: ". A" or ") A" or ".) A" etc.
# We find all positions where a paragraph break would be natural
SENTENCE_END = re.compile(
    r'(?:'
    r'\)\s*'           # After closing parenthesis
    r'|'
    r'[.!?]\s+'        # After period/exclamation/question + space
    r'|'
    r'[.!?]\)\s+'      # After period inside closing paren + space
    r')'
    r'(?=[A-ZÀ-ÿ«\—\-\(])'   # Followed by uppercase, guillemet, dash, or opening paren
)

# Stronger break points: after parenthetical bible references
STRONG_BREAK = re.compile(
    r'\)\s+(?=[A-ZÀ-ÿ])'   # ") Uppercase" — very natural break after reference
)

def find_break_points(text):
    """Find all candidate break positions in text.
    Returns list of (position, strength) where position is where to insert \n\n.
    """
    breaks = []
    for m in SENTENCE_END.finditer(text):
        # Position = end of the match (just before the uppercase letter)
        pos = m.end()
        # Determine strength
        matched = m.group(0)
        # Check if inside parentheses at this point
        before = text[:m.start()]
        open_parens = before.count('(') - before.count(')')
        if open_parens > 0:
            continue  # Inside parentheses, skip

        # Check if inside guillemets
        open_g = before.count('«') - before.count('»')
        if open_g > 0:
            continue

        # Strong break: after closing paren
        if ')' in matched:
            breaks.append((pos, 2))  # strength 2 = strong
        else:
            breaks.append((pos, 1))  # strength 1 = normal

    return breaks


def insert_paragraphs(text):
    """Insert \n\n paragraph breaks into text at natural positions."""
    if len(text) < MIN_ENTRY_LEN:
        return text, 0

    breaks = find_break_points(text)
    if not breaks:
        return text, 0

    # Find existing break positions (already has \n\n)
    existing_breaks = set()
    for m in re.finditer(r'\n\n', text):
        existing_breaks.add(m.start())

    # Walk through text and decide where to insert breaks
    insert_positions = []
    last_break = 0  # Position of last paragraph break (start of text or last \n\n)

    # Update last_break to account for existing \n\n
    all_existing = sorted(m.start() for m in re.finditer(r'\n\n', text))

    # Merge candidate breaks with existing structure
    # Process the text in segments between existing breaks
    segment_starts = [0] + [pos + 2 for pos in all_existing]  # +2 to skip \n\n
    segment_ends = all_existing + [len(text)]

    for seg_start, seg_end in zip(segment_starts, segment_ends):
        segment_len = seg_end - seg_start
        if segment_len < MIN_BLOCK + MIN_TAIL:
            continue  # Segment too short to need breaks

        # Find break candidates within this segment
        seg_breaks = [(pos, strength) for pos, strength in breaks
                      if seg_start < pos < seg_end]

        if not seg_breaks:
            continue

        # Walk through and pick break points
        cursor = seg_start
        for pos, strength in seg_breaks:
            dist = pos - cursor
            remaining = seg_end - pos

            if dist < MIN_BLOCK:
                continue  # Too soon since last break

            if remaining < MIN_TAIL:
                continue  # Would leave too short a tail

            # Good break point
            insert_positions.append(pos)
            cursor = pos

    # Apply insertions (reverse order to preserve positions)
    if not insert_positions:
        return text, 0

    result = list(text)
    for pos in sorted(insert_positions, reverse=True):
        # Check we're not already at a \n\n
        if pos >= 2 and text[pos-2:pos] == '\n\n':
            continue
        if pos < len(text) - 1 and text[pos:pos+2] == '\n\n':
            continue

        # Insert \n\n — replace the space before the uppercase with \n\n
        # We need to find the exact space to replace
        # The break position is just before the start of the new sentence
        # There should be a space just before pos
        if pos > 0 and result[pos - 1] == ' ':
            result[pos - 1] = '\n'
            result.insert(pos, '\n')
        else:
            result.insert(pos, '\n')
            result.insert(pos, '\n')

    return ''.join(result), len(insert_positions)


# ══════════════════════════════════════════════════
# Appliquer
# ══════════════════════════════════════════════════
print("── Insertion de paragraphes ──\n")

total_breaks = 0
entries_modified = 0
details = []

for entry in smith:
    d = entry.get("definition", "")
    if not d or len(d) < MIN_ENTRY_LEN:
        continue

    new_d, num_breaks = insert_paragraphs(d)

    if num_breaks > 0:
        entry["definition"] = new_d
        entry["definition_length"] = len(new_d)
        total_breaks += num_breaks
        entries_modified += 1
        details.append((entry["id"], entry["mot"], len(d), num_breaks))

# Show results
for eid, mot, length, nb in sorted(details, key=lambda x: -x[3])[:30]:
    print(f"  {mot} ({eid}): {nb} paragraphes ajoutés ({length} chars)")

if len(details) > 30:
    print(f"  ... et {len(details) - 30} autres entrées")

# ══════════════════════════════════════════════════
# Save
# ══════════════════════════════════════════════════
text = json.dumps(smith, ensure_ascii=False, indent=2)
if has_bom:
    SMITH_PATH.write_bytes(b'\xef\xbb\xbf' + text.encode('utf-8'))
else:
    SMITH_PATH.write_bytes(text.encode('utf-8'))
print(f"\n  Sauvegardé: {SMITH_PATH.name}")

# ══════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════
print(f"\n══════════════════════════════════════════════")
print(f"  RÉSUMÉ — PARAGRAPHES SMITH")
print(f"══════════════════════════════════════════════")
print(f"  Entrées modifiées:     {entries_modified}")
print(f"  Paragraphes ajoutés:   {total_breaks}")
print(f"  Entrées inchangées:    {len(smith) - entries_modified}")
print(f"══════════════════════════════════════════════")
