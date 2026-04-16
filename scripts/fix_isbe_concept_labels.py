#!/usr/bin/env python3
"""Translate English labels on ISBE-only concepts to French."""
import json, re, sys

sys.stdout.reconfigure(encoding='utf-8')

with open('uploads/dictionnaires/concepts.json', 'r', encoding='utf-8-sig') as f:
    concepts = json.load(f)

# Full title translations (high-confidence manual translations)
FULL_FR = {
    "Abomination Of Desolation": "Abomination de la desolation",
    "Acts Of Pilate": "Actes de Pilate",
    "Acts Of Solomon": "Actes de Salomon",
    "Adam In The New Testament": "Adam dans le Nouveau Testament",
    "Adam In The Old Testament": "Adam dans l'Ancien Testament",
    "Adam In The Old Testament And The Apocrypha": "Adam dans l'AT et les Apocryphes",
    "Adrammelech And Anammelech": "Adrammelech et Anammelech",
    "After; Afterward": "Apres",
    "Against": "Contre",
    "Ages, Rock Of": "Rocher des Ages",
    "Ahab And Zedekiah": "Achab et Sedecias",
    "Alpha And Omega": "Alpha et Omega",
    "Ancient Of Days": "Ancien des Jours",
    "Angel Of God": "Ange d'Elohim",
    "Angel Of Yahweh": "Ange de YHWH",
    "Angels Of The Seven Churches": "Anges des sept Assemblees",
    "Apocalypse Of Baruch": "Apocalypse de Baruch",
    "Apostles' Creed; The": "Credo des Apotres",
    "Apostles, Gospel Of The Twelve": "Evangile des Douze Apotres",
    "Apostolic Fathers, Epistles Of": "Epitres des Peres apostoliques",
    "Apple, Of The Eye": "Prunelle de l'oeil",
    "Apples Of Sodom": "Pommes de Sodome",
    "Arabic Gospel Of The Infancy": "Evangile arabe de l'Enfance",
    "Arabic History Of Joseph The Carpenter": "Histoire arabe de Joseph le Charpentier",
    "Ark Of Bulrushes": "Corbeille de joncs",
    "Ark Of Noah": "Arche de Noe",
    "Ark Of Testimony": "Arche du Temoignage",
    "Ark Of The Covenant": "Arche de l'Alliance",
    "Armenian Versions, Of The Bible": "Versions armeniennes de la Bible",
    "Arrest, And Trial Of Jesus": "Arrestation et proces de Yehoshoua",
    "As": "Comme",
    "Ascension Of Isaiah": "Ascension d'Esaie",
    "Asochis, Plain Of": "Plaine d'Asochis",
    "Assemblies, Masters Of": "Maitres des assemblees",
    "Assumption Of Moses": "Assomption de Moise",
    "Assyria And Babylonia, Religion Of": "Religion d'Assyrie et de Babylonie",
    "Assyrian And Babylonian Libraries": "Bibliotheques assyriennes et babyloniennes",
    "At One": "En accord",
    "Authority; Authority In General": "Autorite ; Autorite en general",
    "Away With": "Enlever",
    "Balm Of Gilead": "Baume de Galaad",
    "Baptism Of The Holy Spirit": "Bapteme du Saint-Esprit",
    "Battle-Bow": "Arc de guerre",
    "Battle-Ax": "Hache de guerre",
    "Bear; Borne": "Porter",
    "Beaten Gold": "Or battu",
    "Between The Testaments": "Entre les Testaments",
    "Bind; Bound": "Lier",
    "Birds Of Abomination": "Oiseaux d'abomination",
    "Birds Of Prey": "Oiseaux de proie",
    "Blood, Avenger (Revenger) Of": "Vengeur du sang",
    "Blood, Field Of": "Champ du sang",
    "Blood, Issue Of": "Perte de sang",
    "Book Of Life": "Livre de Vie",
    "Book Of The Covenant": "Livre de l'Alliance",
    "Books Of Adam": "Livres d'Adam",
    "Bread Of The Presence": "Pain de la Presence",
    "By And By": "Bientot",
    "Calf, Golden": "Veau d'or",
    "Canon Of The New Testament": "Canon du Nouveau Testament",
    "Canon Of The Old Testament": "Canon de l'Ancien Testament",
    "Children Of God": "Enfants d'Elohim",
    "Christ, Offices Of": "Offices du Mashiah",
    "Christ, The Exaltation Of": "Exaltation du Mashiah",
    "Church Government": "Gouvernement de l'Assemblee",
    "Circumcision, In The New Testament": "Circoncision dans le NT",
    "City Of David": "Cite de David",
    "Covenant, In The Old Testament": "Alliance dans l'Ancien Testament",
    "Covenant, The New": "Nouvelle Alliance",
    "Day Of Atonement": "Jour des Expiations",
    "Day Of Christ": "Jour du Mashiah",
    "Day Of The Lord (Yahweh)": "Jour de YHWH",
    "Dead Sea": "Mer Morte",
    "Dial Of Ahaz": "Cadran d'Achaz",
    "Door Of Hope": "Porte de l'esperance",
    "Education In The Old Testament": "Education dans l'AT",
    "Ephesians, Epistle To The": "Epitre aux Ephesiens",
    "Esther, Additions To": "Additions a Esther",
    "Eternal Life": "Vie eternelle",
    "Eternal Punishment": "Chatiment eternel",
    "Everlasting Fire": "Feu eternel",
    "Faith In The Old Testament": "Foi dans l'Ancien Testament",
    "Fall Of Man": "Chute de l'homme",
    "Family, The Christian": "Famille chretienne",
    "Fear Of God": "Crainte d'Elohim",
    "Feast Of Dedication": "Fete de la Dedicace",
    "Feast Of Lights": "Fete des Lumieres",
    "Feast Of Tabernacles": "Fete des Tabernacles",
    "Feast Of Unleavened Bread": "Fete des Pains sans levain",
    "Feast Of Weeks": "Fete des Semaines",
    "Fullness Of God": "Plenitude d'Elohim",
    "Glory Of God": "Gloire d'Elohim",
    "God, Names Of": "Noms d'Elohim",
    "God, Children Of": "Enfants d'Elohim",
    "God, The Living": "Elohim vivant",
    "God, Image Of": "Image d'Elohim",
    "God, Son Of": "Fils d'Elohim",
    "God, Sons Of": "Fils d'Elohim",
    "God, Word Of": "Parole d'Elohim",
    "Gospels, The Synoptic": "Evangiles synoptiques",
    "Grace In The Old Testament": "Grace dans l'AT",
    "House Of God": "Maison d'Elohim",
    "In The Lord": "Dans le Seigneur",
    "Israel, History Of": "Histoire d'Israel",
    "Israel, Religion Of": "Religion d'Israel",
    "Jesus Christ": "Yehoshoua Mashiah",
    "John, The Epistles Of": "Epitres de Jean",
    "John, The Gospel Of": "Evangile de Jean",
    "Jubilee, Year Of": "Annee du Jubile",
    "Kingdom Of God": "Royaume d'Elohim",
    "Kingdom Of Heaven": "Royaume des Cieux",
    "King, Christ As": "Le Mashiah comme Roi",
    "Lamb Of God": "Agneau d'Elohim",
    "Land Of Promise": "Terre Promise",
    "Law Of Moses": "Loi de Moise",
    "Lord'S Day, The": "Jour du Seigneur",
    "Lord'S Prayer, The": "Priere du Seigneur",
    "Lord'S Supper; (Eucharist)": "Repas du Seigneur",
    "Lord; The Lord": "Seigneur",
    "Love Of God": "Amour d'Elohim",
    "Man Of Sin": "Homme de peche",
    "Man, Son Of": "Fils de l'homme",
    "Marriage In The New Testament": "Mariage dans le NT",
    "Mount Of Olives": "Mont des Oliviers",
    "Mountain Of God": "Montagne d'Elohim",
    "Name Of God": "Nom d'Elohim",
    "Names Of God": "Noms d'Elohim",
    "New Commandment": "Nouveau commandement",
    "Obedience Of Christ": "Obeissance du Mashiah",
    "Paul, The Apostle": "Paul l'Apotre",
    "People Of God": "Peuple d'Elohim",
    "Peter, The First Epistle Of": "Premiere Epitre de Pierre",
    "Peter, The Second Epistle Of": "Deuxieme Epitre de Pierre",
    "Peter, Simon": "Simon Pierre",
    "Pillar Of Cloud And Fire": "Colonne de nuee et de feu",
    "Priest, High": "Grand Pretre",
    "Psalms, Book Of": "Livre des Psaumes",
    "Punishment, Everlasting": "Chatiment eternel",
    "Red Sea": "Mer Rouge",
    "Sabbath, In The New Testament": "Shabbat dans le NT",
    "Sea Of Glass": "Mer de verre",
    "Sermon On The Mount": "Sermon sur la Montagne",
    "Sin, Man Of": "Homme de peche",
    "Song Of Solomon": "Cantique de Salomon",
    "Song Of Songs": "Cantique des Cantiques",
    "Song Of The Three Children": "Cantique des Trois Enfants",
    "Spirit Of God": "Esprit d'Elohim",
    "Star Of The Magi": "Etoile des Mages",
    "Stone Of Stumbling": "Pierre d'achoppement",
    "Temple Of Jerusalem": "Temple de Jerusalem",
    "Testament, Old And New": "Testament, Ancien et Nouveau",
    "Tower Of Babel": "Tour de Babel",
    "Tree Of Knowledge": "Arbre de la Connaissance",
    "Tree Of Life": "Arbre de Vie",
    "Tribes Of Israel": "Tribus d'Israel",
    "Urim And Thummim": "Ourim et Toummim",
    "Versions Of The Scriptures": "Versions des Ecritures",
    "Wisdom Of Solomon, The": "Sagesse de Salomon",
    "Word Of God": "Parole d'Elohim",
    "Wrath Of God": "Colere d'Elohim",
}

# Word-level translations for remaining titles
WORD_FR = {
    'Of': 'de', 'The': '', 'And': 'et', 'In': 'dans', 'For': 'pour',
    'To': 'a', 'At': 'a', 'By': 'par', 'On': 'sur', 'Or': 'ou',
    'With': 'avec', 'From': 'de', 'As': 'comme', 'Between': 'entre',
    'Through': 'a travers', 'Under': 'sous', 'Upon': 'sur',
    'Into': 'dans', 'Before': 'avant', 'After': 'apres',
    'Against': 'contre', 'Among': 'parmi', 'Without': 'sans',
    'Book': 'Livre', 'Books': 'Livres', 'Epistle': 'Epitre',
    'Epistles': 'Epitres', 'Gospel': 'Evangile', 'History': 'Histoire',
    'Song': 'Cantique', 'Psalm': 'Psaume', 'Psalms': 'Psaumes',
    'Children': 'Enfants', 'Sons': 'Fils', 'Son': 'Fils',
    'Father': 'Pere', 'Fathers': 'Peres', 'Mother': 'Mere',
    'Brother': 'Frere', 'Sister': 'Soeur', 'Daughter': 'Fille',
    'Wife': 'Epouse', 'King': 'Roi', 'Kings': 'Rois',
    'Priest': 'Pretre', 'Priests': 'Pretres', 'Prophet': 'Prophete',
    'Angel': 'Ange', 'Angels': 'Anges', 'Church': 'Assemblee',
    'Temple': 'Temple', 'Kingdom': 'Royaume', 'Covenant': 'Alliance',
    'Sacrifice': 'Sacrifice', 'Offering': 'Offrande',
    'Mountain': 'Montagne', 'Mount': 'Mont', 'Valley': 'Vallee',
    'River': 'Fleuve', 'Sea': 'Mer', 'Lake': 'Lac',
    'City': 'Ville', 'Gate': 'Porte', 'Tower': 'Tour',
    'House': 'Maison', 'Land': 'Terre', 'Rock': 'Rocher',
    'Stone': 'Pierre', 'Tree': 'Arbre', 'Fire': 'Feu',
    'Water': 'Eau', 'Blood': 'Sang', 'Death': 'Mort',
    'Life': 'Vie', 'Light': 'Lumiere', 'Day': 'Jour',
    'Night': 'Nuit', 'Year': 'Annee', 'Versions': 'Versions',
    'Version': 'Version', 'Religion': 'Religion', 'Education': 'Education',
    'Government': 'Gouvernement', 'Marriage': 'Mariage',
    'Family': 'Famille', 'Baptism': 'Bapteme', 'Prayer': 'Priere',
    'Worship': 'Adoration', 'Faith': 'Foi', 'Grace': 'Grace',
    'Love': 'Amour', 'Hope': 'Esperance', 'Sin': 'Peche',
    'Judgment': 'Jugement', 'Salvation': 'Salut', 'War': 'Guerre',
    'Peace': 'Paix', 'Law': 'Loi', 'Old': 'Ancien', 'New': 'Nouveau',
    'Great': 'Grand', 'High': 'Grand', 'Holy': 'Saint',
    'Plain': 'Plaine', 'Pool': 'Bassin', 'Spring': 'Source',
    'Well': 'Puits', 'Brook': 'Torrent', 'Hill': 'Colline',
    'Libraries': 'Bibliotheques', 'Library': 'Bibliotheque',
    'Additions': 'Additions', 'Canon': 'Canon',
    'Circumcision': 'Circoncision', 'Sabbath': 'Shabbat',
    'Feast': 'Fete', 'Golden': 'Or', 'Calf': 'Veau',
    'Tabernacles': 'Tabernacles', 'Weeks': 'Semaines',
    'Unleavened': 'sans levain', 'Bread': 'Pain',
    'Eternal': 'Eternel', 'Everlasting': 'Eternel',
    'Punishment': 'Chatiment', 'Commandment': 'Commandement',
}

PROPER_FR = {
    'Moses': 'Moise', 'Isaiah': 'Esaie', 'Jeremiah': 'Jeremie',
    'Ezekiel': 'Ezechiel', 'Solomon': 'Salomon', 'David': 'David',
    'Abraham': 'Abraham', 'Noah': 'Noe', 'Jesus': 'Yehoshoua',
    'Christ': 'Mashiah', 'Paul': 'Paul', 'Peter': 'Pierre',
    'John': 'Jean', 'James': 'Jacques', 'Luke': 'Luc',
    'Mark': 'Marc', 'Matthew': 'Matthieu', 'Mary': 'Marie',
    'Joseph': 'Joseph', 'Elijah': 'Elie', 'Baruch': 'Baruch',
    'Israel': 'Israel', 'Jerusalem': 'Jerusalem', 'Babylon': 'Babylone',
    'Egypt': 'Egypte', 'Assyria': 'Assyrie', 'Babylonia': 'Babylonie',
    'Syria': 'Syrie', 'Gilead': 'Galaad', 'Moab': 'Moab',
    'Sodom': 'Sodome', 'Babel': 'Babel',
}

en_func = re.compile(r'\b(?:Of|The|And|In|For|To|At|By|On|Or|With|From|As|Between|Through|Under|Upon|Into|Before|After|Against|Among|Without)\b')

fixed = 0
for c in concepts:
    label = c.get('label', '')
    if not en_func.search(label):
        continue

    # Only fix ISBE-only or ISBE concepts
    sources = set(e.get('dictionary', '') for e in c.get('entries', []))
    if 'isbe' not in sources:
        continue

    # Try full translation first
    if label in FULL_FR:
        new_label = FULL_FR[label]
    else:
        # Word-by-word fallback
        words = re.split(r'(\s+|[,;:()])', label)
        translated = []
        for w in words:
            stripped = w.strip()
            if not stripped or re.match(r'^[\s,;:()]+$', w):
                translated.append(w)
            elif stripped in PROPER_FR:
                translated.append(PROPER_FR[stripped])
            elif stripped in WORD_FR:
                translated.append(WORD_FR[stripped])
            else:
                translated.append(w)
        new_label = ''.join(translated).strip()
        # Capitalize first letter
        if new_label and new_label[0].islower():
            new_label = new_label[0].upper() + new_label[1:]

    if new_label != label:
        c['label'] = new_label
        # Also update display_titles
        dt = c.get('display_titles', {})
        if dt.get('primary') == label:
            dt['primary'] = new_label
        if dt.get('strategy') == 'french_only':
            dt['primary'] = new_label
        c['display_titles'] = dt
        # Update public_forms
        pf = c.get('public_forms', {})
        if pf.get('french_reference') == label:
            pf['french_reference'] = new_label
        # Keep English in english_labels
        if label not in (pf.get('english_labels') or []):
            pf.setdefault('english_labels', []).append(label)
        c['public_forms'] = pf
        fixed += 1

with open('uploads/dictionnaires/concepts.json', 'w', encoding='utf-8') as f:
    json.dump(concepts, f, ensure_ascii=False, indent=2)

print(f"Concepts fixed: {fixed}")

# Verify
remaining = 0
for c in concepts:
    if en_func.search(c.get('label', '')):
        sources = set(e.get('dictionary', '') for e in c.get('entries', []))
        if 'isbe' in sources:
            remaining += 1

print(f"Remaining English labels on ISBE concepts: {remaining}")
PYEOF
