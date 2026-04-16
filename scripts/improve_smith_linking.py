"""
Improve Smith concept-linking: merge Smith-only concepts into existing
multi-source concepts when a match is found via normalized labels,
base forms, aliases, = splits, Or-right-side, etc.
"""
import json, re, unicodedata, sys
from collections import Counter

def load_json(path):
    with open(path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def strip_accents(s):
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

def norm(s):
    s = s.lower().strip()
    s = strip_accents(s)
    s = re.sub(r'[^a-z0-9 ]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

# ── Load data ──
base = 'uploads/dictionnaires'
concepts = load_json(f'{base}/concepts.json')
links = load_json(f'{base}/concept-entry-links.json')
smith = load_json(f'{base}/smith/smith.entries.json')
easton = load_json(f'{base}/easton/easton.entries.json')

smith_by_id = {e['id']: e for e in smith}
easton_by_id = {e['id']: e for e in easton}
concept_by_id = {c['concept_id']: c for c in concepts}

# ── Classify concepts ──
smith_only_concepts = []
target_concepts = []

for c in concepts:
    sources = set()
    for e in c.get('entries', []):
        sources.add(e.get('entry_id', '').split('-')[0])
    if sources == {'smith'}:
        smith_only_concepts.append(c)
    else:
        target_concepts.append(c)

# ── Build indexes from target concepts ──
idx_label = {}    # norm(label) -> concept_id
idx_alias = {}    # norm(alias) -> concept_id
idx_en = {}       # norm(english_title) -> concept_id

for c in target_concepts:
    cid = c['concept_id']

    for field in ('label', 'label_restore'):
        val = c.get(field, '')
        if val:
            idx_label[norm(val)] = cid

    for dt in c.get('display_titles', {}).values():
        if dt:
            idx_label[norm(dt)] = cid

    for pf in c.get('public_forms', []):
        if pf:
            idx_label[norm(pf)] = cid

    for e_ref in c.get('entries', []):
        eid = e_ref.get('entry_id', '')
        if eid.startswith('easton-'):
            ee = easton_by_id.get(eid)
            if ee:
                for a in ee.get('aliases', []):
                    if a:
                        idx_alias[norm(a)] = cid
                en = ee.get('source_title_en', '')
                if en:
                    idx_en[norm(en)] = cid

# ── Match each Smith-only concept ──
def try_match(label, en_title, fr_label, smith_aliases):
    """Try multiple strategies, return (target_concept_id, strategy) or None."""
    n = norm(label)

    # 1. Exact normalized label
    if n in idx_label:
        return idx_label[n], 'label_normalized'

    # 2. English title exact
    if en_title:
        n_en = norm(en_title)
        if n_en in idx_en:
            return idx_en[n_en], 'en_title_exact'
        if n_en in idx_label:
            return idx_label[n_en], 'en_title_in_labels'

    # 3. Base form (before comma, Or, =, And)
    base = re.split(r',\s*| Or | = | And ', label)[0].strip()
    n_base = norm(base)
    if n_base != n and n_base in idx_label:
        return idx_label[n_base], 'base_form'

    # 4. English base form
    if en_title:
        en_base = re.split(r',\s*| Or | = | And ', en_title)[0].strip()
        n_en_base = norm(en_base)
        if n_en_base in idx_en:
            return idx_en[n_en_base], 'en_base_form'
        if n_en_base in idx_label:
            return idx_label[n_en_base], 'en_base_in_labels'

    # 5. = split: try each part
    if ' = ' in label:
        for part in label.split(' = '):
            np = norm(part.strip())
            if np in idx_label:
                return idx_label[np], 'eq_split'
            if np in idx_en:
                return idx_en[np], 'eq_split_en'

    # 6. Or right-side
    if ' Or ' in label:
        parts = label.split(' Or ')
        for p in parts[1:]:
            np = norm(p.strip())
            if np in idx_label:
                return idx_label[np], 'or_right'
            if np in idx_en:
                return idx_en[np], 'or_right_en'

    # 7. Alias match
    if n in idx_alias:
        return idx_alias[n], 'alias_match'
    if n_base != n and n_base in idx_alias:
        return idx_alias[n_base], 'alias_base_match'

    # 8. "Book Of X" -> X
    book_m = re.match(r'(.+?),?\s+Book Of$', label, re.I)
    if book_m:
        bn = norm(book_m.group(1))
        if bn in idx_label:
            return idx_label[bn], 'book_of'

    # 9. French label
    if fr_label:
        n_fr = norm(fr_label)
        if n_fr in idx_label:
            return idx_label[n_fr], 'fr_label'

    # 10. Smith aliases
    for a in smith_aliases:
        na = norm(a)
        if na in idx_label:
            return idx_label[na], 'smith_alias'
        if na in idx_en:
            return idx_en[na], 'smith_alias_en'
        if na in idx_alias:
            return idx_alias[na], 'smith_alias_cross'

    return None

# ── Execute matching ──
merges = []  # (smith_concept, smith_entry_id, target_concept_id, strategy)
strategies = Counter()

for sc in smith_only_concepts:
    label = sc.get('label', '')
    smith_entries = [e for e in sc.get('entries', []) if e['entry_id'].startswith('smith-')]
    if not smith_entries:
        continue

    smith_eid = smith_entries[0]['entry_id']
    se = smith_by_id.get(smith_eid)
    if not se:
        continue

    en_title = se.get('source_title_en', '')
    fr_label = se.get('label_fr', se.get('mot', ''))
    aliases = se.get('aliases', [])

    result = try_match(label, en_title, fr_label, aliases)
    if result:
        target_cid, strategy = result
        merges.append((sc, smith_eid, target_cid, strategy))
        strategies[strategy] += 1

print(f"Smith-only concepts: {len(smith_only_concepts)}")
print(f"New merges found: {len(merges)}")
print(f"Remaining unique: {len(smith_only_concepts) - len(merges)}")
print(f"\nStrategies:")
for s, c in strategies.most_common():
    print(f"  {s}: {c}")

# ── Apply merges ──
merged_concept_ids = set()
links_index = {l['entry_id']: l for l in links}

for sc, smith_eid, target_cid, strategy in merges:
    target = concept_by_id[target_cid]

    # Add smith entry to target concept's entries array
    entry_ref = {
        'entry_id': smith_eid,
        'dictionary': 'smith',
        'display_role': 'detailed_reference'
    }
    # Check not already there
    existing_eids = {e['entry_id'] for e in target.get('entries', [])}
    if smith_eid not in existing_eids:
        target['entries'].append(entry_ref)

    # Update the link
    if smith_eid in links_index:
        old_link = links_index[smith_eid]
        old_link['concept_id'] = target_cid
        old_link['match_strategy'] = f'improved_{strategy}'
        old_link['confidence'] = 0.85
        old_link['notes'] = f'Re-linked from {sc["concept_id"]}'

    # Mark smith-only concept for removal
    merged_concept_ids.add(sc['concept_id'])

# Remove merged smith-only concepts
concepts_new = [c for c in concepts if c['concept_id'] not in merged_concept_ids]

print(f"\nConcepts before: {len(concepts)}")
print(f"Concepts after: {len(concepts_new)}")
print(f"Removed: {len(merged_concept_ids)}")

# ── Save ──
save_json(f'{base}/concepts.json', concepts_new)
save_json(f'{base}/concept-entry-links.json', links)

# ── Final stats ──
multi = 0
smith_only_final = 0
no_smith = 0
for c in concepts_new:
    sources = set()
    for e in c.get('entries', []):
        sources.add(e.get('entry_id','').split('-')[0])
    if 'smith' in sources:
        if len(sources) > 1:
            multi += 1
        else:
            smith_only_final += 1
    else:
        no_smith += 1

print(f"\nFinal breakdown:")
print(f"  Multi-source (Smith+other): {multi}")
print(f"  Smith-only: {smith_only_final}")
print(f"  No Smith: {no_smith}")
print(f"  Total concepts: {len(concepts_new)}")

cross_pct = multi / (multi + smith_only_final + no_smith) * 100
print(f"\nCross-source rate: {cross_pct:.1f}%")
