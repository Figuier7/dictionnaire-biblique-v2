#!/usr/bin/env python3
"""
Simulateur de rendu concept — reproduit en console ce que
bible-v2-app.js + functions.php SSR afficheraient pour un concept donné.

Utilise :
- concepts.json           → getConceptDisplayTitles (JS ligne 193+)
- concept-meta.json       → SSR PHP + sitemap + JSON-LD
- slug-map.json           → résolution URL FR → concept_id
- isbe-*.json chunks      → source card rendering (getEntryDisplayTitles, JS ligne 2135+)

Usage :
  python scripts/simulate_concept_render.py <concept_id|url_slug>
  python scripts/simulate_concept_render.py elder-in-the-old-testament
  python scripts/simulate_concept_render.py anciens
  python scripts/simulate_concept_render.py ancients       # test redirect slug-map
"""
import json
import sys
import argparse
import glob
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
DICT_DIR = ROOT / "uploads" / "dictionnaires"


def load_concepts():
    with open(DICT_DIR / "concepts.json", encoding='utf-8-sig') as f:
        return json.load(f)


def load_meta():
    with open(DICT_DIR / "concept-meta.json", encoding='utf-8-sig') as f:
        return json.load(f)


def load_slug_map():
    with open(DICT_DIR / "slug-map.json", encoding='utf-8-sig') as f:
        return json.load(f)


def load_isbe():
    by_id = {}
    for fp in sorted((DICT_DIR / "isbe").glob("isbe-?.json")):
        with open(fp, encoding='utf-8-sig') as f:
            for e in json.load(f):
                by_id[e['id']] = e
    return by_id


def resolve_slug(slug, concept_by_id, slug_map):
    """Reproduit figuier_bible_resolve_slug de functions.php"""
    # 1) Try as concept_id directly
    if slug in concept_by_id:
        return slug
    # 2) Try slug-map
    if slug in slug_map:
        return slug_map[slug]
    return None


def get_url_slug(concept_id, meta):
    """Reproduit figuier_bible_get_url_slug de functions.php"""
    m = meta.get(concept_id, {})
    return m.get('u') or concept_id


def get_concept_display_titles(concept):
    """Reproduit getConceptDisplayTitles de bible-v2-app.js ligne 193"""
    dt = concept.get('display_titles', {}) or {}
    primary = dt.get('primary', '').strip()
    secondary = dt.get('secondary', '').strip()
    strategy = dt.get('strategy', '').strip()

    if not primary:
        primary = (concept.get('label_restore')
                   or concept.get('label')
                   or concept.get('concept_id')).strip()
    if not strategy:
        strategy = 'restored_first' if secondary else 'french_only'

    return {'strategy': strategy, 'primary': primary, 'secondary': secondary}


def get_entry_display_titles(dictionary_id, entry):
    """Reproduit getEntryDisplayTitles de bible-v2-app.js ligne 2135"""
    primary = ''
    secondary = ''
    if dictionary_id == 'bym_lexicon' and entry.get('mot_restore'):
        if entry['mot_restore'] != (entry.get('label_fr') or entry.get('mot', '')):
            primary = entry['mot_restore']
            secondary = entry.get('label_fr') or entry.get('mot', '')
        else:
            primary = entry.get('label_fr') or entry.get('mot_restore') or entry.get('mot', '')
    else:
        primary = entry.get('label_fr') or entry.get('mot_restore') or entry.get('mot', '')
        if entry.get('mot') and entry['mot'] != primary:
            secondary = entry['mot']
    return {'primary': primary, 'secondary': secondary}


def render_concept(concept_id_or_slug):
    concepts = load_concepts()
    concept_by_id = {c['concept_id']: c for c in concepts}
    meta = load_meta()
    slug_map = load_slug_map()
    isbe_by_id = load_isbe()

    # Resolve
    resolved = resolve_slug(concept_id_or_slug, concept_by_id, slug_map)
    if not resolved:
        print(f"❌ Slug '{concept_id_or_slug}' introuvable")
        return 1

    if resolved != concept_id_or_slug:
        print(f"🔀 Slug redirect: '{concept_id_or_slug}' → '{resolved}'")

    concept = concept_by_id.get(resolved)
    if not concept:
        print(f"❌ Concept '{resolved}' introuvable dans concepts.json")
        return 1

    m = meta.get(resolved, {})
    url_slug = get_url_slug(resolved, meta)
    dt = get_concept_display_titles(concept)

    # ─── Header rendu (bible-v2-app.js style) ───
    print()
    print('╔══════════════════════════════════════════════════════════════════╗')
    print(f'║  URL FINALE : /dictionnaire-biblique/{url_slug}/')
    print(f'║  concept_id : {resolved}')
    print('╚══════════════════════════════════════════════════════════════════╝')
    print()
    print('┌─ Header concept (bible-v2-app.js) ─────────────────────────────────')
    print(f'│  <h1>     {dt["primary"]}')
    if dt['secondary']:
        print(f'│  <sub>    {dt["secondary"]}')
    print(f'│  Catégorie: {concept.get("category", "")}')
    print('└────────────────────────────────────────────────────────────────────')

    # ─── Meta SSR (functions.php) ───
    primary_meta = m.get('p') or m.get('l') or resolved
    secondary_meta = m.get('s', '')
    page_title_parts = [primary_meta]
    if secondary_meta and secondary_meta != primary_meta:
        page_title_parts.append(secondary_meta)
    page_title = ' — '.join(page_title_parts) + ' | Dictionnaire Biblique'
    print()
    print('┌─ SEO meta tags (functions.php SSR) ───────────────────────────────')
    print(f'│  <title>{page_title}</title>')
    print(f'│  <meta description="{m.get("e", "")[:80]}..."')
    print(f'│  <link canonical="https://alombredufiguier.org/dictionnaire-biblique/{url_slug}/">')
    print('└────────────────────────────────────────────────────────────────────')

    # ─── Source cards (bible-v2-app.js renderSourceCard) ───
    entries = concept.get('entries', [])
    print()
    print(f'┌─ Source cards ({len(entries)} entries) ─────────────────────────────')
    for e in entries:
        dict_id = e['dictionary']
        entry_id = e['entry_id']
        role = e.get('display_role', '')
        if dict_id == 'isbe':
            isbe_entry = isbe_by_id.get(entry_id)
            if not isbe_entry:
                print(f'│  [{dict_id}] {entry_id} — NOT FOUND in chunks')
                continue
            titles = get_entry_display_titles(dict_id, isbe_entry)
            print(f'│  ┌─ [{dict_id}] {role} / {entry_id}')
            print(f'│  │  primary   : {titles["primary"]}')
            if titles['secondary']:
                print(f'│  │  secondary : {titles["secondary"]}')
            if isbe_entry.get('aliases'):
                al = isbe_entry['aliases']
                print(f'│  │  aliases   : {al[:3]}{"..." if len(al) > 3 else ""}')
            defn = isbe_entry.get('definition', '')
            if defn:
                preview = defn.replace('\n', ' ')[:120]
                print(f'│  │  definition: {preview}...')
            print(f'│  └──')
        else:
            print(f'│  [{dict_id}] {role} / {entry_id}')
    print('└────────────────────────────────────────────────────────────────────')

    # ─── Aliases concept ───
    aliases = concept.get('aliases', [])
    if aliases:
        print()
        print(f'Aliases concept : {aliases}')

    # ─── Related concepts ───
    rel = concept.get('related_concepts', [])
    if rel:
        print(f'Related ({len(rel)}): {[r.get("concept_id") for r in rel[:5]]}{"..." if len(rel) > 5 else ""}')

    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('concept', help='concept_id ou slug FR (ex: anciens, ancients, elder-in-the-old-testament)')
    args = parser.parse_args()
    return render_concept(args.concept)


if __name__ == '__main__':
    sys.exit(main())
