#!/usr/bin/env python3
"""
Phase 4A : Construit le mapping de renvois "Voir ANGLAIS" → FR.

Lit concepts.json et construit un index inversé :
  ENGLISH_LABEL (uppercase) → {concept_id, label_fr}

Utilise :
- concept.label (FR)
- public_forms.english_labels
- aliases
- concept_id (pour les renvois vers des noms propres identiques FR/EN)

Produit :
- work/audit/voir-crossref-map.json
"""
import json
import sys
import re
import glob
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
DICT_DIR = ROOT / "uploads" / "dictionnaires"
AUDIT_DIR = ROOT / "work" / "audit"
OUT_JSON = AUDIT_DIR / "voir-crossref-map.json"

def main():
    with open(DICT_DIR / 'concepts.json', encoding='utf-8') as f:
        concepts = json.load(f)

    # Build reverse index: UPPERCASE_KEY → {concept_id, label_fr}
    index = {}

    for c in concepts:
        cid = c['concept_id']
        label = c.get('label', '')
        if not label:
            continue

        # Index by label (uppercase)
        key = label.upper()
        if key not in index:
            index[key] = {'concept_id': cid, 'label_fr': label}

        # Index by english_labels
        pf = c.get('public_forms', {}) or {}
        for en in (pf.get('english_labels', []) or []):
            key = en.upper()
            if key not in index:
                index[key] = {'concept_id': cid, 'label_fr': label}

        # Index by aliases
        for alias in (c.get('aliases', []) or []):
            key = alias.upper()
            if key not in index:
                index[key] = {'concept_id': cid, 'label_fr': label}

        # Index by concept_id transformed
        cid_label = cid.replace('-', ' ').replace('_', ' ').upper()
        if cid_label not in index:
            index[cid_label] = {'concept_id': cid, 'label_fr': label}

    print(f'Index size: {len(index)} entries')

    # Now scan ISBE definitions for "Voir [UPPERCASE]" patterns
    voir_re = re.compile(r'Voir\s+([A-ZÀ-Ý][A-ZÀ-Ý\s\-\',;()]+?)(?:\s*[.;,:\)\]]|$)')

    all_targets = {}
    for fp in sorted((DICT_DIR / 'isbe').glob('isbe-?.json')):
        with open(fp, encoding='utf-8-sig') as f:
            entries = json.load(f)
        for e in entries:
            defn = e.get('definition', '')
            matches = voir_re.findall(defn)
            for target in matches:
                target = target.strip().rstrip(',;.:)')
                if target and len(target) >= 2:
                    key = target.upper()
                    if key not in all_targets:
                        all_targets[key] = {'original': target, 'count': 0}
                    all_targets[key]['count'] += 1

    print(f'Unique Voir targets found: {len(all_targets)}')

    # Match targets to concepts
    resolved = {}
    unresolved = {}
    for key, info in all_targets.items():
        if key in index:
            resolved[key] = {
                'original': info['original'],
                'concept_id': index[key]['concept_id'],
                'label_fr': index[key]['label_fr'],
                'count': info['count'],
            }
        else:
            unresolved[key] = info

    print(f'Resolved: {len(resolved)}')
    print(f'Unresolved: {len(unresolved)}')

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump({
            'index_size': len(index),
            'targets_total': len(all_targets),
            'resolved_count': len(resolved),
            'unresolved_count': len(unresolved),
            'resolved': resolved,
            'unresolved': unresolved,
        }, f, ensure_ascii=False, indent=2)

    print(f'Output: {OUT_JSON}')
    print()
    print('=== Sample resolved ===')
    for k, v in list(resolved.items())[:15]:
        print(f'  {k:30s} → {v["label_fr"]!r} (concept {v["concept_id"]})')
    print()
    print('=== Sample unresolved ===')
    for k, v in list(unresolved.items())[:15]:
        print(f'  {k:30s} (x{v["count"]})')


if __name__ == '__main__':
    main()
