#!/usr/bin/env python3
"""
Patch C2/C3 : surgical patch sur concepts.json et concept-meta.json
pour les concepts dont le label est un résidu anglais ISBE.

Principe :
- Pour chaque concept C2/C3 candidat, on récupère son ENTRÉE ISBE primaire
  (celle qui a été translatée par C4 + C4.2, donc label_fr est en français)
- On met à jour concept.label, display_titles.primary à partir de ce label_fr
- Le label EN original devient display_titles.secondary (backref historique)
- public_forms.french_reference aligné
- public_forms.english_labels enrichi avec le mot EN original
- concept.aliases enrichi avec label_fr + mot EN
- Mirror dans concept-meta.json : l, p, s, e mis à jour
- concept_id NE CHANGE JAMAIS (URL stable)
- u (url_slug dans concept-meta) NE CHANGE PAS non plus

Deux modes :
- dry-run (défaut) : produit work/audit/isbe-c2c3-dry-run.json + .md, aucune écriture
- apply (--apply) : écrit concepts.json et concept-meta.json

Safeguards :
- Backup vérifié obligatoire
- Tous les champs inchangés sont strictement identiques avant/après
- Log détaillé par concept
"""
import json
import sys
import argparse
import glob
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
DICT_DIR = ROOT / "uploads" / "dictionnaires"
ISBE_DIR = DICT_DIR / "isbe"
AUDIT_DIR = ROOT / "work" / "audit"
BACKUP_DIR = ROOT / "work" / "backups"
FOCUSED_JSON = AUDIT_DIR / "isbe-residues-focused.json"
CONCEPTS_JSON = DICT_DIR / "concepts.json"
CONCEPT_META_JSON = DICT_DIR / "concept-meta.json"
BUGS_JSON = AUDIT_DIR / "isbe-c4-json-bugs.json"
DRY_RUN_JSON = AUDIT_DIR / "isbe-c2c3-dry-run.json"
DRY_RUN_MD = AUDIT_DIR / "isbe-c2c3-dry-run.md"
APPLY_LOG_JSON = AUDIT_DIR / "isbe-c2c3-apply-log.json"


def check_backup():
    if not BACKUP_DIR.exists():
        return False
    backups = sorted(BACKUP_DIR.glob("dictionnaires-*.zip"))
    if not backups:
        return False
    print(f"✓ Backup : {backups[-1].name}")
    return True


def load_isbe_entries():
    """Indexe toutes les entrées ISBE par entry_id."""
    by_id = {}
    for fp in sorted(ISBE_DIR.glob("isbe-?.json")):
        with open(fp, 'r', encoding='utf-8-sig') as f:
            for e in json.load(f):
                by_id[e['id']] = e
    return by_id


def pick_primary_isbe_entry(concept, isbe_by_id):
    """Choisit l'entrée ISBE principale pour dériver le label FR.
    Préférence : is_primary_for_role=True et display_role=deep_read.
    Fallback : première entry ISBE."""
    isbe_entries = [e for e in concept.get('entries', []) if e.get('dictionary') == 'isbe']
    if not isbe_entries:
        return None
    # Prefer primary + deep_read
    for e in isbe_entries:
        if e.get('is_primary_for_role') and e.get('display_role') == 'deep_read':
            entry_data = isbe_by_id.get(e['entry_id'])
            if entry_data:
                return entry_data
    # Fallback : first with is_primary_for_role
    for e in isbe_entries:
        if e.get('is_primary_for_role'):
            entry_data = isbe_by_id.get(e['entry_id'])
            if entry_data:
                return entry_data
    # Last fallback : first available
    for e in isbe_entries:
        entry_data = isbe_by_id.get(e['entry_id'])
        if entry_data:
            return entry_data
    return None


def build_patch(concept, isbe_entry):
    """Construit le diff pour un concept à patcher.
    Retourne (patch_concept, patch_meta, summary) ou (None, None, reason)."""
    # Le label FR source = entry.label_fr de l'entrée ISBE primaire
    new_label = isbe_entry.get('label_fr', '').strip()
    if not new_label:
        return None, None, "label_fr entrée ISBE vide"
    old_label = concept.get('label', '').strip()
    # Si déjà identique, no-op
    if new_label == old_label:
        return None, None, "no-op (label déjà à jour)"

    # Le secondary = mot EN original
    new_secondary = isbe_entry.get('mot', '').strip()

    # ─── Patch concepts.json ───
    before_concept = json.loads(json.dumps(concept))  # deep copy

    patched = json.loads(json.dumps(concept))
    patched['label'] = new_label
    # display_titles
    dt = patched.get('display_titles', {}) or {}
    dt['primary'] = new_label
    if new_secondary and new_secondary != new_label:
        dt['secondary'] = new_secondary
        dt['strategy'] = 'french_first'
    else:
        dt['secondary'] = ''
        dt['strategy'] = 'french_only'
    patched['display_titles'] = dt
    # public_forms
    pf = patched.get('public_forms', {}) or {}
    pf['french_reference'] = new_label
    en_labels = list(pf.get('english_labels', []) or [])
    if new_secondary and new_secondary != new_label and new_secondary not in en_labels:
        en_labels.append(new_secondary)
    pf['english_labels'] = en_labels
    patched['public_forms'] = pf
    # aliases (concept level)
    aliases = list(patched.get('aliases', []) or [])
    for candidate in [new_label, new_secondary]:
        if candidate and candidate not in aliases:
            aliases.append(candidate)
    patched['aliases'] = aliases

    # ─── Patch concept-meta.json ───
    # Uses short key format : l, r, p, s, c, a, e, d, u
    # We update l (label), p (primary), s (secondary)
    # We do NOT touch c (category), a (alpha), e (excerpt), d (definition), u (url_slug), r (restored)
    meta_patch = {
        'l': new_label,
        'p': new_label,
        's': new_secondary if new_secondary and new_secondary != new_label else '',
    }

    summary = {
        'concept_id': concept['concept_id'],
        'old_label': old_label,
        'new_label': new_label,
        'new_secondary': new_secondary if new_secondary != new_label else '',
        'isbe_source': isbe_entry['id'],
    }

    return patched, meta_patch, summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Apply changes (default: dry-run)')
    args = parser.parse_args()

    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'Mode : {mode}')
    print()

    if args.apply and not check_backup():
        print("ERREUR : backup manquant")
        sys.exit(1)

    # Load all data
    print("Chargement concepts.json...")
    with open(CONCEPTS_JSON, 'r', encoding='utf-8-sig') as f:
        concepts = json.load(f)
    concept_by_id = {c['concept_id']: c for c in concepts}
    print(f"  {len(concepts)} concepts")

    print("Chargement concept-meta.json...")
    with open(CONCEPT_META_JSON, 'r', encoding='utf-8-sig') as f:
        meta = json.load(f)
    print(f"  {len(meta)} meta entries")

    print("Chargement ISBE chunks...")
    isbe_by_id = load_isbe_entries()
    print(f"  {len(isbe_by_id)} ISBE entries")

    print("Chargement cluster C2/C3 focused...")
    with open(FOCUSED_JSON, 'r', encoding='utf-8-sig') as f:
        focused = json.load(f)
    c2_ids = {it['concept_id'] for it in focused['clusters']['C2_focused']['items']}
    c3_ids = {it['concept_id'] for it in focused['clusters']['C3_focused']['items']}
    candidate_ids = sorted(c2_ids | c3_ids)
    print(f"  C2: {len(c2_ids)} | C3: {len(c3_ids)} | total: {len(candidate_ids)}")
    print()

    with open(BUGS_JSON, 'r', encoding='utf-8-sig') as f:
        bug_ids = {b['id'] for b in json.load(f)['items']}

    patches = []
    skipped_no_isbe = []
    skipped_bug_only = []
    skipped_no_op = []
    skipped_not_in_meta = []

    # Special : concepts with NO ISBE source (like sacrifice-quotidien, temple-de-salomon)
    # These are Easton-only, we DON'T patch their labels because they're already correct.
    # We only process concepts that have an ISBE entry providing the translated label_fr.

    for cid in candidate_ids:
        c = concept_by_id.get(cid)
        if not c:
            continue
        isbe_entry = pick_primary_isbe_entry(c, isbe_by_id)
        if not isbe_entry:
            skipped_no_isbe.append(cid)
            continue
        # Skip if the primary ISBE entry is a known JSON-bug chunk.
        # We do NOT fall back to another ISBE entry because it may be semantically
        # unrelated (e.g. concept `sacrifice` primary = isbe-007190 (bug) ;
        # fallback isbe-007191 = "Sacrifice, Human" is a DIFFERENT sub-topic).
        # These concepts will be properly translated during the separate
        # "28 chunks JSON corrompus" repair chantier.
        if isbe_entry['id'] in bug_ids:
            skipped_bug_only.append(cid)
            continue

        patched_concept, meta_patch, summary = build_patch(c, isbe_entry)
        if patched_concept is None:
            if summary == "no-op (label déjà à jour)":
                skipped_no_op.append(cid)
            continue

        if cid not in meta:
            skipped_not_in_meta.append(cid)
            # Still we patch concepts.json even if not in meta (log-only)

        patches.append({
            'concept_id': cid,
            'summary': summary,
            'patched_concept': patched_concept,
            'meta_patch': meta_patch,
            'meta_before': dict(meta.get(cid, {})),
        })

    # ─── Dry-run reporting ───
    report = {
        'mode': mode,
        'timestamp': datetime.now().isoformat(),
        'candidates_total': len(candidate_ids),
        'patches_count': len(patches),
        'skipped_no_isbe': len(skipped_no_isbe),
        'skipped_bug_only': len(skipped_bug_only),
        'skipped_no_op': len(skipped_no_op),
        'skipped_not_in_meta': len(skipped_not_in_meta),
        'patches': [
            {
                'concept_id': p['concept_id'],
                'summary': p['summary'],
                'meta_before': p['meta_before'],
                'meta_after': {**p['meta_before'], **p['meta_patch']},
            }
            for p in patches
        ],
        'skipped_details': {
            'no_isbe': skipped_no_isbe,
            'bug_only': skipped_bug_only,
            'no_op': skipped_no_op,
            'not_in_meta': skipped_not_in_meta,
        },
    }

    with open(DRY_RUN_JSON, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # MD
    lines = []
    lines.append(f'# C2/C3 concepts patch — {mode}')
    lines.append('')
    lines.append(f'- Candidats         : **{len(candidate_ids)}**')
    lines.append(f'- Patches proposés  : **{len(patches)}**')
    lines.append(f'- Skip sans ISBE    : {len(skipped_no_isbe)}')
    lines.append(f'- Skip bugs only    : {len(skipped_bug_only)}')
    lines.append(f'- Skip no-op        : {len(skipped_no_op)}')
    lines.append(f'- Skip hors meta    : {len(skipped_not_in_meta)}')
    lines.append('')
    lines.append('## Patches')
    lines.append('')
    lines.append('| concept_id | old label | → new label | secondary (EN) | source ISBE |')
    lines.append('|---|---|---|---|---|')
    for p in patches:
        s = p['summary']
        lines.append(f"| `{s['concept_id']}` | {s['old_label']} | **{s['new_label']}** | {s['new_secondary'] or '—'} | `{s['isbe_source']}` |")
    lines.append('')
    if skipped_no_isbe:
        lines.append('## Skippés (sans source ISBE — Easton/Smith only, labels déjà OK)')
        lines.append('')
        for cid in skipped_no_isbe:
            lines.append(f'- `{cid}`')
        lines.append('')
    if skipped_bug_only:
        lines.append('## Skippés (seule entrée ISBE est un chunk corrompu)')
        lines.append('')
        for cid in skipped_bug_only:
            lines.append(f'- `{cid}`')
        lines.append('')

    with open(DRY_RUN_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Patches proposés : {len(patches)}")
    print(f"Skip no-op       : {len(skipped_no_op)}")
    print(f"Skip sans ISBE   : {len(skipped_no_isbe)}")
    print(f"Skip bugs-only   : {len(skipped_bug_only)}")
    print(f"Rapport MD       : {DRY_RUN_MD}")
    print(f"Rapport JSON     : {DRY_RUN_JSON}")

    # ─── Apply mode ───
    if args.apply:
        print()
        print("=== APPLICATION ===")
        # Apply to concepts.json
        for p in patches:
            for i, c in enumerate(concepts):
                if c['concept_id'] == p['concept_id']:
                    concepts[i] = p['patched_concept']
                    break
        # Apply to concept-meta.json
        for p in patches:
            cid = p['concept_id']
            if cid in meta:
                meta[cid].update(p['meta_patch'])

        # Write SANS BOM (PHP json_decode ne tolère pas le BOM UTF-8)
        print(f"Écriture concepts.json ({len(concepts)} concepts)...")
        with open(CONCEPTS_JSON, 'w', encoding='utf-8') as f:
            json.dump(concepts, f, ensure_ascii=False, indent=2)

        print(f"Écriture concept-meta.json ({len(meta)} entries)...")
        with open(CONCEPT_META_JSON, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))

        # Log
        with open(APPLY_LOG_JSON, 'w', encoding='utf-8') as f:
            json.dump({
                'applied_at': datetime.now().isoformat(),
                'patches_applied': len(patches),
                'concepts_file': str(CONCEPTS_JSON),
                'meta_file': str(CONCEPT_META_JSON),
                'patches': [p['summary'] for p in patches],
            }, f, ensure_ascii=False, indent=2)

        print(f"✓ {len(patches)} patches appliqués")
        print(f"Log : {APPLY_LOG_JSON}")


if __name__ == '__main__':
    main()
