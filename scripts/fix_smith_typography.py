#!/usr/bin/env python3
"""Fix Smith dictionary typography for better readability."""
import json, re, sys, os

sys.stdout.reconfigure(encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SMITH_PATH = os.path.join(BASE, 'uploads', 'dictionnaires', 'smith', 'smith.entries.json')

with open(SMITH_PATH, 'r', encoding='utf-8-sig') as f:
    entries = json.load(f)

stats = {
    'plus_headers': 0,
    'double_bracket_refs': 0,
    'single_bracket_refs': 0,
    'straight_quotes': 0,
    'guillemet_spacing': 0,
    'double_spaces': 0,
    'trailing_whitespace': 0,
    'dash_normalization': 0,
}

for e in entries:
    d = e['definition']
    original = d

    # =====================================================
    # 1. Convert + headers to bold markdown
    # Pattern: "\n+ Text" or "\n\n+ Text" -> "\n\n**Text**"
    # Also handle start of definition: "+ Text"
    # =====================================================
    def fix_plus_header(m):
        prefix = m.group(1)  # newlines before
        text = m.group(2).strip()
        if text:
            return prefix + '**' + text + '**'
        return prefix

    # + at start of line (after newlines)
    d = re.sub(r'(\n+)\+ ([^\n]+)', fix_plus_header, d)
    # + at very start of definition
    d = re.sub(r'^(\+ )([^\n]+)', lambda m: '**' + m.group(2).strip() + '**', d)

    if d != original:
        stats['plus_headers'] += 1

    prev = d
    # =====================================================
    # 2. Clean double bracket refs: [[N]Word] -> Word
    # Pattern: [[123]Some Word] -> Some Word
    # Also handle [[123]Word, [124]Word2] -> Word, Word2
    # =====================================================
    # First handle complex patterns: [[N]Word, [N]Word2, ...]
    def clean_double_bracket(m):
        inner = m.group(1)
        # Remove all [N] patterns inside
        cleaned = re.sub(r'\[(\d+)\]', '', inner)
        # Clean up extra spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    d = re.sub(r'\[\[(\d+\][^\]]*)\]', clean_double_bracket, d)

    if d != prev:
        stats['double_bracket_refs'] += 1

    prev = d
    # =====================================================
    # 3. Clean single bracket refs: [N]Word -> Word
    # But preserve the referenced word
    # =====================================================
    d = re.sub(r'\[(\d+)\]', '', d)

    if d != prev:
        stats['single_bracket_refs'] += 1

    prev = d
    # =====================================================
    # 4. Convert straight quotes to French guillemets
    # "text" -> « text »
    # =====================================================
    def fix_straight_quotes(m):
        content = m.group(1)
        return '\u00ab\u00a0' + content + '\u00a0\u00bb'

    d = re.sub(r'"([^"]+)"', fix_straight_quotes, d)

    if d != prev:
        stats['straight_quotes'] += 1

    prev = d
    # =====================================================
    # 5. Fix guillemet spacing: «text» -> « text »
    # Ensure non-breaking space inside guillemets
    # =====================================================
    # Fix opening guillemet: « or «\s -> «\u00a0
    d = re.sub(r'«\s*', '«\u00a0', d)
    # Fix closing guillemet: \s*» -> \u00a0»
    d = re.sub(r'\s*»', '\u00a0»', d)

    if d != prev:
        stats['guillemet_spacing'] += 1

    prev = d
    # =====================================================
    # 6. Normalize dashes
    # -- -> — (em dash)
    # =====================================================
    d = d.replace(' -- ', ' — ')
    d = d.replace('--', '—')

    if d != prev:
        stats['dash_normalization'] += 1

    prev = d
    # =====================================================
    # 7. Clean up whitespace
    # =====================================================
    # Remove trailing spaces on lines
    d = re.sub(r' +\n', '\n', d)
    # Remove excessive blank lines (3+ -> 2)
    d = re.sub(r'\n{3,}', '\n\n', d)
    # Remove trailing whitespace
    d = d.strip()

    if d != prev:
        stats['trailing_whitespace'] += 1

    prev = d
    # =====================================================
    # 8. Clean double spaces
    # =====================================================
    d = re.sub(r'  +', ' ', d)

    if d != prev:
        stats['double_spaces'] += 1

    # Update entry
    e['definition'] = d
    e['definition_length'] = len(d)

# Save
with open(SMITH_PATH, 'w', encoding='utf-8') as f:
    json.dump(entries, f, ensure_ascii=False, indent=2)

print("=== TYPOGRAPHY FIXES APPLIED ===")
for k, v in stats.items():
    print(f"  {k}: {v} entries modified")
print(f"\nTotal entries: {len(entries)}")

# Show some examples of the fixes
print("\n=== SAMPLE RESULTS ===")
samples = ['smith-000003', 'smith-000339', 'smith-003000', 'smith-004000']
by_id = {e['id']: e for e in entries}
for sid in samples:
    e = by_id.get(sid)
    if e:
        print(f"\n--- {e['mot']} ---")
        print(e['definition'][:400])
