#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase A3 : Re-parser les 39 livres morphhb WLC XML pour enrichir les JSON
interlinéaires locaux avec :
  - `sa` : augment suffix (e.g., 'A', 'B') quand le lemme morphhb l'indique
  - `pre` : prefix letters du lemme (e.g., 'b', 'd', 'c', 'cb') pour les mots
           à préfixes prépositionnels / article / conjonction

Stratégie :
- Pour chaque livre : charger morphhb/wlc/{book}.xml + at/{NN-Book}.json
- Matcher par (chapitre, verset, position du mot) — positionnel
- Extraire le champ `lemma` XML et le parser :
  - parts = lemma.split('/')
  - parts qui matchent /^[a-z]+$/ → prefix
  - part qui matche /^(\d+)(?:\s+([a-z]))?$/ → base Strong + aug letter
- Ajouter `sa` (uppercase letter) et `pre` (joined prefixes) au word object
  (backward-compat : champs optionnels)

Sortie : overwrite uploads/dictionnaires/interlinear/at/*.json
Backup _bak-pre-phaseA/ déjà créé avant le lancement.
"""

import json
import os
import re
import sys
import glob
import xml.etree.ElementTree as ET
from collections import Counter


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MORPHHB_DIR = os.path.join(ROOT, 'work', 'openscriptures', 'morphhb', 'wlc')
INTERLIN_DIR = os.path.join(ROOT, 'uploads', 'dictionnaires', 'interlinear', 'at')

NS = '{http://www.bibletechnologies.net/2003/OSIS/namespace}'

# Mapping morphhb book code → our JSON file prefix + local book code
# (our JSON is named like "01-Gen.json" with book="Gen")
MORPHHB_TO_FILE = {
    'Gen':   '01-Gen',   'Exod':  '02-Exod',  'Lev':   '03-Lev',
    'Num':   '04-Num',   'Deut':  '05-Deut',  'Josh':  '06-Josh',
    'Judg':  '07-Judg',  'Ruth':  '08-Ruth',  '1Sam':  '09-1Sam',
    '2Sam':  '10-2Sam',  '1Kgs':  '11-1Kgs',  '2Kgs':  '12-2Kgs',
    '1Chr':  '13-1Chr',  '2Chr':  '14-2Chr',  'Ezra':  '15-Ezra',
    'Neh':   '16-Neh',   'Esth':  '17-Esth',  'Job':   '18-Job',
    'Ps':    '19-Ps',    'Prov':  '20-Prov',  'Eccl':  '21-Eccl',
    'Song':  '22-Song',  'Isa':   '23-Isa',   'Jer':   '24-Jer',
    'Lam':   '25-Lam',   'Ezek':  '26-Ezek',  'Dan':   '27-Dan',
    'Hos':   '28-Hos',   'Joel':  '29-Joel',  'Amos':  '30-Amos',
    'Obad':  '31-Obad',  'Jonah': '32-Jonah', 'Mic':   '33-Mic',
    'Nah':   '34-Nah',   'Hab':   '35-Hab',   'Zeph':  '36-Zeph',
    'Hag':   '37-Hag',   'Zech':  '38-Zech',  'Mal':   '39-Mal',
}


LEMMA_TOKEN_RE = re.compile(r'^(\d+)(?:\s+([a-z]))?$')
PREFIX_RE = re.compile(r'^[a-z]+$')


def parse_lemma(lemma):
    """Parse a morphhb lemma string → (pre, strong, aug).
    Examples :
      'b/7225'   → ('b', 7225, '')
      '1254 a'   → ('', 1254, 'A')
      'c/1121 a' → ('c', 1121, 'A')
      '430'      → ('', 430, '')
      'd/8064'   → ('d', 8064, '')
      'c/b/1234' → ('cb', 1234, '')  (prefixes concatenated)
    Returns ('', None, '') on parse failure.
    """
    if not lemma:
        return ('', None, '')
    parts = lemma.split('/')
    pre_list = []
    strong = None
    aug = ''
    for p in parts:
        pp = p.strip()
        if not pp:
            continue
        if PREFIX_RE.match(pp):
            pre_list.append(pp)
            continue
        m = LEMMA_TOKEN_RE.match(pp)
        if m:
            strong = int(m.group(1))
            if m.group(2):
                aug = m.group(2).upper()
    return (''.join(pre_list), strong, aug)


def parse_morphhb_book(xml_path):
    """Parse a morphhb XML book.
    Returns dict[(chapter_int, verse_int)] = list of word dicts
    Each word dict : {t: text, lemma_raw, pre, strong_parsed, sa}"""
    tree = ET.parse(xml_path)
    verses = {}
    for verse_el in tree.iter(NS + 'verse'):
        osis_id = verse_el.get('osisID', '')
        # Format: Book.Chapter.Verse
        parts = osis_id.split('.')
        if len(parts) != 3:
            continue
        try:
            ch = int(parts[1])
            vs = int(parts[2])
        except ValueError:
            continue
        words = []
        for w_el in verse_el.iter(NS + 'w'):
            text = (w_el.text or '').strip()
            lemma = w_el.get('lemma', '')
            morph = w_el.get('morph', '')
            wid = w_el.get('id', '')
            pre, strong, aug = parse_lemma(lemma)
            words.append({
                't': text,
                'lemma_raw': lemma,
                'morph_raw': morph,
                'id_raw': wid,
                'pre': pre,
                'strong_parsed': strong,
                'sa': aug,
            })
        verses[(ch, vs)] = words
    return verses


def process_book(book_code):
    """Process a single book. Returns stats dict."""
    stats = Counter()
    xml_path = os.path.join(MORPHHB_DIR, f'{book_code}.xml')
    json_name = MORPHHB_TO_FILE.get(book_code)
    if not json_name:
        return None
    json_path = os.path.join(INTERLIN_DIR, f'{json_name}.json')

    if not os.path.exists(xml_path) or not os.path.exists(json_path):
        print(f'[{book_code}] missing file(s) — skip')
        return None

    # Parse both
    xml_verses = parse_morphhb_book(xml_path)
    with open(json_path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)

    # Walk our JSON structure
    chapters = data.get('chapters', {})
    for ch_str, verses_dict in chapters.items():
        try:
            ch = int(ch_str)
        except ValueError:
            continue
        for vs_str, words in verses_dict.items():
            try:
                vs = int(vs_str)
            except ValueError:
                continue

            xml_words = xml_verses.get((ch, vs), [])
            if not xml_words:
                stats['verse_not_in_xml'] += 1
                continue

            if len(words) != len(xml_words):
                stats['word_count_mismatch'] += 1
                # still process what we can by position
            match_len = min(len(words), len(xml_words))
            for i in range(match_len):
                w = words[i]
                xw = xml_words[i]

                # Sanity check : Hebrew text should match (optional)
                if w.get('t') != xw['t']:
                    stats['text_mismatch'] += 1
                    # still update if we're confident (same position)
                    # but we skip when text drastically differs to avoid corruption
                    if len(w.get('t', '')) == 0 or len(xw['t']) == 0:
                        continue

                pre = xw['pre']
                sa = xw['sa']
                if pre:
                    w['pre'] = pre
                    stats['pre_added'] += 1
                if sa:
                    w['sa'] = sa
                    stats['sa_added'] += 1
            stats['verses_processed'] += 1
            stats['words_processed'] += match_len

    # Save back with same formatting (compact, same as other JSON in project)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(', ', ': '))

    return stats


def main():
    global_stats = Counter()
    books_done = 0
    print(f'[A3] Processing {len(MORPHHB_TO_FILE)} books ...')
    for book_code in MORPHHB_TO_FILE:
        st = process_book(book_code)
        if st is None:
            continue
        books_done += 1
        for k, v in st.items():
            global_stats[k] += v
        print(f'  [{book_code:<6}] verses={st["verses_processed"]:>6}  words={st["words_processed"]:>7}  pre+={st["pre_added"]:>6}  sa+={st["sa_added"]:>6}  text_mis={st["text_mismatch"]:>3}')

    print()
    print('=' * 50)
    print(f'Phase A3 Global Stats ({books_done} books)')
    print('=' * 50)
    for k in ['verses_processed', 'words_processed', 'pre_added', 'sa_added',
             'word_count_mismatch', 'verse_not_in_xml', 'text_mismatch']:
        print(f'  {k:<25} : {global_stats[k]:,}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
    main()
