#!/usr/bin/env python3
"""
Construit la table de mapping C4.2 : entrées ISBE orphelines
(non couvertes par C4 initial) mais liées à des concepts C2/C3.

Lecture seule. Produit :
- work/audit/isbe-c4-2-mot-map.json
- work/audit/isbe-c4-2-mot-map.md

Exclut automatiquement les 2 entrées en JSON-bug (isbe-007190, isbe-008281).
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / "work" / "audit"
ORPHANS_JSON = AUDIT_DIR / "isbe-c4-2-orphans.json"
BUGS_JSON = AUDIT_DIR / "isbe-c4-json-bugs.json"
OUT_JSON = AUDIT_DIR / "isbe-c4-2-mot-map.json"
OUT_MD = AUDIT_DIR / "isbe-c4-2-mot-map.md"

# Mapping supplémentaire EN -> FR pour les entrées orphelines.
# Cohérent avec les décisions éditoriales déjà prises :
# - Priest -> Prêtre (alias Sacrificateur)
# - Grand Prêtre (alias Souverain Sacrificateur)
# - Procès de Yéhoshoua (alias Procès de Jésus)
# - Apocryphes (pluriel)
# - Ancien = autorité, Antique = temporel
MOT_MAP_2 = {
    "Agrarian Laws": {"fr": "Lois Agraires", "aliases": []},
    "Apostolical Church Ordinances": {"fr": "Ordonnances Apostoliques de l'Église", "aliases": []},
    "Battle": {"fr": "Bataille", "aliases": ["Combat"]},
    "Belus, Temple Of": {"fr": "Bélus, Temple de", "aliases": []},
    "Birds": {"fr": "Oiseaux", "aliases": []},
    "Birds, Unclean": {"fr": "Oiseaux impurs", "aliases": []},
    "Brazen": {"fr": "Airain", "aliases": ["Bronze"]},
    "Brazen Sea": {"fr": "Mer d'Airain", "aliases": ["Mer de Bronze"]},
    "Brother'S Wife": {"fr": "Femme du frère", "aliases": ["Belle-sœur"]},
    "Brotherly Kindness; Brotherly Love": {"fr": "Bienveillance fraternelle ; Amour fraternel", "aliases": []},
    "Burnt Sacrifice": {"fr": "Holocauste", "aliases": ["Sacrifice consumé par le feu"]},
    "Church Government": {"fr": "Gouvernement de l'Église", "aliases": []},
    "Churches, Robbers Of": {"fr": "Églises, voleurs des", "aliases": []},
    "Churches, Seven": {"fr": "Sept Églises", "aliases": []},
    "Cities Of Refuge": {"fr": "Villes de Refuge", "aliases": []},
    "Corner Gate": {"fr": "Porte de l'Angle", "aliases": []},
    "Daily Offering; Daily Sacrifice": {"fr": "Oblation perpétuelle ; Sacrifice perpétuel", "aliases": ["Tamid"]},
    "Eve In The New Testament": {"fr": "Ève dans le Nouveau Testament", "aliases": []},
    "Eve In The Old Testament": {"fr": "Ève dans l'Ancien Testament", "aliases": []},
    "Exposure, To Wild Beasts": {"fr": "Exposition aux bêtes sauvages", "aliases": []},
    "Fish Gate": {"fr": "Porte des Poissons", "aliases": []},
    "Fortification; Fort; Fortified Cities; Fortress": {"fr": "Fortification ; Fort ; Villes fortifiées ; Forteresse", "aliases": []},
    "Fountain Gate": {"fr": "Porte de la Fontaine", "aliases": []},
    "Freewill Offering": {"fr": "Offrande Volontaire", "aliases": []},
    "Golden City": {"fr": "Cité d'Or", "aliases": []},
    "Guilt Offering": {"fr": "Sacrifice de Culpabilité", "aliases": ["Sacrifice de Réparation"]},
    "High Priest": {"fr": "Grand Prêtre", "aliases": ["Souverain Sacrificateur"]},
    "Human Sacrifice": {"fr": "Sacrifice humain", "aliases": []},
    "Husband'S Brother": {"fr": "Frère du mari", "aliases": ["Beau-frère"]},
    "Jordan Valley": {"fr": "Vallée du Jourdain", "aliases": []},
    "Judging Judgment": {"fr": "Juger, jugement", "aliases": []},
    "Judgment, Last": {"fr": "Jugement dernier", "aliases": []},
    "Know; Knowledge": {"fr": "Connaître ; Connaissance", "aliases": []},
    "Land Laws": {"fr": "Lois sur la Terre", "aliases": ["Lois foncières"]},
    "Levitical Cities": {"fr": "Villes lévitiques", "aliases": []},
    "Manuscripts Of The Old Testament": {"fr": "Manuscrits de l'Ancien Testament", "aliases": []},
    "Meal Offering": {"fr": "Oblation", "aliases": ["Offrande de farine"]},
    "Mediterranean Sea": {"fr": "Mer Méditerranée", "aliases": []},
    "Molten Sea": {"fr": "Mer de Fonte", "aliases": []},
    "New Birth": {"fr": "Nouvelle Naissance", "aliases": ["Régénération"]},
    "New Covenant": {"fr": "Nouvelle Alliance", "aliases": []},
    "Offer; Offering": {"fr": "Offrir ; Offrande", "aliases": []},
    "Old Testament Languages": {"fr": "Langues de l'Ancien Testament", "aliases": []},
    "Peace Offering": {"fr": "Sacrifice de Prospérité", "aliases": ["Sacrifice de Paix"]},
    "Persian Religion (Ancient)": {"fr": "Religion perse (antique)", "aliases": []},
    "Potsherd Gate": {"fr": "Porte des Tessons", "aliases": []},
    "Potter'S Field": {"fr": "Champ du Potier", "aliases": []},
    "Quotations In The New Testament": {"fr": "Citations dans le Nouveau Testament", "aliases": []},
    "Royal City": {"fr": "Cité royale", "aliases": []},
    "Sacrifice, Human": {"fr": "Sacrifice humain", "aliases": []},
    "Scriptures, Search The": {"fr": "Écritures, sondez les", "aliases": []},
    "Second Death": {"fr": "Seconde Mort", "aliases": []},
    "Seven Churches": {"fr": "Sept Églises", "aliases": []},
    "Shin, Sin": {"fr": "Shin, Sin", "aliases": [], "note": "Lettres hébraïques, identiques"},
    "Sin Money": {"fr": "Argent du péché", "aliases": []},
    "Sodomitish; Sea": {"fr": "Mer de Sodome", "aliases": []},
    "Spiritual Rock": {"fr": "Rocher spirituel", "aliases": []},
    "Spiritual Sacrifice": {"fr": "Sacrifice spirituel", "aliases": []},
    "Strange Wife": {"fr": "Femme étrangère", "aliases": []},
    "Stumbling-Block; Stumbling-Stone": {"fr": "Pierre d'achoppement ; Pierre de scandale", "aliases": []},
    "Sun Gate": {"fr": "Porte du Soleil", "aliases": []},
    "Swift Beasts": {"fr": "Bêtes rapides", "aliases": []},
    "Synagogue Of Libertines": {"fr": "Synagogue des Affranchis", "aliases": ["Synagogue des Libertins"]},
    "Synagogue Of Satan": {"fr": "Synagogue de Satan", "aliases": []},
    "Thank Offering": {"fr": "Sacrifice d'Actions de Grâces", "aliases": []},
    "Unpardonable Sin": {"fr": "Péché impardonnable", "aliases": ["Blasphème contre l'Esprit"]},
    "Utmost Sea; Uttermost Sea": {"fr": "Mer ultime ; Mer la plus éloignée", "aliases": []},
    "Valley Gate": {"fr": "Porte de la Vallée", "aliases": []},
    "Wife": {"fr": "Épouse", "aliases": ["Femme"]},
    "Wife, Brother'S": {"fr": "Épouse, du frère", "aliases": []},
    "Wild Beast": {"fr": "Bête sauvage", "aliases": []},
}


def main():
    with open(ORPHANS_JSON, 'r', encoding='utf-8-sig') as f:
        orphans_doc = json.load(f)
    orphans = orphans_doc['items']

    with open(BUGS_JSON, 'r', encoding='utf-8-sig') as f:
        bugs_doc = json.load(f)
    bug_ids = {b['id'] for b in bugs_doc['items']}

    mapped = []
    unmapped = []
    excluded_bugs = []
    for o in orphans:
        if o['entry_id'] in bug_ids:
            excluded_bugs.append(o)
            continue
        mot = o['mot']
        if mot in MOT_MAP_2:
            spec = MOT_MAP_2[mot]
            mapped.append({
                'entry_id': o['entry_id'],
                'chunk': o['chunk'].replace('isbe\\', '').replace('isbe/', ''),
                'mot_en': mot,
                'mot_fr': spec['fr'],
                'aliases': spec.get('aliases', []),
                'note': spec.get('note', ''),
                'concept_id': o['concept_id'],
                'concept_label': o['concept_label'],
            })
        else:
            unmapped.append(o)

    result = {
        'total_orphans': len(orphans),
        'bugs_excluded': len(excluded_bugs),
        'mapped_count': len(mapped),
        'unmapped_count': len(unmapped),
        'mapped': mapped,
        'unmapped': unmapped,
        'excluded_bugs': [{'entry_id': b['entry_id'], 'mot': b['mot']} for b in excluded_bugs],
    }

    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # MD
    lines = []
    lines.append('# Mapping C4.2 — Orphelins ISBE (complément C4 initial)')
    lines.append('')
    lines.append(f'- Orphelins totaux     : **{len(orphans)}**')
    lines.append(f'- Exclus (JSON bugs)   : **{len(excluded_bugs)}**')
    lines.append(f'- Mapping complété     : **{len(mapped)}**')
    lines.append(f'- Mapping MANQUANT     : **{len(unmapped)}**')
    lines.append('')

    if excluded_bugs:
        lines.append('## Exclus (traités dans chantier séparé "28 chunks JSON corrompus")')
        lines.append('')
        for b in excluded_bugs:
            lines.append(f"- `{b['entry_id']}` {b['mot']!r}")
        lines.append('')

    if unmapped:
        lines.append('## ⚠️ Items sans traduction')
        lines.append('')
        for u in unmapped:
            lines.append(f"- `{u['entry_id']}` {u['mot']!r} (concept: `{u['concept_id']}`)")
        lines.append('')

    lines.append('## Mapping appliqué')
    lines.append('')
    lines.append('| entry_id | chunk | concept_id | mot_en | → mot_fr | aliases |')
    lines.append('|---|---|---|---|---|---|')
    for m in mapped:
        al = ', '.join(m['aliases']) if m['aliases'] else '—'
        lines.append(f"| `{m['entry_id']}` | {m['chunk']} | `{m['concept_id']}` | {m['mot_en']} | **{m['mot_fr']}** | {al} |")
    lines.append('')

    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print(f'Mapping C4.2 JSON : {OUT_JSON}')
    print(f'Mapping C4.2 MD   : {OUT_MD}')
    print(f'Mapped  : {len(mapped)}')
    print(f'Unmapped: {len(unmapped)}')
    print(f'Excluded: {len(excluded_bugs)}')
    if unmapped:
        print()
        print('Items sans traduction :')
        for u in unmapped:
            print(f"  {u['entry_id']} {u['mot']!r}")


if __name__ == '__main__':
    main()
