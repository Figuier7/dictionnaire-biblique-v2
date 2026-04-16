#!/usr/bin/env python3
"""
Patch C7 ad-hoc : traite les 6 concepts signalés par l'utilisateur
(résidus anglais manqués par l'audit C2/C3 précédent).

Concepts :
  builder         → Bâtisseur
  householder     → Maître de maison
  shoulder        → Épaule
  shoulder-blade  → Omoplate
  shoulder-piece  → Épaulières de l'éphod
  soldering       → Soudure

Stratégie identique aux passes précédentes :
- chunks ISBE : label_fr + aliases (ne touche pas mot/slug)
- concepts.json : label + display_titles + public_forms + aliases
- concept-meta.json : l, p, s
- concept_id JAMAIS modifié (URL stable)
- Écriture UTF-8 sans BOM sur concepts.json/concept-meta.json (PHP json_decode strict)

Modes : dry-run (défaut) ou --apply
"""
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
DICT_DIR = ROOT / "uploads" / "dictionnaires"
ISBE_DIR = DICT_DIR / "isbe"
AUDIT_DIR = ROOT / "work" / "audit"
BACKUP_DIR = ROOT / "work" / "backups"

CONCEPTS_JSON = DICT_DIR / "concepts.json"
CONCEPT_META_JSON = DICT_DIR / "concept-meta.json"
LOG_JSON = AUDIT_DIR / "isbe-c7-apply-log.json"

# Mapping fixé avec user le 2026-04-11 :
C7_MAP = {
    'builder': {
        'entry_id': 'isbe-001671',
        'chunk': 'isbe-B.json',
        'mot_en': 'Builder',
        'fr': 'Bâtisseur',
        'aliases': ['Constructeur'],
    },
    'householder': {
        'entry_id': 'isbe-004274',
        'chunk': 'isbe-H.json',
        'mot_en': 'Householder',
        'fr': 'Maître de maison',
        'aliases': ['Chef de famille'],
    },
    'shoulder': {
        'entry_id': 'isbe-007735',
        'chunk': 'isbe-S.json',
        'mot_en': 'Shoulder',
        'fr': 'Épaule',
        'aliases': [],
    },
    'shoulder-blade': {
        'entry_id': 'isbe-007736',
        'chunk': 'isbe-S.json',
        'mot_en': 'Shoulder-Blade',
        'fr': 'Omoplate',
        'aliases': [],
    },
    'shoulder-piece': {
        'entry_id': 'isbe-007737',
        'chunk': 'isbe-S.json',
        'mot_en': 'Shoulder-Piece',
        'fr': 'Épaulière (de l\'éphod)',
        'aliases': ['Épaulière'],
    },
    'soldering': {
        'entry_id': 'isbe-007902',
        'chunk': 'isbe-S.json',
        'mot_en': 'Soldering',
        'fr': 'Soudure',
        'aliases': ['Soudage'],
    },
}


def check_backup():
    if not BACKUP_DIR.exists():
        return False
    backups = sorted(BACKUP_DIR.glob("dictionnaires-*.zip"))
    if not backups:
        return False
    print(f"Backup trouvé : {backups[-1].name}")
    return True


def patch_chunk_entry(entry, spec):
    """Patch une entrée de chunk. Renvoie True si modifié."""
    before_label_fr = entry.get('label_fr', '')
    before_src_en = entry.get('source_title_en', '')
    before_aliases = list(entry.get('aliases', []))

    new_label_fr = spec['fr']
    new_src_en = before_src_en or spec['mot_en']
    # Aliases : FR + extra + mot EN pour recherche
    new_aliases = list(before_aliases)
    for cand in [new_label_fr] + spec.get('aliases', []) + [spec['mot_en']]:
        if cand and cand not in new_aliases:
            new_aliases.append(cand)

    changed = (
        entry.get('label_fr') != new_label_fr or
        entry.get('source_title_en') != new_src_en or
        entry.get('aliases') != new_aliases
    )

    if changed:
        entry['label_fr'] = new_label_fr
        entry['source_title_en'] = new_src_en
        entry['aliases'] = new_aliases

    # Safeguards : mot et slug doivent rester intacts
    assert entry.get('mot') == spec['mot_en'], f"BUG: mot changed for {entry.get('id')}"
    # (slug ne devrait pas être modifié par ce code)

    return changed


def patch_concept(concept, spec):
    """Patch un concept. Renvoie True si modifié."""
    new_label = spec['fr']
    new_secondary = spec['mot_en']

    before_label = concept.get('label', '')
    if before_label == new_label:
        return False

    concept['label'] = new_label
    dt = concept.get('display_titles', {}) or {}
    dt['primary'] = new_label
    dt['secondary'] = new_secondary if new_secondary != new_label else ''
    dt['strategy'] = 'french_first' if new_secondary != new_label else 'french_only'
    concept['display_titles'] = dt

    pf = concept.get('public_forms', {}) or {}
    pf['french_reference'] = new_label
    en_labels = list(pf.get('english_labels', []) or [])
    if new_secondary and new_secondary not in en_labels:
        en_labels.append(new_secondary)
    pf['english_labels'] = en_labels
    concept['public_forms'] = pf

    aliases = list(concept.get('aliases', []) or [])
    for cand in [new_label] + spec.get('aliases', []) + [new_secondary]:
        if cand and cand not in aliases:
            aliases.append(cand)
    concept['aliases'] = aliases

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Apply (default: dry-run)')
    args = parser.parse_args()

    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'Mode : {mode}')
    print()

    if args.apply and not check_backup():
        print("ERREUR : backup manquant")
        sys.exit(1)

    # Group by chunk
    by_chunk = {}
    for cid, spec in C7_MAP.items():
        spec['concept_id'] = cid
        by_chunk.setdefault(spec['chunk'], []).append(spec)

    # ─── 1) Patch chunks ───
    print('=== CHUNKS ISBE ===')
    chunk_patches = []
    chunks_modified_data = {}
    for chunk_name in sorted(by_chunk.keys()):
        chunk_path = ISBE_DIR / chunk_name
        with open(chunk_path, 'r', encoding='utf-8-sig') as f:
            entries = json.load(f)
        by_id = {e['id']: e for e in entries}
        mods = []
        for spec in by_chunk[chunk_name]:
            entry = by_id.get(spec['entry_id'])
            if not entry:
                print(f"  ⚠ {chunk_name} : entry {spec['entry_id']} introuvable")
                continue
            before = {
                'label_fr': entry.get('label_fr', ''),
                'source_title_en': entry.get('source_title_en', ''),
                'aliases': list(entry.get('aliases', [])),
            }
            changed = patch_chunk_entry(entry, spec)
            after = {
                'label_fr': entry.get('label_fr', ''),
                'source_title_en': entry.get('source_title_en', ''),
                'aliases': list(entry.get('aliases', [])),
            }
            status = 'MODIFIED' if changed else 'NO-OP'
            print(f"  [{chunk_name}] {spec['entry_id']} ({spec['mot_en']} → {spec['fr']}) {status}")
            if changed:
                mods.append({
                    'entry_id': spec['entry_id'],
                    'before': before,
                    'after': after,
                })
        if mods:
            chunk_patches.append({'chunk': chunk_name, 'mods': mods})
            chunks_modified_data[chunk_name] = entries

    # ─── 2) Patch concepts + meta ───
    print()
    print('=== CONCEPTS + META ===')
    with open(CONCEPTS_JSON, 'r', encoding='utf-8') as f:
        concepts = json.load(f)
    with open(CONCEPT_META_JSON, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    concept_patches = []
    for cid, spec in C7_MAP.items():
        c = next((c for c in concepts if c['concept_id'] == cid), None)
        if not c:
            print(f"  ⚠ concept {cid} introuvable")
            continue
        before_label = c.get('label', '')
        changed = patch_concept(c, spec)
        if changed:
            # Also patch meta
            if cid in meta:
                meta[cid]['l'] = spec['fr']
                meta[cid]['p'] = spec['fr']
                meta[cid]['s'] = spec['mot_en']
            concept_patches.append({
                'concept_id': cid,
                'before_label': before_label,
                'new_label': spec['fr'],
                'new_secondary': spec['mot_en'],
            })
            print(f"  [{cid}] {before_label!r} → {spec['fr']!r} / ({spec['mot_en']})")
        else:
            print(f"  [{cid}] NO-OP (déjà à jour)")

    # ─── 3) Apply if requested ───
    if args.apply:
        print()
        print('=== ÉCRITURE ===')
        # Chunks
        for chunk_name, entries in chunks_modified_data.items():
            chunk_path = ISBE_DIR / chunk_name
            payload = json.dumps(entries, ensure_ascii=False, separators=(', ', ': '))
            with open(chunk_path, 'w', encoding='utf-8-sig') as f:
                f.write(payload)
            print(f"  ✓ {chunk_name} écrit")

        # concepts.json (sans BOM)
        with open(CONCEPTS_JSON, 'w', encoding='utf-8') as f:
            json.dump(concepts, f, ensure_ascii=False, indent=2)
        print(f"  ✓ concepts.json écrit (sans BOM)")

        # concept-meta.json (sans BOM)
        with open(CONCEPT_META_JSON, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))
        print(f"  ✓ concept-meta.json écrit (sans BOM)")

        # Log
        log = {
            'applied_at': datetime.now().isoformat(),
            'pass': 'C7-ad-hoc-user-signalled',
            'chunks_patches': chunk_patches,
            'concept_patches': concept_patches,
        }
        with open(LOG_JSON, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        print(f"Log : {LOG_JSON}")

    print()
    print(f"=== RÉSUMÉ {mode} ===")
    print(f"Chunks modifiés  : {len(chunk_patches)}")
    print(f"Concepts patchés : {len(concept_patches)}")


if __name__ == '__main__':
    main()
