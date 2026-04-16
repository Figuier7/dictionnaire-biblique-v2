#!/usr/bin/env python3
"""
Re-typage AFFINÉ des 315 concepts initialement problematiques.

Strategie : GPT-4o (plus précis que 4o-mini pour le reasoning sur concepts abstraits),
chunks de ~15 concepts par request pour rester sous quota 90k tokens, prompt
enrichi avec exemples par catégorie dubious.

Usage :
  python scripts/retype_categories_refine_315.py prepare
  python scripts/retype_categories_refine_315.py submit
  python scripts/retype_categories_refine_315.py status
  python scripts/retype_categories_refine_315.py apply [--commit]
"""
import argparse, json, os, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / 'work/retype'
FIX_INPUT_ORIG = OUT_DIR / 'batch_input_fix.jsonl'
REFINE_INPUT = OUT_DIR / 'batch_input_refine.jsonl'
REFINE_OUTPUT = OUT_DIR / 'batch_output_refine.jsonl'
REFINE_META = OUT_DIR / 'batch_meta_refine.json'
TAXONOMY_FILE = OUT_DIR / 'taxonomy.json'
META_PATH = BASE / 'uploads/dictionnaires/concept-meta.json'
CONCEPTS_PATH = BASE / 'uploads/dictionnaires/concepts.json'

SYSTEM_PROMPT = """Tu es un lexicographe biblique francophone precis. Tu classifies des concepts bibliques parmi EXACTEMENT ces 20 categories :

NOMS PROPRES :
- personnage : individu humain nomme dans la Bible (Adam, Paul, Ruth, Dathema)
- etre_spirituel : divinite/ange/demon, nomme OU generique (YHWH, Gabriel, Baal, ange, seraphin, esprit-saint)
- lieu : toponyme geographique profane (Jerusalem, Eden, Canaan, Mont Sinai, Dathema si ville)
- lieu_sacre : lieu religieux (Temple, Tabernacle, Sanctuaire, Chambres de l'idolatrie dans le Temple)
- peuple : tribu/nation/famille nommee (Israelites, Moabites, Tribu de Juda)
- livre_biblique : nom CANONIQUE d'un livre biblique (Genese, Matthieu, Psaumes). PAS "versions arabes" ni "Talmud" qui sont des doctrines/ressources.

CONCEPTS / NOMS COMMUNS :
- doctrine : concept theologique abstrait (foi, salut, peche, grace, incarnation, abondance, pudeur, issue, chance/providence, compatissant, innocent, ruse, rien, versions bibliques non-canoniques, Talmud, apocryphes)
- rite : ceremonie/pratique religieuse (sacrifice, bapteme, circoncision, priere)
- institution : structure sociale PERSISTANTE (royaume, mariage, synagogue-lieu, concubinage comme institution)
- fonction : TITRE/ROLE/METIER (roi, pretre, prophete, scribe, juge, berger, apotre, maitre, chef, concubine comme role)
- objet_sacre : objet liturgique (arche, autel, ephod, menorah)
- objets_et_vetements : objets profanes du quotidien (robe, sandale, balance, lampe, jarre, outil). PAS les concepts abstraits !
- plante : vegetaux (figuier, cedre, ble, absinthe)
- animal : faune (agneau, lion, aigle)
- alimentation_et_agriculture : aliments/produits (pain, vin, miel, moisson, technique agricole)
- corps_et_sante : partie du corps, maladie, sommeil, gras (gras = corps/morphologie ou aliment selon contexte)
- mesures_et_temps : unite ou periode (coudee, shekel, annee, age-apostolique=periode)
- matiere : materiaux (bronze, lin, or, sel, pierre-materiau)
- evenement : EVENEMENT HISTORIQUE PONCTUEL (Exode, Deluge, Babel, Crucifixion, Pentecote, apparition-historique, age-apostolique SI considere comme evenement)
- nature : phenomene naturel, element, geographie NON nommee (desert, pluie, vent, mer-generique, glisser=action physique nature)

REGLES PRECISES :
1. "Versions" (arabes, grecques, etc.) → doctrine (concept de traduction/transmission)
2. "Age apostolique" → evenement (periode historique)
3. "Concubine" → fonction (role social) ou personnage SI nom propre individuel
4. Noms singuliers comme "Dathema", "Chapt", "Apace" : chercher s'ils sont des NOMS (Dathema=ville), des adverbes (apace=rapidement → doctrine), etc.
5. Si hesite entre personnage et lieu : verifier si le label est un individu (personnage) ou un endroit (lieu)
6. "Apparition" (concept general de manifestation) → doctrine ou evenement selon contexte
7. "Sommeil profond" → corps_et_sante

FORMAT REPONSE :
JSON array strict, meme ordre que les concepts donnes.
Chaque objet : {"cid":"<id>","cat":"<une_des_20>"}
RIEN d'autre. Pas de markdown. Pas de texte. Juste le JSON array.
Exemple : [{"cid":"paulos","cat":"personnage"},{"cid":"slip","cat":"nature"}]"""


def truncate(s, n=350):
    s = (s or '').strip().replace('\n',' ').replace('\r',' ').replace('\t',' ')
    while '  ' in s: s = s.replace('  ',' ')
    return s if len(s)<=n else s[:n].rsplit(' ',1)[0]+'...'


def prepare():
    sys.stdout.reconfigure(encoding='utf-8')
    with open(META_PATH, encoding='utf-8') as f:
        meta = json.load(f)

    # Get 315 cids
    cids = []
    with open(FIX_INPUT_ORIG, encoding='utf-8') as f:
        for line in f:
            cids.append(json.loads(line)['custom_id'])
    print(f'Total cids a affiner : {len(cids)}')

    # Chunk by 15
    BATCH_SIZE = 15
    chunks = [cids[i:i+BATCH_SIZE] for i in range(0, len(cids), BATCH_SIZE)]
    print(f'{len(chunks)} requests of up to {BATCH_SIZE} concepts each')

    with open(REFINE_INPUT, 'w', encoding='utf-8') as out:
        for idx, chunk in enumerate(chunks):
            lines = []
            for cid in chunk:
                m = meta.get(cid, {})
                label = m.get('p') or m.get('l') or cid
                secondary = m.get('l') if m.get('p') and m.get('l') != m.get('p') else ''
                excerpt = truncate(m.get('e') or m.get('d') or '', 280)
                cur = m.get('c', '?')
                l = f'- cid="{cid}" | label="{label}"'
                if secondary: l += f' (alt: "{secondary}")'
                l += f' | cat_actuelle_a_verifier="{cur}"'
                if excerpt: l += f' | description="{excerpt}"'
                lines.append(l)

            user_msg = (
                f'Classifie les {len(chunk)} concepts suivants.\n'
                f'Si la categorie actuelle est BONNE, confirme-la. Sinon corrige.\n'
                f'Reponds JSON array de {len(chunk)} objets, meme ordre.\n\n'
                + '\n'.join(lines)
            )
            req = {
                'custom_id': f'refine_{idx:03d}',
                'method': 'POST',
                'url': '/v1/chat/completions',
                'body': {
                    'model': 'gpt-4o',
                    'messages': [
                        {'role':'system','content':SYSTEM_PROMPT},
                        {'role':'user','content':user_msg}
                    ],
                    'max_tokens': max(400, len(chunk)*30),
                    'temperature': 0,
                }
            }
            out.write(json.dumps(req, ensure_ascii=False) + '\n')

    size_kb = REFINE_INPUT.stat().st_size / 1024
    print(f'Wrote {REFINE_INPUT} ({size_kb:.1f} KB)')


def submit():
    from openai import OpenAI
    c = OpenAI()
    with open(REFINE_INPUT, 'rb') as f:
        fo = c.files.create(file=f, purpose='batch')
    print(f'file_id: {fo.id}')
    b = c.batches.create(
        input_file_id=fo.id,
        endpoint='/v1/chat/completions',
        completion_window='24h',
    )
    print(f'batch_id: {b.id} | status: {b.status}')
    with open(REFINE_META, 'w', encoding='utf-8') as f:
        json.dump({'file_id':fo.id,'batch_id':b.id,'status':b.status}, f, indent=2)


def status():
    from openai import OpenAI
    c = OpenAI()
    with open(REFINE_META) as f: meta = json.load(f)
    b = c.batches.retrieve(meta['batch_id'])
    print(f'Status: {b.status} | Progress: {b.request_counts.completed}/{b.request_counts.total}')
    if b.output_file_id and not REFINE_OUTPUT.exists():
        content = c.files.content(b.output_file_id)
        REFINE_OUTPUT.write_bytes(content.read())
        print(f'Downloaded to {REFINE_OUTPUT}')
    if b.errors:
        print(f'Errors: {b.errors}')


def apply(commit=False):
    sys.stdout.reconfigure(encoding='utf-8')
    with open(TAXONOMY_FILE, encoding='utf-8') as f: tax = set(json.load(f)['taxonomy'])
    with open(META_PATH, encoding='utf-8') as f: meta = json.load(f)
    with open(CONCEPTS_PATH, encoding='utf-8') as f: concepts = json.load(f)

    new_cats = {}; invalid = []
    with open(REFINE_OUTPUT, encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            resp = (rec.get('response') or {}).get('body') or {}
            choices = resp.get('choices') or []
            if not choices: continue
            content = choices[0].get('message',{}).get('content','').strip()
            content = re.sub(r'^```(?:json)?\s*\n?','',content)
            content = re.sub(r'\n?```\s*$','',content)
            try: arr = json.loads(content)
            except: continue
            if not isinstance(arr, list): continue
            for it in arr:
                if isinstance(it, dict) and it.get('cid'):
                    cid = it['cid']
                    cat = (it.get('cat','') or '').strip().lower().replace(' ','_').replace('-','_').rstrip('.')
                    if cat in tax:
                        new_cats[cid] = cat
                    else:
                        invalid.append({'cid':cid,'raw':cat})

    print(f'Valid: {len(new_cats)}, Invalid: {len(invalid)}')

    # Compute diff vs current
    changed = []
    same = 0
    for cid, new_cat in new_cats.items():
        cur = meta.get(cid, {}).get('c','?')
        if cur == new_cat:
            same += 1
        else:
            changed.append({'cid':cid,'from':cur,'to':new_cat})
    print(f'Unchanged (4o-mini etait deja bon): {same}')
    print(f'Changed (4o corrige 4o-mini)     : {len(changed)}')

    # Show top directions
    from collections import Counter
    dirs = Counter((c['from'], c['to']) for c in changed)
    print(f'\n=== Top changes ===')
    for (f, t), n in dirs.most_common(15):
        print(f'  {f:30s} -> {t:30s} : {n}')

    # Sample 20 changes
    print(f'\n=== Sample 20 changements ===')
    for c in changed[:20]:
        m = meta.get(c['cid'], {})
        label = m.get('p') or m.get('l') or c['cid']
        print(f'  {c["cid"][:22]:22s} "{label[:20]:20s}" : {c["from"]:20s} -> {c["to"]}')

    if not commit:
        print('\n--- DRY RUN. --commit to apply. ---')
        return

    # Backup
    bak_meta = META_PATH.with_suffix(META_PATH.suffix + '.bak-pre-refine315')
    if not bak_meta.exists(): bak_meta.write_bytes(META_PATH.read_bytes()); print(f'Backup: {bak_meta}')
    bak_con = CONCEPTS_PATH.with_suffix(CONCEPTS_PATH.suffix + '.bak-pre-refine315')
    if not bak_con.exists(): bak_con.write_bytes(CONCEPTS_PATH.read_bytes()); print(f'Backup: {bak_con}')

    # Apply changes
    nm, nc = 0, 0
    for c in changed:
        cid = c['cid']; new_cat = c['to']
        if cid in meta and meta[cid].get('c') != new_cat:
            meta[cid]['c'] = new_cat; nm += 1
        for cpt in concepts:
            if cpt.get('concept_id') == cid and cpt.get('category') != new_cat:
                cpt['category'] = new_cat; nc += 1; break

    with open(META_PATH, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, separators=(',',':'))
    with open(CONCEPTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(concepts, f, ensure_ascii=False, separators=(',',':'))
    print(f'\nUpdated: meta={nm}, concepts={nc}')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['prepare','submit','status','apply'])
    p.add_argument('--commit', action='store_true')
    args = p.parse_args()
    if args.action=='prepare': prepare()
    elif args.action=='submit': submit()
    elif args.action=='status': status()
    elif args.action=='apply': apply(commit=args.commit)
