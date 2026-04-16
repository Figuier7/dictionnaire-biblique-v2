#!/usr/bin/env python3
"""Create missing theological concept pages and link them to existing dictionary entries."""
import json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_json(path):
    with open(path, encoding='utf-8-sig') as f:
        return json.load(f)

# Load concepts
concepts_path = os.path.join(BASE, 'uploads/dictionnaires/concepts.json')
concepts = load_json(concepts_path)
existing_labels = {c.get('label', '').lower(): c for c in concepts}
existing_ids = {c['concept_id'] for c in concepts}

# Load all source entries (by id field)
entry_index = {}  # id -> entry
for src in ['easton', 'smith']:
    path = os.path.join(BASE, 'uploads', 'dictionnaires', src, f'{src}.entries.json')
    if os.path.exists(path):
        for e in load_json(path):
            entry_index[e['id']] = e

isbe_dir = os.path.join(BASE, 'uploads', 'dictionnaires', 'isbe')
if os.path.isdir(isbe_dir):
    for fname in sorted(os.listdir(isbe_dir)):
        if fname.endswith('.json'):
            for e in load_json(os.path.join(isbe_dir, fname)):
                entry_index[e['id']] = e

print(f'Loaded {len(entry_index)} source entries')

# Load hebrew map for Strong links
hmap_path = os.path.join(BASE, 'uploads/dictionnaires/concept-hebrew-map.json')
hmap = load_json(hmap_path)

# Define concepts to create
CONCEPTS = [
    {
        'id': 'sagesse', 'label': 'Sagesse', 'cat': 'doctrine',
        'search': ['Sagesse', 'Wisdom'], 'en': ['Wisdom'],
        'strong': ['H2449', 'H2451'],
    },
    {
        'id': 'louange', 'label': 'Louange', 'cat': 'rite',
        'search': ['Louange', 'Praise'], 'en': ['Praise'],
        'strong': ['H1984', 'H8416'],
    },
    {
        'id': 'jugement', 'label': 'Jugement', 'cat': 'doctrine',
        'search': ['Jugement', 'Judgment'], 'en': ['Judgment'],
        'strong': ['H4941', 'H8199'],
    },
    {
        'id': 'royaume', 'label': 'Royaume', 'cat': 'doctrine',
        'search': ['Royaume', 'Kingdom', 'Royaume de Dieu'], 'en': ['Kingdom'],
        'strong': ['H4467', 'H4468'],
    },
    {
        'id': 'nation', 'label': 'Nation', 'cat': 'institution',
        'search': ['Nation', 'Nations'], 'en': ['Nation'],
        'strong': ['H1471'],
    },
    {
        'id': 'peuple', 'label': 'Peuple', 'cat': 'institution',
        'search': ['Peuple', 'People'], 'en': ['People'],
        'strong': ['H5971'],
    },
    {
        'id': 'commandement', 'label': 'Commandement', 'cat': 'doctrine',
        'search': ['Commandement', 'Commandments', 'Commandement de Dieu'], 'en': ['Commandment'],
        'strong': ['H4687'],
    },
    {
        'id': 'delivrance', 'label': 'Delivrance', 'cat': 'doctrine',
        'search': ['Delivrance', 'Deliverance'], 'en': ['Deliverance'],
        'strong': ['H3444', 'H6413'],
    },
    {
        'id': 'decret', 'label': 'Decret', 'cat': 'institution',
        'search': ['Decret', 'Decree'], 'en': ['Decree'],
        'strong': ['H1881', 'H2706'],
    },
    {
        'id': 'psaume', 'label': 'Psaume', 'cat': 'rite',
        'search': ['Psaume', 'Psaumes', 'Psalms'], 'en': ['Psalm', 'Psalms'],
        'strong': ['H4210'],
    },
    {
        'id': 'cantique', 'label': 'Cantique', 'cat': 'rite',
        'search': ['Cantique', 'Song', 'Cantique des cantiques'], 'en': ['Song'],
        'strong': ['H7892'],
    },
    {
        'id': 'montagne', 'label': 'Montagne', 'cat': 'lieu',
        'search': ['Montagne', 'Mountain', 'Montagnes'], 'en': ['Mountain'],
        'strong': ['H2022'],
    },
    {
        'id': 'fleuve', 'label': 'Fleuve', 'cat': 'lieu',
        'search': ['Fleuve', 'River', 'Riviere'], 'en': ['River'],
        'strong': ['H5104'],
    },
    {
        'id': 'eau', 'label': 'Eau', 'cat': 'matiere',
        'search': ['Eau', 'Water', 'Eaux'], 'en': ['Water'],
        'strong': ['H4325'],
    },
    {
        'id': 'or-metal', 'label': 'Or', 'cat': 'matiere',
        'search': ['Or', 'Gold'], 'en': ['Gold'],
        'strong': ['H2091'],
    },
    {
        'id': 'bronze-metal', 'label': 'Bronze', 'cat': 'matiere',
        'search': ['Airain', 'Bronze', 'Brass'], 'en': ['Bronze', 'Brass'],
        'strong': ['H5178'],
    },
    {
        'id': 'pourpre', 'label': 'Pourpre', 'cat': 'matiere',
        'search': ['Pourpre', 'Purple'], 'en': ['Purple'],
        'strong': ['H713'],
    },
    {
        'id': 'sacrificateur', 'label': 'Sacrificateur', 'cat': 'institution',
        'search': ['Sacrificateur', 'Priest', 'Pretrise', 'Pretre'], 'en': ['Priest'],
        'strong': ['H3548'],
    },
    {
        'id': 'pasteur', 'label': 'Pasteur', 'cat': 'institution',
        'search': ['Pasteur', 'Pastor', 'Berger'], 'en': ['Pastor', 'Shepherd'],
        'strong': ['H7462'],
    },
    {
        'id': 'joie', 'label': 'Joie', 'cat': 'doctrine',
        'search': ['Joie', 'Joy'], 'en': ['Joy'],
        'strong': ['H8057', 'H1524'],
    },
    {
        'id': 'crainte', 'label': 'Crainte', 'cat': 'doctrine',
        'search': ['Crainte', 'Fear', 'Crainte de Dieu'], 'en': ['Fear'],
        'strong': ['H3374'],
    },
    {
        'id': 'chemin', 'label': 'Chemin', 'cat': 'doctrine',
        'search': ['Chemin', 'Way', 'Voie'], 'en': ['Way'],
        'strong': ['H1870'],
    },
    {
        'id': 'heritage', 'label': 'Heritage', 'cat': 'doctrine',
        'search': ['Heritage', 'Inheritance'], 'en': ['Inheritance'],
        'strong': ['H5159'],
    },
]

# Find entries for each concept
lex_path = os.path.join(BASE, 'hebrew-lexicon-fr-compact.json')
lexicon = load_json(lex_path)
lex_by_strong = {e['s']: e for e in lexicon}

created = 0
skipped = 0

for spec in CONCEPTS:
    cid = spec['id']
    label = spec['label']

    # Skip if already exists
    if label.lower() in existing_labels or cid in existing_ids:
        print(f'SKIP (exists): {label}')
        skipped += 1
        continue

    # Find matching entries
    search_lower = [t.lower() for t in spec['search']]
    entries = []
    for eid, entry in entry_index.items():
        mot = (entry.get('mot') or '').strip().lower()
        if mot in search_lower:
            src = entry.get('dictionary', '')
            role_map = {
                'easton': 'main_definition',
                'smith': 'detailed_reference',
                'isbe': 'deep_read',
                'bym_lexicon': 'quick_gloss',
            }
            entries.append({
                'entry_id': eid,
                'dictionary': src,
                'display_role': role_map.get(src, 'deep_read'),
                'is_primary_for_role': True,
            })

    # Build concept
    alpha = label[0].upper()
    concept = {
        'concept_id': cid,
        'label': label,
        'label_restore': '',
        'display_titles': {
            'strategy': 'french_only',
            'primary': label,
            'secondary': '',
        },
        'public_forms': {
            'restored_reference': '',
            'french_reference': label,
            'other_forms': [],
            'english_labels': spec.get('en', []),
            'aliases_public': [],
        },
        'aliases': [],
        'category': spec['cat'],
        'alpha_letter': alpha,
        'status': 'ready',
        'entries': entries,
        'related_concepts': [],
    }

    concepts.append(concept)
    created += 1

    # Add to hebrew map
    strong_entries = []
    for sid in spec.get('strong', []):
        e = lex_by_strong.get(sid)
        if e:
            strong_entries.append({'s': sid, 'h': e.get('h', ''), 'x': e.get('x', '')})
    if strong_entries:
        hmap[cid] = strong_entries

    n_entries = len(entries)
    print(f'CREATED: {label} [{spec["cat"]}] {n_entries} entries, {len(spec.get("strong",[]))} Strong')

# Save
with open(concepts_path, 'w', encoding='utf-8') as f:
    json.dump(concepts, f, ensure_ascii=False, indent=2)

with open(hmap_path, 'w', encoding='utf-8') as f:
    json.dump(hmap, f, ensure_ascii=False, separators=(',', ':'))

print(f'\n=== Summary ===')
print(f'Created: {created}')
print(f'Skipped (existed): {skipped}')
print(f'Total concepts: {len(concepts)}')
print(f'Hebrew map: {len(hmap)} concepts')
