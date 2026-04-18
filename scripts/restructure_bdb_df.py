#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chantier D : restructure les `df` (BDB complète) avec hiérarchie de sens.

Stratégie révisée : extrait directement du BDB XML un texte structuré avec
séparateurs naturels anglais, puis demande au LLM de traduire en préservant
ces séparateurs. Pas de marqueurs artificiels — le LLM voit directement la
forme cible.

Exemple source généré (H8064) :
  "[שָׁמַי] n.m. only pl. שָׁמַיִם 421 heavens, sky.
  1. a. visible heavens, sky, where stars, etc., are.
  b. phrases.
  2. a. as abode of God.
  b. Elijah taken up הַשּׁ׳ in whirlwind.
  3. הַשּׁ׳ personified in various relations."

Pour les verbes avec stems (Qal, Niph, Pi, etc.), le stem est émis comme
label textuel avant ses sous-sens :
  "אָבַד vb. perish.
  Qal. 1. perish, die, of individuals. 2. perish, of things.
  Niph. perish, vanish.
  Pi. cause to perish, destroy."

Le LLM traduit ligne par ligne en gardant les séparateurs (nombres, lettres, stems).

Règles BYM appliquées :
- "God" générique → "Elohîm"
- "LORD" / "Jehovah" → "YHWH"
- "Jesus" / "Joshua" → "Yéhoshoua"
- "Messiah" → "Mashiah"
- "Old Testament" → "Tanakh"

Usage :
  python scripts/restructure_bdb_df.py --dry-run
  python scripts/restructure_bdb_df.py --apply [--limit N]
"""

import argparse
import json
import os
import re
import sys
import time
import threading
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI


ROOT = Path(__file__).resolve().parent.parent
LEX_PATH = ROOT / 'uploads' / 'dictionnaires' / 'hebrew' / 'hebrew-lexicon-fr-compact.json'
BDB_XML = ROOT / 'work' / 'openscriptures' / 'HebrewLexicon' / 'BrownDriverBriggs.xml'
LOG_PATH = ROOT / 'work' / 'audit' / 'chantier-d-bdb-restructure.json'

NS = '{http://openscriptures.github.com/morphhb/namespace}'

MODEL = 'gpt-4o-mini'
CHUNK_SIZE = 15  # smaller chunks to avoid truncation on long verb entries
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0
CONCURRENCY = 10  # concurrent API workers
CHECKPOINT_EVERY = 50  # save log every N chunks completed

SYSTEM_PROMPT = """Tu traduis en français des entrées BDB (Brown-Driver-Briggs) de l'hébreu biblique.

Chaque entrée source est un TEXTE STRUCTURÉ avec :
- Une ligne de tête (lemma + part-of-speech + définition principale)
- Des sous-sens numérotés "1.", "2.", "3." avec sous-subdivisions "a.", "b.", "c."
- Des stems verbaux nommés "Qal.", "Niph.", "Pi.", "Pu.", "Hiph.", "Hoph.", "Hithp." etc.

Ta traduction DOIT :

1. **Conserver la structure ligne par ligne** (retours à la ligne).
2. **Conserver les séparateurs** : "1.", "a.", "Qal.", "Niph.", etc. exactement.
3. **Traduire chaque segment** en français concis, registre lexicographique BDB.
4. **Préserver éléments hébreux/grecs** (mots, translittérations, références bibliques Gn, Ex, Lv, Nb, Dt, Jos, Jg, Rt, 1S, 2S, 1R, 2R, 1Ch, 2Ch, Esd, Ne, Est, Jb, Ps, Pr, Ec, Ct, Is, Jr, Lm, Éz, Dn, Os, Jl, Am, Ab, Jon, Mi, Na, Ha, So, Ag, Za, Ml).
5. **Préserver abréviations savantes** : Pf., Pt., Impf., Impv., Inf., abs., cstr., ∥, cf., v., MT, LXX, 𝔊.

**Règles éditoriales BYM (ligne éditoriale) :**
- "God" (générique divin) → "Elohîm"
- "LORD" / "Jehovah" / "Yahweh" → "YHWH"
- "Jesus" → "Yéhoshoua"
- "Joshua" → "Yéhoshoua"
- "Messiah" / "the Messiah" → "Mashiah"
- "Old Testament" → "Tanakh"

**Références anglaises → françaises** :
- Nu, Num, Numbers → Nb
- Ex, Exod → Ex
- Gn, Gen → Gn
- Dt, Deut → Dt
- Jos → Jos
- Jg, Jud → Jg
- Ru, Ruth → Rt
- ψ (psalmes) → Ps
- Je, Jer → Jr
- Ez, Ezek → Éz

Format de sortie : JSON strict {"entries": [{"s": "H####", "fr": "traduction"}]}
Retourne UNIQUEMENT le JSON, pas de markdown.
"""


def extract_text_no_status(el):
    """Extrait le texte d'un élément XML, en concaténant text/tail mais en
    EXCLUANT les balises <status> (métadonnée)."""
    parts = []
    def walk(node):
        if node.tag == NS + 'status':
            return
        if node.text:
            parts.append(node.text)
        for ch in node:
            walk(ch)
            if ch.tail:
                parts.append(ch.tail)
    walk(el)
    txt = ''.join(parts)
    txt = re.sub(r'\s+', ' ', txt).strip()
    return txt


def get_text_before_subsenses(el):
    """Retourne le texte directement dans `el`, avant ses enfants <sense>,
    excluant <status>."""
    parts = []
    if el.text:
        parts.append(el.text)
    for ch in el:
        if ch.tag == NS + 'sense':
            break
        if ch.tag == NS + 'status':
            continue
        parts.append(extract_text_no_status(ch))
        if ch.tail:
            parts.append(ch.tail)
    return re.sub(r'\s+', ' ', ''.join(parts)).strip()


def has_subsenses(el):
    return any(ch.tag == NS + 'sense' for ch in el)


def find_stem_label(sense_el):
    """Si le sense a un <stem> direct, retourne son texte + point."""
    stem = sense_el.find(NS + 'stem')
    if stem is not None and stem.text:
        t = stem.text.strip()
        return t.rstrip('.') + '.'
    return None


def format_entry(bdb_entry):
    """Construit le texte structuré anglais avec lignes, numéros, stems.
    Retourne None si pas de senses (rien à restructurer)."""
    top_senses = [s for s in bdb_entry.findall(NS + 'sense')]
    if not top_senses:
        return None

    lines = []
    # Head
    head = get_text_before_subsenses(bdb_entry)
    head = head.rstrip('.,;:— ')
    if head:
        lines.append(head + '.')

    # Helper récursif
    def render_sense(sense_el, depth, numbering_state):
        """depth 0 = top-level, 1 = a/b/c level, 2 = i/ii/iii level.
        numbering_state = list of dicts per depth tracking next auto-num.
        Emit lines."""
        n = sense_el.get('n')
        stem_label = find_stem_label(sense_el) if depth == 0 else None

        # Determine marker
        marker = None
        if stem_label:
            marker = stem_label  # "Qal.", "Niph."
        elif n:
            marker = f'{n}.'
        else:
            # auto-numbering at this depth
            while len(numbering_state) <= depth:
                if depth == 0:
                    numbering_state.append({'type': 'num', 'next': 1})
                elif depth == 1:
                    numbering_state.append({'type': 'alpha', 'next': 0})
                else:
                    numbering_state.append({'type': 'num', 'next': 1})
            st = numbering_state[depth]
            if st['type'] == 'num':
                marker = f'{st["next"]}.'
                st['next'] += 1
            else:
                marker = f'{chr(ord("a") + st["next"])}.'
                st['next'] += 1

        # Keep state consistent if `n` was explicit
        if n and n.isdigit():
            while len(numbering_state) <= depth:
                numbering_state.append({'type': 'num', 'next': 1})
            numbering_state[depth] = {'type': 'num', 'next': int(n) + 1}
        elif n and n.isalpha() and len(n) == 1:
            while len(numbering_state) <= depth:
                numbering_state.append({'type': 'alpha', 'next': 0})
            numbering_state[depth] = {'type': 'alpha', 'next': ord(n) - ord('a') + 1}

        # Reset deeper levels when a new top emerges
        if depth == 0:
            numbering_state[:] = numbering_state[:1]

        sub_senses = [ch for ch in sense_el if ch.tag == NS + 'sense']

        if sub_senses:
            # Text before subs
            pre_text = get_text_before_subsenses(sense_el)
            # If there's a stem, strip the stem word from the pre_text (it's emitted as marker)
            if stem_label:
                stem_word = stem_label.rstrip('.')
                pre_text = re.sub(r'^' + re.escape(stem_word) + r'\.?\s*', '', pre_text, flags=re.I)
            pre_text = pre_text.strip(' .,;:—')
            if pre_text:
                lines.append(f'{marker} {pre_text}.')
            else:
                lines.append(marker)
            for sub in sub_senses:
                render_sense(sub, depth + 1, numbering_state)
        else:
            full_text = extract_text_no_status(sense_el)
            # Strip stem word if present
            if stem_label:
                stem_word = stem_label.rstrip('.')
                full_text = re.sub(r'^' + re.escape(stem_word) + r'\.?\s*', '', full_text, flags=re.I)
            full_text = full_text.strip(' .,;:—')
            if full_text:
                lines.append(f'{marker} {full_text}.')
            else:
                lines.append(marker)

    numbering_state = []
    for top in top_senses:
        render_sense(top, 0, numbering_state)

    return '\n'.join(lines)


def translate_chunk(client, chunk):
    """chunk = list of {s, en}. returns dict {s: fr_text}."""
    user_msg = 'Traduis en français en préservant la structure ligne par ligne. Retourne JSON strict.\n\n' + json.dumps({'entries': chunk}, ensure_ascii=False)
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=16000,
                temperature=0.1,
                response_format={'type': 'json_object'},
                messages=[
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': user_msg},
                ],
            )
            text = resp.choices[0].message.content.strip()
            if text.startswith('```'):
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)
            data = json.loads(text)
            out = {}
            for item in data.get('entries', []):
                s = item.get('s')
                fr = (item.get('fr') or '').strip()
                if s and fr:
                    out[s] = fr
            return out
        except Exception as e:
            last_err = e
            print(f'    [retry {attempt+1}/{MAX_RETRIES}] {type(e).__name__}: {e}')
            time.sleep(RETRY_BACKOFF * (attempt + 1))
    raise RuntimeError(f'Failed: {last_err}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()
    if not args.dry_run and not args.apply:
        ap.error('--dry-run or --apply required')

    print('[D] Parsing BDB XML ...')
    tree = ET.parse(str(BDB_XML))
    bdb_by_id = {}
    for entry in tree.iter(NS + 'entry'):
        eid = entry.get('id')
        if not eid:
            continue
        structured = format_entry(entry)
        if structured:
            bdb_by_id[eid] = structured
    print(f'[D] BDB entries with structured senses : {len(bdb_by_id):,}')

    print('[D] Loading lexicon ...')
    with open(LEX_PATH, 'r', encoding='utf-8-sig') as f:
        lex = json.load(f)

    to_translate = []
    for e in lex:
        bdb_code = e.get('b')
        if not bdb_code:
            continue
        src = bdb_by_id.get(bdb_code)
        if not src:
            continue
        to_translate.append({'s': e['s'], 'en': src})
    print(f'[D] Entries eligible : {len(to_translate):,}')

    if args.limit:
        to_translate = to_translate[:args.limit]

    if args.dry_run:
        print()
        print('=== SAMPLE SOURCES (first 3) ===')
        for item in to_translate[:3]:
            print(f'\n--- {item["s"]} ---')
            print(item['en'][:800])
            if len(item['en']) > 800: print('...')
        return

    # apply (parallel)
    client = OpenAI()

    # Resume from checkpoint if log file has translations
    translations = {}
    if LOG_PATH.exists():
        try:
            with open(LOG_PATH, 'r', encoding='utf-8') as f:
                translations = json.load(f)
            # filter out non-eligible entries
            wanted = set(t['s'] for t in to_translate)
            translations = {k: v for k, v in translations.items() if k in wanted}
            print(f'[D] Resuming with {len(translations)} existing translations')
        except Exception:
            pass

    # skip already-done entries
    to_translate = [t for t in to_translate if t['s'] not in translations]
    print(f'[D] Remaining to translate: {len(to_translate)}')

    chunks = [to_translate[i:i+CHUNK_SIZE] for i in range(0, len(to_translate), CHUNK_SIZE)]
    print(f'[D] {len(chunks)} chunks of up to {CHUNK_SIZE} entries — {CONCURRENCY} concurrent workers...')
    t0 = time.time()
    lock = threading.Lock()
    completed = [0]

    def worker(chunk_idx, chunk):
        tr = translate_chunk(client, chunk)
        with lock:
            translations.update(tr)
            completed[0] += 1
            done = completed[0]
            if done % 5 == 0 or done == len(chunks):
                elapsed = time.time() - t0
                rate = done / max(elapsed, 1) * 60
                eta_min = (len(chunks) - done) / max(rate / 60, 0.01)
                print(f'  [{done}/{len(chunks)}] cumulative={len(translations)} elapsed={elapsed:.0f}s rate={rate:.1f}chunks/min eta={eta_min:.0f}s')
            if done % CHECKPOINT_EVERY == 0:
                # save checkpoint
                LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(LOG_PATH, 'w', encoding='utf-8') as f:
                    json.dump(translations, f, ensure_ascii=False, indent=2)
        return tr

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futures = [ex.submit(worker, i, c) for i, c in enumerate(chunks)]
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as e:
                print(f'  CHUNK FAILED: {type(e).__name__}: {e}')
    elapsed = time.time() - t0
    print(f'[D] Done in {elapsed:.1f}s, {len(translations)} total translations.')

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)
    print(f'[D] Log : {LOG_PATH}')

    # Merge — convert newlines to " | " for compact storage (one-line df)
    merged = 0
    for e in lex:
        fr = translations.get(e.get('s'))
        if fr is None:
            continue
        # Keep as single line with sense markers visible (the line breaks serve
        # as separators but compact storage flattens to spaces)
        flat = re.sub(r'\s*\n\s*', ' ', fr).strip()
        # Final period
        if flat and flat[-1] not in '.!?…':
            flat += '.'
        e['df'] = flat
        merged += 1

    with open(LEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(lex, f, ensure_ascii=False, separators=(', ', ': '))

    missing = [t['s'] for t in to_translate if t['s'] not in translations]
    print(f'[D] df updated : {merged}, missing : {len(missing)}')
    if missing[:10]: print(f'  sample missing: {missing[:10]}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
    main()
