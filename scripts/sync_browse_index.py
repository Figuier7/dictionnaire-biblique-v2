#!/usr/bin/env python3
"""
Re-synchronise browse-index.json depuis concept-meta.json.

A utiliser apres toute mise a jour de concept-meta.json (traductions, re-typage
categories, etc.) pour garder browse-index coherent.

Usage : python scripts/sync_browse_index.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
META_PATH = BASE / 'uploads/dictionnaires/concept-meta.json'
BROWSE_PATH = BASE / 'uploads/dictionnaires/browse-index.json'


def main():
    sys.stdout.reconfigure(encoding='utf-8')

    with open(META_PATH, encoding='utf-8') as f:
        meta = json.load(f)
    # browse-index.json est UTF-8 BOM
    with open(BROWSE_PATH, encoding='utf-8-sig') as f:
        browse = json.load(f)

    print(f'Meta   : {len(meta)} concepts')
    print(f'Browse : {len(browse.get("letters", []))} letters')

    # =========================================================
    # 1. Sync labels + categories dans les items par lettre
    # =========================================================
    fixed = 0
    total_items = 0

    def update_item(item):
        nonlocal fixed, total_items
        cid = item.get('concept_id')
        if not cid:
            return
        total_items += 1
        m = meta.get(cid)
        if not m:
            return
        # BYM priority : p (restored) > l (FR)
        new_label = (m.get('p') or m.get('l') or item.get('label', '')).strip()
        new_cat = m.get('c') or item.get('category', '')
        changed = False
        if new_label and new_label != item.get('label'):
            item['label'] = new_label
            item['display_title_primary'] = new_label
            changed = True
        if new_cat and new_cat != item.get('category'):
            item['category'] = new_cat
            changed = True
        if changed:
            fixed += 1

    for letter_obj in browse.get('letters', []):
        for key in ('preview_items', 'items', 'all_items'):
            v = letter_obj.get(key)
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        update_item(item)

    # =========================================================
    # 2. Reconstruire la section 'categories' (groupement)
    # =========================================================
    from collections import defaultdict
    items_by_cat = defaultdict(list)
    for letter_obj in browse.get('letters', []):
        for item in letter_obj.get('items', []):
            if isinstance(item, dict):
                cat = item.get('category', '')
                if cat and cat != 'non_classifie':
                    items_by_cat[cat].append(item)

    # Ordre taxonomique fixe
    TAXONOMY_ORDER = [
        'personnage', 'etre_spirituel', 'lieu', 'lieu_sacre', 'peuple', 'livre_biblique',
        'doctrine', 'rite', 'institution', 'fonction',
        'objet_sacre', 'objets_et_vetements',
        'plante', 'animal', 'alimentation_et_agriculture', 'corps_et_sante',
        'mesures_et_temps', 'matiere', 'evenement', 'nature',
    ]

    new_categories = []
    for cat in TAXONOMY_ORDER:
        items = items_by_cat.get(cat, [])
        if not items:
            continue
        # Preview : 6 items representatifs (alphabetiques)
        sorted_items = sorted(items, key=lambda x: (x.get('label') or '').lower())
        preview = sorted_items[:6]
        new_categories.append({
            'category': cat,
            'count': len(items),
            'preview_items': preview,
        })

    # Ajouter non_classifie en dernier si restant
    if items_by_cat.get('non_classifie'):
        new_categories.append({
            'category': 'non_classifie',
            'count': len(items_by_cat['non_classifie']),
            'preview_items': items_by_cat['non_classifie'][:6],
        })

    old_cat_count = len(browse.get('categories', []))
    browse['categories'] = new_categories

    # Aussi mettre a jour les preview_items des lettres
    # (prendre les 6 premiers items de chaque lettre, coherents)
    for letter_obj in browse.get('letters', []):
        items = letter_obj.get('items', [])
        if items:
            letter_obj['preview_items'] = items[:6]
            letter_obj['count'] = len(items)

    # =========================================================
    # 3. Timestamps + save
    # =========================================================
    now = datetime.now().isoformat(timespec='seconds')
    browse['generated_at'] = now
    browse['version'] = now

    with open(BROWSE_PATH, 'w', encoding='utf-8-sig') as f:
        json.dump(browse, f, ensure_ascii=False, indent=2)

    print(f'Items processed   : {total_items}')
    print(f'Items updated     : {fixed}')
    print(f'Categories rebuilt : {old_cat_count} -> {len(new_categories)}')
    for c in new_categories:
        print(f'  {c["category"]:30s} : {c["count"]:>5} concepts, {len(c["preview_items"])} preview')
    print(f'Saved             : {BROWSE_PATH}')


if __name__ == '__main__':
    main()
