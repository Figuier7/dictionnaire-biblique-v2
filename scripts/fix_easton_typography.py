#!/usr/bin/env python3
"""Fix Easton dictionary typography to match Smith quality."""
import json, re, sys, os

sys.stdout.reconfigure(encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EASTON_PATH = os.path.join(BASE, 'uploads', 'dictionnaires', 'easton', 'easton.entries.json')

with open(EASTON_PATH, 'r', encoding='utf-8-sig') as f:
    entries = json.load(f)

stats = {
    'bracket_refs_cleaned': 0,
    'orphan_brackets_cleaned': 0,
    'straight_quotes_fixed': 0,
    'guillemet_spacing_fixed': 0,
    'numbered_lists_formatted': 0,
    'triple_newlines': 0,
    'voir_refs_cleaned': 0,
}

for e in entries:
    d = e['definition']
    original = d

    # =====================================================
    # 1. Clean double bracket refs: [[N]Word] -> Word
    # =====================================================
    d = re.sub(r'\[\[(\d+\][^\]]*)\]', lambda m: re.sub(r'\[\d+\]', '', m.group(1)).strip(), d)

    # =====================================================
    # 2. Clean single bracket refs: [N]WORD -> WORD
    # =====================================================
    prev = d
    d = re.sub(r'\[(\d+)\]', '', d)
    if d != prev:
        stats['bracket_refs_cleaned'] += 1

    # =====================================================
    # 3. Clean orphan bracket fragments: N]Word -> Word
    # =====================================================
    prev = d
    # Pattern: "number]Word" (orphan from [number]Word)
    d = re.sub(r'(?<!\[)(\d{1,4})\]([A-Z\u00c9\u00c8\u00ca\u00c0\u00c2])', r'\2', d)
    # Pattern: ", number]" at end
    d = re.sub(r',\s*\d+\]', '', d)
    if d != prev:
        stats['orphan_brackets_cleaned'] += 1

    # =====================================================
    # 4. Convert straight quotes to French guillemets
    #    "text" -> \u00ab\u00a0text\u00a0\u00bb
    #    But NOT for geographic coordinates (N' N")
    #    and NOT for abbreviated inches/seconds
    # =====================================================
    prev = d

    def fix_quotes(m):
        content = m.group(1)
        # Skip if it looks like coordinates (just numbers)
        if re.match(r'^\d+$', content.strip()):
            return m.group(0)
        return '\u00ab\u00a0' + content + '\u00a0\u00bb'

    d = re.sub(r'"([^"]+)"', fix_quotes, d)
    if d != prev:
        stats['straight_quotes_fixed'] += 1

    # =====================================================
    # 5. Fix guillemet spacing: ensure non-breaking space
    # =====================================================
    prev = d
    d = re.sub(r'\u00ab\s*', '\u00ab\u00a0', d)
    d = re.sub(r'\s*\u00bb', '\u00a0\u00bb', d)
    if d != prev:
        stats['guillemet_spacing_fixed'] += 1

    # =====================================================
    # 6. Format numbered lists: (1) ... (2) ... -> line breaks
    # =====================================================
    prev = d
    # Find entries with sequential (1) (2) patterns
    num_matches = list(re.finditer(r'\((\d+)\)\s', d))
    if len(num_matches) >= 2:
        nums_found = []
        for m in num_matches:
            n = int(m.group(1))
            after = d[m.end():m.end()+15]
            # Skip Bible refs: (1 Sam, (2 Rois, (1 Chr, etc.
            if re.match(r'(Sam|Rois|Chr|Cor|Tim|Pi|Jean|Thess|Mac)', after):
                continue
            nums_found.append((n, m.start()))

        has_list = False
        vals = [n for n, _ in nums_found]
        if 1 in vals and 2 in vals:
            has_list = True

        if has_list:
            for n, pos in sorted(nums_found, reverse=True):
                if n >= 1 and pos > 0:
                    before = d[max(0, pos-2):pos]
                    if '\n' not in before:
                        d = d[:pos] + '\n\n' + d[pos:]

    if d != prev:
        stats['numbered_lists_formatted'] += 1

    # =====================================================
    # 7. Clean (Voir [N]WORD.) -> (Voir WORD.)
    #    Already handled by step 2, but clean remaining
    # =====================================================
    prev = d
    # Pattern: "(Voir WORD.)" - already clean after step 2
    # Clean "Voir  " double spaces from removed [N]
    d = re.sub(r'Voir\s{2,}', 'Voir ', d)
    if d != prev:
        stats['voir_refs_cleaned'] += 1

    # =====================================================
    # 8. Clean up whitespace
    # =====================================================
    prev = d
    d = re.sub(r' +\n', '\n', d)
    d = re.sub(r'\n{3,}', '\n\n', d)
    d = re.sub(r'  +', ' ', d)
    d = d.strip()
    if d != prev:
        stats['triple_newlines'] += 1

    # =====================================================
    # 9. Rejoin paragraphs split mid-sentence
    # =====================================================
    lines = d.split('\n\n')
    if len(lines) > 1:
        merged = [lines[0]]
        for i in range(1, len(lines)):
            prev_line = merged[-1].rstrip()
            curr_line = lines[i].lstrip()

            should_join = False
            if prev_line and curr_line:
                last_char = prev_line[-1]
                if last_char.isalpha() and last_char.islower():
                    should_join = True
                if prev_line.endswith(' av'):
                    should_join = True
                if last_char in (',', '('):
                    should_join = True
                if curr_line and curr_line[0].islower():
                    should_join = True
                if curr_line.startswith('J.-C.'):
                    should_join = True

                # Don't join numbered items
                if re.match(r'^\(\d+\)', curr_line):
                    should_join = False
                if last_char in ('.', ')', '!', '?', ':', '\u00bb', ';'):
                    should_join = False

            if should_join:
                merged[-1] = prev_line + ' ' + curr_line
            else:
                merged.append(lines[i])

        d = '\n\n'.join(merged)

    e['definition'] = d
    e['definition_length'] = len(d)

# Save
with open(EASTON_PATH, 'w', encoding='utf-8') as f:
    json.dump(entries, f, ensure_ascii=False, indent=2)

print("=== EASTON TYPOGRAPHY FIXES ===")
for k, v in stats.items():
    print(f"  {k}: {v} entries")

# Final audit
print("\n=== POST-FIX AUDIT ===")
post = {
    'bracket_refs': sum(1 for e in entries if re.search(r'\[\d+\]', e['definition'])),
    'orphan_brackets': sum(1 for e in entries if re.search(r'(?<!\[)\d{2,}\][A-Z]', e['definition'])),
    'straight_quotes': sum(1 for e in entries if re.search(r'"[^"]{3,}"', e['definition'])),
    'unclosed_bold': sum(1 for e in entries if e['definition'].count('**') % 2 != 0),
    'triple_newlines': sum(1 for e in entries if '\n\n\n' in e['definition']),
    'guillemets': sum(1 for e in entries if '\u00ab' in e['definition']),
    'numbered_lists': sum(1 for e in entries if re.search(r'\n\n\(\d+\)', e['definition'])),
}
for k, v in post.items():
    print(f"  {k}: {v}")

# Show samples
print("\n=== FIXED SAMPLES ===")
for name in ['Aaron', 'Abraham', 'Abdi', 'Achbor', 'Amasai', 'Ablution']:
    for e in entries:
        if e['mot'] == name:
            print(f"\n--- {e['mot']} ---")
            print(e['definition'][:500])
            break
