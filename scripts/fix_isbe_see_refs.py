#!/usr/bin/env python3
"""Fix remaining See→Voir cross-references in ISBE chunks."""
import json, re, os, glob, sys

isbe_dir = 'uploads/dictionnaires/isbe'
fixes = 0

for path in sorted(glob.glob(os.path.join(isbe_dir, 'isbe-*.json'))):
    with open(path, 'r', encoding='utf-8-sig') as f:
        entries = json.load(f)

    changed = False
    for e in entries:
        d = e['definition']
        new_d = d
        # "See X" where X starts with uppercase
        new_d = re.sub(r'\bSee\s+(?=[A-Z])', 'Voir ', new_d)
        # "(see X)" -> "(Voir X)"
        new_d = re.sub(r'\(see\s+(?=[A-Z])', '(Voir ', new_d)
        # "see also" -> "Voir aussi"
        new_d = re.sub(r'\bsee also\b', 'Voir aussi', new_d, flags=re.IGNORECASE)
        # "; see X" after semicolon
        new_d = re.sub(r';\s*see\s+(?=[A-Z])', '; Voir ', new_d)

        if new_d != d:
            e['definition'] = new_d
            fixes += 1
            changed = True

    if changed:
        with open(path, 'w', encoding='utf-8-sig') as f:
            json.dump(entries, f, ensure_ascii=False)

sys.stdout.reconfigure(encoding='utf-8')
print(f"See->Voir fixes: {fixes}")

# Verify
remaining = 0
for path in sorted(glob.glob(os.path.join(isbe_dir, 'isbe-*.json'))):
    with open(path, 'r', encoding='utf-8-sig') as f:
        entries = json.load(f)
    for e in entries:
        for m in re.finditer(r'\b[Ss]ee\s+[A-Z]', e['definition']):
            remaining += 1

print(f"Remaining See: {remaining}")
