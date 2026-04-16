#!/usr/bin/env python3
"""
Dry-run de la passe C4 : simule la correction des champs `label_fr` et
`aliases` dans les chunks isbe-*.json à partir de la table
work/audit/isbe-c4-mot-map.json.

STRATÉGIE RÉVISÉE (2026-04-11) :
- `mot` reste INCHANGÉ (= backref anglais, consommé par bible-v2-app.js comme secondary display)
- `source_title_en` rempli avec `mot` si vide (contrat explicite du backref)
- `label_fr` mis à jour avec la traduction FR
- `aliases` : union des alias FR du mapping + le `mot` EN original (pour la recherche)
- `slug` INCHANGÉ (indexing interne)
- `definition`, `id`, `mot_restore`, `letter` : inchangés

Le rendu bible-v2-app.js ligne 2135-2143 produira alors :
- primary = label_fr (FR)
- secondary = mot (EN)
Les deux formes sont visibles, recherche trouve les deux, URL inchangées.

LECTURE SEULE. Produit :
- work/audit/isbe-c4-dry-run.json : patch détaillé avant/après par entrée
- work/audit/isbe-c4-dry-run.md   : rapport humain pour revue

Pour exécuter en mode écriture : python scripts/apply_isbe_c4.py (après validation).
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
ISBE_DIR = ROOT / "uploads" / "dictionnaires" / "isbe"
AUDIT_DIR = ROOT / "work" / "audit"
MAP_JSON = AUDIT_DIR / "isbe-c4-mot-map.json"
OUT_JSON = AUDIT_DIR / "isbe-c4-dry-run.json"
OUT_MD = AUDIT_DIR / "isbe-c4-dry-run.md"


def make_slug(text):
    """Produit un slug compatible avec la convention existante des chunks."""
    norm = unicodedata.normalize('NFD', text)
    norm = ''.join(c for c in norm if unicodedata.category(c) != 'Mn')
    norm = norm.lower()
    norm = re.sub(r"[^a-z0-9]+", "-", norm).strip("-")
    return norm


def main():
    with open(MAP_JSON, 'r', encoding='utf-8-sig') as f:
        mapping_doc = json.load(f)
    mapped = {m['entry_id']: m for m in mapping_doc['mapped']}

    # Index entries à modifier par chunk
    by_chunk = {}
    for entry_id, spec in mapped.items():
        by_chunk.setdefault(spec['chunk'], []).append(entry_id)

    patches = []
    warnings = []

    for chunk_name in sorted(by_chunk.keys()):
        chunk_path = ISBE_DIR / chunk_name
        if not chunk_path.exists():
            warnings.append(f"CHUNK MISSING: {chunk_path}")
            continue
        with open(chunk_path, 'r', encoding='utf-8-sig') as f:
            entries = json.load(f)
        entry_by_id = {e['id']: e for e in entries}

        for entry_id in by_chunk[chunk_name]:
            spec = mapped[entry_id]
            if entry_id not in entry_by_id:
                warnings.append(f"ENTRY MISSING: {entry_id} in {chunk_name}")
                continue
            e = entry_by_id[entry_id]

            before = {
                'mot': e.get('mot', ''),
                'label_fr': e.get('label_fr', ''),
                'slug': e.get('slug', ''),
                'aliases': list(e.get('aliases', [])),
                'source_title_en': e.get('source_title_en', ''),
            }

            # Stratégie révisée (2026-04-11) : ne touche PAS mot ni slug.
            # - `mot` inchangé (backref EN, affiché comme secondary par bible-v2-app.js)
            # - `slug` inchangé (indexing interne)
            # - `label_fr` mis à jour avec la traduction FR (drive le primary display)
            # - `source_title_en` rempli avec `mot` si vide
            # - `aliases` : union existants + alias FR du mapping + le `mot` EN
            new_mot = before['mot']           # ← INCHANGÉ
            new_slug = before['slug']          # ← INCHANGÉ
            new_label_fr = spec['mot_fr']
            new_source_title_en = before['source_title_en'] or before['mot']

            existing_aliases = [a for a in before['aliases'] if a]
            new_aliases_to_add = []
            # 1) Le mot FR canonique (label_fr) comme alias explicite si différent des existants
            if new_label_fr and new_label_fr not in existing_aliases:
                new_aliases_to_add.append(new_label_fr)
            # 2) Les alias supplémentaires définis dans le mapping
            for a in spec.get('aliases', []):
                if a and a not in existing_aliases and a not in new_aliases_to_add:
                    new_aliases_to_add.append(a)
            # 3) Le mot EN original (pour la recherche quand label_fr diffère de mot)
            if before['mot'] and before['mot'] not in existing_aliases and before['mot'] not in new_aliases_to_add:
                new_aliases_to_add.append(before['mot'])
            final_aliases = existing_aliases + new_aliases_to_add

            after = {
                'mot': new_mot,
                'label_fr': new_label_fr,
                'slug': new_slug,
                'aliases': final_aliases,
                'source_title_en': new_source_title_en,
            }

            # Diff champs modifiés (mot et slug ne doivent JAMAIS changer)
            diffs = {}
            for k in ('mot', 'label_fr', 'slug', 'aliases', 'source_title_en'):
                if before[k] != after[k]:
                    diffs[k] = {'before': before[k], 'after': after[k]}
            # Safeguard : si mot ou slug apparaissent dans diffs, c'est un bug
            if 'mot' in diffs or 'slug' in diffs:
                warnings.append(f"CRITICAL: {entry_id} — mot ou slug modifié (bug logique)")
                continue
            if diffs:
                patches.append({
                    'entry_id': entry_id,
                    'chunk': chunk_name,
                    'mot_en_original': before['mot'],
                    'note': spec.get('note', ''),
                    'diffs': diffs,
                })
            else:
                warnings.append(f"NO-OP: {entry_id} in {chunk_name} (déjà conforme?)")

    result = {
        'source_mapping': str(MAP_JSON),
        'total_patches': len(patches),
        'warnings_count': len(warnings),
        'warnings': warnings,
        'patches': patches,
    }
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Markdown synthétique pour revue
    lines = []
    lines.append('# Dry-run passe C4 — ISBE `mot` → FR')
    lines.append('')
    lines.append(f'- Mapping source    : `{MAP_JSON.name}`')
    lines.append(f'- Patches générés   : **{len(patches)}**')
    lines.append(f'- Warnings          : {len(warnings)}')
    lines.append('')
    if warnings:
        lines.append('## Warnings')
        lines.append('')
        for w in warnings[:50]:
            lines.append(f'- {w}')
        if len(warnings) > 50:
            lines.append(f'- ... ({len(warnings)-50} de plus)')
        lines.append('')

    lines.append('## Patches (aperçu des 30 premiers)')
    lines.append('')
    lines.append('| entry_id | chunk | mot_en | → mot_fr | slug change | aliases ajoutés |')
    lines.append('|---|---|---|---|---|---|')
    for p in patches[:30]:
        d = p['diffs']
        mot_fr = d.get('mot', {}).get('after', '—')
        slug_chg = 'oui' if 'slug' in d else 'non'
        new_al = []
        if 'aliases' in d:
            before_al = set(d['aliases']['before'])
            after_al = set(d['aliases']['after'])
            new_al = sorted(after_al - before_al)
        al_txt = ', '.join(new_al) if new_al else '—'
        lines.append(f"| `{p['entry_id']}` | {p['chunk']} | {p['mot_en_original']} | **{mot_fr}** | {slug_chg} | {al_txt} |")
    if len(patches) > 30:
        lines.append('')
        lines.append(f'_… et {len(patches)-30} autres patches (voir isbe-c4-dry-run.json)_')
    lines.append('')

    # Stats par chunk
    from collections import Counter
    by_ch = Counter(p['chunk'] for p in patches)
    lines.append('## Répartition par chunk')
    lines.append('')
    lines.append('| chunk | patches |')
    lines.append('|---|---:|')
    for ch, cnt in sorted(by_ch.items()):
        lines.append(f"| {ch} | {cnt} |")
    lines.append('')

    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print(f'Dry-run JSON : {OUT_JSON}')
    print(f'Dry-run MD   : {OUT_MD}')
    print(f'Patches      : {len(patches)}')
    print(f'Warnings     : {len(warnings)}')
    if warnings:
        print()
        print('Premiers warnings :')
        for w in warnings[:10]:
            print(f'  {w}')


if __name__ == '__main__':
    main()
