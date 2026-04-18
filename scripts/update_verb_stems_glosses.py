#!/usr/bin/env python3
"""
Raffine la gloss des verbes he\u0301breux selon leur STEM (binyan).
Modifie uniquement `g` dans les fichiers interlinear (pas le lexique, car
la gloss par stem ne peut pas etre unique pour un Strong donne\u0301).

Lecture : champ `m` du mot (code morphologique OSHB).
Format du code : lang(H/A) + V(erb) + stem(1 char) + aspect(1 char) + person/gender/number
Exemples : HVqp3ms (Qal Perfect 3rd masc sing), HVhi3ms (Hiphil Imperfect...)

Stems:
  q = Qal      (simple actif)
  N = Niphal   (passif/re\u0301fle\u0301chi)
  p = Piel     (intensif/factitif)
  P = Pual     (passif du Piel)
  h = Hiphil   (causatif)
  H = Hophal   (passif du Hiphil)
  t = Hithpael (re\u0301flechi intensif)
  o = Po\u02bbl / Polel (racines concaves)

Usage:
    python scripts/update_verb_stems_glosses.py             # dry-run
    python scripts/update_verb_stems_glosses.py --apply
"""
import argparse
import io
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
INTERLIN_DIR = BASE / 'uploads' / 'dictionnaires' / 'interlinear'

# Table de gloss par stem (base : BDB classique + distribution reele)
# La gloss par defaut `_default` est utilisee si un stem non liste est rencontre\u0301.
VERB_STEM_GLOSS = {
    # H935 \u05D1\u05D5\u05B9\u05D0 - venir/amener
    'H935': {
        'q': 'venir',
        'h': 'amener',
        'H': 'e\u0302tre amene\u0301',
        '_default': 'venir',
    },
    # H3318 \u05D9\u05B8\u05E6\u05B8\u05D0 - sortir/faire sortir
    'H3318': {
        'q': 'sortir',
        'h': 'faire sortir',
        'H': 'e\u0302tre mene\u0301 dehors',
        '_default': 'sortir',
    },
    # H7725 \u05E9\u05C1\u05D5\u05BC\u05D1 - retourner/ramener
    'H7725': {
        'q': 'retourner',
        'h': 'ramener',
        'o': 'restaurer',   # Polel
        'H': 'e\u0302tre ramene\u0301',
        '_default': 'retourner',
    },
    # H5927 \u05E2\u05B8\u05DC\u05B8\u05D4 - monter/offrir
    'H5927': {
        'q': 'monter',
        'h': 'faire monter',  # usage sacrificatoire courant : "offrir"
        'N': 'e\u0302tre e\u0301leve\u0301',
        'H': 'e\u0302tre offert',
        't': 'se dresser',
        '_default': 'monter',
    },
    # H7200 \u05E8\u05B8\u05D0\u05B8\u05D4 - voir/apparai\u0302tre/montrer
    'H7200': {
        'q': 'voir',
        'N': 'apparai\u0302tre',
        'p': 'pre\u0301senter',
        'P': 'e\u0302tre montre\u0301',
        'h': 'montrer',
        'H': 'e\u0302tre montre\u0301',
        't': 'se regarder',
        '_default': 'voir',
    },
    # H8085 \u05E9\u05C1\u05B8\u05DE\u05B7\u05E2 - entendre/proclamer
    'H8085': {
        'q': 'entendre',
        'N': 'e\u0302tre entendu',
        'p': 'convoquer',
        'h': 'proclamer',
        '_default': 'entendre',
    },
    # H3045 \u05D9\u05B8\u05D3\u05B7\u05E2 - conna\u00eetre/re\u0301ve\u0301ler
    'H3045': {
        'q': 'connai\u0302tre',
        'N': 'e\u0302tre connu',
        'p': 'faire connai\u0302tre',
        'P': 'e\u0302tre re\u0301ve\u0301le\u0301',
        'h': 'faire connai\u0302tre',
        'H': 'e\u0302tre re\u0301ve\u0301le\u0301',
        't': 'se faire connai\u0302tre',
        '_default': 'connai\u0302tre',
    },
    # H1696 \u05D3\u05B8\u05D1\u05B7\u05E8 - parler (Piel dominant)
    'H1696': {
        'q': 'parler',  # Qal rare mais on garde "parler"
        'N': 'converser',
        'p': 'parler',   # Piel = forme dominante
        'P': 'e\u0302tre dit',
        'h': 'diriger',
        't': 'parler a\u0300 soi-me\u0302me',
        '_default': 'parler',
    },
    # H1288 \u05D1\u05B8\u05E8\u05B7\u05DA - be\u0301nir (Piel dominant) / s'agenouiller (Qal)
    'H1288': {
        'q': 's\u2019agenouiller',
        'N': 'e\u0302tre be\u0301ni',
        'p': 'be\u0301nir',      # Piel = dominant
        'P': 'e\u0302tre be\u0301ni',
        'h': 'faire agenouiller',
        't': 'se be\u0301nir',
        '_default': 'be\u0301nir',
    },
    # H6680 \u05E6\u05B8\u05D5\u05B8\u05D4 - commander (Piel quasi exclusif)
    'H6680': {
        'p': 'commander',
        'P': 'e\u0302tre commande\u0301',
        '_default': 'commander',
    },
    # H4427 \u05DE\u05B8\u05DC\u05B7\u05DA - re\u0301gner/etablir
    'H4427': {
        'q': 're\u0301gner',
        'h': 'faire roi',
        'N': 'e\u0302tre conseille\u0301',
        'H': 'e\u0302tre couronne\u0301',
        '_default': 're\u0301gner',
    },
    # H3427 \u05D9\u05B8\u05E9\u05C1\u05B7\u05D1 - habiter/s'asseoir
    'H3427': {
        'q': 'habiter',
        'N': 'e\u0302tre habite\u0301',
        'p': 'e\u0301tablir',
        'h': 'faire habiter',
        'H': 'e\u0302tre peuple\u0301',
        '_default': 'habiter',
    },

    # ======= BATCH 2 : Verbes de mouvement / action additionnels =======

    # H1980 \u05D4\u05B8\u05DC\u05B7\u05DA ha\u0302lak - marcher/aller
    'H1980': {
        'q': 'marcher',
        'p': 'mener',
        't': 'se promener',   # Hithpael : marcher avec Elohi\u0302m, se conduire
        'N': 'disparai\u0302tre',
        'h': 'faire aller',
        '_default': 'marcher',
    },
    # H7121 \u05E7\u05B8\u05E8\u05B8\u05D0 qara' - appeler/nommer/proclamer
    'H7121': {
        'q': 'appeler',
        'N': 'e\u0302tre appele\u0301',
        'P': 'e\u0302tre nomme\u0301',
        '_default': 'appeler',
    },
    # H4191 \u05DE\u05D5\u05BC\u05EA muth - mourir/tuer
    'H4191': {
        'q': 'mourir',
        'h': 'mettre a\u0300 mort',   # Hiphil causatif
        'H': 'e\u0302tre mis a\u0300 mort',
        'o': 'tuer',                 # Polel (poetique)
        '_default': 'mourir',
    },
    # H5117 \u05E0\u05D5\u05BC\u05D7\u05B7 nu\u0101\u1e25 - reposer/de\u0301poser
    'H5117': {
        'q': 'se reposer',
        'h': 'de\u0301poser',
        'H': 'e\u0302tre de\u0301pose\u0301',
        '_default': 'se reposer',
    },
    # H3947 \u05DC\u05B8\u05E7\u05B7\u05D7 laqach - prendre
    'H3947': {
        'q': 'prendre',
        'N': 'e\u0302tre pris',
        'P': 'e\u0302tre saisi',
        't': 'e\u0302tre enlace\u0301',   # rare (Ex 9:24 feu qui s'entrelace)
        '_default': 'prendre',
    },
    # H3467 \u05D9\u05B8\u05E9\u05C1\u05B7\u05E2 yashaʻ - sauver (PAS de Qal !)
    'H3467': {
        'h': 'sauver',               # Hiphil dominant - racine de Yehoshoua/Yeshoua
        'N': 'e\u0302tre sauve\u0301',
        '_default': 'sauver',
    },
    # H6030 \u05E2\u05B8\u05E0\u05B8\u05D4 ʻanah - re\u0301pondre / affliger
    'H6030': {
        'q': 're\u0301pondre',
        'N': 'e\u0302tre entendu',
        'p': 'affliger',             # Piel = humilier, affliger
        'P': 'e\u0302tre afflige\u0301',
        'h': 'faire chanter',        # rare
        '_default': 're\u0301pondre',
    },
    # H3205 \u05D9\u05B8\u05DC\u05B7\u05D3 yalad - engendrer/naître/accoucher
    'H3205': {
        'q': 'engendrer',            # enfanter/engendrer selon sujet
        'N': 'nai\u0302tre',
        'p': 'aider a\u0300 accoucher',    # Piel = sage-femme
        'P': 'e\u0302tre ne\u0301',
        'h': 'engendrer',
        'H': 'e\u0302tre mis au monde',
        't': 'se de\u0301clarer',         # rare
        '_default': 'engendrer',
    },
    # H2421 \u05D7\u05B8\u05D9\u05B8\u05D4 chayah - vivre/ranimer
    'H2421': {
        'q': 'vivre',
        'p': 'faire vivre',           # Piel = pre\u0301server, ranimer
        'h': 'ramener a\u0300 la vie',    # Hiphil causatif
        '_default': 'vivre',
    },
    # H5674 \u05E2\u05B8\u05D1\u05B7\u05E8 ʻabar - passer / faire passer / transgresser
    'H5674': {
        'q': 'passer',
        'h': 'faire passer',
        'N': 'e\u0302tre transgresse\u0301',
        'p': 'irriter',              # Piel = provoquer, transgresser
        't': 's\u2019emporter',           # Hithpael = se courroucer
        '_default': 'passer',
    },
    # H7311 \u05E8\u05D5\u05BC\u05DD rum - e\u0301lever / e\u0302tre haut
    'H7311': {
        'q': 'e\u0302tre haut',
        'h': 'e\u0301lever',
        'o': 'exalter',              # Polel = louer, elever (poetique)
        'H': 'e\u0302tre e\u0301leve\u0301',
        '_default': 'e\u0301lever',
    },
}


def extract_stem(morph):
    """Extrait le stem depuis le code morph. Ex: 'HVqp3ms' -> 'q'."""
    if not morph:
        return None
    m = str(morph)
    if m.startswith(('H', 'A')):
        m = m[1:]
    for seg in m.split('/'):
        if seg.startswith('V') and len(seg) >= 2:
            return seg[1]
    return None


def read_json_with_bom(path):
    with open(path, 'rb') as f:
        raw = f.read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    if bom:
        raw = raw[3:]
    return json.loads(raw.decode('utf-8')), bom


def write_json_preserve_bom(path, data, bom):
    payload = json.dumps(data, ensure_ascii=False, separators=(', ', ': '))
    body = payload.encode('utf-8')
    if bom:
        body = b'\xef\xbb\xbf' + body
    with open(path, 'wb') as f:
        f.write(body)


def process(apply_changes):
    stats = {s: Counter() for s in VERB_STEM_GLOSS}
    total_updates = 0

    for fp in sorted(INTERLIN_DIR.glob('*.json')):
        data, bom = read_json_with_bom(fp)
        file_changes = 0

        for chap, verses in (data.get('chapters') or {}).items():
            for vnum, words in verses.items():
                for w in words:
                    s = w.get('s')
                    if s not in VERB_STEM_GLOSS:
                        continue
                    stem_map = VERB_STEM_GLOSS[s]
                    stem = extract_stem(w.get('m'))
                    if stem in stem_map:
                        new_gloss = stem_map[stem]
                        stats[s][stem] += 1
                    else:
                        new_gloss = stem_map.get('_default', w.get('g', ''))
                        stats[s]['_default'] += 1
                    if w.get('g') != new_gloss:
                        w['g'] = new_gloss
                        file_changes += 1

        if apply_changes and file_changes:
            write_json_preserve_bom(fp, data, bom)
            print(f'  [{fp.name}] {file_changes} updates')
        elif file_changes:
            print(f'  [{fp.name}] {file_changes} updates (dry-run)')
        total_updates += file_changes

    print()
    print('=== Stats par verbe par stem ===')
    for s in VERB_STEM_GLOSS:
        if not stats[s]:
            continue
        print(f'\n{s}:')
        for stem, count in stats[s].most_common():
            if stem == '_default':
                label = '(default) ' + VERB_STEM_GLOSS[s].get('_default', '?')
            else:
                label = VERB_STEM_GLOSS[s].get(stem, '?')
            print(f'  {stem:<8} -> {label:<25} : {count}')

    print(f'\nTOTAL updates : {total_updates}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'=== Verb stems gloss update {mode} ===')
    print(f'Verbs tracked: {len(VERB_STEM_GLOSS)} | {list(VERB_STEM_GLOSS.keys())}')
    print()
    process(args.apply)


if __name__ == '__main__':
    main()
