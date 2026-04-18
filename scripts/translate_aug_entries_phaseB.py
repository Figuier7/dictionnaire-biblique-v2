#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase B : Traduire les 1 157 nouvelles entrées augmentées du lexique
(bd: EN → FR) via Claude Haiku 4.5.

Pour chaque entrée avec `_stub: True` :
  - bd_en = entry.bd[0]   (ex: "red", "rosy", "cut down")
  - Claude traduit → bd_fr (court, précis, BYM editorial)
  - entry.bd = [bd_fr]     (remplace, les entrées hors stub ont déjà bd en FR)
  - entry.d  = bd_fr        (short def FR en clair)
  - supprime entry._stub

Batching : chunks de 80 entrées par appel API (input ~3K tokens, output ~2K).
Modèle : claude-haiku-4-5 (fast, cheap, bon sur traduction).

Retry : 3 tentatives par chunk avec backoff.

Usage:
  python scripts/translate_aug_entries_phaseB.py --dry-run           # preview prompts + échantillon
  python scripts/translate_aug_entries_phaseB.py --apply              # exécute la traduction
  python scripts/translate_aug_entries_phaseB.py --apply --limit 10   # test sur 10 entrées
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from openai import OpenAI


ROOT = Path(__file__).resolve().parent.parent
LEX_PATH = ROOT / 'uploads' / 'dictionnaires' / 'hebrew' / 'hebrew-lexicon-fr-compact.json'
LOG_PATH = ROOT / 'work' / 'audit' / 'phase-b-translations.json'

MODEL = 'gpt-4o-mini'
CHUNK_SIZE = 80
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0

SYSTEM_PROMPT = """Tu traduis des glossaires courts hébreu biblique pour un lexique Brown-Driver-Briggs en français.

Chaque entrée correspond à un mot hébreu + Strong number, avec une GLOSS COURTE en anglais.
Tu retournes une gloss FRANÇAISE équivalente, préservant :
- La nuance sémantique exacte (ces mots sont des DÉSAMBIGUATIONS, ne pas confondre)
- Le ton lexicographique BDB (concis, précis, pas de paraphrase)

Règles éditoriales BYM (ligne éditoriale du projet) :
- Elohîm (jamais "Dieu") pour nom divin générique
- YHWH (jamais "Éternel" ni "Seigneur" ni "Jéhovah") pour le Tétragramme
- Mashiah (jamais "Messie") pour le terme technique
- Yéhoshoua (jamais "Josué", "Jésus") pour le nom
- Tanakh (jamais "Ancien Testament")
- Ces règles s'appliquent UNIQUEMENT si le sens concerne Elohîm/YHWH/etc. — pour des mots communs
  (rouge, créer, pain...) traduire normalement.

Format de sortie : JSON strict, un objet avec clé "entries" = array d'objets {"s": strong_id, "fr": "traduction française courte"}.
Garde EXACTEMENT les mêmes strong_id que la source. Retourne UNIQUEMENT le JSON, pas de markdown, pas de texte autour.

Exemples :
  IN:  {"s": "H122A", "h": "אָדֹם", "bd_en": "red"}
  OUT: {"s": "H122A", "fr": "rouge"}

  IN:  {"s": "H122B", "h": "אֱדֹם", "bd_en": "rosy"}
  OUT: {"s": "H122B", "fr": "rougeâtre"}

  IN:  {"s": "H176A", "h": "אוֹ", "bd_en": "or"}  # POS C = conjonction
  OUT: {"s": "H176A", "fr": "ou (conj.)"}

  IN:  {"s": "H176B", "h": "אוֹ", "bd_en": "desire"}  # POS N = nom
  OUT: {"s": "H176B", "fr": "désir"}

  IN:  {"s": "H1254A", "h": "בָּרָא", "bd_en": "create"}
  OUT: {"s": "H1254A", "fr": "créer"}

  IN:  {"s": "H1254B", "h": "בָּרָא", "bd_en": "cut down"}
  OUT: {"s": "H1254B", "fr": "couper, tailler"}

  IN:  {"s": "H1254C", "h": "בָּרָא", "bd_en": "make fat"}
  OUT: {"s": "H1254C", "fr": "engraisser"}
"""


def collect_stubs(lex):
    stubs = []
    for e in lex:
        if not e.get('_stub'):
            continue
        bd_list = e.get('bd') or []
        bd_en = bd_list[0] if bd_list else ''
        stubs.append({
            's': e['s'],
            'h': e.get('h', ''),
            'x': e.get('x', ''),
            'p': e.get('p', ''),
            'bd_en': bd_en,
        })
    return stubs


def chunk_stubs(stubs, size):
    for i in range(0, len(stubs), size):
        yield stubs[i:i + size]


def build_user_message(chunk):
    """Build user message for a chunk of stubs."""
    # Pass each entry with s, h, p, bd_en so Claude can disambiguate context (POS matters)
    entries = [{'s': s['s'], 'h': s['h'], 'p': s['p'], 'bd_en': s['bd_en']} for s in chunk]
    payload = {'entries': entries}
    return (
        "Traduis les glosses anglais ci-dessous en français court. Retourne JSON strict.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def translate_chunk(client, chunk):
    """Call OpenAI API for a chunk. Returns dict {strong_id: fr_translation}."""
    user_msg = build_user_message(chunk)
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=4096,
                temperature=0.2,
                response_format={'type': 'json_object'},
                messages=[
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': user_msg},
                ],
            )
            text = resp.choices[0].message.content.strip()
            # Strip markdown fences if present (shouldn't be when using response_format)
            if text.startswith('```'):
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)
            data = json.loads(text)
            translated = {}
            for item in data.get('entries', []):
                s = item.get('s')
                fr = (item.get('fr') or '').strip()
                if s and fr:
                    translated[s] = fr
            return translated
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            last_err = e
            print(f'  [retry {attempt+1}/{MAX_RETRIES}] error: {type(e).__name__}: {e}')
            time.sleep(RETRY_BACKOFF * (attempt + 1))
        except Exception as e:
            last_err = e
            print(f'  [retry {attempt+1}/{MAX_RETRIES}] api error: {type(e).__name__}: {e}')
            time.sleep(RETRY_BACKOFF * (attempt + 1))
    raise RuntimeError(f'Failed after {MAX_RETRIES} retries: {last_err}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help='Preview prompt + sample payload')
    ap.add_argument('--apply', action='store_true', help='Execute translation')
    ap.add_argument('--limit', type=int, default=0, help='Limit to N stubs (for testing)')
    args = ap.parse_args()

    if not args.dry_run and not args.apply:
        ap.error('Specify --dry-run or --apply')

    with open(LEX_PATH, 'r', encoding='utf-8-sig') as f:
        lex = json.load(f)

    stubs = collect_stubs(lex)
    print(f'[phaseB] Found {len(stubs)} stub entries in lexicon')

    if args.limit:
        stubs = stubs[:args.limit]
        print(f'[phaseB] Limited to {len(stubs)} entries for testing')

    if args.dry_run:
        print()
        print('=== SYSTEM PROMPT ===')
        print(SYSTEM_PROMPT[:500], '...')
        print()
        print('=== SAMPLE USER MESSAGE (first 5 stubs) ===')
        print(build_user_message(stubs[:5]))
        print()
        print(f'=== CHUNKS ({CHUNK_SIZE} per chunk) ===')
        chunks = list(chunk_stubs(stubs, CHUNK_SIZE))
        print(f'Total chunks: {len(chunks)}')
        print(f'Last chunk size: {len(chunks[-1])}')
        return

    # Apply mode
    client = OpenAI()  # picks up OPENAI_API_KEY env var
    translations = {}
    chunks = list(chunk_stubs(stubs, CHUNK_SIZE))
    print(f'[phaseB] Processing {len(chunks)} chunks of up to {CHUNK_SIZE} entries...')
    t0 = time.time()
    for i, chunk in enumerate(chunks, 1):
        print(f'[phaseB] Chunk {i}/{len(chunks)} ({len(chunk)} entries)...')
        tr = translate_chunk(client, chunk)
        translations.update(tr)
        print(f'[phaseB]   got {len(tr)} translations (cumulative: {len(translations)})')
    elapsed = time.time() - t0
    print(f'[phaseB] Translation done in {elapsed:.1f}s. Total {len(translations)} translations.')

    # Log translations
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)
    print(f'[phaseB] Log saved to {LOG_PATH}')

    # Merge back into lexicon
    print('[phaseB] Merging translations into lexicon...')
    merged = 0
    missing = []
    for e in lex:
        if not e.get('_stub'):
            continue
        s = e['s']
        fr = translations.get(s)
        if fr:
            e['bd'] = [fr]
            e['d'] = fr
            e.pop('_stub', None)
            merged += 1
        else:
            missing.append(s)

    if missing:
        print(f'[phaseB] WARNING: {len(missing)} stubs not translated: {missing[:10]}...')

    with open(LEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(lex, f, ensure_ascii=False, separators=(', ', ': '))

    print(f'[phaseB] Lexicon updated: {merged} entries translated, {len(missing)} missing.')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
    main()
