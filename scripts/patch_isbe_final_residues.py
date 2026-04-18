#!/usr/bin/env python3
"""
Patch final des résidus anglais ISBE — Phases 1+2+3.

Phase 1: 168 labels mixtes FR/EN cassés (Body de Mort, Breach de Alliance...)
Phase 2: 128 anglais communs composés (Axle-Tree, Bald Locust, Born Again...)
Phase 3: ~400-500 anglais dans les 1144 ambigus (Ability, Abject, Access...)

Stratégie :
- Chunks ISBE : label_fr + aliases (mot inchangé)
- concepts.json : label + display_titles + public_forms + aliases
- concept-meta.json : l, p, s
- UTF-8 sans BOM pour concepts/meta

Modes : dry-run (default) ou --apply
"""
import json
import sys
import re
import argparse
import glob
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
LOG_JSON = AUDIT_DIR / "isbe-final-residues-log.json"

# ══════════════════════════════════════════════════════════════════
# PHASE 1 : Traduction des patterns mixtes FR/EN cassés
# ══════════════════════════════════════════════════════════════════
# Règles de remplacement pour les mots EN résiduels dans labels FR
WORD_REPLACEMENTS = {
    # Noms communs EN → FR
    'Body': 'Corps', 'Bands': 'Liens', 'Bill': 'Acte', 'Breach': 'Rupture',
    'Break': 'Aube', 'Breastplate': 'Pectoral', 'Brethren': 'Frères',
    'Calves': 'Veaux', 'Chambers': 'Chambres', 'Change': 'Vêtement de rechange',
    'Chariots': 'Chars', 'Children': 'Enfants', 'Church': 'Église',
    'Churches': 'Églises', 'Cities': 'Villes', 'City': 'Ville',
    'Cloud': 'Nuée', 'Coat': 'Tunique', 'Colors': 'Couleurs',
    'Coming': 'Venue', 'Commandments': 'Commandements', 'Corner': 'Angle',
    'Court': 'Parvis', 'Covenant': 'Alliance', 'Cross': 'Croix',
    'Crown': 'Couronne', 'Cup': 'Coupe', 'Darkness': 'Ténèbres',
    'Day': 'Jour', 'Days': 'Jours', 'Dead': 'Mort', 'Death': 'Mort',
    'Divorcement': 'Divorce', 'Door': 'Porte', 'Dream': 'Songe',
    'Dust': 'Poussière', 'Earth': 'Terre', 'East': 'Orient',
    'Face': 'Face', 'Father': 'Père', 'Fathers': 'Pères',
    'Feast': 'Fête', 'Field': 'Champ', 'Fire': 'Feu',
    'First': 'Premier', 'Flesh': 'Chair', 'Food': 'Nourriture',
    'Fruit': 'Fruit', 'Fruits': 'Fruits', 'Garden': 'Jardin',
    'Gate': 'Porte', 'Gates': 'Portes', 'Generation': 'Génération',
    'Gift': 'Don', 'Glory': 'Gloire', 'God': 'Elohîm',
    'Gold': 'Or', 'Good': 'Bon', 'Gospel': 'Évangile',
    'Government': 'Gouvernement', 'Grace': 'Grâce',
    'Great': 'Grand', 'Green': 'Vert',
    'Ground': 'Sol', 'Guilt': 'Culpabilité',
    'Hand': 'Main', 'Head': 'Tête', 'Heart': 'Cœur',
    'Heaven': 'Ciel', 'High': 'Haut', 'Hills': 'Collines',
    'Holy': 'Saint', 'Host': 'Armée', 'House': 'Maison',
    'Imagery': 'Idolâtrie', 'Iron': 'Fer',
    'Jubilees': 'Jubilés', 'Judgment': 'Jugement',
    'King': 'Roi', 'Kingdom': 'Royaume', 'Knowledge': 'Connaissance',
    'Lamb': 'Agneau', 'Law': 'Loi', 'Laws': 'Lois',
    'Life': 'Vie', 'Light': 'Lumière', 'Lips': 'Lèvres',
    'Lord': 'Seigneur', 'Love': 'Amour',
    'Man': 'Homme', 'Many': 'Nombreux', 'Men': 'Hommes',
    'Mercy': 'Miséricorde', 'Mind': 'Esprit',
    'Moon': 'Lune', 'Most': 'Très', 'Mountain': 'Montagne',
    'Mountains': 'Montagnes', 'Mouth': 'Bouche',
    'Name': 'Nom', 'Night': 'Nuit', 'Nose': 'Nez',
    'Offering': 'Offrande', 'Old': 'Ancien',
    'Peace': 'Paix', 'People': 'Peuple',
    'Place': 'Lieu', 'Plain': 'Plaine', 'Poor': 'Pauvre',
    'Prey': 'Proie', 'Priest': 'Prêtre', 'Prince': 'Prince',
    'Prison': 'Prison', 'Promise': 'Promesse', 'Prophet': 'Prophète',
    'Raiment': 'Vêtement', 'Remembrance': 'Souvenir',
    'Right': 'Droite', 'Ritual': 'Rituel', 'River': 'Fleuve',
    'Rock': 'Rocher', 'Rod': 'Verge', 'Rudder': 'Gouvernail',
    'Sacrifice': 'Sacrifice', 'Sanctuary': 'Sanctuaire',
    'Sea': 'Mer', 'Seed': 'Semence', 'Seven': 'Sept',
    'Sin': 'Péché', 'Sins': 'Péchés', 'Son': 'Fils',
    'Sons': 'Fils', 'Soul': 'Âme', 'Spirit': 'Esprit',
    'Star': 'Étoile', 'Stone': 'Pierre', 'Stones': 'Pierres',
    'Sun': 'Soleil', 'Sword': 'Épée', 'Tabernacle': 'Tabernacle',
    'Temple': 'Temple', 'Ten': 'Dix', 'Throne': 'Trône',
    'Time': 'Temps', 'Times': 'Temps', 'Tongue': 'Langue',
    'Tree': 'Arbre', 'Trust': 'Confiance', 'Truth': 'Vérité',
    'Twelve': 'Douze', 'Two': 'Deux',
    'Unclean': 'Impur', 'Unleavened': 'Sans levain',
    'Valley': 'Vallée', 'Vine': 'Vigne',
    'War': 'Guerre', 'Water': 'Eau', 'Waters': 'Eaux',
    'Way': 'Chemin', 'Wheat': 'Blé', 'Wicked': 'Méchant',
    'Wine': 'Vin', 'Wisdom': 'Sagesse', 'Witness': 'Témoin',
    'Woman': 'Femme', 'Word': 'Parole', 'Words': 'Paroles',
    'World': 'Monde', 'Wrath': 'Colère',
}

# Full label overrides for specific concepts (Phase 1 + 2)
LABEL_OVERRIDES = {
    # Phase 1 : Mixtes cassés
    'bands-of-rudder': 'Attaches du gouvernail',
    'bill-of-divorcement': "Acte de divorce",
    'body-of-death': 'Corps de la mort',
    'body-of-heaven': 'Corps du ciel',
    'book-of-remembrance': 'Livre du souvenir',
    'breach-of-covenant': "Rupture d'alliance",
    'breach-of-ritual': 'Rupture de rituel',
    'breach-of-trust': 'Abus de confiance',
    'break-of-day': 'Aube',
    'breastplate-of-the-high-priest': 'Pectoral du Grand Prêtre',
    'brethren-of-the-lord': 'Frères du Seigneur',
    'calves-of-the-lips': 'Veaux des lèvres',
    'chambers-of-imagery': "Chambres de l'idolâtrie",
    'change-of-raiment': 'Vêtement de rechange',
    'chariots-of-the-sun': 'Chars du Soleil',
    'children-of-eden': "Enfants d'Éden",
    'children-of-the-east': "Fils de l'Orient",
    'coat-of-many-colors': 'Tunique de plusieurs couleurs',
    'coming-second': 'Seconde Venue',
    'day-of-atonement': "Jour de l'Expiation",
    'day-of-the-lord': 'Jour de YHWH',
    'days-last': 'Derniers Jours',
    'door-of-hope': "Porte de l'espérance",
    'east-country': "Pays de l'Orient",
    'evil-one': 'Le Malin',
    'evil-spirit': 'Esprit mauvais',
    'field-of-blood': 'Champ du sang',
    'fruit-of-the-spirit': "Fruit de l'Esprit",
    'garden-of-eden': "Jardin d'Éden",
    'gate-of-heaven': 'Porte du Ciel',
    'gift-of-tongues': 'Don des langues',
    'glory-of-god': "Gloire d'Elohîm",
    'gospel-of-peter': 'Évangile de Pierre',
    'house-of-god': "Maison d'Elohîm",
    'house-of-prayer': 'Maison de prière',
    'king-of-kings': 'Roi des rois',
    'kingdom-of-god': "Royaume d'Elohîm",
    'kingdom-of-heaven': 'Royaume des cieux',
    'lamb-of-god': "Agneau d'Elohîm",
    'last-days': 'Derniers Jours',
    'latter-days': 'Derniers Jours',
    'man-of-god': "Homme d'Elohîm",
    'man-of-sin': 'Homme du péché',
    'mouth-of-god': "Bouche d'Elohîm",
    'name-of-god': "Nom d'Elohîm",
    'night-watch': 'Veille de nuit',
    'peace-of-god': "Paix d'Elohîm",
    'promise-of-the-father': 'Promesse du Père',
    'rod-of-iron': 'Verge de fer',
    'rod-of-moses': 'Verge de Moïse',
    'seal-of-god': "Sceau d'Elohîm",
    'seed-of-david': 'Semence de David',
    'servant-of-god': "Serviteur d'Elohîm",
    'son-of-god': "Fils d'Elohîm",
    'son-of-man': "Fils de l'homme",
    'sons-of-god': "Fils d'Elohîm",
    'sons-of-the-prophets': 'Fils des prophètes',
    'spirit-of-god': "Esprit d'Elohîm",
    'spirit-of-man': "Esprit de l'homme",
    'star-of-the-magi': "Étoile des Mages",
    'sword-of-the-spirit': "Épée de l'Esprit",
    'throne-of-god': "Trône d'Elohîm",
    'tree-of-knowledge': 'Arbre de la connaissance',
    'tree-of-life': 'Arbre de vie',
    'valley-of-dry-bones': 'Vallée des ossements',
    'valley-of-salt': 'Vallée du sel',
    'voice-of-god': "Voix d'Elohîm",
    'wrath-of-god': "Colère d'Elohîm",
    'word-of-god': "Parole d'Elohîm",
    'word-of-the-lord': 'Parole du Seigneur',

    # Phase 2 : Anglais communs composés
    'axle-tree': "Essieu",
    'bald-locust': 'Criquet chauve',
    'beast-fight': 'Combat de bêtes',
    'beauty-and-bands': 'Beauté et Liens',
    'bind-bound': 'Lier ; Lié',
    'birth-stool': "Siège d'accouchement",
    'bloody-flux': 'Dysenterie',
    'body-guard': 'Garde du corps',
    'born-again': 'Né de nouveau',
    'broad-place': 'Place large',
    'caesar-s-household': 'Maison de César',
    'chief-friends-good-men': 'Premiers amis ; Hommes de bien',
    'chief-musician': 'Chef de musique',
    'chief-seats': 'Premiers sièges',
    'counter-charm': 'Contre-charme',
    'covered-way': 'Chemin couvert',
    'covering-for-the-head': 'Voile pour la tête',
    'dead-body': 'Corps mort',
    'deep-sleep': 'Sommeil profond',
    'encampment-by-the-red-sea': 'Campement près de la mer Rouge',
    'evil-eye': 'Mauvais œil',
    'evil-merodach': 'Évil-Mérodach',
    'fenced-city': 'Ville fortifiée',
    'first-begotten': 'Premier-né',
    'first-born': 'Premier-né',
    'first-fruits': 'Prémices',
    'full-grown': 'Adulte',
    'good-will': 'Bonne volonté',
    'great-owl': 'Grand hibou',
    'half-shekel': 'Demi-sicle',
    'hand-breadth': 'Largeur de main',
    'hard-hearted': 'Au cœur dur',
    'high-minded': 'Orgueilleux',
    'high-place': 'Haut lieu',
    'high-places': 'Hauts lieux',
    'hired-servant': 'Serviteur à gages',
    'holy-ghost': 'Saint-Esprit',
    'holy-land': 'Terre Sainte',
    'holy-one': 'Saint',
    'holy-spirit': 'Saint-Esprit',
    'horned-owl': 'Hibou à aigrettes',
    'ill-will': 'Mauvaise volonté',
    'inner-man': 'Homme intérieur',
    'joint-heir': 'Cohéritier',
    'judge-made-law': 'Droit jurisprudentiel',
    'just-man': 'Homme juste',
    'king-s-garden': 'Jardin du roi',
    'king-s-highway': "Route du roi",
    'king-s-pool': 'Étang du roi',
    'last-supper': 'Dernière Cène',
    'latter-rain': 'Pluie tardive',
    'lay-hands-on': 'Imposer les mains',
    'left-handed': 'Gaucher',
    'lord-s-day': 'Jour du Seigneur',
    'lord-s-supper-eucharist': 'Sainte Cène (Eucharistie)',
    'meat-offering': 'Oblation',
    'most-high': 'Très-Haut',
    'most-holy-place': 'Lieu très saint',
    'new-moon': 'Nouvelle lune',
    'old-gate': 'Porte ancienne',
    'old-prophet-the': 'Le vieux prophète',
    'olive-tree': 'Olivier',
    'outer-man': 'Homme extérieur',
    'over-against': 'En face de',
    'palm-tree': 'Palmier',
    'piece-of-money': 'Pièce de monnaie',
    'right-hand': 'Main droite',
    'ring-streaked': 'Rayé',
    'scape-goat': 'Bouc émissaire',
    'sea-monster': 'Monstre marin',
    'set-apart': 'Mis à part',
    'sin-offering': 'Sacrifice pour le péché',
    'strong-drink': 'Boisson enivrante',
    'sun-dial': 'Cadran solaire',
    'swift-beasts': 'Bêtes rapides',
    'table-land': 'Plateau',
    'thank-offering': "Sacrifice d'actions de grâces",
    'trespass-offering': 'Sacrifice de culpabilité',
    'wave-offering': "Offrande de tournoiement",
    'well-beloved': 'Bien-aimé',
    'whole-burnt-offering': 'Holocauste complet',
    'wild-goat': 'Bouquetin',
    'wild-ox': 'Buffle sauvage',
    'wine-press': 'Pressoir',
    'wise-man': 'Sage',
    'witness-of-the-spirit': "Témoignage de l'Esprit",
}

# Phase 3 : Mots anglais certains dans les ambigus
ENGLISH_WORDS_TRANSLATIONS = {
    'Ability': 'Capacité', 'Abject': 'Abject', 'Abode': 'Demeure',
    'Abstinence': 'Abstinence', 'Abundance': 'Abondance', 'Abuse': 'Abus',
    'Acceptance': 'Acceptation', 'Access': 'Accès',
    'Accountability': 'Responsabilité', 'Acknowledge': 'Reconnaître',
    'Acrostic': 'Acrostiche', 'Addict': 'S\'adonner', 'Admonish': 'Avertir',
    'Adorn': 'Orner', 'Advantage': 'Avantage', 'Adventure': 'Aventure',
    'Adversary': 'Adversaire', 'Advocate': 'Avocat', 'Afflict': 'Affliger',
    'Afford': 'Fournir', 'Agree': 'S\'accorder', 'Allegory': 'Allégorie',
    'Allow': 'Permettre', 'Allure': 'Séduire', 'Ambassador': 'Ambassadeur',
    'Ambush': 'Embuscade', 'Anathema': 'Anathème', 'Ancle': 'Cheville',
    'Announce': 'Annoncer', 'Antichrist': 'Antichrist', 'Ape': 'Singe',
    'Appeal': 'Appel', 'Approach': 'Approcher', 'Archer': 'Archer',
    'Arise': 'Se lever', 'Armlet': 'Bracelet', 'Array': 'Disposition',
    'Ascend': 'Monter', 'Ashamed': 'Honteux', 'Assault': 'Assaut',
    'Assent': 'Consentement', 'Assign': 'Assigner', 'Astonish': 'Étonner',
    'Astray': 'Égaré', 'Athlete': 'Athlète', 'Atonement': 'Expiation',
    'Attain': 'Atteindre', 'Attire': 'Parure', 'Avenge': 'Venger',
    'Avenger': 'Vengeur', 'Avoid': 'Éviter', 'Awl': 'Alêne',
    'Backslide': 'Rétrograde', 'Bald': 'Chauve', 'Balm': 'Baume',
    'Band': 'Bande', 'Banquet': 'Banquet', 'Bargain': 'Marché',
    'Barren': 'Stérile', 'Bastard': 'Bâtard', 'Beacon': 'Signal',
    'Beam': 'Poutre', 'Bed': 'Lit', 'Beetle': 'Scarabée',
    'Beget': 'Engendrer', 'Behave': 'Se comporter', 'Behold': 'Voici',
    'Believe': 'Croire', 'Below': 'En dessous', 'Bend': 'Courber',
    'Beseech': 'Supplier', 'Bestow': 'Accorder', 'Betroth': 'Fiancer',
    'Bewitch': 'Ensorceler', 'Bind': 'Lier', 'Birthright': 'Droit d\'aînesse',
    'Bishop': 'Évêque', 'Blame': 'Blâme', 'Blasphemy': 'Blasphème',
    'Blaze': 'Flamme', 'Blemish': 'Défaut', 'Blood': 'Sang',
    'Bloom': 'Fleur', 'Boast': 'Se glorifier', 'Bondage': 'Servitude',
    'Booth': 'Cabane', 'Booty': 'Butin', 'Borrow': 'Emprunter',
    'Bow': 'Arc', 'Bowels': 'Entrailles', 'Bramble': 'Ronce',
    'Bribe': 'Pot-de-vin', 'Bride': 'Fiancée', 'Bridegroom': 'Fiancé',
    'Bridle': 'Bride', 'Brimstone': 'Soufre', 'Bronze': 'Bronze',
    'Brood': 'Couvée', 'Bruise': 'Meurtrissure', 'Build': 'Bâtir',
    'Bullock': 'Taureau', 'Bunch': 'Grappe', 'Burden': 'Fardeau',
    'Burn': 'Brûler', 'Burst': 'Éclater', 'Bury': 'Ensevelir',
    'Busy': 'Occupé', 'Cage': 'Cage', 'Cake': 'Gâteau',
    'Captain': 'Capitaine', 'Captive': 'Captif', 'Captivity': 'Captivité',
    'Carcase': 'Carcasse', 'Carpenter': 'Charpentier', 'Cart': 'Chariot',
    'Cast': 'Jeter', 'Cattle': 'Bétail', 'Cave': 'Caverne',
    'Cease': 'Cesser', 'Chain': 'Chaîne', 'Chamber': 'Chambre',
    'Champion': 'Champion', 'Charge': 'Charge', 'Chariot': 'Char',
    'Chaste': 'Chaste', 'Cheek': 'Joue', 'Child': 'Enfant',
    'Choose': 'Choisir', 'Circumcise': 'Circoncire', 'Citizen': 'Citoyen',
    'Claim': 'Réclamer', 'Clay': 'Argile', 'Cleanse': 'Purifier',
    'Cleave': 'Attacher', 'Cliff': 'Falaise', 'Climb': 'Grimper',
    'Cloak': 'Manteau', 'Cloud': 'Nuée', 'Coal': 'Charbon',
    'Coast': 'Côte', 'Coat': 'Tunique', 'Coffin': 'Cercueil',
    'Coin': 'Pièce', 'Cold': 'Froid', 'Colony': 'Colonie',
    'Color': 'Couleur', 'Colt': 'Ânon', 'Comfort': 'Consolation',
    'Command': 'Commander', 'Commit': 'Commettre', 'Common': 'Commun',
    'Companion': 'Compagnon', 'Compare': 'Comparer', 'Compel': 'Contraindre',
    'Conceal': 'Cacher', 'Conceit': 'Vanité', 'Condemn': 'Condamner',
    'Confess': 'Confesser', 'Confine': 'Confiner', 'Confirm': 'Confirmer',
    'Confuse': 'Confondre', 'Conquer': 'Vaincre', 'Consent': 'Consentir',
    'Consume': 'Consumer', 'Contain': 'Contenir', 'Contempt': 'Mépris',
    'Contend': 'Contester', 'Content': 'Contentement', 'Convert': 'Convertir',
    'Convince': 'Convaincre', 'Corn': 'Blé', 'Corrupt': 'Corrompre',
    'Cottage': 'Chaumière', 'Counsel': 'Conseil', 'Court': 'Cour',
    'Covet': 'Convoiter', 'Craft': 'Métier', 'Create': 'Créer',
    'Creature': 'Créature', 'Creep': 'Ramper', 'Cross': 'Croix',
    'Crouch': 'Se baisser', 'Crown': 'Couronne', 'Cruel': 'Cruel',
    'Crush': 'Écraser', 'Curse': 'Malédiction', 'Custom': 'Coutume',
    'Dainty': 'Mets délicats', 'Dale': 'Vallée', 'Dark': 'Obscur',
    'Dawn': 'Aurore', 'Daysman': 'Arbitre', 'Dayspring': 'Aurore',
    'Deaf': 'Sourd', 'Deal': 'Traiter', 'Dearth': 'Disette',
    'Debtor': 'Débiteur', 'Deceive': 'Tromper', 'Deck': 'Parer',
    'Declare': 'Déclarer', 'Decline': 'Décliner', 'Decree': 'Décret',
    'Deed': 'Action', 'Defame': 'Diffamer', 'Defeat': 'Défaite',
    'Defile': 'Souiller', 'Defraud': 'Frauder', 'Defy': 'Défier',
    'Delay': 'Délai', 'Delight': 'Délice', 'Deliver': 'Délivrer',
    'Demand': 'Demander', 'Deny': 'Nier', 'Depart': 'Partir',
    'Depth': 'Profondeur', 'Desire': 'Désir', 'Despise': 'Mépriser',
    'Destitute': 'Démuni', 'Destroy': 'Détruire', 'Detain': 'Retenir',
    'Devise': 'Concevoir', 'Devote': 'Consacrer', 'Devour': 'Dévorer',
    'Dim': 'Obscur', 'Disciple': 'Disciple', 'Disclose': 'Révéler',
    'Discord': 'Discorde', 'Discourse': 'Discours', 'Disease': 'Maladie',
    'Disgrace': 'Disgrâce', 'Dish': 'Plat', 'Dismiss': 'Renvoyer',
    'Display': 'Déployer', 'Displease': 'Déplaire', 'Dispose': 'Disposer',
    'Dispute': 'Dispute', 'Divers': 'Divers', 'Divide': 'Diviser',
    'Doom': 'Condamnation', 'Dowry': 'Dot', 'Drag': 'Traîner',
    'Draw': 'Tirer', 'Dread': 'Terreur', 'Dregs': 'Lie',
    'Dress': 'Vêtir', 'Drink': 'Boisson', 'Drive': 'Chasser',
    'Drop': 'Goutte', 'Dross': 'Scories', 'Drought': 'Sécheresse',
    'Drown': 'Noyer', 'Drunk': 'Ivre', 'Dry': 'Sec',
    'Dung': 'Fumier', 'Dungeon': 'Cachot', 'Dust': 'Poussière',
    'Dwell': 'Habiter', 'Dye': 'Teinture',
    'Earnest': 'Arrhes', 'Earthquake': 'Tremblement de terre',
    'Eat': 'Manger', 'Edge': 'Tranchant', 'Edict': 'Édit',
    'Effort': 'Effort', 'Elect': 'Élu', 'Embrace': 'Embrasser',
    'Emerald': 'Émeraude', 'Eminent': 'Éminent',
    'Empire': 'Empire', 'Employ': 'Employer', 'Empty': 'Vide',
    'Enchant': 'Enchanter', 'Endow': 'Doter', 'Endure': 'Endurer',
    'Enemy': 'Ennemi', 'Engrave': 'Graver', 'Enjoy': 'Jouir',
    'Enlarge': 'Élargir', 'Ensign': 'Étendard', 'Enter': 'Entrer',
    'Entreat': 'Supplier', 'Envy': 'Envie', 'Equal': 'Égal',
    'Equity': 'Équité', 'Escape': 'Échapper', 'Estate': 'État',
    'Esteem': 'Estime', 'Eternal': 'Éternel', 'Eunuch': 'Eunuque',
    'Evil': 'Mal', 'Exact': 'Exiger', 'Exalt': 'Exalter',
    'Example': 'Exemple', 'Exceed': 'Surpasser', 'Exchange': 'Échange',
    'Excuse': 'Excuse', 'Exempt': 'Exempter', 'Exercise': 'Exercice',
    'Exile': 'Exil', 'Expose': 'Exposer', 'Express': 'Exprimer',
    'Extreme': 'Extrême', 'Fable': 'Fable', 'Fade': 'Se faner',
    'Fail': 'Échouer', 'Faint': 'Défaillir', 'Fair': 'Beau',
    'Fame': 'Renommée', 'Fancy': 'Fantaisie', 'Fashion': 'Façon',
    'Fast': 'Jeûne', 'Fate': 'Destin', 'Fault': 'Faute',
    'Feast': 'Festin', 'Feather': 'Plume', 'Feeble': 'Faible',
    'Feed': 'Nourrir', 'Fence': 'Clôture', 'Fertile': 'Fertile',
    'Fetch': 'Aller chercher', 'Field': 'Champ', 'Fierce': 'Féroce',
    'Figure': 'Figure', 'Fill': 'Remplir', 'Filth': 'Ordure',
    'Firm': 'Ferme', 'Flame': 'Flamme', 'Flatter': 'Flatter',
    'Flesh': 'Chair', 'Flight': 'Fuite', 'Flock': 'Troupeau',
    'Flood': 'Déluge', 'Fold': 'Bergerie', 'Folk': 'Peuple',
    'Folly': 'Folie', 'Food': 'Nourriture', 'Fool': 'Insensé',
    'Foolish': 'Insensé', 'Forbid': 'Interdire', 'Force': 'Force',
    'Ford': 'Gué', 'Foreign': 'Étranger', 'Forfeit': 'Perdre',
    'Forget': 'Oublier', 'Forgive': 'Pardonner', 'Forsake': 'Abandonner',
    'Fortune': 'Fortune', 'Foul': 'Impur', 'Foundation': 'Fondement',
    'Fowl': 'Volaille', 'Fraud': 'Fraude', 'Fray': 'Effrayer',
    'Free': 'Libre', 'Fret': 'S\'irriter', 'Friend': 'Ami',
    'Fright': 'Frayeur', 'Frost': 'Gelée', 'Fruit': 'Fruit',
    'Fugitive': 'Fugitif', 'Fulfil': 'Accomplir', 'Full': 'Plein',
    'Funeral': 'Funérailles', 'Furnace': 'Fournaise', 'Fury': 'Fureur',
    'Gain': 'Gain', 'Gall': 'Fiel', 'Garden': 'Jardin',
    'Garment': 'Vêtement', 'Garrison': 'Garnison', 'Gasp': 'Haleter',
    'Gaze': 'Contempler', 'Gentle': 'Doux', 'Ghost': 'Esprit',
    'Gift': 'Don', 'Gird': 'Ceindre', 'Girdle': 'Ceinture',
    'Glad': 'Joyeux', 'Glass': 'Verre', 'Gleam': 'Lueur',
    'Glean': 'Glaner', 'Glory': 'Gloire', 'Glow': 'Éclat',
    'Gnash': 'Grincer', 'Goad': 'Aiguillon', 'Goat': 'Chèvre',
    'Gold': 'Or', 'Gospel': 'Évangile', 'Govern': 'Gouverner',
    'Graft': 'Greffer', 'Grain': 'Grain', 'Grant': 'Accorder',
    'Grape': 'Raisin', 'Grass': 'Herbe', 'Grave': 'Sépulcre',
    'Graze': 'Paître', 'Greed': 'Avidité', 'Greet': 'Saluer',
    'Grief': 'Chagrin', 'Grind': 'Moudre', 'Groan': 'Gémir',
    'Grope': 'Tâtonner', 'Grove': 'Bosquet', 'Grow': 'Croître',
    'Grudge': 'Rancune', 'Guard': 'Garde', 'Guest': 'Hôte',
    'Guide': 'Guide', 'Guilt': 'Culpabilité',
    'Hail': 'Grêle', 'Halt': 'Boiter', 'Harden': 'Endurcir',
    'Harlot': 'Prostituée', 'Harm': 'Mal', 'Harness': 'Harnais',
    'Harp': 'Harpe', 'Harrow': 'Herse', 'Harvest': 'Moisson',
    'Haste': 'Hâte', 'Hate': 'Haïr', 'Haunt': 'Fréquenter',
    'Haven': 'Port', 'Hawk': 'Faucon', 'Heal': 'Guérir',
    'Heap': 'Monceau', 'Heart': 'Cœur', 'Hearth': 'Foyer',
    'Heaven': 'Ciel', 'Hedge': 'Haie', 'Heed': 'Attention',
    'Heir': 'Héritier', 'Helm': 'Gouvernail', 'Helmet': 'Casque',
    'Herb': 'Herbe', 'Herd': 'Troupeau', 'Hide': 'Cacher',
    'Highway': 'Grand chemin', 'Hiss': 'Siffler', 'Hither': 'Ici',
    'Hoar': 'Blanc', 'Hollow': 'Creux', 'Homage': 'Hommage',
    'Honest': 'Honnête', 'Honor': 'Honneur', 'Hoof': 'Sabot',
    'Hook': 'Crochet', 'Host': 'Armée', 'Hostage': 'Otage',
    'Howl': 'Hurler', 'Humble': 'Humble', 'Idol': 'Idole',
    'Image': 'Image', 'Impure': 'Impur', 'Incline': 'Incliner',
    'Increase': 'Accroître', 'Infant': 'Nourrisson', 'Inherit': 'Hériter',
    'Injure': 'Blesser', 'Innocent': 'Innocent', 'Inquire': 'S\'enquérir',
    'Inscribe': 'Inscrire', 'Insect': 'Insecte', 'Inspire': 'Inspirer',
    'Instruct': 'Instruire', 'Insult': 'Insulte', 'Invade': 'Envahir',
    'Invoke': 'Invoquer', 'Iron': 'Fer', 'Island': 'Île',
    'Ivory': 'Ivoire',
    'Javelin': 'Javelot', 'Jealous': 'Jaloux', 'Jest': 'Plaisanterie',
    'Jewel': 'Joyau', 'Joint': 'Jointure', 'Journey': 'Voyage',
    'Judge': 'Juge', 'Just': 'Juste',
    'Keen': 'Vif', 'Keep': 'Garder', 'Kettle': 'Chaudron',
    'Kid': 'Chevreau', 'Kindle': 'Allumer', 'King': 'Roi',
    'Kingdom': 'Royaume', 'Kinsman': 'Parent', 'Kiss': 'Baiser',
    'Knead': 'Pétrir', 'Kneel': 'S\'agenouiller', 'Knife': 'Couteau',
    'Knit': 'Tricoter', 'Knock': 'Frapper', 'Know': 'Connaître',
    'Labor': 'Travail', 'Lack': 'Manque', 'Lad': 'Garçon',
    'Lame': 'Boiteux', 'Lamp': 'Lampe', 'Lance': 'Lance',
    'Language': 'Langue', 'Languish': 'Languir', 'Lantern': 'Lanterne',
    'Large': 'Grand', 'Last': 'Dernier', 'Late': 'Tard',
    'Latter': 'Dernier', 'Laugh': 'Rire', 'Lay': 'Poser',
    'Lead': 'Plomb', 'Leaf': 'Feuille', 'League': 'Lieue',
    'Lean': 'Maigre', 'Leap': 'Bondir', 'Learn': 'Apprendre',
    'Leather': 'Cuir', 'Leaven': 'Levain', 'Lend': 'Prêter',
    'Leopard': 'Léopard', 'Leper': 'Lépreux', 'Leprosy': 'Lèpre',
    'Lesson': 'Leçon', 'Level': 'Niveau', 'Lewd': 'Débauché',
    'Liar': 'Menteur', 'Liberal': 'Libéral', 'Liberty': 'Liberté',
    'Lick': 'Lécher', 'Lift': 'Lever', 'Lime': 'Chaux',
    'Line': 'Cordeau', 'Linen': 'Lin', 'Lion': 'Lion',
    'Listen': 'Écouter', 'Load': 'Charge', 'Loan': 'Prêt',
    'Loathe': 'Détester', 'Lock': 'Serrure', 'Lodge': 'Loger',
    'Lofty': 'Altier', 'Lonely': 'Solitaire', 'Lord': 'Seigneur',
    'Lose': 'Perdre', 'Lot': 'Sort', 'Loud': 'Fort',
    'Low': 'Bas', 'Lurk': 'Guetter', 'Luxury': 'Luxe',
    'Mad': 'Fou', 'Magic': 'Magie', 'Maiden': 'Vierge',
    'Majesty': 'Majesté', 'Male': 'Mâle', 'Malice': 'Malice',
    'Mantle': 'Manteau', 'Marble': 'Marbre', 'Margin': 'Marge',
    'Marry': 'Marier', 'Marvel': 'S\'émerveiller', 'Measure': 'Mesure',
    'Meddle': 'Se mêler', 'Melt': 'Fondre', 'Mend': 'Réparer',
    'Merchant': 'Marchand', 'Mercy': 'Miséricorde', 'Merit': 'Mérite',
    'Merry': 'Joyeux', 'Metal': 'Métal', 'Mild': 'Doux',
    'Mildew': 'Moisissure', 'Mingle': 'Mêler', 'Miracle': 'Miracle',
    'Mirth': 'Gaieté', 'Mischief': 'Méfait', 'Mock': 'Moquer',
    'Modest': 'Modeste', 'Moisture': 'Humidité', 'Molest': 'Molester',
    'Mortal': 'Mortel', 'Mourn': 'Pleurer', 'Murder': 'Meurtre',
    'Murmur': 'Murmure', 'Muster': 'Rassemblement', 'Muzzle': 'Museler',
    'Mystery': 'Mystère', 'Naked': 'Nu', 'Narrow': 'Étroit',
    'Nation': 'Nation', 'Native': 'Natif', 'Nature': 'Nature',
    'Navel': 'Nombril', 'Needle': 'Aiguille', 'Neglect': 'Négliger',
    'Noble': 'Noble', 'Noise': 'Bruit',
    'Oath': 'Serment', 'Obey': 'Obéir', 'Obscure': 'Obscur',
    'Observe': 'Observer', 'Obtain': 'Obtenir', 'Offend': 'Offenser',
    'Offer': 'Offrir', 'Oil': 'Huile', 'Olive': 'Olive',
    'Omen': 'Présage', 'Oppress': 'Opprimer', 'Oracle': 'Oracle',
    'Orchard': 'Verger', 'Ordain': 'Ordonner', 'Organ': 'Orgue',
    'Ornament': 'Ornement', 'Orphan': 'Orphelin', 'Outcast': 'Banni',
    'Outrage': 'Outrage', 'Overcome': 'Vaincre', 'Owe': 'Devoir',
    'Pace': 'Pas', 'Palace': 'Palais', 'Palm': 'Paume',
    'Pant': 'Haleter', 'Paradise': 'Paradis', 'Pardon': 'Pardon',
    'Path': 'Sentier', 'Pattern': 'Modèle', 'Pause': 'Pause',
    'Pawn': 'Gage', 'Pearl': 'Perle', 'Peculiar': 'Particulier',
    'Peel': 'Peler', 'Penny': 'Denier', 'People': 'Peuple',
    'Perceive': 'Percevoir', 'Perfect': 'Parfait', 'Perfume': 'Parfum',
    'Perish': 'Périr', 'Persecute': 'Persécuter', 'Persuade': 'Persuader',
    'Pervert': 'Pervertir', 'Phantom': 'Fantôme', 'Pierce': 'Percer',
    'Pillar': 'Colonne', 'Pit': 'Fosse', 'Plague': 'Plaie',
    'Plain': 'Plaine', 'Plant': 'Planter', 'Plead': 'Plaider',
    'Pledge': 'Gage', 'Plenty': 'Abondance', 'Plough': 'Charrue',
    'Pluck': 'Arracher', 'Plumb': 'Aplomb', 'Plunder': 'Pillage',
    'Poison': 'Poison', 'Pollute': 'Polluer', 'Pond': 'Étang',
    'Pool': 'Bassin', 'Poor': 'Pauvre', 'Possess': 'Posséder',
    'Pour': 'Verser', 'Praise': 'Louange', 'Preach': 'Prêcher',
    'Precious': 'Précieux', 'Preserve': 'Préserver', 'Prevail': 'Prévaloir',
    'Prevent': 'Prévenir', 'Priest': 'Prêtre', 'Prince': 'Prince',
    'Prison': 'Prison', 'Proclaim': 'Proclamer', 'Profane': 'Profane',
    'Profit': 'Profit', 'Promise': 'Promesse', 'Prophecy': 'Prophétie',
    'Prosper': 'Prospérer', 'Protect': 'Protéger', 'Proud': 'Orgueilleux',
    'Provoke': 'Provoquer', 'Prune': 'Émonder', 'Publish': 'Publier',
    'Punish': 'Punir', 'Pure': 'Pur', 'Purple': 'Pourpre',
    'Pursue': 'Poursuivre', 'Quake': 'Trembler', 'Quarrel': 'Querelle',
    'Queen': 'Reine', 'Quench': 'Éteindre', 'Quiet': 'Tranquille',
    'Quit': 'Quitter', 'Race': 'Race', 'Rage': 'Rage',
    'Rain': 'Pluie', 'Rainbow': 'Arc-en-ciel', 'Raise': 'Élever',
    'Rank': 'Rang', 'Ransom': 'Rançon', 'Raven': 'Corbeau',
    'Reach': 'Atteindre', 'Reap': 'Moissonner', 'Reason': 'Raison',
    'Rebel': 'Rebelle', 'Rebuke': 'Réprimander', 'Reckon': 'Compter',
    'Redeem': 'Racheter', 'Reed': 'Roseau', 'Refuge': 'Refuge',
    'Refuse': 'Refuser', 'Reign': 'Règne', 'Reject': 'Rejeter',
    'Rejoice': 'Se réjouir', 'Release': 'Libérer', 'Relief': 'Secours',
    'Rely': 'Se fier', 'Remain': 'Rester', 'Remedy': 'Remède',
    'Remember': 'Se souvenir', 'Remnant': 'Reste', 'Remove': 'Enlever',
    'Rend': 'Déchirer', 'Renew': 'Renouveler', 'Renown': 'Renommée',
    'Repay': 'Rembourser', 'Repent': 'Se repentir', 'Reproach': 'Reproche',
    'Reprove': 'Reprendre', 'Rescue': 'Délivrer', 'Resist': 'Résister',
    'Respect': 'Respect', 'Rest': 'Repos', 'Restore': 'Restaurer',
    'Restrain': 'Retenir', 'Return': 'Retour', 'Reveal': 'Révéler',
    'Revenge': 'Vengeance', 'Revere': 'Révérer', 'Revile': 'Outrager',
    'Revive': 'Ranimer', 'Revolt': 'Révolte', 'Reward': 'Récompense',
    'Rich': 'Riche', 'Riddle': 'Énigme', 'Ring': 'Anneau',
    'Riot': 'Émeute', 'Ripe': 'Mûr', 'Roam': 'Errer',
    'Robe': 'Robe', 'Roll': 'Rouler', 'Roof': 'Toit',
    'Root': 'Racine', 'Rot': 'Pourrir', 'Rude': 'Grossier',
    'Ruin': 'Ruine', 'Rumor': 'Rumeur', 'Rush': 'Jonc',
    'Sacred': 'Sacré', 'Sacrifice': 'Sacrifice', 'Safe': 'Sûr',
    'Salt': 'Sel', 'Sand': 'Sable', 'Save': 'Sauver',
    'Scarlet': 'Écarlate', 'Scatter': 'Disperser', 'Scent': 'Parfum',
    'School': 'École', 'Scorn': 'Mépris', 'Scourge': 'Fouet',
    'Seal': 'Sceau', 'Season': 'Saison', 'Seat': 'Siège',
    'Seed': 'Semence', 'Seek': 'Chercher', 'Seize': 'Saisir',
    'Send': 'Envoyer', 'Sense': 'Sens', 'Settle': 'Établir',
    'Severe': 'Sévère', 'Shade': 'Ombre', 'Shadow': 'Ombre',
    'Shaft': 'Hampe', 'Shake': 'Secouer', 'Shame': 'Honte',
    'Shape': 'Forme', 'Share': 'Part', 'Shave': 'Raser',
    'Shear': 'Tondre', 'Shed': 'Verser', 'Sheep': 'Brebis',
    'Shell': 'Coquille', 'Shelter': 'Abri', 'Shepherd': 'Berger',
    'Shield': 'Bouclier', 'Shine': 'Briller', 'Ship': 'Navire',
    'Shock': 'Tas', 'Shoe': 'Soulier', 'Shoot': 'Rejeton',
    'Shore': 'Rivage', 'Shout': 'Cri', 'Shrink': 'Reculer',
    'Shut': 'Fermer', 'Sick': 'Malade', 'Sickle': 'Faucille',
    'Siege': 'Siège', 'Sift': 'Cribler', 'Sight': 'Vue',
    'Sign': 'Signe', 'Silk': 'Soie', 'Silver': 'Argent',
    'Simple': 'Simple', 'Sin': 'Péché', 'Sinew': 'Tendon',
    'Sink': 'Sombrer', 'Sit': 'S\'asseoir', 'Skull': 'Crâne',
    'Slaughter': 'Massacre', 'Slave': 'Esclave', 'Slay': 'Tuer',
    'Sleep': 'Sommeil', 'Slip': 'Glisser', 'Slow': 'Lent',
    'Smell': 'Odeur', 'Smite': 'Frapper', 'Smith': 'Forgeron',
    'Smoke': 'Fumée', 'Smooth': 'Lisse', 'Snare': 'Piège',
    'Snow': 'Neige', 'Sober': 'Sobre', 'Soft': 'Doux',
    'Soil': 'Sol', 'Soldier': 'Soldat', 'Solemn': 'Solennel',
    'Soothe': 'Apaiser', 'Sore': 'Plaie', 'Sorrow': 'Tristesse',
    'Soul': 'Âme', 'South': 'Sud', 'Sow': 'Semer',
    'Spare': 'Épargner', 'Speak': 'Parler', 'Spear': 'Lance',
    'Spice': 'Aromate', 'Spider': 'Araignée', 'Spill': 'Répandre',
    'Spin': 'Filer', 'Spirit': 'Esprit', 'Spoil': 'Dépouille',
    'Sponge': 'Éponge', 'Spot': 'Tache', 'Spread': 'Étendre',
    'Sprinkle': 'Asperger', 'Spur': 'Éperon', 'Stagger': 'Chanceler',
    'Stain': 'Tache', 'Stalk': 'Tige', 'Star': 'Étoile',
    'Starve': 'Affamer', 'State': 'État', 'Statute': 'Statut',
    'Steal': 'Voler', 'Stem': 'Tige', 'Step': 'Pas',
    'Stern': 'Poupe', 'Stiff': 'Raide', 'Stir': 'Remuer',
    'Stock': 'Tronc', 'Stomach': 'Estomac', 'Stone': 'Pierre',
    'Stoop': 'Se baisser', 'Store': 'Provisions', 'Storm': 'Tempête',
    'Stout': 'Fort', 'Straight': 'Droit', 'Strain': 'Filtrer',
    'Strait': 'Détroit', 'Strange': 'Étranger', 'Stream': 'Ruisseau',
    'Strength': 'Force', 'Stretch': 'Étendre', 'Strict': 'Strict',
    'Stride': 'Enjambée', 'Strife': 'Querelle', 'Strike': 'Frapper',
    'String': 'Corde', 'Strip': 'Dépouiller', 'Stripe': 'Meurtrissure',
    'Strive': 'Lutter', 'Stroke': 'Coup', 'Strong': 'Fort',
    'Struggle': 'Lutte', 'Stumble': 'Trébucher', 'Subdue': 'Assujettir',
    'Subject': 'Sujet', 'Submit': 'Soumettre', 'Succeed': 'Réussir',
    'Suffer': 'Souffrir', 'Suit': 'Procès', 'Summit': 'Sommet',
    'Summon': 'Convoquer', 'Surround': 'Entourer', 'Survive': 'Survivre',
    'Suspect': 'Soupçonner', 'Swallow': 'Hirondelle', 'Swear': 'Jurer',
    'Sweet': 'Doux', 'Sword': 'Épée', 'Symbol': 'Symbole',
    'Tame': 'Apprivoiser', 'Taste': 'Goût', 'Teach': 'Enseigner',
    'Tear': 'Déchirer', 'Tempt': 'Tenter', 'Tend': 'Soigner',
    'Tender': 'Tendre', 'Tent': 'Tente', 'Terror': 'Terreur',
    'Testify': 'Témoigner', 'Thank': 'Remercier', 'Thicket': 'Fourré',
    'Thief': 'Voleur', 'Thorn': 'Épine', 'Thread': 'Fil',
    'Threat': 'Menace', 'Thresh': 'Battre le blé', 'Throne': 'Trône',
    'Throw': 'Jeter', 'Thrust': 'Pousser', 'Tidings': 'Nouvelles',
    'Tie': 'Attacher', 'Timber': 'Bois', 'Tired': 'Fatigué',
    'Toil': 'Labeur', 'Toll': 'Péage', 'Tomb': 'Tombeau',
    'Tongue': 'Langue', 'Torch': 'Flambeau', 'Torment': 'Tourment',
    'Touch': 'Toucher', 'Tower': 'Tour', 'Trade': 'Commerce',
    'Trample': 'Fouler', 'Travail': 'Travail', 'Treasure': 'Trésor',
    'Treat': 'Traiter', 'Tree': 'Arbre', 'Tremble': 'Trembler',
    'Trial': 'Épreuve', 'Tribe': 'Tribu', 'Tribute': 'Tribut',
    'Triumph': 'Triomphe', 'Troop': 'Troupe', 'Trouble': 'Trouble',
    'Trust': 'Confiance', 'Truth': 'Vérité', 'Tumult': 'Tumulte',
    'Turn': 'Tourner', 'Tutor': 'Précepteur', 'Twig': 'Rameau',
    'Twilight': 'Crépuscule', 'Twin': 'Jumeau', 'Twist': 'Tordre',
    'Type': 'Type', 'Uncle': 'Oncle', 'Uncover': 'Découvrir',
    'Unjust': 'Injuste', 'Uphold': 'Soutenir', 'Upright': 'Droit',
    'Uproar': 'Tumulte', 'Urgent': 'Urgent', 'Utter': 'Prononcer',
    'Vain': 'Vain', 'Vale': 'Vallée', 'Valor': 'Valeur',
    'Value': 'Valeur', 'Vanish': 'Disparaître', 'Vanity': 'Vanité',
    'Vapor': 'Vapeur', 'Veil': 'Voile', 'Venture': 'Aventure',
    'Vessel': 'Vase', 'Village': 'Village', 'Vine': 'Vigne',
    'Vineyard': 'Vignoble', 'Virgin': 'Vierge', 'Virtue': 'Vertu',
    'Visible': 'Visible', 'Visit': 'Visiter', 'Voice': 'Voix',
    'Void': 'Vide', 'Vow': 'Vœu', 'Vulture': 'Vautour',
    'Wage': 'Salaire', 'Wail': 'Se lamenter', 'Wait': 'Attendre',
    'Wake': 'Veiller', 'Walk': 'Marcher', 'Wander': 'Errer',
    'Want': 'Manque', 'War': 'Guerre', 'Warn': 'Avertir',
    'Warrior': 'Guerrier', 'Wash': 'Laver', 'Waste': 'Dévaster',
    'Wave': 'Vague', 'Wax': 'Cire', 'Weak': 'Faible',
    'Wealth': 'Richesse', 'Weapon': 'Arme', 'Wear': 'Porter',
    'Weave': 'Tisser', 'Weed': 'Ivraie', 'Weigh': 'Peser',
    'Welcome': 'Accueillir', 'West': 'Ouest', 'Wheat': 'Blé',
    'Wheel': 'Roue', 'Whisper': 'Chuchoter', 'White': 'Blanc',
    'Whole': 'Entier', 'Wicked': 'Méchant', 'Widow': 'Veuve',
    'Wild': 'Sauvage', 'Wilderness': 'Désert', 'Wile': 'Ruse',
    'Willing': 'Disposé', 'Willow': 'Saule', 'Wilt': 'Flétrir',
    'Win': 'Gagner', 'Wind': 'Vent', 'Wine': 'Vin',
    'Wing': 'Aile', 'Wisdom': 'Sagesse', 'Wise': 'Sage',
    'Witch': 'Sorcière', 'Woe': 'Malheur', 'Wolf': 'Loup',
    'Woman': 'Femme', 'Womb': 'Sein', 'Wonder': 'Prodige',
    'Wood': 'Bois', 'Wool': 'Laine', 'Word': 'Parole',
    'Work': 'Œuvre', 'World': 'Monde', 'Worm': 'Ver',
    'Worry': 'Tourment', 'Worship': 'Adoration', 'Worth': 'Valeur',
    'Worthy': 'Digne', 'Wound': 'Blessure', 'Wrath': 'Colère',
    'Wreath': 'Couronne', 'Wrong': 'Tort', 'Yoke': 'Joug',
    'Young': 'Jeune', 'Youth': 'Jeunesse', 'Zeal': 'Zèle',
}


def translate_mixed_label(label):
    """Traduit un label mixte FR/EN en remplaçant les mots EN par leur traduction."""
    result = label
    for en, fr in sorted(WORD_REPLACEMENTS.items(), key=lambda x: -len(x[0])):
        # Word boundary replacement
        result = re.sub(r'\b' + re.escape(en) + r'\b', fr, result)
    # Clean up double spaces
    result = re.sub(r'\s{2,}', ' ', result).strip()
    # Clean up ", de  " patterns
    result = re.sub(r',\s*$', '', result)
    return result


def check_backup():
    if not BACKUP_DIR.exists():
        return False
    return bool(list(BACKUP_DIR.glob('dictionnaires-*.zip')))


def patch_chunk_entry(entry, fr_label, mot_en):
    before = entry.get('label_fr', '')
    if before == fr_label:
        return False
    entry['label_fr'] = fr_label
    entry['source_title_en'] = entry.get('source_title_en') or mot_en
    aliases = list(entry.get('aliases', []) or [])
    for a in [fr_label, mot_en]:
        if a and a not in aliases:
            aliases.append(a)
    entry['aliases'] = aliases
    return True


def patch_concept(concept, fr_label, en_secondary):
    if concept.get('label', '') == fr_label:
        return False
    concept['label'] = fr_label
    dt = concept.get('display_titles', {}) or {}
    dt['primary'] = fr_label
    dt['secondary'] = en_secondary if en_secondary != fr_label else ''
    dt['strategy'] = 'french_first' if en_secondary != fr_label else 'french_only'
    concept['display_titles'] = dt
    pf = concept.get('public_forms', {}) or {}
    pf['french_reference'] = fr_label
    en_labels = list(pf.get('english_labels', []) or [])
    if en_secondary and en_secondary not in en_labels:
        en_labels.append(en_secondary)
    pf['english_labels'] = en_labels
    concept['public_forms'] = pf
    aliases = list(concept.get('aliases', []) or [])
    for a in [fr_label, en_secondary]:
        if a and a not in aliases:
            aliases.append(a)
    concept['aliases'] = aliases
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    mode = 'APPLY' if args.apply else 'DRY-RUN'
    print(f'Mode: {mode}')

    if args.apply and not check_backup():
        print("ERREUR: backup manquant")
        sys.exit(1)

    # Load classified residues
    with open(AUDIT_DIR / 'isbe-residues-classified.json', encoding='utf-8') as f:
        classified = json.load(f)

    # Build target list: all items to translate
    targets = {}  # concept_id -> fr_label

    # Phase 1: mixed FR/EN
    for item in classified['mixed_items']:
        cid = item['concept_id']
        label = item['label']
        if cid in LABEL_OVERRIDES:
            targets[cid] = LABEL_OVERRIDES[cid]
        else:
            translated = translate_mixed_label(label)
            if translated != label:
                targets[cid] = translated

    # Phase 2: EN common
    for item in classified['en_common_items']:
        cid = item['concept_id']
        label = item['label']
        if cid in LABEL_OVERRIDES:
            targets[cid] = LABEL_OVERRIDES[cid]
        else:
            # Try word-by-word translation for multi-word
            translated = translate_mixed_label(label)
            if translated != label:
                targets[cid] = translated

    # Phase 3: ambiguous — translate only if the label is a known English word
    for item in classified['ambiguous_items']:
        cid = item['concept_id']
        label = item['label']
        if cid in LABEL_OVERRIDES:
            targets[cid] = LABEL_OVERRIDES[cid]
            continue
        # Check if single-word and in our translation dict
        words = re.split(r'[\s;,]+', label)
        first = words[0] if words else ''
        if first in ENGLISH_WORDS_TRANSLATIONS:
            if len(words) == 1:
                targets[cid] = ENGLISH_WORDS_TRANSLATIONS[first]
            else:
                # Multi-word: try translating each
                translated = translate_mixed_label(label)
                if translated != label:
                    targets[cid] = translated
        elif len(words) > 1:
            # Try mixed translation
            translated = translate_mixed_label(label)
            if translated != label:
                targets[cid] = translated

    print(f'Total targets to translate: {len(targets)}')

    # Load data
    with open(CONCEPTS_JSON, encoding='utf-8') as f:
        concepts = json.load(f)
    concept_by_id = {c['concept_id']: c for c in concepts}

    with open(CONCEPT_META_JSON, encoding='utf-8') as f:
        meta = json.load(f)

    # Build entry_id -> concept_id mapping
    with open(DICT_DIR / 'concept-entry-links.json', encoding='utf-8-sig') as f:
        links = json.load(f)
    entry_to_cid = {}
    for link in links:
        if link.get('entry_id', '').startswith('isbe-'):
            entry_to_cid[link['entry_id']] = link['concept_id']

    # Build concept_id -> primary entry_id
    cid_to_entry = {}
    for c in concepts:
        for e in c.get('entries', []):
            if e.get('dictionary') == 'isbe' and e.get('is_primary_for_role'):
                cid_to_entry[c['concept_id']] = e['entry_id']
                break
        if c['concept_id'] not in cid_to_entry:
            for e in c.get('entries', []):
                if e.get('dictionary') == 'isbe':
                    cid_to_entry[c['concept_id']] = e['entry_id']
                    break

    # Apply to chunks
    chunk_changes = 0
    chunks_data = {}
    for fp in sorted(ISBE_DIR.glob('isbe-?.json')):
        with open(fp, encoding='utf-8-sig') as f:
            entries = json.load(f)
        local = 0
        for e in entries:
            cid = entry_to_cid.get(e['id'])
            if cid and cid in targets:
                if patch_chunk_entry(e, targets[cid], e.get('mot', '')):
                    local += 1
        if local:
            chunks_data[fp.name] = entries
            chunk_changes += local

    # Apply to concepts + meta
    concept_changes = 0
    for cid, fr_label in targets.items():
        c = concept_by_id.get(cid)
        if not c:
            continue
        en_secondary = c.get('label', '')
        if patch_concept(c, fr_label, en_secondary):
            concept_changes += 1
            if cid in meta:
                meta[cid]['l'] = fr_label
                meta[cid]['p'] = fr_label
                meta[cid]['s'] = en_secondary

    print(f'Chunk entries modified: {chunk_changes}')
    print(f'Chunks to write: {len(chunks_data)}')
    print(f'Concepts patched: {concept_changes}')

    if args.apply:
        print('\n=== WRITING ===')
        for chunk_name, entries in chunks_data.items():
            payload = json.dumps(entries, ensure_ascii=False, separators=(', ', ': '))
            with open(ISBE_DIR / chunk_name, 'w', encoding='utf-8-sig') as f:
                f.write(payload)
            print(f'  {chunk_name}')

        with open(CONCEPTS_JSON, 'w', encoding='utf-8') as f:
            json.dump(concepts, f, ensure_ascii=False, indent=2)
        print('  concepts.json')

        with open(CONCEPT_META_JSON, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))
        print('  concept-meta.json')

        with open(LOG_JSON, 'w', encoding='utf-8') as f:
            json.dump({
                'applied_at': datetime.now().isoformat(),
                'targets_count': len(targets),
                'chunk_changes': chunk_changes,
                'concept_changes': concept_changes,
            }, f, ensure_ascii=False, indent=2)
        print(f'  Log: {LOG_JSON}')


if __name__ == '__main__':
    main()
