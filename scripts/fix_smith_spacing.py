#!/usr/bin/env python3
"""Fix Smith dictionary spacing, line breaks, and numbered lists."""
import json, re, sys, os

sys.stdout.reconfigure(encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SMITH_PATH = os.path.join(BASE, 'uploads', 'dictionnaires', 'smith', 'smith.entries.json')

with open(SMITH_PATH, 'r', encoding='utf-8-sig') as f:
    entries = json.load(f)

stats = {
    'numbered_lists': 0,
    'bold_sections_newlines': 0,
    'triple_newlines': 0,
    'orphan_brackets': 0,
    'closing_bold_fix': 0,
    'space_after_bold_header': 0,
}

for e in entries:
    d = e['definition']
    original = d

    # =====================================================
    # 1. NUMBERED LISTS: (1) ... (2) ... -> proper line breaks
    # Detect entries with sequential (1) (2) (3) patterns
    # Add line break before each numbered item
    # =====================================================
    # Pattern: text (N) -> text\n\n(N)
    # But NOT for bible refs like (1 Sam. or (1 Rois or single (N) that are chapter refs
    # A numbered list item: (N) followed by uppercase letter or descriptive text

    # First check if this entry has a genuine numbered list
    num_matches = list(re.finditer(r'\((\d+)\)\s', d))
    if len(num_matches) >= 2:
        # Check for sequential numbers starting from 1
        nums_found = []
        for m in num_matches:
            n = int(m.group(1))
            # Check what follows - if it's a Bible book name, skip
            after = d[m.end():m.end()+15]
            if re.match(r'(Sam|Rois|Chr|Cor|Tim|Pi|Jean|Thess|Mac)', after):
                continue
            nums_found.append((n, m.start()))

        has_list = False
        if nums_found:
            vals = [n for n, _ in nums_found]
            if 1 in vals and 2 in vals:
                has_list = True

        if has_list:
            # Add line breaks before each numbered item (N)
            # Work backwards to preserve positions
            for n, pos in sorted(nums_found, reverse=True):
                if n >= 1 and pos > 0:
                    # Check if already preceded by newline
                    before = d[max(0, pos-2):pos]
                    if '\n' not in before:
                        d = d[:pos] + '\n\n' + d[pos:]

            if d != original:
                stats['numbered_lists'] += 1

    prev = d
    # =====================================================
    # 2. BOLD SECTION HEADERS: ensure newline before **Title**
    # Pattern: text\n\n**Title -> already good
    # Pattern: text**Title -> text\n\n**Title
    # =====================================================
    # Ensure double newline before ** bold headers (but not at start)
    d = re.sub(r'([^\n])\n(\*\*)', r'\1\n\n\2', d)

    if d != prev:
        stats['bold_sections_newlines'] += 1

    prev = d
    # =====================================================
    # 3. Fix bold headers that swallowed the entire paragraph
    # Pattern: **Title text text** -> **Title**\n\nText text
    # A bold header should be short (< 80 chars)
    # =====================================================
    def fix_long_bold(m):
        content = m.group(1)
        # If the bold section is very long, it's likely a header + body
        if len(content) > 80:
            # Try to split at first sentence boundary after ~20 chars
            # Look for " — " or ". " as split point
            split_match = re.search(r'^(.{10,60}?)(\s*[—\-]\s*|\.\s+)', content)
            if split_match:
                header = split_match.group(1).strip()
                rest = content[split_match.end():].strip()
                separator = split_match.group(2).strip()
                if separator in ('—', '-'):
                    return '**' + header + '**\n\n' + rest
                else:
                    return '**' + header + '**\n\n' + rest
            else:
                # No good split point - just close bold after first phrase
                # Look for first comma or period
                split2 = re.search(r'^(.{10,60}?)[,.]\s', content)
                if split2:
                    header = content[:split2.end()-1].strip()
                    rest = content[split2.end():].strip()
                    return '**' + header + '**\n\n' + rest
        return m.group(0)

    d = re.sub(r'\*\*(.+?)\*\*', fix_long_bold, d, flags=re.DOTALL)

    if d != prev:
        stats['closing_bold_fix'] += 1

    prev = d
    # =====================================================
    # 4. Clean up triple+ newlines
    # =====================================================
    d = re.sub(r'\n{3,}', '\n\n', d)

    if d != prev:
        stats['triple_newlines'] += 1

    prev = d
    # =====================================================
    # 5. Clean orphan bracket fragments from old cross-refs
    # Pattern: 26]Word, [27Word -> remove these artifacts
    # =====================================================
    d = re.sub(r'\d+\]([A-Z][\w\s,]+?)(?=\n|$|\))', r'\1', d)
    # Clean [27Word patterns (missing opening bracket number)
    d = re.sub(r'\[\d+(?=[A-Z])', '', d)

    if d != prev:
        stats['orphan_brackets'] += 1

    prev = d
    # =====================================================
    # 6. Ensure space after bold header before next paragraph
    # =====================================================
    d = re.sub(r'\*\*\n([A-ZÉÈÊÀÂ])', r'**\n\n\1', d)

    if d != prev:
        stats['space_after_bold_header'] += 1

    # Final cleanup
    d = d.strip()
    d = re.sub(r'\n{3,}', '\n\n', d)

    e['definition'] = d
    e['definition_length'] = len(d)

# Save
with open(SMITH_PATH, 'w', encoding='utf-8') as f:
    json.dump(entries, f, ensure_ascii=False, indent=2)

print("=== SPACING & LIST FIXES ===")
for k, v in stats.items():
    print(f"  {k}: {v} entries modified")
print(f"\nTotal entries: {len(entries)}")

# Show samples
by_id = {e['id']: e for e in entries}
for name in ['Aarat', 'Apostle', 'Abijah Or Abijam', 'Amos, Book Of']:
    for e in entries:
        if e['mot'] == name:
            print(f"\n{'='*50}")
            print(f"--- {e['mot']} ---")
            print(e['definition'][:700])
            break
