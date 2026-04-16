#!/usr/bin/env python3
"""
APPLIQUE la passe C4 en ÉCRITURE sur les chunks isbe-*.json.

Stratégie révisée (2026-04-11) :
- `mot` INCHANGÉ (backref EN, utilisé par bible-v2-app.js pour le secondary display)
- `slug` INCHANGÉ (indexing interne)
- `label_fr` mis à jour avec la traduction FR
- `source_title_en` rempli avec `mot` si vide
- `aliases` : union des alias FR du mapping + `mot` EN original
- `definition`, `id`, `mot_restore`, `letter`, etc. : inchangés

Préserve :
- UTF-8 BOM
- Format compact single-line (pas d'indentation)
- Ordre des clés existantes dans chaque entrée

Safeguards :
- Backup préalable vérifié (work/backups/dictionnaires-*.zip)
- Aucune entrée non-listée dans le mapping n'est touchée
- Si `mot` ou `slug` serait modifié → abort (bug logique)
- Crée un fichier de trace work/audit/isbe-c4-apply-log.json avec les diffs appliqués
"""
import json
import sys
import glob
import os
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
ISBE_DIR = ROOT / "uploads" / "dictionnaires" / "isbe"
AUDIT_DIR = ROOT / "work" / "audit"
BACKUP_DIR = ROOT / "work" / "backups"
MAP_JSON = AUDIT_DIR / "isbe-c4-mot-map.json"
LOG_JSON = AUDIT_DIR / "isbe-c4-apply-log.json"


def check_backup():
    """Vérifie qu'un backup existe dans work/backups/"""
    if not BACKUP_DIR.exists():
        print("ERREUR : aucun dossier work/backups/ — faire un backup d'abord")
        return False
    backups = sorted(BACKUP_DIR.glob("dictionnaires-*.zip"))
    if not backups:
        print("ERREUR : aucun backup dictionnaires-*.zip trouvé")
        return False
    latest = backups[-1]
    size_mb = latest.stat().st_size / 1024 / 1024
    print(f"✓ Backup trouvé : {latest.name} ({size_mb:.1f} MB)")
    return True


def apply_entry(entry, spec):
    """Applique les modifications à une entrée. Retourne (modifié: bool, diffs: dict)"""
    before = {
        'mot': entry.get('mot', ''),
        'label_fr': entry.get('label_fr', ''),
        'slug': entry.get('slug', ''),
        'aliases': list(entry.get('aliases', [])),
        'source_title_en': entry.get('source_title_en', ''),
    }

    new_label_fr = spec['mot_fr']
    new_source_title_en = before['source_title_en'] or before['mot']

    existing_aliases = [a for a in before['aliases'] if a]
    new_aliases_to_add = []
    # 1) label_fr FR comme alias (si différent)
    if new_label_fr and new_label_fr not in existing_aliases:
        new_aliases_to_add.append(new_label_fr)
    # 2) alias supplémentaires du mapping
    for a in spec.get('aliases', []):
        if a and a not in existing_aliases and a not in new_aliases_to_add:
            new_aliases_to_add.append(a)
    # 3) le mot EN original (pour la recherche)
    if before['mot'] and before['mot'] not in existing_aliases and before['mot'] not in new_aliases_to_add:
        new_aliases_to_add.append(before['mot'])
    final_aliases = existing_aliases + new_aliases_to_add

    # Safeguards : on ne doit JAMAIS toucher mot ni slug
    # (on les laisse passer tels quels)

    # Application in-place
    changed = False
    diffs = {}

    if entry.get('label_fr', '') != new_label_fr:
        diffs['label_fr'] = {'before': entry.get('label_fr', ''), 'after': new_label_fr}
        entry['label_fr'] = new_label_fr
        changed = True

    if entry.get('source_title_en', '') != new_source_title_en:
        diffs['source_title_en'] = {'before': entry.get('source_title_en', ''), 'after': new_source_title_en}
        entry['source_title_en'] = new_source_title_en
        changed = True

    if entry.get('aliases', []) != final_aliases:
        diffs['aliases'] = {'before': list(entry.get('aliases', [])), 'after': final_aliases}
        entry['aliases'] = final_aliases
        changed = True

    # Paranoia check : mot et slug doivent être intacts
    if entry.get('mot', '') != before['mot']:
        raise RuntimeError(f"BUG: mot was modified for {entry.get('id')}")
    if entry.get('slug', '') != before['slug']:
        raise RuntimeError(f"BUG: slug was modified for {entry.get('id')}")

    return changed, diffs


def write_chunk(chunk_path, entries):
    """Écrit un chunk en préservant le format : UTF-8 BOM, compact single-line."""
    # Assemble the JSON manually with compact format
    payload = json.dumps(entries, ensure_ascii=False, separators=(', ', ': '))
    # Write with utf-8-sig to preserve BOM
    with open(chunk_path, 'w', encoding='utf-8-sig') as f:
        f.write(payload)


def main():
    if not check_backup():
        sys.exit(1)

    with open(MAP_JSON, 'r', encoding='utf-8-sig') as f:
        mapping_doc = json.load(f)
    mapped = {m['entry_id']: m for m in mapping_doc['mapped']}

    # Group by chunk
    by_chunk = {}
    for entry_id, spec in mapped.items():
        by_chunk.setdefault(spec['chunk'], []).append(entry_id)

    print(f"Mapping : {len(mapped)} entrées sur {len(by_chunk)} chunks")
    print()

    log = {
        'started_at': datetime.now().isoformat(),
        'strategy': 'revised_2026_04_11_keep_mot_slug',
        'chunks_modified': 0,
        'entries_modified': 0,
        'entries_no_op': 0,
        'chunks': {},
    }

    total_entries_modified = 0
    total_chunks_modified = 0

    for chunk_name in sorted(by_chunk.keys()):
        chunk_path = ISBE_DIR / chunk_name
        if not chunk_path.exists():
            print(f"SKIP : {chunk_name} non trouvé")
            continue

        with open(chunk_path, 'r', encoding='utf-8-sig') as f:
            entries = json.load(f)

        entry_by_id = {e['id']: e for e in entries}
        chunk_log = {'entries_modified': 0, 'entries_no_op': 0, 'patches': []}

        for entry_id in by_chunk[chunk_name]:
            spec = mapped[entry_id]
            if entry_id not in entry_by_id:
                print(f"  WARN {chunk_name} : entry {entry_id} introuvable")
                continue
            entry = entry_by_id[entry_id]
            changed, diffs = apply_entry(entry, spec)
            if changed:
                chunk_log['entries_modified'] += 1
                chunk_log['patches'].append({
                    'entry_id': entry_id,
                    'diffs': diffs,
                })
            else:
                chunk_log['entries_no_op'] += 1

        if chunk_log['entries_modified'] > 0:
            write_chunk(chunk_path, entries)
            total_chunks_modified += 1
            total_entries_modified += chunk_log['entries_modified']
            log['chunks'][chunk_name] = chunk_log
            print(f"  ✓ {chunk_name} : {chunk_log['entries_modified']} modif, {chunk_log['entries_no_op']} no-op")
        else:
            log['chunks'][chunk_name] = chunk_log
            print(f"  · {chunk_name} : 0 modif (no-op)")

    log['chunks_modified'] = total_chunks_modified
    log['entries_modified'] = total_entries_modified
    log['finished_at'] = datetime.now().isoformat()

    with open(LOG_JSON, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print()
    print(f"=== RÉSUMÉ ===")
    print(f"Chunks modifiés : {total_chunks_modified}/{len(by_chunk)}")
    print(f"Entrées modifiées : {total_entries_modified}")
    print(f"Log détaillé : {LOG_JSON}")


if __name__ == '__main__':
    main()
