#!/usr/bin/env python3
"""
Patch C8 : 265 concepts Category A (suffixes -er, -ing, -ness, etc.)
Table de traduction complète EN→FR avec arbitrages éditoriaux BYM
(Prêtre, Yéhoshoua, Mashiah, etc.).

Stratégie :
- chunks ISBE : label_fr + aliases (ne touche pas mot/slug)
- concepts.json : label + display_titles + public_forms + aliases
- concept-meta.json : l, p, s
- UTF-8 sans BOM pour concepts et concept-meta

Modes : dry-run (défaut) ou --apply
"""
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
DICT_DIR = ROOT / "uploads" / "dictionnaires"
ISBE_DIR = DICT_DIR / "isbe"
AUDIT_DIR = ROOT / "work" / "audit"
BACKUP_DIR = ROOT / "work" / "backups"

CONCEPTS_JSON = DICT_DIR / "concepts.json"
CONCEPT_META_JSON = DICT_DIR / "concept-meta.json"
FILTERED_JSON = AUDIT_DIR / "isbe-c8-cat-a-filtered.json"
LOG_JSON = AUDIT_DIR / "isbe-c8-apply-log.json"
DRY_MD = AUDIT_DIR / "isbe-c8-dry-run.md"

# Noms propres bibliques à EXCLURE (skippés, pas de traduction)
SKIP_PROPER_NOUNS = {
    'Emmer', 'Jether', 'Shepher', 'Taber', 'Theodotion', 'Zecher',
    'Oleaster',  # Arbre mais identique FR/EN
    'Chitlish', 'Marish',  # Toponymes bibliques
}

# Faux positifs : le mot est déjà correct en français ou proche
# (on ne touche pas le label, on va juste skipper)
SKIP_ALREADY_FR = {
    'Answer',  # à voir — mais "Answer" n'est pas français
    'Business',  # proche
    'Defence',  # FR=Défense, très similaire mais orthographe différente → on traduit
    'Defer',  # verbe déférer, proche mais anglais
}

# Table de traduction complète
# Key = mot EN original, Value = (traduction FR, alias supplémentaires)
MAP = {
    'Abolish': ('Abolir', []),
    'Admiration': ('Admiration', []),  # skip — identique FR
    'Altogether': ('Entièrement', ['Complètement']),
    'Ambushment': ('Embuscade', []),
    'Angling': ('Pêche à la ligne', []),
    'Anguish': ('Angoisse', ['Tourment']),
    'Answer': ('Réponse', []),
    'Appearing': ('Apparition', ['Manifestation']),
    'Assiduous': ('Assidu', []),
    'Astonishment': ('Étonnement', ['Stupeur']),
    'Asunder': ('En deux', ['Séparé']),
    'Babbler': ('Discoureur', ['Bavard']),
    'Babbling': ('Bavardage', ['Babillage']),
    'Baking': ('Cuisson', ['Fournée']),
    'Banishment': ('Bannissement', ['Exil']),
    'Beating': ('Battage', ['Coups']),
    'Bedchamber': ('Chambre à coucher', ['Chambre']),
    'Beginning': ('Commencement', ['Début']),
    'Beheading': ('Décapitation', []),
    'Beholding': ('Contemplation', ['Observation']),
    'Bitterness': ('Amertume', []),
    'Blackness': ('Noirceur', ['Obscurité']),
    'Blessedness': ('Béatitude', ['Bonheur']),
    'Blessing': ('Bénédiction', []),
    'Blinding': ('Aveuglement', []),
    'Bloodguiltiness': ('Culpabilité du sang', ['Sang versé']),
    'Bloodshedding': ('Effusion de sang', []),
    'Boldness': ('Hardiesse', ['Assurance']),
    'Borderer': ('Habitant des frontières', []),
    'Borrowing': ('Emprunt', []),
    'Boxing': ('Pugilat', ['Boxe']),
    'Branding': ('Marquage au fer', []),
    'Brawler': ('Querelleur', []),
    'Brightness': ('Éclat', ['Brillance', 'Splendeur']),
    'Bring': ('Apporter', []),
    'Brotherhood': ('Fraternité', []),
    'Buckler': ('Bouclier', []),
    'Burier': ('Enterreur', ['Fossoyeur']),
    'Business': ('Affaires', []),
    'Buying': ('Achat', []),
    'Calker': ('Calfat', []),
    'Calling': ('Appel', ['Vocation']),
    'Casement': ('Fenêtre à battants', []),
    'Changer': ('Changeur', []),
    'Chatter': ('Babil', ['Bavardage']),
    'Cherish': ('Chérir', []),
    'Choler': ('Colère', ['Bile']),
    'Cluster': ('Grappe', ['Amas']),
    'Coffer': ('Coffre', ['Coffret']),
    'Comfortless': ('Sans consolation', ['Désolé']),
    'Complaining': ('Plainte', ['Murmure']),
    'Concerning': ('Concernant', ['Au sujet de']),
    'Consider': ('Considérer', []),
    'Convulsing': ('Convulsion', []),
    'Coping': ('Couronnement', ['Faîte']),
    'Costliness': ('Somptuosité', ['Coût élevé']),
    'Coupling': ('Accouplement', ['Jonction']),
    'Crashing': ('Fracas', ['Effondrement']),
    'Crier': ('Crieur', ['Héraut']),
    'Cucumber': ('Concombre', []),
    'Cunning': ('Ruse', ['Astuce']),
    'Cupbearer': ('Échanson', []),
    'Dagger': ('Poignard', ['Dague']),
    'Dancing': ('Danse', []),
    'Danger': ('Danger', []),  # skip — identique FR
    'Decision': ('Décision', []),  # skip
    'Deer': ('Cerf', ['Daim', 'Biche']),
    'Defence': ('Défense', []),
    'Defer': ('Différer', []),
    'Deliver': ('Délivrer', []),
    'Delusion': ('Illusion', ['Égarement']),
    'Derision': ('Dérision', []),  # skip
    'Diminish': ('Diminuer', []),
    'Dinner': ('Dîner', ['Repas']),
    'Discover': ('Découvrir', []),
    'Disposition': ('Disposition', []),  # skip
    'Doleful': ('Lugubre', ['Plaintif']),
    'Doorkeeper': ('Portier', []),
    'Drowning': ('Noyade', []),
    'Drunkenness': ('Ivresse', []),
    'Earring': ('Boucle d\'oreille', ['Pendant d\'oreille']),
    'Either': ('Ou bien', ['L\'un ou l\'autre']),
    'Enchantment': ('Enchantement', ['Sortilège']),
    'Engraving': ('Gravure', []),
    'Enrolment': ('Enrôlement', ['Inscription']),
    'Experiment': ('Expérience', []),
    'Famish': ('Affamer', []),
    'Fatherless': ('Orphelin de père', ['Sans père']),
    'Fatness': ('Graisse', ['Embonpoint']),
    'Feeling': ('Sentiment', []),
    'Fellowship': ('Communion', ['Fraternité', 'Société']),
    'Fetter': ('Entrave', ['Fers']),
    'Fever': ('Fièvre', []),
    'Finish': ('Achever', ['Terminer']),
    'Finisher': ('Consommateur', []),  # Heb 12:2 "auteur et consommateur"
    'Firstling': ('Premier-né', ['Prémice']),
    'Fishing': ('Pêche', []),
    'Flaying': ('Écorchement', []),
    'Flourish': ('Fleurir', ['Prospérer']),
    'Follower': ('Disciple', ['Suiveur']),
    'Forbearance': ('Longanimité', ['Patience']),
    'Forefather': ('Ancêtre', ['Aïeul']),
    'Foreigner': ('Étranger', []),
    'Foreship': ('Proue', []),
    'Forgiveness': ('Pardon', []),
    'Former': ('Précédent', ['Ancien', 'Autrefois']),
    'Founder': ('Fondateur', []),
    'Frontier': ('Frontière', []),
    'Frowardness': ('Perversité', []),
    'Fullness': ('Plénitude', []),
    'Furnish': ('Fournir', ['Pourvoir']),
    'Gardener': ('Jardinier', []),
    'Garner': ('Grenier', []),
    'Gather': ('Rassembler', ['Recueillir']),
    'Gender': ('Genre', []),  # skip / close to FR
    'Gentleness': ('Douceur', []),
    'Gleaning': ('Glanage', []),
    'Glistering': ('Étincelant', ['Resplendissant']),
    'Godless': ('Impie', ['Sans Elohîm']),
    'Goodliness': ('Beauté', ['Excellence']),
    'Gracious': ('Gracieux', ['Bienveillant']),
    'Greeting': ('Salutation', []),
    'Grievance': ('Grief', ['Plainte']),
    'Grinder': ('Meule', ['Broyeur', 'Molaire']),
    'Guiltless': ('Innocent', ['Sans faute']),
    'Handful': ('Poignée', []),
    'Happiness': ('Bonheur', []),
    'Healing': ('Guérison', []),
    'Hereafter': ('Ci-après', ['Désormais']),
    'Hewer': ('Bûcheron', ['Tailleur de pierre']),
    'Holding': ('Possession', ['Propriété']),
    'Huckster': ('Colporteur', []),
    'Hunger': ('Faim', []),
    'Imprisonment': ('Emprisonnement', []),
    'Incantation': ('Incantation', []),  # skip
    'Incorruption': ('Incorruptibilité', []),
    'Injurious': ('Injurieux', []),
    'Jangling': ('Vain bavardage', ['Querelle']),
    'Jesting': ('Plaisanterie', ['Bouffonnerie']),
    'Jumping': ('Saut', ['Bondissement']),
    'Kindness': ('Bonté', ['Bienveillance']),
    'Kneading': ('Pétrissage', []),
    'Lasciviousness': ('Impudicité', ['Luxure']),
    'Laughter': ('Rire', []),
    'Lawful': ('Légitime', ['Licite']),
    'Lawgiver': ('Législateur', []),
    'Lawless': ('Sans loi', ['Impie']),
    'Leaping': ('Bondissement', ['Saut']),
    'Leasing': ('Mensonge', []),  # KJV archaic = "lie"
    'Licence': ('Licence', []),  # skip
    'Longsuffering': ('Longanimité', ['Patience']),
    'Lover': ('Amant', ['Amoureux', 'Ami']),
    'Lovingkindness': ('Bonté', ['Amour fidèle']),
    'Lying': ('Mensonge', []),
    'Maker': ('Créateur', ['Fabricant']),
    'Manstealing': ('Kidnapping', ['Enlèvement d\'homme']),
    'Mariner': ('Marin', ['Matelot']),
    'Master': ('Maître', []),
    'Matter': ('Matière', ['Sujet']),
    'Member': ('Membre', []),  # skip
    'Monster': ('Monstre', []),  # skip
    'Morning': ('Matin', []),
    'Motion': ('Mouvement', []),
    'Muffler': ('Voile', ['Écharpe']),
    'Munition': ('Munition', []),  # skip
    'Mutilation': ('Mutilation', []),  # skip
    'Mutter': ('Murmurer', []),
    'Neesing': ('Éternuement', []),
    'Nothing': ('Rien', []),
    'Nourish': ('Nourrir', []),
    'Offscouring': ('Rebut', ['Ordure']),
    'Offspring': ('Descendance', ['Postérité']),
    'Order': ('Ordre', []),
    'Outer': ('Extérieur', []),
    'Outgoing': ('Sortie', []),
    'Outlandish': ('Étranger', ['Exotique']),
    'Overseer': ('Surveillant', ['Évêque']),
    'Owner': ('Propriétaire', []),
    'Painfulness': ('Labeur pénible', ['Douleur']),
    'Painting': ('Peinture', []),
    'Passover': ('Pâque', []),
    'Peacemaker': ('Artisan de paix', []),
    'Perseverance': ('Persévérance', []),  # skip
    'Pitiful': ('Compatissant', ['Miséricordieux']),
    'Ponder': ('Méditer', ['Peser']),
    'Power': ('Pouvoir', ['Puissance']),
    'Prefer': ('Préférer', []),
    'Provender': ('Fourrage', []),
    'Purloining': ('Vol', ['Détournement']),
    'Purtenance': ('Entrailles', []),
    'Quarter': ('Quartier', []),
    'Rafter': ('Poutre', ['Chevron']),
    'Reading': ('Lecture', []),
    'Reaping': ('Moisson', []),
    'Receiver': ('Receveur', []),
    'Reclining': ('Repos à table', []),
    'Recover': ('Recouvrer', ['Guérir']),
    'Register': ('Registre', []),  # skip
    'Remainder': ('Reste', []),
    'Ringleader': ('Chef de file', ['Meneur']),
    'Rising': ('Lever', ['Éruption cutanée']),
    'Roller': ('Rouleau', []),
    'Ruler': ('Chef', ['Gouverneur']),
    'Runner': ('Coureur', []),
    'Sedition': ('Sédition', []),  # skip
    'Setting': ('Monture', ['Sertissage']),
    'Sever': ('Séparer', []),
    'Shamefacedness': ('Pudeur', ['Modestie']),
    'Shamefastness': ('Pudeur', ['Modestie']),
    'Shaving': ('Rasage', []),
    'Shipmaster': ('Capitaine de navire', []),
    'Shower': ('Averse', ['Ondée']),
    'Sinlessness': ('Absence de péché', []),
    'Sinner': ('Pécheur', []),
    'Sister': ('Sœur', []),
    'Slander': ('Calomnie', ['Médisance']),
    'Slaying': ('Meurtre', ['Tuerie']),
    'Sodering': ('Soudure', []),  # typo of "soldering"
    'Sottish': ('Stupide', ['Ivrogne']),
    'Spoiler': ('Pillard', ['Spoliateur']),
    'Spring': ('Source', ['Printemps']),
    'Stammerer': ('Bègue', []),
    'Standing': ('Position', ['Stature']),
    'Stealing': ('Vol', ['Larcin']),
    'Stedfastness': ('Fermeté', ['Stabilité']),
    'Sting': ('Aiguillon', []),
    'Strangling': ('Étranglement', []),
    'Substance': ('Substance', []),  # skip
    'Suffering': ('Souffrance', []),
    'Summer': ('Été', []),
    'Sunrising': ('Lever du soleil', ['Orient']),
    'Superscription': ('Inscription', ['Titre']),
    'Swearing': ('Serment', ['Juron']),
    'Tanner': ('Tanneur', []),
    'Taskmaster': ('Exacteur', ['Contremaître']),
    'Tattler': ('Rapporteur', ['Bavard']),
    'Temper': ('Tempérament', ['Trempe']),
    'Tetter': ('Dartre', ['Eczéma']),
    'Traveller': ('Voyageur', []),
    'Treasurer': ('Trésorier', []),
    'Trucebkeaker': ('Déloyal', []),  # typo "truce-breaker"
    'Unbeliever': ('Incrédule', ['Incroyant']),
    'Undersetter': ('Support', ['Appui']),
    'Viper': ('Vipère', []),
    'Wafer': ('Gâteau', ['Galette']),
    'Watcher': ('Veilleur', []),
    'Water': ('Eau', []),
    'Weather': ('Temps', ['Météo']),
    'Wedding': ('Noce', ['Mariage']),
    'Weeping': ('Pleurs', ['Larmes']),
    'Wellspring': ('Source', []),
    'Winebibber': ('Buveur de vin', ['Ivrogne']),
    'Winter': ('Hiver', []),
    'Wish': ('Souhait', []),
    'Wrestling': ('Lutte', []),
    'Writing': ('Écriture', []),
}


def check_backup():
    if not BACKUP_DIR.exists():
        return False
    return bool(list(BACKUP_DIR.glob('dictionnaires-*.zip')))


def patch_chunk_entry(entry, fr_label, extra_aliases, mot_en):
    before_aliases = list(entry.get('aliases', []))
    new_src = entry.get('source_title_en') or mot_en
    new_aliases = list(before_aliases)
    for cand in [fr_label] + list(extra_aliases) + [mot_en]:
        if cand and cand not in new_aliases:
            new_aliases.append(cand)

    changed = (
        entry.get('label_fr') != fr_label
        or entry.get('source_title_en') != new_src
        or entry.get('aliases') != new_aliases
    )
    if changed:
        entry['label_fr'] = fr_label
        entry['source_title_en'] = new_src
        entry['aliases'] = new_aliases
    return changed


def patch_concept(concept, fr_label, extra_aliases, mot_en):
    if concept.get('label', '') == fr_label:
        return False
    concept['label'] = fr_label
    dt = concept.get('display_titles', {}) or {}
    dt['primary'] = fr_label
    dt['secondary'] = mot_en if mot_en != fr_label else ''
    dt['strategy'] = 'french_first' if mot_en != fr_label else 'french_only'
    concept['display_titles'] = dt

    pf = concept.get('public_forms', {}) or {}
    pf['french_reference'] = fr_label
    en_labels = list(pf.get('english_labels', []) or [])
    if mot_en and mot_en not in en_labels:
        en_labels.append(mot_en)
    pf['english_labels'] = en_labels
    concept['public_forms'] = pf

    aliases = list(concept.get('aliases', []) or [])
    for cand in [fr_label] + list(extra_aliases) + [mot_en]:
        if cand and cand not in aliases:
            aliases.append(cand)
    concept['aliases'] = aliases
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'Mode : {mode}')
    print()

    if args.apply and not check_backup():
        print("ERREUR : backup manquant")
        sys.exit(1)

    with open(FILTERED_JSON, encoding='utf-8') as f:
        doc = json.load(f)
    real = doc['real']

    # Build lookup : mot → spec in map
    mapped = []
    skipped_not_in_map = []
    skipped_proper = []
    for s in real:
        mot = s['mot']
        if mot in SKIP_PROPER_NOUNS:
            skipped_proper.append(s)
            continue
        if mot not in MAP:
            skipped_not_in_map.append(s)
            continue
        fr, aliases = MAP[mot]
        mapped.append({**s, 'fr': fr, 'aliases': aliases})

    print(f'Input real          : {len(real)}')
    print(f'Skipped proper      : {len(skipped_proper)}')
    print(f'Skipped not in map  : {len(skipped_not_in_map)}')
    print(f'Mapped              : {len(mapped)}')
    print()
    if skipped_not_in_map:
        print('=== MOTS NON MAPPÉS ===')
        for s in skipped_not_in_map:
            print(f"  {s['mot']:25s} [{s['entry_id']}]  {s['def_preview'][:80]}")
        print()

    # Load concepts + meta
    with open(CONCEPTS_JSON, encoding='utf-8') as f:
        concepts = json.load(f)
    with open(CONCEPT_META_JSON, encoding='utf-8') as f:
        meta = json.load(f)

    # Group by chunk
    by_chunk = {}
    for m in mapped:
        by_chunk.setdefault(m['chunk'], []).append(m)

    chunk_patches_count = 0
    chunks_data = {}
    for chunk_name in sorted(by_chunk.keys()):
        chunk_path = ISBE_DIR / chunk_name
        with open(chunk_path, encoding='utf-8-sig') as f:
            entries = json.load(f)
        by_id = {e['id']: e for e in entries}
        local_changed = 0
        for m in by_chunk[chunk_name]:
            entry = by_id.get(m['entry_id'])
            if not entry:
                continue
            changed = patch_chunk_entry(entry, m['fr'], m['aliases'], m['mot'])
            if changed:
                local_changed += 1
        if local_changed:
            chunks_data[chunk_name] = entries
            chunk_patches_count += local_changed

    concept_changes = []
    for m in mapped:
        cid = m['concept_id']
        c = next((c for c in concepts if c['concept_id'] == cid), None)
        if not c:
            continue
        before_label = c.get('label', '')
        if patch_concept(c, m['fr'], m['aliases'], m['mot']):
            concept_changes.append((cid, before_label, m['fr']))
            if cid in meta:
                meta[cid]['l'] = m['fr']
                meta[cid]['p'] = m['fr']
                meta[cid]['s'] = m['mot']

    print(f'Chunks entries modifiées : {chunk_patches_count}')
    print(f'Chunks files à écrire    : {len(chunks_data)}')
    print(f'Concepts patchés         : {len(concept_changes)}')

    # Write MD preview
    lines = [f'# C8 Dry-run — {len(mapped)} translations', '']
    lines.append('| mot EN | label_fr | aliases |')
    lines.append('|---|---|---|')
    for m in mapped:
        al = ', '.join(m['aliases']) if m['aliases'] else '—'
        lines.append(f"| {m['mot']} | **{m['fr']}** | {al} |")
    with open(DRY_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    if args.apply:
        print()
        print('=== ÉCRITURE ===')
        for chunk_name, entries in chunks_data.items():
            payload = json.dumps(entries, ensure_ascii=False, separators=(', ', ': '))
            with open(ISBE_DIR / chunk_name, 'w', encoding='utf-8-sig') as f:
                f.write(payload)
            print(f'  ✓ {chunk_name}')
        with open(CONCEPTS_JSON, 'w', encoding='utf-8') as f:
            json.dump(concepts, f, ensure_ascii=False, indent=2)
        print('  ✓ concepts.json')
        with open(CONCEPT_META_JSON, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))
        print('  ✓ concept-meta.json')

        log = {
            'applied_at': datetime.now().isoformat(),
            'pass': 'C8-category-A',
            'mapped_count': len(mapped),
            'chunk_entries_modified': chunk_patches_count,
            'concepts_patched': len(concept_changes),
            'chunks_written': sorted(chunks_data.keys()),
            'concept_changes': [
                {'cid': c[0], 'old': c[1], 'new': c[2]} for c in concept_changes
            ],
        }
        with open(LOG_JSON, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        print(f'Log : {LOG_JSON}')


if __name__ == '__main__':
    main()
