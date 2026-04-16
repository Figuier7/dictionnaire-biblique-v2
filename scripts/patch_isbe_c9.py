#!/usr/bin/env python3
"""
Patch C9 : 640 concepts Category B (noms communs anglais restants).

Mapping massif EN→FR avec arbitrages biblique/éditoriaux.
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
FILTERED_JSON = AUDIT_DIR / "isbe-c9-cat-b.json"
LOG_JSON = AUDIT_DIR / "isbe-c9-apply-log.json"
DRY_MD = AUDIT_DIR / "isbe-c9-dry-run.md"

# Noms propres bibliques à EXCLURE
SKIP_PROPER_NOUNS = set()

# Mapping exhaustif
MAP = {
    # A
    'Abase': ('Abaisser', ['Humilier']),
    'Abate': ('Diminuer', ['Décroître']),
    'Abhor': ('Abhorrer', ['Détester']),
    'Abide': ('Demeurer', ['Rester']),
    'About': ('Au sujet de', ['Environ']),
    'Abroad': ('À l\'étranger', ['Au loin']),
    'Abuse': ('Abus', ['Mauvais traitement']),
    'Abyss': ('Abîme', []),
    'Accursed': ('Maudit', ['Anathème']),
    'Add': ('Ajouter', []),
    'Advent': ('Avènement', ['Venue']),
    'Afternoon': ('Après-midi', []),
    'Again': ('De nouveau', []),
    'Aid': ('Aide', ['Secours']),
    'Alien': ('Étranger', []),
    'Alive': ('Vivant', ['En vie']),
    'All': ('Tout', []),
    'Allied': ('Allié', []),
    'Alloy': ('Alliage', []),
    'Almighty': ('Tout-Puissant', []),
    'Almost': ('Presque', []),
    'Aloft': ('En haut', ['En l\'air']),
    'Along': ('Le long de', []),
    'Also': ('Aussi', ['Également']),
    'Ankle': ('Cheville', []),
    'Antiquity': ('Antiquité', []),
    'Apart': ('À part', ['Séparé']),
    'Appetite': ('Appétit', []),
    'Apply': ('Appliquer', []),
    'Appoint': ('Désigner', ['Établir']),
    'Approve': ('Approuver', []),
    'Apron': ('Tablier', []),
    'Aqueduct': ('Aqueduc', []),
    'Argue': ('Argumenter', ['Raisonner']),
    'Aright': ('Avec droiture', ['Correctement']),
    'Arithmetic': ('Arithmétique', []),
    'Armory': ('Arsenal', []),
    'Array': ('Ordre de bataille', ['Rangée']),
    'Arrive': ('Arriver', []),
    'Arrow': ('Flèche', []),
    'Ascend': ('Monter', ['S\'élever']),
    'Ashamed': ('Honteux', []),
    'Assault': ('Assaut', []),
    'Assay': ('Essai', ['Test']),
    'Assembly': ('Assemblée', ['Congrégation']),
    'Assent': ('Consentement', []),
    'Assign': ('Assigner', ['Attribuer']),
    'Astray': ('Égaré', ['Errant']),
    'Aunt': ('Tante', []),
    'Avail': ('Profit', ['Avantage']),
    'Awe': ('Crainte révérentielle', []),
    # B
    'Ball': ('Balle', ['Boule']),
    'Balsam': ('Baume', ['Baumier']),
    'Bank': ('Rive', ['Berge', 'Banque']),
    'Baptist': ('Baptiste', []),
    'Base': ('Base', ['Piédestal']),
    'Beach': ('Plage', ['Rivage']),
    'Bean': ('Fève', ['Haricot']),
    'Beauty': ('Beauté', []),
    'Become': ('Devenir', []),
    'Beef': ('Bœuf', []),
    'Begin': ('Commencer', []),
    'Beguile': ('Séduire', ['Tromper']),
    'Behalf': ('Part', ['Faveur']),
    'Beloved': ('Bien-aimé', []),
    'Belt': ('Ceinture', []),
    'Beneath': ('En dessous de', ['Sous']),
    'Benefit': ('Bienfait', []),
    'Beside': ('À côté de', ['Auprès']),
    'Besiege': ('Assiéger', []),
    'Best': ('Meilleur', []),
    'Bestow': ('Accorder', ['Conférer']),
    'Betray': ('Trahir', []),
    'Bewail': ('Se lamenter', ['Pleurer']),
    'Bid': ('Ordonner', ['Offrir']),
    'Blast': ('Souffle', ['Rafale']),
    'Blaze': ('Flamme', ['Embrasement']),
    'Blessed': ('Béni', ['Heureux']),
    'Bloody': ('Sanglant', []),
    'Blow': ('Souffler', ['Coup']),
    'Board': ('Planche', ['Conseil']),
    'Boast': ('Se vanter', ['Gloire']),
    'Boat': ('Barque', ['Bateau']),
    'Body': ('Corps', []),
    'Born': ('Né', []),
    'Bottom': ('Fond', []),
    'Bough': ('Branche', []),
    'Bound': ('Limite', ['Lié']),
    'Boy': ('Garçon', []),
    'Brand': ('Tison', ['Marque']),
    'Break': ('Briser', ['Rompre']),
    'Breast': ('Poitrine', ['Sein']),
    'Brim': ('Bord', []),
    'Brink': ('Bord', []),
    'Broad': ('Large', []),
    'Broom': ('Balai', ['Genêt']),
    'Broth': ('Bouillon', []),
    'Brow': ('Front', ['Sourcil']),
    'Brown': ('Brun', []),
    'Bud': ('Bourgeon', []),
    'Buffet': ('Soufflet', ['Gifle']),
    'Bulwark': ('Rempart', ['Boulevard']),
    'Bundle': ('Fardeau', ['Paquet']),
    # C
    'Cabin': ('Cabane', ['Hutte']),
    'Car': ('Char', []),
    'Carry': ('Porter', ['Emporter']),
    'Case': ('Cas', []),
    'Cast': ('Jeter', ['Lancer']),
    'Cat': ('Chat', []),
    'Cease': ('Cesser', []),
    'Chant': ('Chant', []),
    'Charm': ('Charme', ['Sortilège']),
    'Chief': ('Chef', ['Principal']),
    'Choice': ('Choix', []),
    'Choke': ('Étouffer', []),
    'Chop': ('Couper', ['Hacher']),
    'Circle': ('Cercle', []),
    'Clap': ('Frapper', ['Applaudir']),
    'Claw': ('Griffe', ['Serre']),
    'Cleanse': ('Purifier', []),
    'Cleave': ('Attacher', ['Fendre']),
    'Clerk': ('Scribe', ['Greffier']),
    'Clod': ('Motte', []),
    'Close': ('Fermer', ['Proche']),
    'Club': ('Massue', ['Gourdin']),
    'Cold': ('Froid', []),
    'Come': ('Venir', []),
    'Comfort': ('Consolation', ['Réconfort']),
    'Compel': ('Contraindre', ['Forcer']),
    'Complete': ('Complet', ['Achever']),
    'Conceal': ('Cacher', ['Dissimuler']),
    'Conceit': ('Orgueil', ['Présomption']),
    'Conduct': ('Conduite', []),
    'Consent': ('Consentir', []),
    'Consort': ('Compagnon', []),
    'Constrain': ('Contraindre', []),
    'Consult': ('Consulter', []),
    'Consume': ('Consumer', ['Dévorer']),
    'Contain': ('Contenir', []),
    'Convince': ('Convaincre', []),
    'Cool': ('Frais', ['Rafraîchir']),
    'Count': ('Compter', []),
    'Country': ('Pays', ['Campagne']),
    'Couple': ('Couple', ['Paire']),
    'Courage': ('Courage', []),
    'Cousin': ('Cousin', []),
    'Covet': ('Convoiter', []),
    'Crag': ('Rocher', ['Escarpement']),
    'Crib': ('Mangeoire', ['Étable']),
    'Cripple': ('Estropié', ['Boiteux']),
    'Crop': ('Récolte', ['Moisson']),
    'Crumb': ('Miette', []),
    'Cushion': ('Coussin', ['Oreiller']),
    'Custody': ('Garde', ['Détention']),
    'Cymbal': ('Cymbale', []),
    # D
    'Dam': ('Digue', ['Barrage']),
    'Damage': ('Dommage', ['Préjudice']),
    'Damsel': ('Jeune fille', ['Demoiselle']),
    'Dandle': ('Bercer', ['Dorloter']),
    'Dash': ('Briser', ['Précipiter']),
    'Daub': ('Enduire', ['Crépir']),
    'Dead': ('Mort', ['Défunt']),
    'Deaf': ('Sourd', []),
    'Deal': ('Partager', ['Distribuer']),
    'Debate': ('Débat', ['Dispute']),
    'Decay': ('Décrépitude', ['Pourrir']),
    'Deceit': ('Tromperie', ['Ruse']),
    'Decline': ('Décliner', []),
    'Deed': ('Action', ['Œuvre']),
    'Defy': ('Défier', ['Provoquer']),
    'Degree': ('Degré', ['Rang']),
    'Delay': ('Délai', ['Retard']),
    'Delight': ('Délice', ['Plaisir']),
    'Demand': ('Demander', []),
    'Deny': ('Nier', ['Renier']),
    'Deposit': ('Dépôt', []),
    'Depth': ('Profondeur', []),
    'Devout': ('Dévot', ['Pieux']),
    'Die': ('Mourir', []),
    'Dig': ('Creuser', []),
    'Dip': ('Plonger', ['Tremper']),
    'Dispatch': ('Expédier', []),
    'Ditch': ('Fossé', ['Tranchée']),
    'Divide': ('Diviser', ['Partager']),
    'Doom': ('Sort', ['Jugement']),
    'Door': ('Porte', []),
    'Dote': ('Radoter', ['S\'entêter']),
    'Double': ('Double', []),
    'Doubt': ('Douter', []),
    'Drum': ('Tambour', []),
    'Due': ('Dû', []),
    'Duty': ('Devoir', ['Obligation']),
    # E
    'Early': ('Tôt', ['De bonne heure']),
    'Earthly': ('Terrestre', []),
    'Ease': ('Aise', ['Soulagement']),
    'Edge': ('Bord', ['Tranchant']),
    'Elect': ('Élu', []),
    'Embrace': ('Embrasser', ['Étreindre']),
    'Eminent': ('Éminent', []),
    'Enjoin': ('Enjoindre', ['Ordonner']),
    'Enlighten': ('Éclairer', ['Illuminer']),
    'Enquire': ('S\'enquérir', []),
    'Ensue': ('S\'ensuivre', []),
    'Entreat': ('Supplier', ['Implorer']),
    'Envy': ('Envie', ['Jalousie']),
    'Equal': ('Égal', []),
    'Equity': ('Équité', ['Droiture']),
    'Estate': ('État', ['Condition']),
    'Esteem': ('Estime', []),
    'Eternal': ('Éternel', []),
    'Event': ('Événement', []),
    'Evil': ('Mal', ['Méchant']),
    'Express': ('Exprimer', []),
    'Eyelid': ('Paupière', []),
    # F
    'Fade': ('Se faner', ['Se flétrir']),
    'Fail': ('Échouer', ['Manquer']),
    'Faint': ('Défaillir', ['Faible']),
    'Fair': ('Beau', ['Juste']),
    'Family': ('Famille', []),
    'Fancy': ('Fantaisie', ['Imagination']),
    'Fare': ('Se porter', ['Repas']),
    'Fashion': ('Façon', ['Manière']),
    'Favor': ('Faveur', []),
    'Fawn': ('Faon', []),
    'Fear': ('Crainte', ['Peur']),
    'Fellow': ('Compagnon', ['Semblable']),
    'Female': ('Femme', ['Femelle']),
    'Festival': ('Fête', []),
    'Fetch': ('Aller chercher', ['Rapporter']),
    'Fight': ('Combattre', ['Lutte']),
    'Figure': ('Figure', []),
    'File': ('Lime', ['File']),
    'Fine': ('Fin', ['Amende']),
    'First': ('Premier', []),
    'Five': ('Cinq', []),
    'Flag': ('Roseau', ['Drapeau']),
    'Flame': ('Flamme', []),
    'Flee': ('Fuir', []),
    'Flock': ('Troupeau', []),
    'Folk': ('Peuple', ['Gens']),
    'Follow': ('Suivre', []),
    'Folly': ('Folie', []),
    'Foot': ('Pied', []),
    'For': ('Pour', []),
    'Forbid': ('Interdire', []),
    'Forecast': ('Prévoir', ['Prédire']),
    'Forfeit': ('Perdre', ['Forfaire']),
    'Fork': ('Fourche', []),
    'Form': ('Forme', []),
    'Forth': ('En avant', ['Dehors']),
    'Fortune': ('Fortune', ['Destin']),
    'Forty': ('Quarante', []),
    'Foul': ('Souillé', ['Immonde']),
    'Fourteen': ('Quatorze', []),
    'Fragment': ('Fragment', []),
    'Frame': ('Cadre', ['Charpente']),
    'Freely': ('Librement', ['Gratuitement']),
    'Fresh': ('Frais', []),
    'Fulfil': ('Accomplir', []),
    'Funeral': ('Funérailles', []),
    'Future': ('Futur', ['Avenir']),
    # G
    'Gain': ('Gain', ['Profit']),
    'Girl': ('Fille', []),
    'Give': ('Donner', []),
    'Glorious': ('Glorieux', []),
    'Go': ('Aller', []),
    'Good': ('Bon', ['Bien']),
    'Goods': ('Biens', ['Marchandises']),
    'Gore': ('Transpercer', ['Corner']),
    'Granary': ('Grenier', []),
    'Grasp': ('Saisir', ['Empoigner']),
    'Gravel': ('Gravier', []),
    'Gray': ('Gris', []),
    'Groan': ('Gémir', []),
    'Gross': ('Gras', ['Épais']),
    'Grudge': ('Rancune', []),
    'Guile': ('Ruse', ['Fourberie']),
    'Guilt': ('Culpabilité', ['Faute']),
    'Guilty': ('Coupable', []),
    'Gulf': ('Golfe', ['Gouffre']),
    # H
    'Half': ('Moitié', []),
    'Handle': ('Manche', ['Poignée']),
    'Happen': ('Arriver', ['Se produire']),
    'Haste': ('Hâte', []),
    'Have': ('Avoir', []),
    'He': ('Il', ['Lui']),
    'Head': ('Tête', []),
    'Heal': ('Guérir', []),
    'Health': ('Santé', []),
    'Heat': ('Chaleur', []),
    'Heavenly': ('Céleste', []),
    'Heel': ('Talon', []),
    'Help': ('Aider', ['Secours']),
    'Here': ('Ici', []),
    'Heritage': ('Héritage', []),
    'Hidden': ('Caché', []),
    'Hip': ('Hanche', []),
    'Hire': ('Embaucher', ['Salaire']),
    'His': ('Son', ['Sa']),
    'Hold': ('Tenir', ['Saisir']),
    'Hollow': ('Creux', []),
    'Home': ('Maison', ['Foyer']),
    'Horrible': ('Horrible', []),
    'Horror': ('Horreur', []),
    'Household': ('Maison', ['Ménage']),
    'How': ('Comment', []),
    'Hundred': ('Cent', []),
    'Hurt': ('Blesser', []),
    # I
    'Imagine': ('Imaginer', []),
    'Impart': ('Communiquer', ['Donner']),
    'Incense': ('Encens', []),
    'Increase': ('Augmenter', ['Accroître']),
    'Ink': ('Encre', []),
    'Inquire': ('S\'enquérir', []),
    'Interest': ('Intérêt', []),
    'Issue': ('Issue', ['Descendance']),
    'Itch': ('Démangeaison', []),
    'Ivy': ('Lierre', []),
    # J
    'Join': ('Unir', ['Joindre']),
    'Joy': ('Joie', []),
    'Juice': ('Jus', []),
    # K
    'Kernel': ('Noyau', ['Grain']),
    'Kick': ('Donner un coup de pied', []),
    'Kin': ('Parenté', ['Famille']),
    # L
    'Labor': ('Travail', ['Labeur']),
    'Lace': ('Lacet', ['Dentelle']),
    'Lack': ('Manque', ['Faire défaut']),
    'Lad': ('Jeune garçon', []),
    'Lady': ('Dame', []),
    'Lake': ('Lac', []),
    'Lament': ('Se lamenter', []),
    'Lane': ('Ruelle', ['Allée']),
    'Lap': ('Giron', ['Sein']),
    'Left': ('Gauche', ['Restant']),
    'Leg': ('Jambe', []),
    'Let': ('Laisser', []),
    'Liberty': ('Liberté', []),
    'Lift': ('Lever', ['Élever']),
    'Line': ('Ligne', ['Corde']),
    'Linen': ('Lin', ['Toile de lin']),
    'Loaf': ('Pain', ['Miche']),
    'Locust': ('Sauterelle', []),
    'Look': ('Regarder', []),
    'Loss': ('Perte', []),
    'Lovely': ('Aimable', ['Charmant']),
    'Lust': ('Convoitise', ['Concupiscence']),
    # M
    'Mail': ('Cotte de mailles', []),
    'Male': ('Mâle', ['Masculin']),
    'Mankind': ('Humanité', ['Genre humain']),
    'Marrow': ('Moelle', []),
    'Marsh': ('Marais', []),
    'Marshal': ('Maréchal', []),
    'Mast': ('Mât', []),
    'Mastery': ('Maîtrise', []),
    'Meal': ('Repas', ['Farine']),
    'Mean': ('Signifier', ['Moyen']),
    'Meat': ('Viande', []),
    'Meet': ('Rencontrer', []),
    'Mess': ('Plat', ['Portion']),
    'Metal': ('Métal', []),
    'Mete': ('Mesurer', []),
    'Mice': ('Souris', []),
    'Midday': ('Midi', []),
    'Midnight': ('Minuit', []),
    'Mirror': ('Miroir', []),
    'Mischief': ('Méfait', ['Malice']),
    'Mist': ('Brume', ['Brouillard']),
    'Mistress': ('Maîtresse', []),
    'Moment': ('Moment', []),
    'Morsel': ('Morceau', ['Bouchée']),
    'Mouth': ('Bouche', []),
    # N
    'Name': ('Nom', []),
    'Nature': ('Nature', []),
    'Navy': ('Flotte', ['Marine']),
    'Needy': ('Indigent', ['Nécessiteux']),
    'Neigh': ('Hennir', ['Hennissement']),
    'Neighbor': ('Prochain', ['Voisin']),
    'Nephew': ('Neveu', []),
    'Nest': ('Nid', []),
    'Nigh': ('Proche', ['Près']),
    'Noise': ('Bruit', []),
    'Note': ('Note', []),
    # O
    'Oar': ('Rame', ['Aviron']),
    'Observe': ('Observer', []),
    'Occasion': ('Occasion', []),
    'Odor': ('Odeur', []),
    'Office': ('Office', ['Fonction']),
    'Often': ('Souvent', []),
    'Old': ('Vieux', ['Ancien']),
    'Olive': ('Olive', ['Olivier']),
    'One': ('Un', []),
    'Open': ('Ouvrir', ['Ouvert']),
    'Ornament': ('Ornement', []),
    'Orphan': ('Orphelin', []),
    'Outcast': ('Banni', ['Rejeté']),
    'Owl': ('Hibou', ['Chouette']),
    # P
    'Pace': ('Pas', ['Allure']),
    'Paddle': ('Pagayer', ['Pelle']),
    'Pair': ('Paire', []),
    'Park': ('Parc', []),
    'Part': ('Partie', ['Part']),
    'Pattern': ('Modèle', ['Patron']),
    'Paw': ('Patte', []),
    'Peace': ('Paix', []),
    'Peep': ('Jeter un regard', ['Pépier']),
    'Pencil': ('Crayon', []),
    'Pension': ('Pension', []),
    'People': ('Peuple', ['Gens']),
    'Perform': ('Accomplir', []),
    'Picture': ('Image', ['Tableau']),
    'Pile': ('Tas', ['Amas']),
    'Pillow': ('Oreiller', []),
    'Pilot': ('Pilote', []),
    'Pine': ('Pin', ['Se languir']),
    'Pity': ('Pitié', []),
    'Pleasure': ('Plaisir', []),
    'Plow': ('Charrue', ['Labourer']),
    'Poet': ('Poète', []),
    'Pole': ('Perche', ['Mât']),
    'Poll': ('Tête', ['Recenser']),
    'Pound': ('Livre', ['Frapper']),
    'Poverty': ('Pauvreté', []),
    'Praise': ('Louer', ['Louange']),
    'Present': ('Présenter', ['Présent']),
    'Press': ('Presser', ['Pressoir']),
    'Prevent': ('Empêcher', []),
    'Prey': ('Proie', []),
    'Price': ('Prix', []),
    'Prick': ('Aiguillon', ['Piquer']),
    'Principal': ('Principal', []),
    'Prize': ('Prix', ['Récompense']),
    'Prove': ('Prouver', ['Éprouver']),
    'Purge': ('Purifier', []),
    'Purity': ('Pureté', []),
    'Purple': ('Pourpre', []),
    # Q
    'Quail': ('Caille', []),
    'Quarrel': ('Querelle', []),
    'Quench': ('Éteindre', ['Étancher']),
    'Question': ('Question', []),
    'Quiet': ('Silencieux', ['Paisible']),
    'Quit': ('Quitter', []),
    # R
    'Radiant': ('Rayonnant', ['Radieux']),
    'Rag': ('Haillon', ['Guenille']),
    'Raid': ('Raid', ['Incursion']),
    'Raiment': ('Vêtement', ['Habit']),
    'Raise': ('Élever', ['Relever']),
    'Rampart': ('Rempart', []),
    'Range': ('Rangée', ['Portée']),
    'Rank': ('Rang', []),
    'Ready': ('Prêt', []),
    'Rebuke': ('Réprimander', ['Réprimande']),
    'Record': ('Enregistrement', ['Mémoire']),
    'Red': ('Rouge', []),
    'Reform': ('Réforme', []),
    'Refuge': ('Refuge', []),
    'Refuse': ('Refuser', ['Rebut']),
    'Reign': ('Régner', ['Règne']),
    'Release': ('Libération', ['Délivrance']),
    'Remnant': ('Reste', ['Résidu']),
    'Renew': ('Renouveler', []),
    'Repair': ('Réparer', []),
    'Require': ('Exiger', ['Requérir']),
    'Reward': ('Récompense', []),
    'Rib': ('Côte', []),
    'Riches': ('Richesses', []),
    'Right': ('Droit', ['Juste']),
    'Riot': ('Émeute', ['Débauche']),
    'Roast': ('Rôtir', []),
    'Rod': ('Verge', ['Bâton']),
    'Root': ('Racine', []),
    'Rope': ('Corde', []),
    'Royal': ('Royal', []),
    'Rude': ('Grossier', ['Rude']),
    'Rug': ('Tapis', []),
    'Ruin': ('Ruine', []),
    'Rump': ('Croupe', ['Queue']),
    'Rush': ('Se précipiter', ['Jonc']),
    'Rust': ('Rouille', []),
    # S
    'Saddle': ('Selle', []),
    'Sale': ('Vente', []),
    'Sand': ('Sable', []),
    'Save': ('Sauver', []),
    'Scaffold': ('Échafaud', ['Échafaudage']),
    'Scale': ('Écaille', ['Balance']),
    'Scent': ('Odeur', ['Parfum']),
    'School': ('École', []),
    'Scorn': ('Mépriser', ['Mépris']),
    'Scroll': ('Rouleau', []),
    'Scurvy': ('Scorbut', ['Gale']),
    'Search': ('Chercher', ['Rechercher']),
    'Seat': ('Siège', []),
    'Secret': ('Secret', []),
    'See': ('Voir', []),
    'Seed': ('Semence', ['Graine']),
    'Sent': ('Envoyé', []),
    'Separate': ('Séparer', []),
    'Set': ('Placer', ['Établir']),
    'Seventy': ('Soixante-dix', []),
    'Shaft': ('Hampe', ['Puits']),
    'Shame': ('Honte', []),
    'Shape': ('Forme', []),
    'Share': ('Part', ['Partager']),
    'Shawl': ('Châle', []),
    'Shear': ('Tondre', []),
    'Sheath': ('Fourreau', ['Gaine']),
    'Sheet': ('Drap', ['Feuille']),
    'Sheriff': ('Shérif', ['Officier']),
    'Shine': ('Briller', ['Luire']),
    'Shore': ('Rivage', ['Côte']),
    'Show': ('Montrer', []),
    'Shroud': ('Linceul', []),
    'Shrub': ('Arbuste', ['Buisson']),
    'Siege': ('Siège', []),
    'Sign': ('Signe', []),
    'Simple': ('Simple', []),
    'Sinew': ('Tendon', ['Nerf']),
    'Sir': ('Monsieur', ['Seigneur']),
    'Sixty': ('Soixante', []),
    'Skin': ('Peau', []),
    'Skirt': ('Pan', ['Jupe']),
    'Skull': ('Crâne', []),
    'Sky': ('Ciel', []),
    'Sleep': ('Dormir', ['Sommeil']),
    'Slip': ('Glisser', []),
    'Slow': ('Lent', []),
    'Smell': ('Odeur', ['Sentir']),
    'Smoke': ('Fumée', []),
    'Sneeze': ('Éternuer', []),
    'Soldier': ('Soldat', []),
    'Sometime': ('Autrefois', ['Parfois']),
    'Sore': ('Douloureux', ['Plaie']),
    'Sorrow': ('Tristesse', ['Chagrin']),
    'Soul': ('Âme', []),
    'Sound': ('Son', ['Sain']),
    'Sour': ('Aigre', []),
    'Span': ('Empan', ['Mesure']),
    'Spark': ('Étincelle', []),
    'Speech': ('Parole', ['Discours']),
    'Spelt': ('Épeautre', []),
    'Spirit': ('Esprit', []),
    'Spoil': ('Butin', ['Piller']),
    'Spoon': ('Cuillère', []),
    'Spy': ('Espion', []),
    'Stack': ('Meule', ['Tas']),
    'Staff': ('Bâton', ['Perche']),
    'Stair': ('Marche', ['Escalier']),
    'Stake': ('Pieu', ['Poteau']),
    'Stalk': ('Tige', []),
    'Stall': ('Étable', ['Stalle']),
    'Stature': ('Stature', ['Taille']),
    'Stay': ('Rester', ['Demeurer']),
    'Still': ('Encore', ['Tranquille']),
    'Stock': ('Tronc', ['Souche']),
    'Stomach': ('Estomac', []),
    'Stool': ('Tabouret', []),
    'Story': ('Histoire', ['Récit']),
    'Strain': ('Tendre', ['Filtrer']),
    'Stream': ('Ruisseau', ['Courant']),
    'Street': ('Rue', []),
    'Strike': ('Frapper', []),
    'Strive': ('Lutter', ['S\'efforcer']),
    'Stronghold': ('Forteresse', []),
    'Stuff': ('Étoffe', ['Effets']),
    'Supply': ('Fournir', ['Approvisionner']),
    'Sweat': ('Sueur', []),
    'Swell': ('Enfler', ['Gonfler']),
    'Swift': ('Rapide', ['Prompt']),
    # T
    'Table': ('Table', []),
    'Tail': ('Queue', []),
    'Take': ('Prendre', []),
    'Tassel': ('Frange', ['Houppe']),
    'Taste': ('Goût', ['Goûter']),
    'Teat': ('Mamelle', []),
    'Tell': ('Dire', ['Raconter']),
    'Tenth': ('Dixième', []),
    'Thicket': ('Fourré', ['Hallier']),
    'Thief': ('Voleur', []),
    'Thigh': ('Cuisse', []),
    'Think': ('Penser', []),
    'Third': ('Troisième', []),
    'Thirst': ('Soif', []),
    'Thought': ('Pensée', []),
    'Thousand': ('Mille', []),
    'Three': ('Trois', []),
    'Time': ('Temps', []),
    'Title': ('Titre', []),
    'Tomorrow': ('Demain', []),
    'Tongue': ('Langue', []),
    'Torch': ('Torche', ['Flambeau']),
    'Town': ('Ville', ['Bourgade']),
    'Trade': ('Métier', ['Commerce']),
    'Trap': ('Piège', []),
    'Tread': ('Fouler', ['Marcher']),
    'Treason': ('Trahison', []),
    'Tree': ('Arbre', []),
    'Trench': ('Fossé', ['Tranchée']),
    'Trim': ('Parer', ['Ajuster']),
    'Triumph': ('Triomphe', []),
    'Troop': ('Troupe', []),
    'Trough': ('Auge', ['Abreuvoir']),
    'Tutor': ('Précepteur', ['Tuteur']),
    'Twelve': ('Douze', []),
    'Twenty': ('Vingt', []),
    'Twilight': ('Crépuscule', []),
    'Twine': ('Fil retors', []),
    'Two': ('Deux', []),
    # U
    'Uncle': ('Oncle', []),
    'Undertake': ('Entreprendre', []),
    'Unequal': ('Inégal', []),
    'Uttermost': ('Extrême', ['Le plus éloigné']),
    # V
    'Vain': ('Vain', ['Futile']),
    'Vapor': ('Vapeur', []),
    'Vault': ('Voûte', []),
    'Vein': ('Veine', []),
    'Very': ('Très', []),
    'Vessel': ('Vase', ['Vaisseau']),
    'Vineyard': ('Vigne', ['Vignoble']),
    # W
    'Wait': ('Attendre', []),
    'Walk': ('Marcher', []),
    'Wallet': ('Besace', ['Bourse']),
    'Ward': ('Garde', ['Pupille']),
    'Warp': ('Chaîne', ['Trame']),
    'Wasp': ('Guêpe', []),
    'Watch': ('Veiller', ['Garde']),
    'Watchman': ('Sentinelle', ['Veilleur']),
    'Way': ('Chemin', ['Voie']),
    'Web': ('Toile', []),
    'Weight': ('Poids', []),
    'West': ('Ouest', ['Occident']),
    'Whelp': ('Petit', ['Lionceau']),
    'Whirlwind': ('Tourbillon', []),
    'Will': ('Volonté', []),
    'Wind': ('Vent', []),
    'Wink': ('Clin d\'œil', []),
    'Witty': ('Ingénieux', []),
    'Word': ('Parole', ['Mot']),
    'Wrest': ('Déformer', ['Pervertir']),
    'Wrinkle': ('Ride', []),
    # Y
    'Yea': ('Oui', ['Certes']),
    'Yellow': ('Jaune', []),
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

    if args.apply and not check_backup():
        print("ERREUR : backup manquant")
        sys.exit(1)

    with open(FILTERED_JSON, encoding='utf-8') as f:
        doc = json.load(f)
    real = doc['items']

    mapped = []
    skipped = []
    for s in real:
        mot = s['mot']
        if mot in SKIP_PROPER_NOUNS or mot not in MAP:
            skipped.append(s)
            continue
        fr, aliases = MAP[mot]
        mapped.append({**s, 'fr': fr, 'aliases': aliases})

    print(f'Input   : {len(real)}')
    print(f'Mapped  : {len(mapped)}')
    print(f'Skipped : {len(skipped)}')
    if skipped:
        print(f'\n=== Non mappés ({len(skipped)}) ===')
        for s in skipped[:20]:
            print(f"  {s['mot']}")
        if len(skipped) > 20:
            print(f'  ... ({len(skipped)-20} autres)')

    with open(CONCEPTS_JSON, encoding='utf-8') as f:
        concepts = json.load(f)
    with open(CONCEPT_META_JSON, encoding='utf-8') as f:
        meta = json.load(f)

    by_chunk = {}
    for m in mapped:
        by_chunk.setdefault(m['chunk'], []).append(m)

    chunks_data = {}
    chunk_changes = 0
    for chunk_name in sorted(by_chunk.keys()):
        chunk_path = ISBE_DIR / chunk_name
        with open(chunk_path, encoding='utf-8-sig') as f:
            entries = json.load(f)
        by_id = {e['id']: e for e in entries}
        local = 0
        for m in by_chunk[chunk_name]:
            entry = by_id.get(m['entry_id'])
            if entry and patch_chunk_entry(entry, m['fr'], m['aliases'], m['mot']):
                local += 1
        if local:
            chunks_data[chunk_name] = entries
            chunk_changes += local

    concept_changes = []
    for m in mapped:
        cid = m['concept_id']
        c = next((c for c in concepts if c['concept_id'] == cid), None)
        if not c:
            continue
        before = c.get('label', '')
        if patch_concept(c, m['fr'], m['aliases'], m['mot']):
            concept_changes.append((cid, before, m['fr']))
            if cid in meta:
                meta[cid]['l'] = m['fr']
                meta[cid]['p'] = m['fr']
                meta[cid]['s'] = m['mot']

    print(f'\nChunks entries modifiées : {chunk_changes}')
    print(f'Chunks files à écrire    : {len(chunks_data)}')
    print(f'Concepts patchés         : {len(concept_changes)}')

    # Dry-run MD
    lines = [f'# C9 Dry-run — {len(mapped)} translations', '', '| mot EN | label_fr | aliases |', '|---|---|---|']
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
            'pass': 'C9-category-B',
            'mapped_count': len(mapped),
            'chunk_entries_modified': chunk_changes,
            'concepts_patched': len(concept_changes),
            'chunks_written': sorted(chunks_data.keys()),
        }
        with open(LOG_JSON, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        print(f'\nLog : {LOG_JSON}')


if __name__ == '__main__':
    main()
