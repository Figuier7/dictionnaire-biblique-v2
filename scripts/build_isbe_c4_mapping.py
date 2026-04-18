#!/usr/bin/env python3
"""
Construit la table de mapping C4 EN -> FR pour les 182 chunks ISBE à corriger.

Lecture seule. Produit work/audit/isbe-c4-mot-map.json et
work/audit/isbe-c4-mot-map.md pour revue humaine avant application.

La table intègre les décisions éditoriales validées :
- Ancient -> Antique (sens temporel, distinct de ancien=autorité)
- Ancient Of Days -> Ancien des Jours (Elohîm)
- Ancients -> Anciens (vieillards)
- Elder -> Ancien
- High Priest -> Grand Prêtre (alias: Souverain sacrificateur)
- Trial Of Jesus -> Procès de Yéhoshoua (terminologie BYM)
- Apocrypha/Apocyphra -> Apocryphes
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / "work" / "audit"
FOCUSED_JSON = AUDIT_DIR / "isbe-residues-focused.json"
BUGS_JSON = AUDIT_DIR / "isbe-c4-json-bugs.json"
OUT_JSON = AUDIT_DIR / "isbe-c4-mot-map.json"
OUT_MD = AUDIT_DIR / "isbe-c4-mot-map.md"

# ==================================================================
# Mapping canonique EN -> FR, arbitré avec user le 2026-04-11
# ==================================================================
# Convention :
#   'fr'    : traduction française du mot complet
#   'aliases' : liste d'alias (stockés dans chunk.aliases[] pour la recherche)
#   'note'  : commentaire éditorial pour revue humaine
#
# Si un mot n'est PAS dans la table, le script produira un rapport
# d'items non-traduits à compléter manuellement.

MOT_MAP = {
    # === Single words (cluster C2 aussi) ===
    "Ancient": {"fr": "Antique", "aliases": [], "note": "Sens temporel ; distinct de 'ancien' (autorité)"},
    "Ancient Of Days": {"fr": "Ancien des Jours", "aliases": [], "note": "Elohîm (Dn 7:9,13,22)"},
    "Ancients": {"fr": "Anciens", "aliases": ["Vieillards"], "note": "Sens vieillard/autorité"},
    "Altar": {"fr": "Autel", "aliases": []},
    "Angel": {"fr": "Ange", "aliases": []},
    "Apocrypha": {"fr": "Apocryphes", "aliases": ["Apocryphe"]},
    "Against": {"fr": "Contre", "aliases": [], "note": "Article lexicographique sur le mot 'contre'"},
    "Battle": {"fr": "Bataille", "aliases": ["Combat"]},
    "Beast": {"fr": "Bête", "aliases": ["Animal"]},
    "Before": {"fr": "Devant", "aliases": ["Avant"]},
    "Birds": {"fr": "Oiseaux", "aliases": []},
    "Brotherly": {"fr": "Fraternel", "aliases": []},
    "Burial": {"fr": "Sépulture", "aliases": ["Enterrement"]},
    "Church": {"fr": "Église", "aliases": []},
    "City": {"fr": "Ville", "aliases": ["Cité"]},
    "Daily": {"fr": "Perpétuel", "aliases": ["Quotidien"], "note": "Sens Tamid (sacrifice perpétuel)"},
    "Death": {"fr": "Mort", "aliases": []},
    "Divorce": {"fr": "Divorce", "aliases": [], "note": "Identique FR/EN"},
    "Elder": {"fr": "Ancien", "aliases": ["Presbytre"]},
    "Faith": {"fr": "Foi", "aliases": []},
    "Gate": {"fr": "Porte", "aliases": []},
    "Grace": {"fr": "Grâce", "aliases": []},
    "Holiness": {"fr": "Sainteté", "aliases": []},
    "Hope": {"fr": "Espérance", "aliases": ["Espoir"]},
    "Husband": {"fr": "Époux", "aliases": ["Mari"]},
    "Land": {"fr": "Pays", "aliases": ["Terre"]},
    "Letters": {"fr": "Lettres", "aliases": ["Alphabet"]},
    "Love": {"fr": "Amour", "aliases": []},
    "Manuscripts": {"fr": "Manuscrits", "aliases": []},
    "Marriage": {"fr": "Mariage", "aliases": []},
    "Prayer": {"fr": "Prière", "aliases": []},
    "Priest": {"fr": "Prêtre", "aliases": ["Sacrificateur"], "note": "User decision 2026-04-11"},
    "Righteousness": {"fr": "Justice", "aliases": []},
    "River": {"fr": "Fleuve", "aliases": ["Rivière"]},
    "Rock": {"fr": "Rocher", "aliases": ["Roc", "Pierre"]},
    "Sea": {"fr": "Mer", "aliases": []},
    "Servant": {"fr": "Serviteur", "aliases": []},
    "Sojourner": {"fr": "Résident étranger", "aliases": ["Étranger", "Séjourneur"]},
    "Synagogue": {"fr": "Synagogue", "aliases": [], "note": "Identique FR/EN"},
    "Trial": {"fr": "Procès", "aliases": ["Jugement"]},
    "Wickedness": {"fr": "Méchanceté", "aliases": ["Iniquité"]},
    "Widow": {"fr": "Veuve", "aliases": []},
    "Wife": {"fr": "Épouse", "aliases": ["Femme"]},
    "Wilderness": {"fr": "Désert", "aliases": []},
    "Well": {"fr": "Puits", "aliases": []},

    # === "X In The Old/New Testament" ===
    "Decease, In New Testament": {"fr": "Décès dans le Nouveau Testament", "aliases": []},
    "Decease, In The Old Testament And Apocyphra": {"fr": "Décès dans l'Ancien Testament et les Apocryphes", "aliases": [], "note": "Typo 'Apocyphra' -> Apocryphes"},
    "Divorce In The New Testament": {"fr": "Divorce dans le Nouveau Testament", "aliases": []},
    "Divorce In The Old Testament": {"fr": "Divorce dans l'Ancien Testament", "aliases": []},
    "Elder In The New Testament": {"fr": "Ancien dans le Nouveau Testament", "aliases": ["Presbytre dans le Nouveau Testament"]},
    "Elder In The Old Testament": {"fr": "Ancien dans l'Ancien Testament", "aliases": []},
    "Languages Of The Old Testament": {"fr": "Langues de l'Ancien Testament", "aliases": []},
    "Manuscripts Of The New Testament": {"fr": "Manuscrits du Nouveau Testament", "aliases": []},
    "Testament, New, Text And Manuscripts Of The": {"fr": "Nouveau Testament, texte et manuscrits du", "aliases": []},

    # === "Adam / Eve / Angel Of..." variantes ===
    "Adam In The Old Testament And The Apocrypha": {"fr": "Adam dans l'Ancien Testament et les Apocryphes", "aliases": []},
    "Adam, Books Of": {"fr": "Adam, livres d'", "aliases": []},
    "Adam, City Of": {"fr": "Adam, ville d'", "aliases": []},
    "Angels Of The Seven Churches": {"fr": "Anges des Sept Églises", "aliases": []},

    # === Titres composés avec Gate/City/Valley/Sea/Field ===
    "Abomination, Birds Of": {"fr": "Abomination, oiseaux d'", "aliases": []},
    "After; Afterward": {"fr": "Après ; Ensuite", "aliases": []},
    "Ages, Rock Of": {"fr": "Rocher des Âges", "aliases": []},
    "Ark Of The Covenant": {"fr": "Arche de l'Alliance", "aliases": []},
    "Arrest, And Trial Of Jesus": {"fr": "Arrestation et procès de Yéhoshoua", "aliases": ["Arrestation et procès de Jésus"]},
    "Away With": {"fr": "Emporter ; Supporter", "aliases": []},
    "Battle-Bow": {"fr": "Arc de guerre", "aliases": ["Arc de bataille"]},
    "Beracah, Valley Of": {"fr": "Beraca, vallée de", "aliases": []},
    "Beth-Horon, The Battle Of": {"fr": "Beth-Horon, la bataille de", "aliases": []},
    "Body Of Death": {"fr": "Corps de la mort", "aliases": []},
    "Bow, In The Cloud": {"fr": "Arc, dans la nuée", "aliases": ["Arc-en-ciel"]},
    "Breastplate Of The High Priest": {"fr": "Pectoral du Grand Prêtre", "aliases": ["Pectoral du Souverain Sacrificateur"]},
    "Cities Of The Plain; Ciccar": {"fr": "Villes de la Plaine ; Ciccar", "aliases": []},
    "City Of Confusion": {"fr": "Cité de la Confusion", "aliases": []},
    "City Of Destruction": {"fr": "Cité de la Destruction", "aliases": []},
    "City, Rulers Of": {"fr": "Ville, chefs de la", "aliases": []},
    "Corner-Stone": {"fr": "Pierre angulaire", "aliases": ["Pierre d'angle"]},
    "Course Of Priests And Levites": {"fr": "Classes des sacrificateurs et Lévites", "aliases": ["Classes des prêtres et Lévites"]},
    "Court Of The Sanctuary; Tabernacle; Temple": {"fr": "Parvis du Sanctuaire ; Tabernacle ; Temple", "aliases": []},
    "Covenant Of Salt": {"fr": "Alliance de Sel", "aliases": []},
    "Covenant, Book Of The": {"fr": "Alliance, livre de l'", "aliases": []},
    "Covenant, In The New Testament": {"fr": "Alliance, dans le Nouveau Testament", "aliases": []},
    "Covenant, In The Old Testament": {"fr": "Alliance, dans l'Ancien Testament", "aliases": []},
    "Covenant, The New": {"fr": "Nouvelle Alliance", "aliases": []},
    "Day Before The Sabbath": {"fr": "Jour avant le Sabbat", "aliases": []},
    "Dead Sea, The": {"fr": "Mer Morte", "aliases": []},
    "Death, Body Of": {"fr": "Mort, corps de", "aliases": []},
    "Decision, Valley Of": {"fr": "Vallée de la Décision", "aliases": []},
    "Dedication, Feast Of": {"fr": "Dédicace, fête de la", "aliases": ["Hanoukka"]},
    "Encampment By The Red Sea": {"fr": "Campement près de la mer Rouge", "aliases": []},
    "Ephraim, Gate Of": {"fr": "Éphraïm, porte d'", "aliases": []},
    "Fasts And Feasts": {"fr": "Jeûnes et Fêtes", "aliases": []},
    "Feasts And Fasts": {"fr": "Fêtes et Jeûnes", "aliases": []},
    "Feasts, Seasons For": {"fr": "Fêtes, saisons des", "aliases": []},
    "Fuller'S Field, The": {"fr": "Champ du Foulon", "aliases": []},
    "Gad, Valley Of": {"fr": "Gad, vallée de", "aliases": []},
    "Galilee, Mountain In": {"fr": "Galilée, montagne en", "aliases": []},
    "Galilee, Sea Of": {"fr": "Mer de Galilée", "aliases": []},
    "Gate, The Beautiful": {"fr": "Porte la Belle", "aliases": ["Belle Porte"]},
    "Gennesaret, Land Of": {"fr": "Génésareth, pays de", "aliases": []},
    "Giants, Valley Of The": {"fr": "Vallée des Géants", "aliases": []},
    "Glass, Sea Of": {"fr": "Mer de Verre", "aliases": []},
    "Greece, Religion In Ancient": {"fr": "Grèce, religion antique en", "aliases": []},
    "Habakkuk, The Prayer Of": {"fr": "Habacuc, la prière de", "aliases": []},
    "Hammiphkad, Gate Of": {"fr": "Hammiphqad, porte de", "aliases": []},
    "Harod, Well Of": {"fr": "Harod, puits de", "aliases": ["Harod, source de"]},
    "Hinnom, Valley Of": {"fr": "Hinnom, vallée de", "aliases": ["Géhenne"]},
    "Horns Of The Altar": {"fr": "Cornes de l'Autel", "aliases": []},
    "Hours Of Prayer": {"fr": "Heures de prière", "aliases": []},
    "Ingathering, Feasts Of": {"fr": "Récolte, fête de la", "aliases": ["Fête de la Moisson"]},
    "Israel, Kingdom Of": {"fr": "Israël, Royaume d'", "aliases": []},
    "Jehoshaphat, Valley Of": {"fr": "Josaphat, vallée de", "aliases": ["Yehoshaphat, vallée de"]},
    "Joseph, Husband Of Mary": {"fr": "Joseph, époux de Marie", "aliases": ["Yosef, époux de Miryam"]},
    "Joseph, Prayer Of": {"fr": "Joseph, prière de", "aliases": []},
    "Judah, Kingdom Of": {"fr": "Juda, Royaume de", "aliases": []},
    "Land-Crocodile": {"fr": "Crocodile terrestre", "aliases": []},
    "Lord'S Prayer, The": {"fr": "Prière du Seigneur", "aliases": ["Notre Père", "Pater Noster"]},
    "Man Of Sin": {"fr": "Homme du péché", "aliases": []},
    "Manasses, The Prayer Of": {"fr": "Manassé, la prière de", "aliases": []},
    "Mercy-Seat, The": {"fr": "Propitiatoire", "aliases": []},
    "Miphkad; Gate Of": {"fr": "Miphqad ; porte de", "aliases": []},
    "Money, Love Of": {"fr": "Amour de l'argent", "aliases": ["Avarice"]},
    "Moriah, Land Of": {"fr": "Morija, pays de", "aliases": ["Moriah, pays de"]},
    "Morrow After The Sabbath": {"fr": "Lendemain du Sabbat", "aliases": []},
    "Mount Of The Valley": {"fr": "Mont de la Vallée", "aliases": []},
    "Old Prophet, The": {"fr": "Vieux Prophète, le", "aliases": []},
    "Persian Language And Literature (Ancient)": {"fr": "Langue et littérature perses (anciennes)", "aliases": []},
    "Philistines, Sea Of The": {"fr": "Mer des Philistins", "aliases": []},
    "Prayer Of Habakkuk": {"fr": "Prière d'Habacuc", "aliases": []},
    "Prayer Of Joseph": {"fr": "Prière de Joseph", "aliases": []},
    "Prayer Of Manasses": {"fr": "Prière de Manassé", "aliases": []},
    "Prayer, Hours Of": {"fr": "Prière, heures de", "aliases": []},
    "Refuge, Cities Of": {"fr": "Refuge, villes de", "aliases": ["Villes de refuge"]},
    "Rehoboth By The River": {"fr": "Rehoboth près du fleuve", "aliases": []},
    "Remission Of Sins": {"fr": "Rémission des péchés", "aliases": []},
    "River Of Egypt": {"fr": "Fleuve d'Égypte", "aliases": ["Torrent d'Égypte"]},
    "Rock Of Ages": {"fr": "Rocher des Âges", "aliases": []},
    "Rock-Badger": {"fr": "Daman", "aliases": ["Rock-badger"]},
    "Ruler Of The Feast": {"fr": "Maître du festin", "aliases": ["Ordonnateur du festin"]},
    "Ruler Of The Synagogue": {"fr": "Chef de la Synagogue", "aliases": []},
    "Rulers Of The City": {"fr": "Chefs de la Ville", "aliases": []},
    "Sabbath, Day Before The": {"fr": "Sabbat, jour avant le", "aliases": []},
    "Sabbath, Morrow After The": {"fr": "Sabbat, lendemain du", "aliases": []},
    "Sabbath, Second After The First": {"fr": "Sabbat, second après le premier", "aliases": []},
    "Salt, City Of": {"fr": "Sel, ville du", "aliases": []},
    "Salt, Valley Of": {"fr": "Vallée du Sel", "aliases": []},
    "Samaria, City Of": {"fr": "Samarie, ville de", "aliases": ["Shomron, ville de"]},
    "Samuel, Books Of": {"fr": "Samuel, livres de", "aliases": ["Shemouel, livres de"]},
    "Satan, Synagogue Of": {"fr": "Satan, synagogue de", "aliases": []},
    "Sea Of Jazer": {"fr": "Mer de Jaezer", "aliases": []},
    "Sea, The Great": {"fr": "Mer, la Grande", "aliases": ["Grande Mer", "Mer Méditerranée"]},
    "Sea, The Molten; Sea, The Brazen": {"fr": "Mer de Fonte ; Mer d'Airain", "aliases": []},
    "Sea-Mew": {"fr": "Goéland", "aliases": ["Mouette"]},
    "Sea-Monster": {"fr": "Monstre marin", "aliases": []},
    "Search The Scriptures": {"fr": "Sondez les Écritures", "aliases": []},
    "Self-Righteousness": {"fr": "Propre justice", "aliases": ["Justice propre"]},
    "Servant Of Jehovah; Servant Of The Lord; Servant Of Yahweh": {"fr": "Serviteur de YHWH", "aliases": ["Serviteur du Seigneur", "Serviteur de l'Éternel"]},
    "Shaalim, Land Of": {"fr": "Shaalim, pays de", "aliases": []},
    "Shadow Of Death": {"fr": "Ombre de la mort", "aliases": []},
    "Shalishah, Land Of": {"fr": "Shalisha, pays de", "aliases": []},
    "Shallecheth, The Gate": {"fr": "Shallékheth, la porte", "aliases": []},
    "Shual, Land Of": {"fr": "Shual, pays de", "aliases": []},
    "Sin, Man Of": {"fr": "Péché, homme du", "aliases": []},
    "Sin, Wilderness Of": {"fr": "Sin, désert de", "aliases": []},
    "Sinim, Land Of": {"fr": "Sinim, pays de", "aliases": []},
    "Sirah, Well Of": {"fr": "Sira, puits de", "aliases": []},
    "Slaughter, Valley Of": {"fr": "Vallée du Carnage", "aliases": ["Vallée du Massacre"]},
    "Sorek, Valley Of": {"fr": "Soreq, vallée de", "aliases": ["Sorek, vallée de"]},
    "Store-Cities": {"fr": "Villes-magasins", "aliases": ["Villes d'entrepôt"]},
    "Stranger And Sojourner (In The Apocrypha And The New Testament)": {"fr": "Étranger et résident (dans les Apocryphes et le Nouveau Testament)", "aliases": []},
    "Stranger And Sojourner (In The Old Testament)": {"fr": "Étranger et résident (dans l'Ancien Testament)", "aliases": []},
    "Synagogue, The Great": {"fr": "Grande Synagogue", "aliases": []},
    "Tabernacles, Feast Of": {"fr": "Fête des Tabernacles", "aliases": ["Soukkot"]},
    "Tiberias, Sea Of": {"fr": "Mer de Tibériade", "aliases": []},
    "Tob, The Land Of": {"fr": "Tob, le pays de", "aliases": []},
    "Treasury, (Of Temple)": {"fr": "Trésor (du Temple)", "aliases": ["Trésorerie du Temple"]},
    "Trial Of Jesus": {"fr": "Procès de Yéhoshoua", "aliases": ["Procès de Jésus"]},
    "Trumpets, Feast Of": {"fr": "Fête des Trompettes", "aliases": ["Rosh Hashana"]},
    "Valley Of Decision": {"fr": "Vallée de la Décision", "aliases": []},
    "Valley Of Giants": {"fr": "Vallée des Géants", "aliases": []},
    "Valley Of Slaughter": {"fr": "Vallée du Carnage", "aliases": []},
    "Valley Of Vision": {"fr": "Vallée de la Vision", "aliases": []},
    "Weeks, Feast Of": {"fr": "Fête des Semaines", "aliases": ["Shavouot", "Pentecôte"]},
    "Wisdom Of Solomon, The": {"fr": "Sagesse de Salomon", "aliases": ["Sagesse de Shelomoh"]},
    "Zephathah, Valley Of": {"fr": "Zephathah, vallée de", "aliases": []},
    "Zoheleth, The Stone Of": {"fr": "Pierre de Zoheleth", "aliases": []},
    "Zophim, The Field Of": {"fr": "Champ de Tsofim", "aliases": ["Champ des guetteurs"]},
}


def main():
    with open(FOCUSED_JSON, 'r', encoding='utf-8-sig') as f:
        focused = json.load(f)
    c4_items = focused['clusters']['C4_focused']['items']

    with open(BUGS_JSON, 'r', encoding='utf-8-sig') as f:
        bugs = {b['id'] for b in json.load(f)['items']}

    c4_clean = [it for it in c4_items if it['entry_id'] not in bugs]

    mapped = []
    unmapped = []
    for it in c4_clean:
        mot = it['mot']
        if mot in MOT_MAP:
            spec = MOT_MAP[mot]
            mapped.append({
                'entry_id': it['entry_id'],
                'chunk': it['chunk'],
                'mot_en': mot,
                'mot_fr': spec['fr'],
                'aliases': spec.get('aliases', []),
                'note': spec.get('note', ''),
            })
        else:
            unmapped.append({
                'entry_id': it['entry_id'],
                'chunk': it['chunk'],
                'mot_en': mot,
                'def_preview': it.get('def_preview', ''),
            })

    result = {
        'total_c4_items': len(c4_items),
        'bugs_excluded': len(c4_items) - len(c4_clean),
        'c4_clean_total': len(c4_clean),
        'mapped_count': len(mapped),
        'unmapped_count': len(unmapped),
        'mapped': mapped,
        'unmapped': unmapped,
    }
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # MD
    lines = []
    lines.append('# Mapping C4 EN → FR — ISBE chunks')
    lines.append('')
    lines.append(f'- C4 brut (focalisé)     : **{len(c4_items)}**')
    lines.append(f'- Bugs JSON exclus       : **{len(c4_items) - len(c4_clean)}**')
    lines.append(f'- C4 nettoyé             : **{len(c4_clean)}**')
    lines.append(f'- Mapping complété       : **{len(mapped)}**')
    lines.append(f'- Mapping MANQUANT       : **{len(unmapped)}**')
    lines.append('')
    if unmapped:
        lines.append('## ⚠️ Items sans traduction définie')
        lines.append('')
        lines.append('| entry_id | chunk | mot_en | def_preview |')
        lines.append('|---|---|---|---|')
        for u in unmapped:
            prev = u['def_preview'].replace('|', '\\|')[:100]
            lines.append(f"| `{u['entry_id']}` | {u['chunk']} | **{u['mot_en']}** | {prev} |")
        lines.append('')
    lines.append('## Mapping appliqué')
    lines.append('')
    lines.append('| entry_id | chunk | mot_en | → mot_fr | aliases | note |')
    lines.append('|---|---|---|---|---|---|')
    for m in mapped:
        al = ', '.join(m['aliases']) if m['aliases'] else '—'
        nt = m['note'].replace('|', '\\|') if m['note'] else ''
        lines.append(f"| `{m['entry_id']}` | {m['chunk']} | {m['mot_en']} | **{m['mot_fr']}** | {al} | {nt} |")
    lines.append('')

    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print(f'Mapping C4 écrit : {OUT_JSON}')
    print(f'Mapping C4 MD    : {OUT_MD}')
    print(f'Mapped   : {len(mapped)}')
    print(f'Unmapped : {len(unmapped)}')
    if unmapped:
        print()
        print('Items sans mapping :')
        for u in unmapped:
            print(f"  {u['entry_id']} {u['mot_en']!r}")


if __name__ == '__main__':
    main()
