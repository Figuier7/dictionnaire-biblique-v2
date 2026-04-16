#!/usr/bin/env python3
"""
PHASE B - Prepare le batch OpenAI pour re-typage des categories concept.

Strategie : 50 concepts par requete, system prompt compact -> divise le cout
input par ~50 et passe sous le quota org enqueue (2M tokens gpt-4o-mini).

Output attendu par le LLM : JSON array {"cid": "...", "cat": "..."}, dans le
meme ordre que les concepts dans la requete.
"""
import json
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
META_PATH = BASE / 'uploads/dictionnaires/concept-meta.json'
OUT_DIR = BASE / 'work/retype'
OUT_DIR.mkdir(parents=True, exist_ok=True)
BATCH_INPUT = OUT_DIR / 'batch_input.jsonl'

TAXONOMY = [
    'personnage','etre_spirituel','lieu','lieu_sacre','peuple','livre_biblique',
    'doctrine','rite','institution','fonction',
    'objet_sacre','objets_et_vetements',
    'plante','animal','alimentation_et_agriculture','corps_et_sante',
    'mesures_et_temps','matiere','evenement','nature',
]

SYSTEM_PROMPT = """Classifie chaque concept biblique dans UNE categorie parmi les 20 suivantes :

NOMS PROPRES :
- personnage : individu humain nomme (David, Paul)
- etre_spirituel : divinite/ange/demon, nomme OU generique (YHWH, Gabriel, Baal, ange, seraphin)
- lieu : toponyme profane (Jerusalem, Eden)
- lieu_sacre : lieu religieux (Temple, Tabernacle, Sanctuaire)
- peuple : tribu/nation/famille (Israelites, Moabites)
- livre_biblique : nom d'un livre canonique (Genese, Matthieu)

CONCEPTS :
- doctrine : theologique abstrait (foi, salut, peche, grace, incarnation)
- rite : ceremonie/pratique religieuse (bapteme, circoncision, Paque-rite)
- institution : structure sociale persistante (royaume, mariage, synagogue-institution)
- fonction : titre/role/metier (roi, pretre, prophete, scribe, juge, berger, apotre)
- objet_sacre : objet liturgique (arche, autel, ephod, menorah)
- objets_et_vetements : objets profanes (robe, sandale, balance, lampe)
- plante : vegetaux (figuier, cedre, ble, absinthe)
- animal : faune (agneau, lion, aigle, serpent)
- alimentation_et_agriculture : aliments/agri (pain, vin, miel, vendanges)
- corps_et_sante : corps/maladie (coeur, main, lepre, hydropisie)
- mesures_et_temps : unite/periode (coudee, shekel, annee, sabbat)
- matiere : materiaux (bronze, lin, or, sel)
- evenement : evenement historique ponctuel (Exode, Deluge)
- nature : phenomene/geographie generique (desert, pluie, mer)

Regles :
- "Roi/pretre/prophete/scribe" = fonction (titre). David, Paul = personnage (individu).
- Temple, Tabernacle, Saint-des-Saints = lieu_sacre.
- Ange/demon generique (pas de nom propre) = etre_spirituel.
- "Peche" doctrine ; "Sacrifice" rite ; "Autel" objet_sacre.
- Si hesite : choisir la categorie la PLUS SPECIFIQUE et la plus PROBABLE en contexte biblique.

FORMAT DE REPONSE OBLIGATOIRE :
JSON array strict, un objet par concept recu dans le MEME ordre.
Chaque objet : {"cid":"<id_recu>","cat":"<categorie_de_la_liste>"}

Exemple si on te donne 3 concepts (paulos, temple, figuier), reponds :
[{"cid":"paulos","cat":"personnage"},{"cid":"temple","cat":"lieu_sacre"},{"cid":"figuier","cat":"plante"}]

RIEN d'autre que ce JSON. Pas de markdown, pas de ```json, pas d'explication."""


def truncate(s, n=250):
    s = (s or '').strip().replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    while '  ' in s: s = s.replace('  ', ' ')
    return s if len(s) <= n else s[:n].rsplit(' ', 1)[0] + '...'


def concept_line(cid, entry):
    label = entry.get('p') or entry.get('l') or cid
    excerpt = truncate(entry.get('e') or entry.get('d') or '', 220)
    return f'{cid} | {label} | {excerpt}' if excerpt else f'{cid} | {label}'


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    with open(META_PATH, encoding='utf-8') as f:
        meta = json.load(f)
    print(f'Loaded {len(meta)} concepts')

    BATCH_SIZE = 50
    items = list(meta.items())
    batches = [items[i:i+BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]
    print(f'Chunked into {len(batches)} requests of up to {BATCH_SIZE} concepts each')

    total_chars = 0
    with open(BATCH_INPUT, 'w', encoding='utf-8') as out:
        for idx, chunk in enumerate(batches):
            lines = [concept_line(cid, e) for cid, e in chunk]
            user_msg = (
                f'Classifie les {len(chunk)} concepts suivants (format "cid | label | extrait"). '
                f'Reponds avec un JSON array de {len(chunk)} objets, meme ordre.\n\n'
                + '\n'.join(lines)
            )
            request = {
                'custom_id': f'chunk_{idx:04d}',
                'method': 'POST',
                'url': '/v1/chat/completions',
                'body': {
                    'model': 'gpt-4o-mini',
                    'messages': [
                        {'role': 'system', 'content': SYSTEM_PROMPT},
                        {'role': 'user', 'content': user_msg}
                    ],
                    'max_tokens': max(600, len(chunk) * 28),
                    'temperature': 0,
                }
            }
            j = json.dumps(request, ensure_ascii=False)
            total_chars += len(j)
            out.write(j + '\n')

    size_mb = BATCH_INPUT.stat().st_size / (1024*1024)
    print(f'Wrote {len(batches)} requests to {BATCH_INPUT.name} ({size_mb:.1f} MB)')
    est_tokens = total_chars / 4
    print(f'Estimated input tokens: {est_tokens:,.0f}')
    print(f'Estimated cost (4o-mini batch $0.075/$0.30 per 1M): ~${est_tokens/1e6*0.075 + len(batches)*600/1e6*0.30:.2f}')

    tax_path = OUT_DIR / 'taxonomy.json'
    with open(tax_path, 'w', encoding='utf-8') as f:
        json.dump({'taxonomy': TAXONOMY, 'system_prompt': SYSTEM_PROMPT, 'batch_size': BATCH_SIZE}, f, ensure_ascii=False, indent=2)
    print(f'Saved taxonomy to {tax_path}')


if __name__ == '__main__':
    main()
