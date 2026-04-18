#!/usr/bin/env python3
"""
Enrichit les entre\u0301es BDB dont la source est pauvre (H6030 ʻanah,
H1696 davar) avec une structure `se` manuelle base\u0301e sur BDB classique.

Usage:
    python scripts/enrich_bdb_poor_entries.py --apply
"""
import argparse
import io
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent.parent
LEX_PATH = BASE / 'uploads' / 'dictionnaires' / 'hebrew' / 'hebrew-lexicon-fr-compact.json'

# Enrichissements manuels base\u0301s sur BDB (Brown-Driver-Briggs)
ENRICHMENTS = {
    'H6030': {
        'se': [
            {
                'st': 'Qal',
                'd': 're\u0301pondre',
                'c': [
                    {'n': '1', 'd': 're\u0301pondre a\u0300 une question ou un appel'},
                    {'n': '2', 'd': 'te\u0301moigner, prendre la parole solennellement'},
                    {'n': '3', 'd': 're\u0301pondre par un signe (Dieu qui re\u0301pond par le feu, etc.)'},
                    {'n': '4', 'd': 'faire e\u0301cho, chanter en re\u0301ponse'},
                ],
            },
            {
                'st': 'Niph',
                'd': 'e\u0302tre exauce\u0301, e\u0302tre entendu',
                'c': [
                    {'n': '1', 'd': 'recevoir une re\u0301ponse (priere exauce\u0301e)'},
                ],
            },
            {
                'st': 'Hiph',
                'd': 'faire entendre, donner re\u0301ponse',
            },
            # Racine homonyme : ʻanah II = affliger
            {
                'st': 'Pi',
                'd': 'affliger, humilier (racine homonyme \u05E2\u05B8\u05E0\u05B8\u05D4 II)',
                'c': [
                    {'n': '1', 'd': 'humilier, affaiblir'},
                    {'n': '2', 'd': 'violenter (contexte sexuel)'},
                    {'n': '3', 'd': 'accabler, opprimer'},
                ],
            },
        ],
        'bd': ['re\u0301pondre', 'e\u0302tre exauce\u0301', 'affliger', 'humilier'],
    },
    'H1696': {
        'se': [
            {
                'st': 'Qal',
                'd': 'parler (rare, forme archaïque)',
                'c': [
                    {'n': '1', 'd': 'parler — forme pre\u0301-classique rare, surtout en participe'},
                ],
            },
            {
                'st': 'Niph',
                'd': 'converser, parler ensemble',
                'c': [
                    {'n': '1', 'd': 'se parler les uns aux autres'},
                    {'n': '2', 'd': 'tenir conseil'},
                ],
            },
            {
                'st': 'Pi',
                'd': 'parler (forme dominante de la racine)',
                'c': [
                    {'n': '1', 'd': 'parler, s\u2019exprimer (sens ge\u0301ne\u0301rique)'},
                    {'n': '2', 'd': 'promettre, de\u0301clarer'},
                    {'n': '3', 'd': 'commander, ordonner par la parole'},
                    {'n': '4', 'd': 'raconter, rapporter'},
                    {'n': '5', 'd': 'pre\u0301dire (prophe\u0301tiser au nom de YHWH)'},
                    {'n': '6', 'd': 'converser, discuter'},
                ],
            },
            {
                'st': 'Pu',
                'd': 'e\u0302tre dit, e\u0302tre annonce\u0301',
            },
            {
                'st': 'Hithp',
                'd': 'parler a\u0300 soi-me\u0302me, conserver une conversation',
            },
            {
                'st': 'Hiph',
                'd': 'diriger, dominer (rare, sens causatif "faire parler")',
            },
        ],
        'bd': ['parler', 'ordonner', 'de\u0301clarer', 'converser'],
    },
}


def read_json_with_bom(path):
    with open(path, 'rb') as f:
        raw = f.read()
    bom = raw.startswith(b'\xef\xbb\xbf')
    if bom:
        raw = raw[3:]
    return json.loads(raw.decode('utf-8')), bom


def write_json_preserve_bom(path, data, bom, separators=(',', ':')):
    payload = json.dumps(data, ensure_ascii=False, separators=separators)
    body = payload.encode('utf-8')
    if bom:
        body = b'\xef\xbb\xbf' + body
    with open(path, 'wb') as f:
        f.write(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'=== Enrich poor BDB entries {mode} ===')

    data, bom = read_json_with_bom(LEX_PATH)
    entries = data if isinstance(data, list) else list(data.values())
    updates = 0
    for e in entries:
        s = e.get('s')
        if s in ENRICHMENTS:
            enr = ENRICHMENTS[s]
            old_se_len = len(e.get('se', []))
            old_bd = e.get('bd', [])
            e['se'] = enr['se']
            e['bd'] = enr['bd']
            new_se_len = len(e['se'])
            updates += 1
            print(f'  [{s}] se: {old_se_len} -> {new_se_len} stems | bd: {old_bd} -> {enr["bd"]}')

    if args.apply and updates:
        write_json_preserve_bom(LEX_PATH, data, bom, separators=(',', ':'))
        print(f'\n{updates} entries mises a\u0300 jour, fichier sauve\u0301 ({os.path.getsize(LEX_PATH):,} bytes)')
    else:
        print(f'\n{updates} entries seraient mises a\u0300 jour (dry-run)')


if __name__ == '__main__':
    main()
