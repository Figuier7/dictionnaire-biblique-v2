#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase A1+A2 : Enrichir hebrew-lexicon-fr-compact.json via LexicalIndex.xml

A1 : combler les TWOT manquants sur les entrées existantes
A2 : créer les entrées augmentées manquantes (H122A, H122B, H1254A, H1254B, ...)

Stratégie :
- Parse LexicalIndex.xml → map { (strong_int, aug_letter) : entry_data }
  où aug_letter = 'a', 'b', '' (pas d'aug)
- Pour chaque entrée courante du lexique (base, e.g. "H1254"):
  → cherche LexicalIndex (strong=1254, aug='')
  → si manque 'tw', remplir
- Pour chaque (strong, aug) dans LexicalIndex avec aug non vide :
  → clé = "H{strong}{AUG_UPPER}"
  → si pas dans lexique courant, créer entrée minimaliste
    (Phase B complètera les champs 'd' FR + 'df' via traduction BDB)

Les nouvelles entrées augmentées auront :
  - s: "H{strong}{AUG_UPPER}"      (e.g. "H1254A")
  - h: Hebrew form                  (from LexicalIndex <w>)
  - x: transliteration              (from LexicalIndex w xlit attr)
  - bp: BDB POS code                (from LexicalIndex <pos>)
  - bd: [short def EN]              (from LexicalIndex <def>)
  - tw: TWOT ref                    (if present)
  - l: 'heb' | 'arc'                (from xml:lang on parent <part>)
  - _stub: true                     (flag : traduction BDB française à faire Phase B)

Sortie : overwrite uploads/dictionnaires/hebrew/hebrew-lexicon-fr-compact.json
Sauvegarde .bak créée séparément.
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LEX_PATH = os.path.join(ROOT, 'uploads', 'dictionnaires', 'hebrew', 'hebrew-lexicon-fr-compact.json')
LI_PATH = os.path.join(ROOT, 'work', 'openscriptures', 'HebrewLexicon', 'LexicalIndex.xml')

NS = '{http://openscriptures.github.com/morphhb/namespace}'


def parse_lexical_index():
    """Parse LexicalIndex.xml, return list of dicts (one per entry).
    Each dict : {id, lang, he, xlit, pos, def, strong, twot, aug, bdb_code}"""
    tree = ET.parse(LI_PATH)
    root = tree.getroot()
    entries = []
    for part in root.iter(NS + 'part'):
        lang = part.get('{http://www.w3.org/XML/1998/namespace}lang', 'heb')
        lang = 'arc' if lang.lower().startswith('arc') or lang.lower().startswith('aramaic') else 'heb'
        for entry in part.iter(NS + 'entry'):
            eid = entry.get('id', '')
            w_el = entry.find(NS + 'w')
            he = w_el.text if w_el is not None and w_el.text else ''
            xlit = w_el.get('xlit', '') if w_el is not None else ''
            pos_el = entry.find(NS + 'pos')
            pos = pos_el.text.strip() if pos_el is not None and pos_el.text else ''
            def_el = entry.find(NS + 'def')
            defn = def_el.text.strip() if def_el is not None and def_el.text else ''
            xref = entry.find(NS + 'xref')
            strong = ''
            twot = ''
            aug = ''
            bdb_code = ''
            if xref is not None:
                strong = xref.get('strong', '') or ''
                twot = xref.get('twot', '') or ''
                aug = xref.get('aug', '') or ''
                bdb_code = xref.get('bdb', '') or ''
            entries.append({
                'id': eid,
                'lang': lang,
                'he': he,
                'xlit': xlit,
                'pos': pos,
                'def': defn,
                'strong': strong,
                'twot': twot,
                'aug': aug,
                'bdb': bdb_code,
            })
    return entries


def build_li_index(entries):
    """Index LexicalIndex entries by (strong_int, aug_letter).
    aug_letter is lowercased. Returns dict[(int, str)] = entry (prefers entries with non-empty pos/def).
    When multiple LI entries share same (strong, aug), prefer the one with most content.
    """
    idx = defaultdict(list)
    for e in entries:
        if not e['strong']:
            continue
        try:
            s_int = int(e['strong'])
        except ValueError:
            continue
        aug = (e['aug'] or '').lower().strip()
        idx[(s_int, aug)].append(e)
    # pick best (most content) per key
    best = {}
    for k, lst in idx.items():
        lst.sort(key=lambda x: (-len(x.get('def', '')), -len(x.get('pos', '')), -len(x.get('xlit', ''))))
        best[k] = lst[0]
    return best


def strong_key(strong_int, aug_letter):
    """Compose 's' field key, e.g. (1254, 'a') → 'H1254A', (1254, '') → 'H1254'."""
    suffix = aug_letter.upper() if aug_letter else ''
    return f'H{strong_int}{suffix}'


def main():
    print('[enrich] Loading LexicalIndex.xml ...')
    li_entries = parse_lexical_index()
    li_idx = build_li_index(li_entries)
    print(f'[enrich]   LexicalIndex total entries : {len(li_entries):,}')
    print(f'[enrich]   LexicalIndex (strong, aug) keys : {len(li_idx):,}')

    print('[enrich] Loading current lexicon ...')
    with open(LEX_PATH, 'r', encoding='utf-8-sig') as f:
        lex = json.load(f)
    print(f'[enrich]   current lexicon entries : {len(lex):,}')

    # Build index of current lexicon by 's' key
    current_by_s = {}
    for e in lex:
        s = (e.get('s') or '').strip().upper()
        if s:
            current_by_s[s] = e

    # Stats
    twot_filled = 0
    augmented_added = 0
    base_augmented_added = 0  # new entries with aug='' we don't already have
    augmented_existing_tw_added = 0

    # Pass 1 : fill TWOT on existing entries
    print('[enrich] Pass 1 : TWOT gap filling on existing entries ...')
    for (s_int, aug), li in li_idx.items():
        if aug:
            continue  # base entries only in pass 1
        key = strong_key(s_int, '')
        cur = current_by_s.get(key)
        if cur is None:
            continue
        if not cur.get('tw') and li.get('twot'):
            cur['tw'] = li['twot']
            twot_filled += 1

    # Pass 2 : add missing augmented entries
    print('[enrich] Pass 2 : add augmented entries ...')
    new_entries = []
    for (s_int, aug), li in li_idx.items():
        if not aug:
            continue
        key = strong_key(s_int, aug)
        if key in current_by_s:
            # already present (unlikely but possible from prior work)
            cur = current_by_s[key]
            if not cur.get('tw') and li.get('twot'):
                cur['tw'] = li['twot']
                augmented_existing_tw_added += 1
            continue

        # Build a minimal new entry
        he = li.get('he', '')
        xlit = li.get('xlit', '')
        pos = li.get('pos', '')
        defn_en = li.get('def', '')
        twot = li.get('twot', '')
        lang = 'arc' if li.get('lang') == 'arc' else 'heb'

        new_entry = {
            's': key,
            'h': he,
            'x': xlit,
            'p': pos,
            'bp': pos,
            'l': lang,
            'bd': [defn_en] if defn_en else [],
            'd': '',        # French short — Phase B
            'df': '',       # French full — Phase B
            '_stub': True,  # marker : awaiting FR translation
        }
        if twot:
            new_entry['tw'] = twot
        if li.get('bdb'):
            new_entry['b'] = li['bdb']

        new_entries.append(new_entry)
        augmented_added += 1

    # Pass 3 : also check if some augmented bases are MISSING in our lexicon entirely
    # (e.g., we have no H1234 at all, but LexicalIndex has H1234a only)
    # We still add the base H1234 if the only LI entry is aug form? no — we only add the aug'ed forms.
    # But some may have both base and aug ; we don't want to add base if we don't have it.
    # For parity, do it :
    print('[enrich] Pass 3 : add missing base entries (LI has base but we don\'t) ...')
    base_added = 0
    for (s_int, aug), li in li_idx.items():
        if aug:
            continue
        key = strong_key(s_int, '')
        if key in current_by_s:
            continue
        he = li.get('he', '')
        xlit = li.get('xlit', '')
        pos = li.get('pos', '')
        defn_en = li.get('def', '')
        twot = li.get('twot', '')
        lang = 'arc' if li.get('lang') == 'arc' else 'heb'
        new_entry = {
            's': key,
            'h': he,
            'x': xlit,
            'p': pos,
            'bp': pos,
            'l': lang,
            'bd': [defn_en] if defn_en else [],
            'd': '',
            'df': '',
            '_stub': True,
        }
        if twot:
            new_entry['tw'] = twot
        if li.get('bdb'):
            new_entry['b'] = li['bdb']
        new_entries.append(new_entry)
        base_added += 1

    # Append new entries to lex
    lex.extend(new_entries)

    # Sort by Strong number (then by augment letter) for readability
    def sort_key(e):
        s = e.get('s', '')
        m = re.match(r'H(\d+)([A-Z]?)', s)
        if m:
            return (int(m.group(1)), m.group(2))
        return (999999, '')
    lex.sort(key=sort_key)

    # Save
    with open(LEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(lex, f, ensure_ascii=False, separators=(', ', ': '))

    # Report
    print()
    print('=' * 50)
    print(f'Phase A1+A2 Results')
    print('=' * 50)
    print(f'  TWOT filled on existing entries : {twot_filled:,}')
    print(f'  Augmented entries added         : {augmented_added:,}')
    print(f'  Missing base entries added      : {base_added:,}')
    print(f'  TWOT filled on existing aug     : {augmented_existing_tw_added}')
    print(f'  Total entries added             : {len(new_entries):,}')
    print(f'  New lexicon size                : {len(lex):,}')
    print(f'  (was {len(current_by_s):,} before)')
    print()
    print(f'New entries are marked _stub=True — awaiting Phase B translation.')
    print(f'Saved to : {LEX_PATH}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
    main()
