#!/usr/bin/env python3
"""
Expansion des mappings concept -> Strong par auto-match first-gloss / translit.

Strategie :
- Concepts SEMANTIQUES (doctrine, rite, objet_sacre, etc.) : match par glosses FR,
  filtrage Strong pos non-proper (n.m / n.f / vb / adj).
- Concepts NOMS PROPRES (personnage, lieu, peuple, etc.) : match par translit
  (concept.p BYM vs Strong.x), filtrage Strong pos proper (n.pr*).
- Concepts PERMISSIFS (etre_spirituel, lieu_sacre) : les deux approches acceptees.

Priorite :
  1. Match exact sur first gloss (g[0]) ou xlit -> confiance HAUTE
  2. Match exact sur n'importe quel gloss -> confiance MOYENNE
  3. Match sur def_short (d) complete ou en preambule -> confiance BASSE
  (seule la HAUTE est appliquee automatiquement par defaut)

Usage :
  python scripts/expand_hebrew_mappings.py             # dry-run + stats
  python scripts/expand_hebrew_mappings.py --commit    # applique les matches HAUTE
  python scripts/expand_hebrew_mappings.py --commit --level=medium  # inclut MOYENNE
"""
import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
META_PATH = BASE / 'uploads/dictionnaires/concept-meta.json'
HMAP_PATH = BASE / 'uploads/dictionnaires/concept-hebrew-map.json'
HLEX_PATH = BASE / 'uploads/dictionnaires/hebrew/hebrew-lexicon-fr-compact.json'
REPORT = BASE / 'work/expand_mappings_report.json'

PROPER_CATS = {'personnage', 'lieu', 'peuple', 'livre_biblique'}
PERMISSIVE_CATS = {'etre_spirituel', 'lieu_sacre'}
SEMANTIC_CATS = {
    'doctrine', 'rite', 'institution', 'fonction',
    'objet_sacre', 'objets_et_vetements',
    'plante', 'animal', 'alimentation_et_agriculture',
    'corps_et_sante', 'mesures_et_temps', 'matiere',
    'evenement', 'nature',
}


def normalize(s):
    if not s: return ''
    s = str(s).lower().strip()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r"[^a-z0-9'\s-]", ' ', s)
    s = re.sub(r"'", '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def normalize_translit(s):
    s = normalize(s)
    # Normalisations de translitteration
    s = re.sub(r'\bj', 'y', s)         # Jirmejah -> yirmejah
    s = s.replace('ch', 'h').replace('kh', 'h')  # Chanok -> hanok
    s = re.sub(r'\btz', 'ts', s)
    s = s.replace('ow', 'o').replace('aw', 'a').replace('ou', 'u')
    s = re.sub(r'[yi]{2,}', 'y', s)
    s = s.replace(' ', '').replace('-', '')
    return s


def pos_is_proper(pos):
    if not pos: return False
    p = pos.lower()
    return 'n-pr' in p or 'n.pr' in p or '.pr.' in p or p.endswith('.pr')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--commit', action='store_true', help='Apply matches (not dry-run)')
    p.add_argument('--level', default='high', choices=['high','medium'],
                   help='Confidence level to apply (default: high)')
    args = p.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')

    with open(META_PATH, encoding='utf-8') as f: meta = json.load(f)
    with open(HMAP_PATH, encoding='utf-8') as f: hmap = json.load(f)
    with open(HLEX_PATH, encoding='utf-8') as f: hlex = json.load(f)

    # Index by Strong
    by_s = {e['s']: e for e in hlex}

    # ===== INDEX POUR MATCHING =====
    # first_gloss_index[normalized_gloss] = [(sid, pos), ...]
    first_gloss_index = defaultdict(list)
    all_gloss_index = defaultdict(list)
    xlit_index = defaultdict(list)

    for entry in hlex:
        sid = entry['s']
        pos = entry.get('bp') or entry.get('p', '') or ''

        glosses = entry.get('g') or []
        if isinstance(glosses, list) and glosses:
            for i, g in enumerate(glosses):
                if not isinstance(g, str): continue
                n = normalize(g)
                if n:
                    all_gloss_index[n].append((sid, pos))
                    if i == 0:
                        first_gloss_index[n].append((sid, pos))

        x = entry.get('x') or ''
        if x:
            n = normalize_translit(x)
            if n:
                xlit_index[n].append((sid, pos))

    print(f'Index built:')
    print(f'  first_gloss unique keys : {len(first_gloss_index)}')
    print(f'  all_gloss unique keys   : {len(all_gloss_index)}')
    print(f'  xlit unique keys        : {len(xlit_index)}')
    print()

    # ===== MATCHING =====
    matches_high = []
    matches_medium = []
    skipped = Counter()

    unmapped_cids = [cid for cid in meta if not hmap.get(cid)]
    print(f'Concepts sans mapping : {len(unmapped_cids)}')

    for cid in unmapped_cids:
        m = meta[cid]
        cat = m.get('c', '')

        # Collecter labels du concept
        labels_raw = []
        for k in ('p', 'l', 'r', 's'):
            if m.get(k): labels_raw.append(m[k])
        for k in ('other_forms', 'aliases'):
            v = m.get(k) or []
            if isinstance(v, list): labels_raw.extend([x for x in v if isinstance(x, str)])
        labels_norm = list({normalize(x) for x in labels_raw if x})
        labels_trans = list({normalize_translit(x) for x in labels_raw if x})

        # Exception : livres bibliques : pas de mapping Strong justifie
        if cat == 'livre_biblique':
            skipped['livre_biblique'] += 1
            continue

        # ===== Strategie par categorie =====
        if cat in PROPER_CATS:
            # Match par translit
            candidates = []
            for lt in labels_trans:
                if lt in xlit_index:
                    for sid, pos in xlit_index[lt]:
                        if pos_is_proper(pos):
                            candidates.append((sid, pos, 'high_translit'))
            if not candidates:
                skipped['proper_no_match'] += 1
                continue
            # Dedup
            seen = set()
            uniq = []
            for c in candidates:
                if c[0] not in seen:
                    seen.add(c[0]); uniq.append(c)
            # Garde tous (un concept peut correspondre a plusieurs Strongs homonymes)
            matches_high.append({'cid': cid, 'cat': cat, 'matches': uniq[:5]})

        elif cat in SEMANTIC_CATS:
            # Match par first gloss exact
            high_cands, medium_cands = [], []
            for ln in labels_norm:
                if ln in first_gloss_index:
                    for sid, pos in first_gloss_index[ln]:
                        if not pos_is_proper(pos):
                            high_cands.append((sid, pos, 'high_first_gloss'))
                elif ln in all_gloss_index:
                    for sid, pos in all_gloss_index[ln]:
                        if not pos_is_proper(pos):
                            medium_cands.append((sid, pos, 'medium_any_gloss'))
            if high_cands:
                seen = set(); uniq = []
                for c in high_cands:
                    if c[0] not in seen: seen.add(c[0]); uniq.append(c)
                matches_high.append({'cid': cid, 'cat': cat, 'matches': uniq[:5]})
            elif medium_cands:
                seen = set(); uniq = []
                for c in medium_cands:
                    if c[0] not in seen: seen.add(c[0]); uniq.append(c)
                matches_medium.append({'cid': cid, 'cat': cat, 'matches': uniq[:5]})
            else:
                skipped['semantic_no_match'] += 1

        elif cat in PERMISSIVE_CATS:
            # Try both strategies
            cands = []
            for lt in labels_trans:
                if lt in xlit_index:
                    for sid, pos in xlit_index[lt]:
                        cands.append((sid, pos, 'high_translit'))
            for ln in labels_norm:
                if ln in first_gloss_index:
                    for sid, pos in first_gloss_index[ln]:
                        cands.append((sid, pos, 'high_first_gloss'))
            if cands:
                seen = set(); uniq = []
                for c in cands:
                    if c[0] not in seen: seen.add(c[0]); uniq.append(c)
                matches_high.append({'cid': cid, 'cat': cat, 'matches': uniq[:5]})
            else:
                skipped['permissive_no_match'] += 1

        else:
            skipped['unknown_cat'] += 1

    # ===== STATS =====
    print(f'\n=== Match results ===')
    print(f'HIGH confidence   : {len(matches_high)}')
    print(f'MEDIUM confidence : {len(matches_medium)}')
    print(f'Skipped:')
    for reason, c in skipped.most_common():
        print(f'  {reason:30s} : {c}')

    # Distribution par catégorie des new matches
    print(f'\n=== HIGH matches par catégorie ===')
    high_by_cat = Counter(m['cat'] for m in matches_high)
    for cat, c in high_by_cat.most_common():
        print(f'  {cat:30s} : {c}')

    # Sample 30 HIGH matches
    print(f'\n=== 30 HIGH matches (sample) ===')
    import random
    random.seed(42)
    sample = random.sample(matches_high, min(30, len(matches_high)))
    for m in sample:
        cid = m['cid']; meta_m = meta.get(cid, {})
        label = meta_m.get('p') or meta_m.get('l') or cid
        matches_str = ', '.join([f'{mm[0]}({mm[1]})' for mm in m['matches'][:3]])
        print(f'  {cid[:22]:22s} ({m["cat"][:12]:12s}) "{label[:15]:15s}" -> {matches_str}')

    # Save report
    report_data = {
        'total_unmapped': len(unmapped_cids),
        'matches_high_count': len(matches_high),
        'matches_medium_count': len(matches_medium),
        'skipped': dict(skipped),
        'high_by_cat': dict(high_by_cat),
        'sample_high': sample[:50],
        'sample_medium': matches_medium[:30],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    print(f'\nReport saved to {REPORT}')

    # Protection mappings critiques apres apply
    CRITICAL = [
        ('pere', 'H1'), ('yhwh', 'H3068'), ('aaron', 'H175'),
        ('moshe', 'H4872'), ('david', 'H1732'), ('figuier', 'H8384'),
        ('temple', 'H1964'), ('amour', 'H1730'), ('paix', 'H7965'),
        ('justice', 'H6666'),
    ]

    if not args.commit:
        print('\n--- DRY RUN. Add --commit to apply. ---')
        return

    # APPLY
    matches_to_apply = list(matches_high)
    if args.level == 'medium':
        matches_to_apply += matches_medium
    print(f'\nApplying {len(matches_to_apply)} matches (level={args.level})...')

    added = 0
    for m in matches_to_apply:
        cid = m['cid']
        if cid in hmap and hmap[cid]:
            continue  # safety
        entries = []
        for sid, pos, source in m['matches']:
            e = by_s.get(sid)
            if e:
                entries.append({'s': sid, 'h': e.get('h',''), 'x': e.get('x','')})
        if entries:
            hmap[cid] = entries
            added += 1

    # Verif critical preservation
    print('\nCritical mappings post-expand :')
    all_ok = True
    for cid, expected in CRITICAL:
        entries = hmap.get(cid, [])
        sids = [e.get('s') if isinstance(e, dict) else e for e in entries]
        if expected in sids:
            print(f'  {cid:15s} : OK')
        else:
            print(f'  {cid:15s} : REGRESSION !! {expected} absent')
            all_ok = False

    if not all_ok:
        print('\n[X] Regression detected — not saving')
        return

    # Backup + save
    bak = HMAP_PATH.with_suffix(HMAP_PATH.suffix + '.bak-pre-expand')
    if not bak.exists():
        bak.write_bytes(HMAP_PATH.read_bytes())
        print(f'Backup: {bak}')
    with open(HMAP_PATH, 'w', encoding='utf-8') as f:
        json.dump(hmap, f, ensure_ascii=False, separators=(',',':'))
    print(f'\n[OK] Added {added} new mappings, total concepts with mapping: {sum(1 for v in hmap.values() if v)}')


if __name__ == '__main__':
    main()
