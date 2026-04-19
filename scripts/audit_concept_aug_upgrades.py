#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase E : audit des upgrades concept-hebrew-map vers Strong augmentés.

Stratégie :
1. Pour chaque paire (concept_id × base_strong) dans concept-hebrew-map.json
   où le base_strong a des variantes augmentées dans le lexique
2. Prompte LLM avec le contexte concept + variantes → demande décision :
     keep_base        : base suffit, variantes équivalentes
     upgrade_single:X : remplacer base par la variante X (A/B/C/...)
     upgrade_multi:XY : remplacer base par plusieurs variantes
3. Sauve toutes les suggestions dans work/audit/phase-e-suggestions.json
4. Auto-classe en HAUT / MOYEN / NUL selon la confidence + le type de decision

Usage :
  python scripts/audit_concept_aug_upgrades.py --dry-run    # preview prompt
  python scripts/audit_concept_aug_upgrades.py --apply      # génère suggestions
"""

import argparse
import json
import os
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from collections import defaultdict, Counter

from openai import OpenAI


ROOT = Path(__file__).resolve().parent.parent
LEX_PATH = ROOT / 'uploads' / 'dictionnaires' / 'hebrew' / 'hebrew-lexicon-fr-compact.json'
CONCEPTS_PATH = ROOT / 'uploads' / 'dictionnaires' / 'concepts.json'
HMAP_PATH = ROOT / 'uploads' / 'dictionnaires' / 'concept-hebrew-map.json'
OUT_PATH = ROOT / 'work' / 'audit' / 'phase-e-suggestions.json'

MODEL = 'gpt-4o-mini'
CHUNK_SIZE = 15
CONCURRENCY = 10
MAX_RETRIES = 3

SYSTEM_PROMPT = """Tu es un lexicographe biblique qui audite les liens concept-Strong dans un dictionnaire hébreu.

Chaque cas présente :
- Un CONCEPT du dictionnaire (label FR + catégorie + aliases)
- Un STRONG BASE actuellement lié à ce concept
- Les VARIANTES AUGMENTÉES disponibles (H1254A, H1254B, etc.), chacune avec sa POS et sa définition courte

Ta tâche : décider si on doit migrer le lien de la base vers une (ou plusieurs) variante augmentée, ou garder la base.

**Décisions possibles :**
- `keep_base` : toutes les variantes désignent la même réalité (homonymes propres, variantes syntaxiques) — la base reste le meilleur pointer générique
- `upgrade_single` : UNE variante correspond précisément au concept ; remplacer base par cette variante (préciser lettre : A/B/C)
- `upgrade_multi` : plusieurs variantes sont pertinentes (préciser lettres, e.g., "AB")

**Niveau de confiance :**
- `high` : la décision est claire (les variantes ont des sens vraiment distincts ET le concept correspond à UN sens spécifique)
- `medium` : la décision est plausible mais pas évidente (variantes proches, concept ambigu)
- `low` : très incertain — préférer keep_base

**Règles pratiques :**
- Si toutes les variantes sont des homonymes PROPRES du même personnage/lieu mais à des moments/contextes différents, keep_base (sauf si le concept cible explicitement UN personnage)
- Si une variante est N (nom) et une autre V (verbe), et le concept est clairement nom, upgrade_single vers la variante N
- Si concept = classe générique (ex "pronom relatif"), keep_base même si 4 variantes existent

Format de sortie : JSON strict {"suggestions": [{"cid": "...", "base": "H###", "decision": "keep_base|upgrade_single:X|upgrade_multi:XY", "confidence": "high|medium|low", "reason": "phrase courte"}]}
Retourne UNIQUEMENT le JSON, pas de markdown.

Exemple :
IN:  {"cases": [
       {"cid": "idole", "cat": "idolatrie", "label": "Idole", "base": "H6090", "hebrew": "עֹצֶב", "variants": [{"id": "A", "pos": "N", "def": "douleur"}, {"id": "B", "pos": "N", "def": "idole"}]},
       {"cid": "chananyah", "cat": "personnage", "label": "Hananiah", "base": "H2608", "hebrew": "חֲנַנְיָה", "variants": [{"id": "A", "pos": "Np", "def": "Hananiah"}, {"id": "B", "pos": "Np", "def": "Hananiah"}]}
     ]}
OUT: {"suggestions": [
       {"cid": "idole", "base": "H6090", "decision": "upgrade_single:B", "confidence": "high", "reason": "H6090B définit explicitement 'idole', H6090A est 'douleur'"},
       {"cid": "chananyah", "base": "H2608", "decision": "keep_base", "confidence": "high", "reason": "homonymes propres du même nom, la base regroupe tous les porteurs"}
     ]}
"""


def load_aug_variants():
    with open(LEX_PATH, 'r', encoding='utf-8-sig') as f:
        lex = json.load(f)
    variants = defaultdict(list)
    for e in lex:
        s = e.get('s', '')
        m = re.match(r'^(H\d+)([A-Z])$', s)
        if m:
            variants[m.group(1)].append({
                'id': m.group(2),
                'pos': e.get('p', ''),
                'def': e.get('d', '') or (e.get('bd', [''])[0] if e.get('bd') else ''),
            })
    return variants


def load_concepts_meta():
    with open(CONCEPTS_PATH, 'r', encoding='utf-8-sig') as f:
        concepts = json.load(f)
    meta = {}
    for c in concepts:
        cid = c.get('concept_id', '')
        if not cid: continue
        meta[cid] = {
            'label': c.get('label', ''),
            'cat': c.get('category', ''),
            'aliases': c.get('aliases', [])[:3],
        }
    return meta


def build_cases():
    """Retourne la liste des cas à auditer : [{cid, label, cat, base, hebrew, variants}]"""
    with open(HMAP_PATH, 'r', encoding='utf-8-sig') as f:
        hmap = json.load(f)
    aug_variants = load_aug_variants()
    meta = load_concepts_meta()

    cases = []
    for cid, entries in hmap.items():
        for item in entries:
            base = item.get('s', '')
            if base not in aug_variants:
                continue
            m = meta.get(cid, {})
            cases.append({
                'cid': cid,
                'label': m.get('label', ''),
                'cat': m.get('cat', ''),
                'base': base,
                'hebrew': item.get('h', ''),
                'variants': aug_variants[base],
            })
    return cases


def translate_chunk(client, chunk):
    """Envoie un chunk de cas, retourne liste de suggestions."""
    user_msg = 'Audite les cas suivants. Retourne JSON strict.\n\n' + json.dumps({'cases': chunk}, ensure_ascii=False)
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=8000,
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
            return data.get('suggestions', [])
        except Exception as e:
            last_err = e
            print(f'    [retry {attempt+1}] {type(e).__name__}: {e}')
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f'Failed: {last_err}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()
    if not args.dry_run and not args.apply:
        ap.error('--dry-run or --apply required')

    cases = build_cases()
    print(f'[E] Total cases to audit : {len(cases)}')

    if args.limit:
        cases = cases[:args.limit]

    if args.dry_run:
        print('\n=== SAMPLE CASES (first 3) ===')
        print(json.dumps({'cases': cases[:3]}, ensure_ascii=False, indent=2))
        return

    client = OpenAI()
    all_suggestions = []
    chunks = [cases[i:i+CHUNK_SIZE] for i in range(0, len(cases), CHUNK_SIZE)]
    print(f'[E] {len(chunks)} chunks × {CHUNK_SIZE} entries, {CONCURRENCY} workers')

    t0 = time.time()
    lock = threading.Lock()
    completed = [0]

    def worker(chunk):
        res = translate_chunk(client, chunk)
        with lock:
            all_suggestions.extend(res)
            completed[0] += 1
            d = completed[0]
            if d % 3 == 0 or d == len(chunks):
                print(f'  [{d}/{len(chunks)}] cumulative suggestions: {len(all_suggestions)}')
        return res

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futures = [ex.submit(worker, c) for c in chunks]
        for fut in as_completed(futures):
            try: fut.result()
            except Exception as e: print(f'  CHUNK FAIL: {e}')

    elapsed = time.time() - t0
    print(f'[E] Done in {elapsed:.1f}s. {len(all_suggestions)} suggestions.')

    # Stats
    stats = Counter()
    for s in all_suggestions:
        decision = s.get('decision', '?')
        kind = decision.split(':')[0]
        conf = s.get('confidence', '?')
        stats[f'{kind}/{conf}'] += 1
    print('\n=== Répartition par décision × confiance ===')
    for k, n in sorted(stats.items()):
        print(f'  {k:<30} : {n}')

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            'stats': dict(stats),
            'suggestions': all_suggestions,
        }, f, ensure_ascii=False, indent=2)
    print(f'\n[E] Saved : {OUT_PATH}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
    main()
