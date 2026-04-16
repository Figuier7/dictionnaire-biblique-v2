#!/usr/bin/env python3
"""Link cross-references from Easton and BYM to concepts."""
import json, re, sys, os

sys.stdout.reconfigure(encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICT = os.path.join(BASE, 'uploads', 'dictionnaires')

with open(os.path.join(DICT, 'easton', 'easton.entries.json'), 'r', encoding='utf-8-sig') as f:
    easton = json.load(f)

with open(os.path.join(DICT, 'smith', 'smith.entries.json'), 'r', encoding='utf-8-sig') as f:
    smith = json.load(f)

with open(os.path.join(DICT, 'bym', 'bym-lexicon.entries.json'), 'r', encoding='utf-8-sig') as f:
    bym = json.load(f)

with open(os.path.join(DICT, 'concepts.json'), 'r', encoding='utf-8-sig') as f:
    concepts = json.load(f)

with open(os.path.join(DICT, 'concept-entry-links.json'), 'r', encoding='utf-8-sig') as f:
    links = json.load(f)

# Build indexes
entry_to_concept = {l['entry_id']: l['concept_id'] for l in links}
concept_by_id = {c['concept_id']: c for c in concepts}

def normalize(s):
    return re.sub(r'[^a-z0-9]', '', s.lower().strip())

# Build wide lookup: all entries from all sources
all_entries_by_norm = {}
for e in easton + smith + bym:
    key = normalize(e['mot'])
    if key not in all_entries_by_norm:
        all_entries_by_norm[key] = e['id']
    if e.get('label_fr'):
        key2 = normalize(e['label_fr'])
        if key2 not in all_entries_by_norm:
            all_entries_by_norm[key2] = e['id']
    if e.get('source_title_en'):
        key3 = normalize(e['source_title_en'])
        if key3 not in all_entries_by_norm:
            all_entries_by_norm[key3] = e['id']

# Concept label index
concept_by_label = {}
for c in concepts:
    for key in [normalize(c['label']), normalize(c.get('label_restore', '') or ''), c['concept_id']]:
        if key:
            concept_by_label[key] = c['concept_id']
    pf = c.get('public_forms', {})
    for field in ['french_reference', 'restored_reference']:
        v = pf.get(field, '')
        if v:
            concept_by_label[normalize(v)] = c['concept_id']
    for arr_field in ['other_forms', 'english_labels', 'aliases_public']:
        for v in pf.get(arr_field, []):
            if v:
                concept_by_label[normalize(v)] = c['concept_id']
    for a in c.get('aliases', []):
        if a:
            concept_by_label[normalize(a)] = c['concept_id']

ref_pattern = re.compile(r'\[(\d+)\]([\w][\w\s\-\x27\u00e9\u00e8\u00ea\u00eb\u00e0\u00e2\u00e4\u00f4\u00f9\u00fb\u00fc\u00ef\u00ee\u00e7\u00c9\u00c8\u00ca\u00cb\u00c0\u00c2\u00c4\u00d4\u00d9\u00db\u00dc\u00cf\u00ce\u00c7]*[\w\)]|[\w])')

def find_target_concept(target_word):
    tw = target_word.strip()
    tn = normalize(tw)

    # Direct entry match
    if tn in all_entries_by_norm:
        cid = entry_to_concept.get(all_entries_by_norm[tn])
        if cid:
            return cid

    # Concept label match
    if tn in concept_by_label:
        return concept_by_label[tn]

    # Clean trailing prepositions
    tw_clean = re.sub(r'\s+(dans|de|du|des|et|ou|le|la|les)$', '', tw, flags=re.IGNORECASE).strip()
    tn_clean = normalize(tw_clean)
    if tn_clean != tn:
        if tn_clean in all_entries_by_norm:
            cid = entry_to_concept.get(all_entries_by_norm[tn_clean])
            if cid:
                return cid
        if tn_clean in concept_by_label:
            return concept_by_label[tn_clean]

    # Split on Or/And/Et
    for word in re.split(r'\s+(?:Or|or|Et|et|And|and)\s+', tw_clean):
        wn = normalize(word.strip())
        if wn in all_entries_by_norm:
            cid = entry_to_concept.get(all_entries_by_norm[wn])
            if cid:
                return cid
        if wn in concept_by_label:
            return concept_by_label[wn]

    return None


def add_relation(source_concept, target_cid):
    """Add bidirectional renvoi relation. Returns True if new."""
    existing = {r.get('concept_id', '') for r in source_concept.get('related_concepts', [])}
    if target_cid in existing:
        return False
    target_concept = concept_by_id.get(target_cid)
    if not target_concept:
        return False

    source_concept['related_concepts'].append({
        'concept_id': target_cid,
        'label': target_concept['label'],
        'relation_type': 'renvoi'
    })

    target_existing = {r.get('concept_id', '') for r in target_concept.get('related_concepts', [])}
    source_cid = None
    for c in concepts:
        if c is source_concept:
            source_cid = c['concept_id']
            break
    if source_cid and source_cid not in target_existing:
        target_concept['related_concepts'].append({
            'concept_id': source_cid,
            'label': source_concept['label'],
            'relation_type': 'renvoi'
        })
    return True


# ===== EASTON [N]WORD cross-refs =====
easton_new = 0
easton_matched = 0
easton_unmatched = 0
easton_unmatched_ex = []

for e in easton:
    matches = ref_pattern.findall(e['definition'])
    if not matches:
        continue

    source_cid = entry_to_concept.get(e['id'])
    if not source_cid:
        continue
    source_concept = concept_by_id.get(source_cid)
    if not source_concept:
        continue

    for num, target_word in matches:
        target_cid = find_target_concept(target_word)
        if target_cid and target_cid != source_cid:
            easton_matched += 1
            if add_relation(source_concept, target_cid):
                easton_new += 1
        else:
            easton_unmatched += 1
            if len(easton_unmatched_ex) < 15:
                easton_unmatched_ex.append(f"  {e['mot']} -> [{num}]{target_word.strip()}")

print(f"=== EASTON ===")
print(f"Bracket refs found: {easton_matched + easton_unmatched}")
print(f"Matched: {easton_matched}")
print(f"Unmatched: {easton_unmatched}")
print(f"New relations added: {easton_new}")

if easton_unmatched_ex:
    print(f"\nUnmatched examples:")
    for ex in easton_unmatched_ex:
        print(ex)

# ===== BYM "Voir [concept]" refs =====
bym_new = 0
bym_matched = 0
bym_voir_pat = re.compile(r'[Vv]oir\s+([A-Z\u00c9\u00c8\u00ca\u00cb\u00c0\u00c2][\w\-\x27 ]+)')

for e in bym:
    d = e['definition']
    voir_matches = bym_voir_pat.findall(d)
    if not voir_matches:
        continue

    source_cid = entry_to_concept.get(e['id'])
    if not source_cid:
        continue
    source_concept = concept_by_id.get(source_cid)
    if not source_concept:
        continue

    for target_word in voir_matches:
        tw = target_word.strip()
        # Skip short Bible book abbreviations
        if len(tw) <= 4:
            continue

        target_cid = find_target_concept(tw)
        if target_cid and target_cid != source_cid:
            bym_matched += 1
            if add_relation(source_concept, target_cid):
                bym_new += 1

print(f"\n=== BYM ===")
print(f"Voir refs matched: {bym_matched}")
print(f"New relations added: {bym_new}")

# Final stats
total_related = sum(len(c.get('related_concepts', [])) for c in concepts)
concepts_with_related = sum(1 for c in concepts if c.get('related_concepts'))
print(f"\n=== TOTAL ===")
print(f"Total related_concepts links: {total_related}")
print(f"Concepts with at least 1 related: {concepts_with_related} / {len(concepts)}")

with open(os.path.join(DICT, 'concepts.json'), 'w', encoding='utf-8') as f:
    json.dump(concepts, f, ensure_ascii=False, indent=2)

print("Saved.")
