#!/usr/bin/env python3
"""
Corrige les 195 residus anglais dans le champ 'mot' de easton.entries.json.
- 190 residus certains (categorie A)
- 5 residus quasi-identiques (categorie C: Archangel, Chameleon, Legion, Revelation, Sanctuary)
"""

import json
import shutil
import os
from datetime import datetime

INPUT = "uploads/dictionnaires/easton/easton.entries.json"
BACKUP = "uploads/dictionnaires/easton/easton.entries.backup_before_mot_residues.json"
REPORT = "reports/easton_mot_english_residues_correction_report.json"

# ── Mapping: id -> new French mot ──────────────────────────────────────────

CORRECTIONS = {
    # ── Categorie A: 190 residus certains ──
    "easton-000050": "Rebuts",
    "easton-000080": "Adam, un type",
    "easton-000171": "Algoum",
    "easton-000182": "Almoug",
    "easton-000257": "Singe",
    "easton-000365": "Cohorte d'Auguste",
    "easton-000371": "Hache",
    "easton-000414": "Rechute",
    "easton-000471": "Bain",
    "easton-000479": "Baie",
    "easton-000482": "Signal",
    "easton-000487": "Ours",
    "easton-000609": "Sueur de sang",
    "easton-000638": "Bracelet",
    "easton-000639": "Ronce",
    "easton-000650": "Bride",
    "easton-000678": "Cabines",
    "easton-000701": "Cypre",
    "easton-000710": "Roseau aromatique",
    "easton-000729": "Chariot",
    "easton-000736": "Forteresse",
    "easton-000756": "Chaine",
    "easton-000763": "Chambellan",
    "easton-000768": "Chancelier",
    "easton-000778": "Enchanteur",
    "easton-000801": "Grand sacrificateur",
    "easton-000837": "Citoyennete",
    "easton-000854": "Basilic",
    "easton-000856": "Ivraie",
    "easton-000878": "Daman",
    "easton-000959": "Maison de Dagon",
    "easton-001016": "Gouverneur",
    "easton-001088": "Dulcimer",
    "easton-001120": "Ebene",
    "easton-001264": "Eunuque ethiopien",
    "easton-001281": "Exercice corporel",
    "easton-001285": "Exorciste",
    "easton-001300": "Beaux Ports",
    "easton-001311": "Liard",
    "easton-001322": "Villes fortifiees",
    "easton-001325": "Fetes religieuses",
    "easton-001349": "Jonc",
    "easton-001395": "Plenitude",
    "easton-001419": "Fiel",
    "easton-001435": "Garnison",
    "easton-001482": "Vautour",
    "easton-001484": "Dons spirituels",
    "easton-001520": "Veau d'or",
    "easton-001529": "Gopher",
    "easton-001548": "Gravure",
    "easton-001596": "Salle",
    "easton-001645": "Harnais",
    "easton-001650": "Herse",
    "easton-001652": "Cerf",
    "easton-001673": "Haine",
    "easton-001676": "Havre",
    "easton-001680": "Foin",
    "easton-001702": "Bruyere",
    "easton-001703": "Paien",
    "easton-001705": "Offrande par elevation",
    "easton-001715": "Heritier",
    "easton-001782": "Grand pretre",
    "easton-001783": "Grand chemin",
    "easton-001788": "Biche",
    "easton-001835": "Armee",
    "easton-001840": "Maison",
    "easton-001850": "Laboureur",
    "easton-001854": "Hypocrite",
    "easton-001882": "Ecritoire",
    "easton-001883": "Auberge",
    "easton-001911": "Cohorte italienne",
    "easton-001918": "Ivoire",
    "easton-001981": "Jaspe",
    "easton-001988": "Offrande de jalousie",
    "easton-002117": "Iota",
    "easton-002128": "Juda au-dela du Jourdain",
    "easton-002135": "Pretoire",
    "easton-002136": "Tribunal",
    "easton-002195": "Parent",
    "easton-002210": "Milan",
    "easton-002215": "Petrin",
    "easton-002216": "Couteau",
    "easton-002218": "Pommeau",
    "easton-002229": "Echelle",
    "easton-002245": "Courroie",
    "easton-002251": "Docteur de la loi",
    "easton-002258": "Cuir",
    "easton-002265": "Main gauche",
    "easton-002266": "Gaucher",
    "easton-002273": "Lettre",
    "easton-002282": "Libertin",
    "easton-002288": "Lieutenant",
    "easton-002289": "Vie",
    "easton-002291": "Eclair",
    "easton-002294": "Lis",
    "easton-002367": "Magistrat",
    "easton-002407": "Meurtrier",
    "easton-002408": "Manteau",
    "easton-002415": "Marbre",
    "easton-002446": "Pioche",
    "easton-002447": "Massue",
    "easton-002454": "Offrande de gateau",
    "easton-002461": "Mediateur",
    "easton-002476": "Melons",
    "easton-002494": "Misericorde",
    "easton-002538": "Sage-femme",
    "easton-002559": "Menestrel",
    "easton-002572": "Obole",
    "easton-002575": "Mitre",
    "easton-002586": "Stele de Mesha",
    "easton-002588": "Taupe",
    "easton-002599": "Mortier",
    "easton-002614": "Souris",
    "easton-002619": "Murier",
    "easton-002621": "Meurtre",
    "easton-002622": "Murmure",
    "easton-002632": "Myrrhe",
    "easton-002662": "Nudite",
    "easton-002716": "Ortie",
    "easton-002729": "Engoulevent",
    "easton-002738": "Nitre",
    "easton-002750": "Pays du nord",
    "easton-002769": "Offense",
    "easton-002808": "Orfraie",
    "easton-002817": "Aiguillon a boeufs",
    "easton-002833": "Paralysie",
    "easton-002843": "Paradis",
    "easton-002873": "Pavillon",
    "easton-002874": "Sacrifices de paix",
    "easton-002948": "Medecin",
    "easton-002967": "Cruche",
    "easton-002976": "Poesie",
    "easton-002989": "Courrier",
    "easton-003009": "Proselyte",
    "easton-003017": "Publicain",
    "easton-003022": "Legumes",
    "easton-003061": "Belier",
    "easton-003076": "Rasoir",
    "easton-003087": "Roseau",
    "easton-003130": "Enigme",
    "easton-003147": "Vol",
    "easton-003149": "Chevreuil",
    "easton-003155": "Rose",
    "easton-003159": "Attaches du gouvernail",
    "easton-003164": "Jonc",
    "easton-003167": "Seigle",
    "easton-003180": "Sadduceens",
    "easton-003223": "Pierre de sardoine",
    "easton-003232": "Bouc emissaire",
    "easton-003279": "Sepulcre",
    "easton-003290": "Serviteur",
    "easton-003322": "Maison de tonte",
    "easton-003409": "Sanctuaires d'argent",
    "easton-003446": "Sacrifice pour le peche",
    "easton-003461": "Forgeron",
    "easton-003464": "Piege",
    "easton-003475": "Portique de Salomon",
    "easton-003476": "Cantiques",
    "easton-003487": "Souverainete",
    "easton-003491": "Aromates",
    "easton-003494": "Nard",
    "easton-003497": "Eponge",
    "easton-003504": "Etoiles",
    "easton-003515": "Cigogne",
    "easton-003516": "Filtrer",
    "easton-003531": "Caution",
    "easton-003536": "Cygne",
    "easton-003538": "Pourceau",
    "easton-003541": "Sycomore",
    "easton-003586": "Ivraie",
    "easton-003587": "Cible",
    "easton-003640": "Chardon",
    "easton-003642": "Epine",
    "easton-003671": "Etain",
    "easton-003672": "Ornements tintinnabulants",
    "easton-003705": "Tourment",
    "easton-003714": "Villes de reserve",
    "easton-003715": "Maisons de tresor",
    "easton-003716": "Tresor",
    "easton-003722": "Tribut",
    "easton-003733": "Tourterelle",
    "easton-003742": "Onction",
    "easton-003762": "Vagabond",
    "easton-003781": "Chariot",
    "easton-003784": "Errance",
    "easton-003807": "Roue",
    "easton-003812": "Saules",
    "easton-003814": "Fenetre",
    "easton-003817": "Cuve a vin",
    "easton-003879": "Zele",

    # ── Categorie C: 5 quasi-identiques ──
    "easton-000289": "Archange",
    "easton-000764": "Cameleon",
    "easton-002267": "Legion",
    "easton-003119": "Revelation",
    "easton-003213": "Sanctuaire",
}


def main():
    # 1. Lire le fichier
    with open(INPUT, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 2. Backup
    shutil.copy2(INPUT, BACKUP)
    print(f"Backup cree: {BACKUP}")

    # 3. Appliquer les corrections
    lookup = {e["id"]: e for e in data}
    applied = []
    missing = []

    for eid, new_mot in CORRECTIONS.items():
        if eid in lookup:
            old_mot = lookup[eid]["mot"]
            if old_mot != new_mot:
                lookup[eid]["mot"] = new_mot
                applied.append({
                    "id": eid,
                    "old_mot": old_mot,
                    "new_mot": new_mot,
                })
            else:
                # Already correct
                pass
        else:
            missing.append(eid)

    # 4. Ecrire le fichier corrige
    with open(INPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Corrections appliquees: {len(applied)}")
    print(f"IDs manquants: {len(missing)}")

    # 5. Rapport
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    report = {
        "date": datetime.now().isoformat(),
        "source_file": INPUT,
        "backup_file": BACKUP,
        "total_corrections_planned": len(CORRECTIONS),
        "corrections_applied": len(applied),
        "ids_missing": missing,
        "details": applied,
    }
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Rapport: {REPORT}")

    # 6. Resume
    print(f"\n=== Resume ===")
    print(f"Entrees modifiees: {len(applied)} / {len(CORRECTIONS)}")
    if missing:
        print(f"IDs non trouves: {missing}")
    print("Termine.")


if __name__ == "__main__":
    main()
