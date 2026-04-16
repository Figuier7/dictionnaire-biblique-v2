import json, sys, io, re, unicodedata
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = "C:/Users/caeng/OneDrive/Documents/A l'ombre du figuier/dictionnaire-biblique-main"

with open(f'{BASE}/isbe.json', 'r', encoding='utf-8') as f:
    isbe = json.load(f)
with open(f'{BASE}/uploads/dictionnaires/concepts.json', 'r', encoding='utf-8-sig') as f:
    concepts = json.load(f)
with open(f'{BASE}/uploads/dictionnaires/concept-entry-links.json', 'r', encoding='utf-8-sig') as f:
    links = json.load(f)
with open(f'{BASE}/uploads/dictionnaires/easton/easton.entries.json', 'r', encoding='utf-8-sig') as f:
    easton = json.load(f)
with open(f'{BASE}/uploads/dictionnaires/smith/smith.entries.json', 'r', encoding='utf-8-sig') as f:
    smith = json.load(f)

def normalize(s):
    s = s.lower().strip()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^a-z0-9 ]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def base_form(s):
    s = re.split(r'[,;(]', s)[0].strip()
    s = re.sub(r'\s+\d+$', '', s)
    s = re.sub(r"'s$", '', s)
    return s

# Build indexes
concept_by_label = {}
concept_by_restore = {}
concept_by_english = {}
concept_by_alias = {}

concept_sources = {}
for link in links:
    cid = link['concept_id']
    src = link['entry_id'].split('-')[0]
    concept_sources.setdefault(cid, set()).add(src)

for c in concepts:
    cid = c['concept_id']
    nl = normalize(c.get('label', ''))
    if nl:
        concept_by_label[nl] = c
    nr = normalize(c.get('label_restore', ''))
    if nr:
        concept_by_restore[nr] = c
    pf = c.get('public_forms', {})
    for el in pf.get('english_labels', []):
        ne = normalize(el)
        if ne:
            concept_by_english[ne] = c
    for al in c.get('aliases', []):
        na = normalize(al)
        if na:
            concept_by_alias[na] = c
    for al in pf.get('aliases_public', []):
        na = normalize(al)
        if na:
            concept_by_alias[na] = c

# Build entry -> concept lookup
link_by_entry = {}
for link in links:
    link_by_entry[link['entry_id']] = link['concept_id']

easton_title_to_concept = {}
for e in easton:
    eid = e.get('id', '')
    src_title = normalize(e.get('source_title_en', e.get('mot', '')))
    cid = link_by_entry.get(eid)
    if cid:
        easton_title_to_concept[src_title] = cid

smith_title_to_concept = {}
for e in smith:
    eid = e.get('id', '')
    src_title = normalize(e.get('source_title_en', e.get('mot', '')))
    cid = link_by_entry.get(eid)
    if cid:
        smith_title_to_concept[src_title] = cid

print(f"Index: label={len(concept_by_label)} restore={len(concept_by_restore)} english={len(concept_by_english)} alias={len(concept_by_alias)} easton={len(easton_title_to_concept)} smith={len(smith_title_to_concept)}")

def is_redirect(defn):
    defn = defn.strip()
    if not defn:
        return True
    if len(defn) < 100 and re.match(r'^(?:See|see)\s+[A-Z]', defn):
        return True
    if re.match(r'^See\s+[A-Z]', defn) and len(defn) < 200 and '\n' not in defn:
        return True
    if re.match(r'^=\s', defn):
        return True
    if re.match(r'^Same as\b', defn):
        return True
    return False

def get_tier(size):
    if size <= 100: return 'T1'
    if size <= 420: return 'T2'
    if size <= 1800: return 'T3'
    if size <= 5000: return 'T4'
    if size <= 20000: return 'T5'
    if size <= 80000: return 'T6'
    return 'T7'

results = []
strategy_counts = Counter()
circle_counts = Counter()

for idx, e in enumerate(isbe):
    mot = e['mot']
    defn = e.get('definition', '')
    char_count = len(defn)
    tier = get_tier(char_count)
    redir = is_redirect(defn)

    matched_concept_id = None
    match_strategy = None

    if redir:
        circle = 'C4'
    else:
        nmot = normalize(mot)
        bmot = normalize(base_form(mot))

        # Strategy cascade
        if nmot in concept_by_english:
            matched_concept_id = concept_by_english[nmot]['concept_id']
            match_strategy = 'english_label_exact'
        elif nmot in concept_by_label:
            matched_concept_id = concept_by_label[nmot]['concept_id']
            match_strategy = 'concept_label_exact'
        elif nmot in concept_by_restore:
            matched_concept_id = concept_by_restore[nmot]['concept_id']
            match_strategy = 'concept_restore_exact'
        elif nmot in concept_by_alias:
            matched_concept_id = concept_by_alias[nmot]['concept_id']
            match_strategy = 'alias_match'
        elif nmot in easton_title_to_concept:
            matched_concept_id = easton_title_to_concept[nmot]
            match_strategy = 'easton_title_match'
        elif nmot in smith_title_to_concept:
            matched_concept_id = smith_title_to_concept[nmot]
            match_strategy = 'smith_title_match'
        elif bmot != nmot:
            if bmot in concept_by_english:
                matched_concept_id = concept_by_english[bmot]['concept_id']
                match_strategy = 'english_label_base'
            elif bmot in concept_by_label:
                matched_concept_id = concept_by_label[bmot]['concept_id']
                match_strategy = 'concept_label_base'
            elif bmot in concept_by_restore:
                matched_concept_id = concept_by_restore[bmot]['concept_id']
                match_strategy = 'concept_restore_base'
            elif bmot in concept_by_alias:
                matched_concept_id = concept_by_alias[bmot]['concept_id']
                match_strategy = 'alias_base'
            elif bmot in easton_title_to_concept:
                matched_concept_id = easton_title_to_concept[bmot]
                match_strategy = 'easton_title_base'
            elif bmot in smith_title_to_concept:
                matched_concept_id = smith_title_to_concept[bmot]
                match_strategy = 'smith_title_base'

        if matched_concept_id:
            sources = concept_sources.get(matched_concept_id, set())
            circle = 'C1' if len(sources) >= 2 else 'C2'
        else:
            circle = 'C3'

    strategy_counts[match_strategy or ('redirect' if redir else 'unmatched')] += 1
    circle_counts[circle] += 1
    results.append({
        'isbe_id': idx, 'mot': mot, 'circle': circle,
        'matched_concept_id': matched_concept_id,
        'match_strategy': match_strategy,
        'char_count': char_count, 'size_tier': tier, 'is_redirect': redir
    })

# Report
print(f"\n=== RESULTATS LINKING ===")
for c in ['C1', 'C2', 'C3', 'C4']:
    entries = [r for r in results if r['circle'] == c]
    vol = sum(r['char_count'] for r in entries)
    big = sum(1 for r in entries if r['char_count'] > 5000)
    print(f"  {c}: {len(entries)} ({len(entries)/len(results)*100:.1f}%), {vol:,} chars, {big} T5+")

print(f"\n--- Strategies ---")
for s, c in strategy_counts.most_common():
    print(f"  {s}: {c}")

for c in ['C1', 'C2', 'C3']:
    entries = sorted([r for r in results if r['circle'] == c], key=lambda r: -r['char_count'])
    print(f"\n--- Top 5 {c} ---")
    for r in entries[:5]:
        print(f"  {r['mot']}: {r['char_count']:,} -> {r['matched_concept_id'] or 'NEW'}")

# Cross distribution
print(f"\n=== CROSS TIER x CIRCLE ===")
tiers_list = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7']
circles_list = ['C1', 'C2', 'C3', 'C4']
cross = {}
for r in results:
    key = (r['size_tier'], r['circle'])
    cross[key] = cross.get(key, 0) + 1

print(f"{'Tier':<8} {'C1':>6} {'C2':>6} {'C3':>6} {'C4':>6} {'Total':>6}")
for t in tiers_list:
    row = [cross.get((t, c), 0) for c in circles_list]
    print(f"{t:<8} {row[0]:>6} {row[1]:>6} {row[2]:>6} {row[3]:>6} {sum(row):>6}")
totals = [sum(cross.get((t, c), 0) for t in tiers_list) for c in circles_list]
print(f"{'Total':<8} {totals[0]:>6} {totals[1]:>6} {totals[2]:>6} {totals[3]:>6} {sum(totals):>6}")

# Save files
with open(f'{BASE}/work/codex_local_isbe/isbe-priority-circles.json', 'w', encoding='utf-8-sig') as f:
    json.dump(results, f, ensure_ascii=False, indent=1)
print(f"\nSaved isbe-priority-circles.json ({len(results)} entries)")

dist = {'by_tier': {}, 'by_circle': {}, 'cross': {}}
for t in tiers_list:
    entries = [r for r in results if r['size_tier'] == t]
    dist['by_tier'][t] = {'count': len(entries), 'chars': sum(r['char_count'] for r in entries)}
for c in circles_list:
    entries = [r for r in results if r['circle'] == c]
    dist['by_circle'][c] = {'count': len(entries), 'chars': sum(r['char_count'] for r in entries)}
for t in tiers_list:
    for c in circles_list:
        entries = [r for r in results if r['size_tier'] == t and r['circle'] == c]
        dist['cross'][f'{t}_{c}'] = {'count': len(entries), 'chars': sum(r['char_count'] for r in entries)}

with open(f'{BASE}/work/codex_local_isbe/isbe-size-distribution.json', 'w', encoding='utf-8-sig') as f:
    json.dump(dist, f, ensure_ascii=False, indent=2)
print(f"Saved isbe-size-distribution.json")
