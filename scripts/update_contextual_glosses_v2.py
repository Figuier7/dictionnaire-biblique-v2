#!/usr/bin/env python3
"""
Raffinement contextuel des glosses pour 3 Strong polysémiques :
  - H7307  רוּחַ  : Esprit / vent / souffle / esprit / côté
  - H120   אָדָם   : Adam / l'humain / humain
  - H2617  חֶסֶד  : bonté / fidélité / miséricorde / grâce

Écrit dans :
  - tous les fichiers uploads/dictionnaires/interlinear/*.json (champ `g`)
  - pas de modif du lexique (ig = gloss par défaut = "esprit" / "humain" / "bonté")

Usage :
    python scripts/update_contextual_glosses_v2.py              # dry-run
    python scripts/update_contextual_glosses_v2.py --apply      # écrit
    python scripts/update_contextual_glosses_v2.py --strong H7307  # limiter

Règles détaillées dans README interne du script.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
INTERLIN_DIR = BASE / 'uploads' / 'dictionnaires' / 'interlinear'

# ==== Strong numbers (références) ====
S_YHWH = 'H3068'
S_ELOHIM = 'H430'
S_EMET = 'H571'
S_BERIT = 'H1285'
S_RAHAMIM = 'H7356'
S_OLAM = 'H5769'
S_HANAN = 'H2603'
S_NASHAB = 'H5380'
S_NEPHESH = 'H5315'
S_KHAY = 'H2416'
S_TSAFON = 'H6828'   # nord
S_YAM = 'H3220'      # mer / ouest
S_QEDEM = 'H6924'    # est / ancien
S_NEGEV = 'H5045'    # sud
S_MIZRAH = 'H4217'   # lever, est
S_QADIM = 'H6921'    # vent d'est / qadim
S_ARBA = 'H702'      # quatre (quatre vents)

DIRECTIONAL = {S_TSAFON, S_YAM, S_QEDEM, S_NEGEV, S_MIZRAH, S_QADIM}


def read_json_with_bom(path):
    with open(path, 'rb') as f:
        raw = f.read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    if bom:
        raw = raw[3:]
    return json.loads(raw.decode('utf-8')), bom


def write_interlinear(path, data, bom):
    # Interlinear files use compact separators (',', ':')
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if bom:
        payload = b'\xef\xbb\xbf' + payload
    with open(path, 'wb') as f:
        f.write(payload)


def strongs_in_window(words, i, window):
    lo = max(0, i - window)
    hi = min(len(words), i + window + 1)
    out = set()
    for j in range(lo, hi):
        if j == i:
            continue
        s = words[j].get('s')
        if s:
            out.add(s)
    return out


def strongs_in_verse(words, i):
    return {words[j].get('s') for j in range(len(words)) if j != i and words[j].get('s')}


# ---------------- H7307 ruaḥ ----------------
def classify_h7307(words, i):
    """Retourne (gloss, rule_tag)

    Ordre de priorité :
    1. Direction cardinale en ±2 → vent (priorité absolue : 'ruaḥ qadim', 'ruaḥ yam')
    2. Divin en ±2 → Esprit
    3. Suffixe + divin dans verset → Esprit
    4. H5315 (nephesh) ou H2416 (khay) en ±2 → souffle (de vie)
    5. H5380 (nashab, souffler) dans verset → vent
    6. Défaut → esprit
    """
    w = words[i]
    morph = w.get('m', '')

    near2 = strongs_in_window(words, i, 2)
    in_verse = strongs_in_verse(words, i)

    # 1. Direction cardinale en ±2 : vent (priorité — 'ruaḥ qadim', 'ruaḥ yam')
    cardinal_near = near2 & DIRECTIONAL
    if cardinal_near or S_ARBA in near2:
        return ('vent', 'directional')

    # 2. ruaḥ YHWH / ruaḥ Elohîm / divin proche
    if S_YHWH in near2 or S_ELOHIM in near2:
        return ('Esprit', 'divine_proximity')

    # 3. Suffixe pronominal + locuteur divin dans verset
    has_suffix = '/Sp' in morph
    if has_suffix and (S_YHWH in in_verse or S_ELOHIM in in_verse):
        return ('Esprit', 'divine_verse_suffix')

    # 4. Pair avec nephesh / khay = souffle de vie
    if S_NEPHESH in near2 or S_KHAY in near2:
        return ('souffle', 'life_pair')

    # 5. Verbe "souffler" dans le verset
    if S_NASHAB in in_verse:
        return ('vent', 'nashab')

    # 6. Défaut : esprit (minuscule — disposition, esprit humain, esprit neutre)
    return ('esprit', 'default')


# ---------------- H120 adam ----------------
def classify_h120(words, i, book, chap):
    """Retourne (gloss, rule_tag)"""
    w = words[i]
    morph = w.get('m', '')
    has_article = '/Td/' in morph or morph.startswith('HTd/')

    # En Gn 1-5 : cas particulier (premier humain / Adam)
    if book == '01-Gen' and chap in ('1', '2', '3', '4', '5'):
        if has_article:
            return ('l\u2019humain', 'gen_with_article')
        else:
            # Sans article en Gn 1-5 : souvent nom propre Adam
            return ('Adam', 'gen_proper')

    # Partout ailleurs : défaut = humain (avec article si ha- présent)
    if has_article:
        return ('l\u2019humain', 'with_article')

    return ('humain', 'default')


# ---------------- H2617 ḥesed ----------------
def classify_h2617(words, i):
    """Retourne (gloss, rule_tag)"""
    near3 = strongs_in_window(words, i, 3)
    in_verse = strongs_in_verse(words, i)

    # 1. Paire classique "ḥesed we-emet" : fidélité
    if S_EMET in near3:
        return ('fid\u00e9lit\u00e9', 'with_emet')

    # 2. Avec berit (alliance) dans le verset : fidélité (d'alliance)
    if S_BERIT in in_verse:
        return ('fid\u00e9lit\u00e9', 'with_berit')

    # 3. Avec rahamim (compassion) : miséricorde
    if S_RAHAMIM in in_verse:
        return ('mis\u00e9ricorde', 'with_rahamim')

    # 4. Avec olam (éternel) en ±3 : fidélité (éternelle) — Ps 136 etc.
    if S_OLAM in near3:
        return ('fid\u00e9lit\u00e9', 'with_olam')

    # 5. Avec hanan (gratifier) en ±3 : grâce
    if S_HANAN in near3:
        return ('gr\u00e2ce', 'with_hanan')

    # 6. Défaut
    return ('bont\u00e9', 'default')


# ---------------- Processor ----------------
CLASSIFIERS = {
    'H7307': lambda words, i, book, chap: classify_h7307(words, i),
    'H120':  lambda words, i, book, chap: classify_h120(words, i, book, chap),
    'H2617': lambda words, i, book, chap: classify_h2617(words, i),
}


def process_files(targets, apply_changes, sample_count=5):
    total_updates = 0
    by_strong = {s: {'count': 0, 'before': Counter(), 'after': Counter(), 'rules': Counter()} for s in targets}
    samples = defaultdict(list)  # (strong, rule) -> [(ref, before, after, text)]

    for fp in sorted(INTERLIN_DIR.glob('*.json')):
        book = fp.stem
        data, bom = read_json_with_bom(fp)
        file_updates = 0

        chapters = data.get('chapters') or {}
        for chap, verses in chapters.items():
            for vnum, words in verses.items():
                for i, w in enumerate(words):
                    s = w.get('s')
                    if s not in targets:
                        continue
                    old_gloss = w.get('g', '')
                    new_gloss, rule = CLASSIFIERS[s](words, i, book, chap)

                    by_strong[s]['count'] += 1
                    by_strong[s]['before'][old_gloss] += 1
                    by_strong[s]['after'][new_gloss] += 1
                    by_strong[s]['rules'][rule] += 1

                    if old_gloss != new_gloss:
                        if len(samples[(s, rule)]) < sample_count:
                            samples[(s, rule)].append({
                                'ref': f'{book} {chap}:{vnum}',
                                'before': old_gloss,
                                'after': new_gloss,
                                'text': w.get('t', ''),
                                'context_strongs': [words[j].get('s') for j in range(max(0, i-2), min(len(words), i+3))],
                            })
                        w['g'] = new_gloss
                        file_updates += 1

        if apply_changes and file_updates:
            write_interlinear(fp, data, bom)
        if file_updates:
            print(f'  [{book}] {file_updates} updates')
        total_updates += file_updates

    print()
    print('=' * 60)
    print('STATISTIQUES PAR STRONG')
    print('=' * 60)
    for s in targets:
        d = by_strong[s]
        print(f'\n=== {s} ({d["count"]} occurrences) ===')
        print('  Glosses AVANT :')
        for g, n in d['before'].most_common():
            print(f'    {g!r:<30} : {n}')
        print('  Glosses APRES :')
        for g, n in d['after'].most_common():
            print(f'    {g!r:<30} : {n}')
        print('  Règles appliquées :')
        for r, n in d['rules'].most_common():
            print(f'    {r:<30} : {n}')

    print()
    print('=' * 60)
    print('ECHANTILLONS (max {} par règle)'.format(sample_count))
    print('=' * 60)
    for (s, rule), ss in sorted(samples.items()):
        print(f'\n--- {s} / {rule} ({len(ss)} ex) ---')
        for x in ss:
            print(f'  {x["ref"]:<22} | {x["text"]:<20} | {x["before"]!r:<12} -> {x["after"]!r:<15} | ctx={x["context_strongs"]}')

    print()
    print(f'TOTAL updates : {total_updates}')
    return total_updates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--strong', action='append', choices=list(CLASSIFIERS.keys()),
                    help='Limiter à un Strong (peut être répété). Par défaut : tous.')
    ap.add_argument('--samples', type=int, default=5)
    args = ap.parse_args()

    targets = set(args.strong) if args.strong else set(CLASSIFIERS.keys())
    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'=== Raffinement contextuel ({mode}) — cibles: {sorted(targets)} ===')
    print()
    process_files(targets, args.apply, args.samples)


if __name__ == '__main__':
    main()
