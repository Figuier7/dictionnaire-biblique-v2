#!/usr/bin/env python3
"""
Repair 28 chunks ISBE dont le champ `definition` contient un JSON brut
concaténé (bug du pipeline de traduction OpenAI).

Stratégie :
1. Parse tous les fragments JSON concaténés dans chaque definition
2. Extrait toutes les entries imbriquées de tous les fragments
3. Choisit la plus longue définition FR exploitable
4. Remplace `definition` du chunk par ce texte propre
5. Safeguards : ne touche pas mot, slug, id

Modes : dry-run (défaut, écrit rapport) ou --apply (écrit les chunks)
"""
import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
ISBE_DIR = ROOT / "uploads" / "dictionnaires" / "isbe"
AUDIT_DIR = ROOT / "work" / "audit"
BACKUP_DIR = ROOT / "work" / "backups"
BUGS_JSON = AUDIT_DIR / "isbe-c4-json-bugs.json"
OUT_JSON = AUDIT_DIR / "isbe-repair-bugs-report.json"
OUT_MD = AUDIT_DIR / "isbe-repair-bugs-report.md"
LOG_JSON = AUDIT_DIR / "isbe-repair-bugs-log.json"


def is_french_text(text):
    """Heuristique : le texte est majoritairement en français ?"""
    if not text or len(text) < 100:
        return False
    # Chercher des marqueurs français clairs
    fr_markers = [' le ', ' la ', ' les ', ' des ', ' du ', ' dans ', ' pour ',
                  ' qui ', ' que ', ' est ', ' sont ', ' avec ', ' sur ',
                  ' à ', 'é', 'è', 'à', 'ê', 'ô', 'ù', 'ç', 'œ']
    fr_count = sum(1 for m in fr_markers if m in text)
    # Chercher des marqueurs anglais clairs
    en_markers = [' the ', ' of ', ' and ', ' in ', ' for ', ' which ',
                  ' that ', ' these ', ' with ', ' are ', ' were ', ' is ',
                  ' has ', ' have ', ' been ', ' from ']
    en_count = sum(1 for m in en_markers if m in text)
    return fr_count > en_count


def extract_all_fragments(defn):
    """Parse tous les fragments JSON concaténés possibles depuis une string.
    Retourne list[dict] des fragments parseables."""
    fragments = []
    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(defn):
        # Skip whitespace
        while idx < len(defn) and defn[idx] in ' \t\n\r':
            idx += 1
        if idx >= len(defn):
            break
        try:
            obj, end = decoder.raw_decode(defn, idx)
            fragments.append(obj)
            idx = end
        except json.JSONDecodeError as ex:
            # Try to skip forward : look for next { character
            next_brace = defn.find('{"entries"', idx + 1)
            if next_brace == -1:
                break
            idx = next_brace
    return fragments


def extract_definitions(fragments):
    """Depuis une liste de fragments dict {'entries': [...]},
    retourne toutes les définitions trouvées en ordre."""
    defs = []
    for frag in fragments:
        if not isinstance(frag, dict):
            continue
        entries = frag.get('entries', [])
        if not isinstance(entries, list):
            continue
        for ent in entries:
            if not isinstance(ent, dict):
                continue
            d = ent.get('definition', '')
            mot = ent.get('mot', '')
            if isinstance(d, str) and d:
                defs.append({
                    'def': d,
                    'mot': mot,
                    'length': len(d),
                    'is_fr': is_french_text(d),
                })
    return defs


def pick_best_definition(defs, target_mot):
    """Construit la meilleure définition possible.

    Deux stratégies :
    A) S'il existe UNE définition qui a déjà une grande longueur (> 5000 chars),
       on la prend telle quelle (article complet).
    B) Sinon, on concatène toutes les définitions en français avec leurs
       sous-titres de section (reconstitution de l'article morcelé)."""
    if not defs:
        return None

    # Filtrer seulement les FR
    fr_defs = [d for d in defs if d['is_fr']]
    if not fr_defs:
        fr_defs = defs  # fallback

    # Stratégie A : une seule grosse définition suffit
    long_defs = [d for d in fr_defs if d['length'] > 5000]
    if long_defs:
        # Prendre la plus longue, priorité à celle dont le mot correspond
        target_lower = (target_mot or '').lower()
        def score_a(d):
            s = d['length']
            if d['mot'].lower() == target_lower:
                s += 100000
            return s
        long_defs.sort(key=score_a, reverse=True)
        return long_defs[0]

    # Stratégie B : concaténer tout avec sous-titres de section
    # Dédupliquer les définitions identiques
    seen = set()
    unique = []
    for d in fr_defs:
        key = d['def'][:200]
        if key in seen:
            continue
        seen.add(key)
        unique.append(d)

    if not unique:
        return None

    # Construire un texte concaténé avec sous-titres
    parts = []
    for d in unique:
        mot = d['mot'].strip()
        text = d['def'].strip()
        if mot and mot != target_mot and len(mot) < 80:
            # Sous-titre utilisable
            parts.append(f'\n\n=== {mot} ===\n{text}')
        else:
            parts.append(text)
    merged = '\n'.join(parts).strip()
    return {
        'def': merged,
        'mot': target_mot or unique[0]['mot'],
        'length': len(merged),
        'is_fr': True,
        'strategy': 'concatenated',
    }


def repair_chunk(chunk_path, bug_ids):
    """Repair toutes les entrées d'un chunk qui sont dans bug_ids.
    Retourne (entries_modifiées, report_par_entry)."""
    with open(chunk_path, 'r', encoding='utf-8-sig') as f:
        entries = json.load(f)

    reports = []
    modified = 0
    for e in entries:
        if e['id'] not in bug_ids:
            continue
        defn = e.get('definition', '')
        fragments = extract_all_fragments(defn)
        all_defs = extract_definitions(fragments)
        best = pick_best_definition(all_defs, e.get('mot', ''))

        rep = {
            'entry_id': e['id'],
            'mot': e.get('mot', ''),
            'original_def_len': len(defn),
            'fragments_found': len(fragments),
            'definitions_found': len(all_defs),
            'best_def_len': best['length'] if best else 0,
            'best_is_fr': best['is_fr'] if best else False,
            'best_mot': best['mot'] if best else '',
            'repaired': False,
        }

        if best and best['length'] > 100:
            # Apply repair
            e['definition'] = best['def']
            e['definition_length'] = best['length']
            # Recalculate render mode
            if best['length'] <= 420:
                e['render_mode_default'] = 'direct'
            elif best['length'] <= 1800:
                e['render_mode_default'] = 'preview_expand'
            else:
                e['render_mode_default'] = 'deep_read'
            rep['repaired'] = True
            rep['new_render_mode'] = e['render_mode_default']
            modified += 1
        else:
            rep['note'] = 'No usable fragment found — manual repair needed'

        reports.append(rep)

    return modified, reports, entries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'Mode : {mode}')
    print()

    if args.apply and not (BACKUP_DIR.exists() and list(BACKUP_DIR.glob('dictionnaires-*.zip'))):
        print("ERREUR : backup manquant")
        sys.exit(1)

    with open(BUGS_JSON, encoding='utf-8') as f:
        bugs_doc = json.load(f)
    bugs = bugs_doc['items']

    # Group by chunk file
    by_chunk = {}
    for b in bugs:
        by_chunk.setdefault(b['file'], set()).add(b['id'])

    all_reports = []
    total_modified = 0
    for chunk_name in sorted(by_chunk.keys()):
        chunk_path = ISBE_DIR / chunk_name
        bug_ids = by_chunk[chunk_name]
        print(f'=== {chunk_name} ({len(bug_ids)} bugs) ===')
        modified, reports, entries = repair_chunk(chunk_path, bug_ids)
        for r in reports:
            status = 'OK' if r['repaired'] else 'FAIL'
            print(f"  [{status}] {r['entry_id']} {r['mot'][:40]:40s}  orig={r['original_def_len']:>6}  frags={r['fragments_found']:>2}  defs={r['definitions_found']:>3}  best={r['best_def_len']:>6}  fr={'Y' if r['best_is_fr'] else 'N'}")
        all_reports.extend(reports)
        total_modified += modified

        if args.apply and modified:
            payload = json.dumps(entries, ensure_ascii=False, separators=(', ', ': '))
            with open(chunk_path, 'w', encoding='utf-8-sig') as f:
                f.write(payload)
            print(f'  ✓ {chunk_name} écrit')
        print()

    print(f'=== RÉSUMÉ {mode} ===')
    print(f'Total entries à repair : {len(all_reports)}')
    print(f'Reparées               : {total_modified}')
    print(f'Échecs                 : {len(all_reports) - total_modified}')

    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump({
            'mode': mode,
            'total': len(all_reports),
            'repaired': total_modified,
            'reports': all_reports,
        }, f, ensure_ascii=False, indent=2)

    if args.apply:
        with open(LOG_JSON, 'w', encoding='utf-8') as f:
            json.dump({
                'applied_at': datetime.now().isoformat(),
                'pass': 'JSON-bugs-repair',
                'repaired': total_modified,
                'reports': all_reports,
            }, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
