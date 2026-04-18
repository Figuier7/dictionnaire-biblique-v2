#!/usr/bin/env python3
"""
Re-audit des mappings concept->Strong apres re-typage categories.

Maintenant que les categories sont propres, on peut appliquer la regle
POS-categorie sans risque de regression.

Regles :
- Concept cat in {personnage, lieu, peuple, etre_spirituel, tribu} -> Strong doit etre n.pr.*
  (sauf etre_spirituel peut avoir nom commun si label BYM matche le terme hebreu)
- Concept cat in {doctrine, rite, objet_sacre, etc.} -> Strong NE DOIT PAS etre n.pr.*
  (sauf etymologies : rachel=brebis, pere=...)

Usage :
    python scripts/reaudit_hebrew_mappings.py              # audit + rapport
    python scripts/reaudit_hebrew_mappings.py --commit     # applique
"""
import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
META_PATH = BASE / 'uploads/dictionnaires/concept-meta.json'
HMAP_PATH = BASE / 'uploads/dictionnaires/concept-hebrew-map.json'
HLEX_PATH = BASE / 'uploads/dictionnaires/hebrew/hebrew-lexicon-fr-compact.json'
REPORT = BASE / 'work/retype/reaudit_report.json'

PROPER_CATS = {
    'personnage', 'lieu', 'peuple', 'livre_biblique',
    # etre_spirituel, lieu_sacre : permissifs (accepte propre ET commun)
    # Lieu_sacre peut etre nom commun (heykal = temple, mishkan = tabernacle)
    # etre_spirituel : nomme (YHWH, Gabriel) ou generique (ange, seraphin)
}
SEMANTIC_CATS = {
    'doctrine', 'rite', 'institution', 'fonction',
    'objet_sacre', 'objets_et_vetements',
    'plante', 'animal', 'alimentation_et_agriculture',
    'corps_et_sante', 'mesures_et_temps', 'matiere',
    'evenement', 'nature',
}
# PERMISSIVE = {etre_spirituel, lieu_sacre} : accepte les deux (implicite, pas dans les regles)


def normalize(s):
    s = str(s or '').lower().strip()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^a-z0-9]', '', s)
    return s


def pos_is_proper(pos):
    if not pos: return False
    p = pos.lower()
    return 'n-pr' in p or 'n.pr' in p or p.endswith('.pr') or '.pr.' in p


PROPER_DEF_PATTERNS = re.compile(
    r'\bun\s+isra[eé]lite\b|le\s+nom\s+(du|de|d\W)|\bnom\s+propre\b|\bn\.pr|'
    r'\bune?\s+moabite\b|\bun\s+proph[eè]te\b|\bun\s+lieu\s+(en|dans|de)\b|'
    r'\bune\s+ville\b|\bune\s+divinit[eé]\b|\bun\s+patriarche\b|\bun\s+archange\b|'
    r'\byahweh\b|\bjeho-vah\b|\btribu\s+de\b|\bun\s+[éeE]domite\b',
    re.IGNORECASE
)
COMMON_DEF_PATTERNS = re.compile(
    r'^une?\s+[a-z]|^la\s+\w|^le\s+\w+\s+\(|^\W?etre\b|^\W?avoir\b|^se\s|'
    r'^\W?d\Wo[uù]\s|^proprement\b|^concr\.|^abstr\.|^celui qui|^ce qui|'
    r'^faire\s|^\W?aller\b|^\W?venir\b|^se\W'
)


def def_is_proper(d):
    return bool(d and PROPER_DEF_PATTERNS.search(d.lower()))


def def_is_common(d):
    if not d: return False
    dl = d.lower().strip()
    if PROPER_DEF_PATTERNS.search(dl): return False
    return bool(COMMON_DEF_PATTERNS.search(dl))


def audit(meta, hmap, lex_by_s):
    kept_map = {}
    removed = []
    stats = Counter()

    for cid, entries in hmap.items():
        m = meta.get(cid, {})
        cat = m.get('c', '')
        if not isinstance(entries, list):
            kept_map[cid] = entries
            continue

        kept = []
        for entry in entries:
            sid = entry if isinstance(entry, str) else entry.get('s', '')
            if not sid: continue
            e = lex_by_s.get(sid, {})
            d = e.get('d', '') or ''
            pos = e.get('bp') or e.get('p', '') or ''

            is_proper = def_is_proper(d) or pos_is_proper(pos)
            is_common = def_is_common(d) and not pos_is_proper(pos)

            reason = None
            if cat in PROPER_CATS:
                # Concept nom propre -> Strong doit etre nom propre
                if is_common and not is_proper:
                    reason = f'{cat}_concept_vs_common_strong'
            elif cat in SEMANTIC_CATS:
                # Concept semantique -> Strong ne doit pas etre nom propre
                if is_proper and not is_common:
                    # Exception : le label du concept ressemble au debut de def Strong
                    labels = [normalize(m.get(k, '')) for k in ('p', 'l', 'r') if m.get(k)]
                    labels = [l for l in labels if l]
                    def_first = normalize(d.split(',')[0] if ',' in d else d)[:10]
                    if not any(l and l[:6] == def_first[:6] for l in labels):
                        reason = f'{cat}_concept_vs_proper_strong'
            # etre_spirituel : permissif, pas de rejet

            if reason:
                removed.append({
                    'cid': cid, 'cat': cat, 's': sid, 'pos': pos,
                    'd': d[:80], 'reason': reason
                })
                stats[reason] += 1
            else:
                kept.append(entry)

        if kept:
            kept_map[cid] = kept

    return kept_map, removed, stats


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--commit', action='store_true')
    args = p.parse_args()

    sys.stdout.reconfigure(encoding='utf-8')

    with open(META_PATH, encoding='utf-8') as f:
        meta = json.load(f)
    with open(HMAP_PATH, encoding='utf-8') as f:
        hmap = json.load(f)
    with open(HLEX_PATH, encoding='utf-8') as f:
        hlex = json.load(f)
    lex_by_s = {e['s']: e for e in hlex}

    kept_map, removed, stats = audit(meta, hmap, lex_by_s)

    total_before = sum(len(v) if isinstance(v, list) else 1 for v in hmap.values())
    total_after = sum(len(v) if isinstance(v, list) else 1 for v in kept_map.values())
    print(f'Mappings: {total_before} -> {total_after} (retraits: {total_before - total_after})')
    print(f'Concepts avec mapping: {len(hmap)} -> {len(kept_map)}')
    print(f'\nRaisons:')
    for reason, count in stats.most_common():
        print(f'  {reason:50s} : {count}')

    # Protection : verifier critical concepts
    CRITICAL = [
        ('pere', 'H1'),
        ('yhwh', 'H3068'),
        ('aaron', 'H175'),
        ('moshe', 'H4872'),
        ('david', 'H1732'),
        ('figuier', 'H8384'),
        ('temple', 'H1964'),
        ('amour', 'H1730'),
        ('paix', 'H7965'),
        ('justice', 'H6666'),
    ]
    print(f'\n=== Verif mappings critiques ===')
    all_ok = True
    for cid, expected_s in CRITICAL:
        entries = kept_map.get(cid, [])
        strongs = [e if isinstance(e, str) else e.get('s', '') for e in entries]
        if expected_s in strongs:
            print(f'  {cid:15s} : OK ({expected_s} preserve)')
        else:
            all_ok = False
            print(f'  {cid:15s} : REGRESSION ! {expected_s} retire (kept: {strongs})')

    with open(REPORT, 'w', encoding='utf-8') as f:
        json.dump({
            'total_before': total_before, 'total_after': total_after,
            'removed_count': len(removed),
            'stats_by_reason': dict(stats),
            'removed_samples': removed[:100],
        }, f, ensure_ascii=False, indent=2)
    print(f'\nReport saved to {REPORT}')

    if not all_ok:
        print('\n[X] Regression detectee. Ne pas committer.')
        sys.exit(1)

    if not args.commit:
        print('\n--- DRY RUN. Add --commit to apply. ---')
        return

    # Backup + apply
    bak = HMAP_PATH.with_suffix(HMAP_PATH.suffix + '.bak-pre-reaudit')
    if not bak.exists():
        bak.write_bytes(HMAP_PATH.read_bytes())
        print(f'Backup: {bak}')
    with open(HMAP_PATH, 'w', encoding='utf-8') as f:
        json.dump(kept_map, f, ensure_ascii=False, separators=(',', ':'))
    print(f'[OK] Applied to {HMAP_PATH}')


if __name__ == '__main__':
    main()
