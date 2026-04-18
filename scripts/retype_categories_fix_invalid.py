#!/usr/bin/env python3
"""
PHASE D-bis - Relance un mini batch sur les concepts dont la 1ere reponse
etait invalide (LLM a repondu "concept" au lieu d'une categorie).

Strategie : requetes individuelles avec prompt tres strict.
"""
import json
import os
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'work/retype'
REPORT = OUT_DIR / 'retype_report.json'
BATCH_INPUT = OUT_DIR / 'batch_input_fix.jsonl'
BATCH_META = OUT_DIR / 'batch_meta_fix.json'
META_PATH = BASE / 'uploads/dictionnaires/concept-meta.json'
CONCEPTS_PATH = BASE / 'uploads/dictionnaires/concepts.json'
TAXONOMY_FILE = OUT_DIR / 'taxonomy.json'

SYSTEM_PROMPT = """Tu classifies UN concept biblique dans une et une seule categorie.

CATEGORIES AUTORISEES (utiliser l'un de ces 20 mots EXACTEMENT) :
personnage, etre_spirituel, lieu, lieu_sacre, peuple, livre_biblique,
doctrine, rite, institution, fonction, objet_sacre, objets_et_vetements,
plante, animal, alimentation_et_agriculture, corps_et_sante,
mesures_et_temps, matiere, evenement, nature

Reponds UNIQUEMENT par un seul mot parmi les 20 ci-dessus.
PAS "concept", PAS "concepts", PAS de phrase, PAS de JSON, PAS de markdown.
Juste le mot. Exemple: doctrine"""


def prepare():
    sys.stdout.reconfigure(encoding='utf-8')
    with open(REPORT, encoding='utf-8') as f:
        report = json.load(f)
    invalid = report.get('invalid_samples', [])
    # Dans apply.py on limite a 50 invalid_samples, re-parser batch_output pour recuperer TOUS
    # (pas grave si on refait tout les invalids, ~315 requetes)
    with open(OUT_DIR / 'batch_output.jsonl', encoding='utf-8') as f:
        all_invalid_cids = []
        with open(TAXONOMY_FILE, encoding='utf-8') as g:
            tax = set(json.load(g)['taxonomy'])
        for line in f:
            rec = json.loads(line)
            resp = (rec.get('response') or {}).get('body') or {}
            choices = resp.get('choices') or []
            if not choices: continue
            c = choices[0].get('message',{}).get('content','').strip()
            c = re.sub(r'^```(?:json)?\s*','',c)
            c = re.sub(r'\s*```$','',c)
            try: arr = json.loads(c)
            except: continue
            if not isinstance(arr, list): continue
            for it in arr:
                if isinstance(it, dict) and it.get('cid'):
                    cat = (it.get('cat') or '').strip().lower()
                    cat = cat.replace(' ','_').replace('-','_').rstrip('.')
                    if cat not in tax:
                        all_invalid_cids.append(it['cid'])

    print(f'Invalid CIDs to re-process : {len(all_invalid_cids)}')

    with open(META_PATH, encoding='utf-8') as f:
        meta = json.load(f)

    def truncate(s, n=250):
        s = (s or '').strip().replace('\n',' ').replace('\r',' ').replace('\t',' ')
        while '  ' in s: s = s.replace('  ',' ')
        return s if len(s)<=n else s[:n].rsplit(' ',1)[0]+'...'

    with open(BATCH_INPUT, 'w', encoding='utf-8') as out:
        for cid in all_invalid_cids:
            m = meta.get(cid, {})
            label = m.get('p') or m.get('l') or cid
            excerpt = truncate(m.get('e') or m.get('d') or '', 300)
            user_msg = f'Concept : {label}\n'
            if excerpt: user_msg += f'Description : {excerpt}\n'
            user_msg += 'Categorie ?'
            req = {
                'custom_id': cid,
                'method': 'POST',
                'url': '/v1/chat/completions',
                'body': {
                    'model': 'gpt-4o-mini',
                    'messages': [
                        {'role':'system','content':SYSTEM_PROMPT},
                        {'role':'user','content':user_msg},
                    ],
                    'max_tokens': 10,
                    'temperature': 0,
                },
            }
            out.write(json.dumps(req, ensure_ascii=False)+'\n')
    print(f'Wrote {BATCH_INPUT} ({BATCH_INPUT.stat().st_size/1024:.1f} KB)')


def submit():
    from openai import OpenAI
    client = OpenAI()
    with open(BATCH_INPUT,'rb') as f:
        file_obj = client.files.create(file=f, purpose='batch')
    print(f'file_id: {file_obj.id}')
    batch = client.batches.create(
        input_file_id=file_obj.id,
        endpoint='/v1/chat/completions',
        completion_window='24h',
    )
    print(f'batch_id: {batch.id}, status: {batch.status}')
    with open(BATCH_META,'w',encoding='utf-8') as f:
        json.dump({'file_id':file_obj.id,'batch_id':batch.id,'status':batch.status}, f, indent=2)


def status():
    from openai import OpenAI
    with open(BATCH_META) as f: meta=json.load(f)
    client = OpenAI()
    b = client.batches.retrieve(meta['batch_id'])
    print(f'Status: {b.status} | Progress: {b.request_counts.completed}/{b.request_counts.total}')
    if b.output_file_id:
        out = OUT_DIR/'batch_output_fix.jsonl'
        if not out.exists():
            content = client.files.content(b.output_file_id)
            out.write_bytes(content.read())
            print(f'Downloaded to {out}')


def apply(commit=False):
    sys.stdout.reconfigure(encoding='utf-8')
    with open(TAXONOMY_FILE, encoding='utf-8') as f:
        tax = set(json.load(f)['taxonomy'])
    out_path = OUT_DIR/'batch_output_fix.jsonl'
    if not out_path.exists():
        print('ERROR: batch_output_fix.jsonl absent. Run --status first.')
        return

    new_cats = {}
    invalid = []
    with open(out_path, encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            cid = rec.get('custom_id','')
            resp = (rec.get('response') or {}).get('body') or {}
            choices = resp.get('choices') or []
            if not choices: continue
            cat = choices[0].get('message',{}).get('content','').strip().lower()
            cat = cat.replace(' ','_').replace('-','_').rstrip('.').split()[0] if cat else ''
            if cat in tax:
                new_cats[cid] = cat
            else:
                invalid.append({'cid':cid, 'raw':cat})
    print(f'Valid: {len(new_cats)}, Invalid: {len(invalid)}')
    if invalid[:10]:
        print('Invalid samples:')
        for inv in invalid[:10]:
            print(f'  {inv["cid"]:25s} -> {inv["raw"]!r}')

    if not commit:
        print('DRY RUN — add --commit to apply')
        return

    with open(META_PATH, encoding='utf-8') as f: meta = json.load(f)
    with open(CONCEPTS_PATH, encoding='utf-8') as f: concepts = json.load(f)

    n_meta = 0
    for cid, cat in new_cats.items():
        if cid in meta and meta[cid].get('c') != cat:
            meta[cid]['c'] = cat
            n_meta += 1
    with open(META_PATH, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, separators=(',',':'))

    n_concepts = 0
    for c in concepts:
        cid = c.get('concept_id')
        if cid in new_cats and c.get('category') != new_cats[cid]:
            c['category'] = new_cats[cid]
            n_concepts += 1
    with open(CONCEPTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(concepts, f, ensure_ascii=False, separators=(',',':'))
    print(f'Updated: meta={n_meta}, concepts={n_concepts}')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['prepare','submit','status','apply'])
    p.add_argument('--commit', action='store_true')
    args = p.parse_args()
    if args.action=='prepare': prepare()
    elif args.action=='submit': submit()
    elif args.action=='status': status()
    elif args.action=='apply': apply(commit=args.commit)
