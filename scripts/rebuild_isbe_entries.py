#!/usr/bin/env python3
"""Rebuild isbe.entries.json from letter chunks with French label_fr translations."""
import json, re, os, glob, unicodedata, sys

sys.stdout.reconfigure(encoding='utf-8')

isbe_dir = 'uploads/dictionnaires/isbe'

# Load all chunks in order
entries = []
for path in sorted(glob.glob(os.path.join(isbe_dir, 'isbe-*.json'))):
    with open(path, 'r', encoding='utf-8-sig') as f:
        entries.extend(json.load(f))

print(f"Loaded {len(entries)} entries from chunks")

# Translation map for common English words in ISBE titles
TITLE_TRANSLATIONS = {
    'Of': 'de', 'The': 'le/la', 'And': 'et', 'In': 'dans/en',
    'For': 'pour', 'To': 'de', 'At': 'de', 'By': 'par',
    'On': 'sur', 'Or': 'ou', 'With': 'avec', 'From': 'de',
    'As': 'comme', 'Book': 'Livre', 'Books': 'Livres',
    'Children': 'Enfants', 'City': 'Ville', 'Day': 'Jour',
    'Epistle': 'Epitre', 'Epistles': 'Epitres', 'Gospel': 'Evangile',
    'History': 'Histoire', 'Kingdom': 'Royaume', 'Land': 'Terre',
    'Life': 'Vie', 'Mount': 'Mont', 'Mountain': 'Montagne',
    'Names': 'Noms', 'People': 'Peuple', 'Psalm': 'Psaume',
    'Psalms': 'Psaumes', 'River': 'Fleuve', 'Sea': 'Mer',
    'Song': 'Cantique', 'Songs': 'Cantiques', 'Temple': 'Temple',
    'Valley': 'Vallee', 'Waters': 'Eaux', 'Water': 'Eau',
    'Great': 'Grand', 'Old': 'Ancien', 'New': 'Nouveau',
    'First': 'Premier', 'Second': 'Deuxieme', 'Third': 'Troisieme',
    'Fourth': 'Quatrieme', 'High': 'Grand', 'Holy': 'Saint',
    'Rod': 'Baton', 'Rock': 'Rocher', 'Tower': 'Tour',
    'Gate': 'Porte', 'Gates': 'Portes', 'Well': 'Puits',
    'Pool': 'Bassin', 'Plain': 'Plaine', 'Brook': 'Torrent',
    'Spring': 'Source', 'Hill': 'Colline', 'Stone': 'Pierre',
    'Stones': 'Pierres', 'Tree': 'Arbre', 'Trees': 'Arbres',
    'House': 'Maison', 'Offering': 'Offrande', 'Offerings': 'Offrandes',
    'Sacrifice': 'Sacrifice', 'Priest': 'Pretre', 'Priests': 'Pretres',
    'Prophet': 'Prophete', 'Prophets': 'Prophetes', 'King': 'Roi',
    'Kings': 'Rois', 'Son': 'Fils', 'Sons': 'Fils',
    'Father': 'Pere', 'Mother': 'Mere', 'Brother': 'Frere',
    'Sister': 'Soeur', 'Daughter': 'Fille', 'Wife': 'Epouse',
    'Church': 'Assemblee', 'Angel': 'Ange', 'Angels': 'Anges',
    'Ancient': 'Ancien', 'Days': 'Jours', 'Night': 'Nuit',
    'Light': 'Lumiere', 'Fire': 'Feu', 'Blood': 'Sang',
    'Death': 'Mort', 'Commandment': 'Commandement',
    'Commandments': 'Commandements', 'Law': 'Loi',
    'Covenant': 'Alliance', 'Promise': 'Promesse',
    'Prayer': 'Priere', 'Worship': 'Adoration',
    'Baptism': 'Bapteme', 'Marriage': 'Mariage',
    'Government': 'Gouvernement', 'War': 'Guerre',
    'Peace': 'Paix', 'Sin': 'Peche', 'Grace': 'Grace',
    'Faith': 'Foi', 'Hope': 'Esperance', 'Love': 'Amour',
    'Judgment': 'Jugement', 'Salvation': 'Salut',
    'Redemption': 'Redemption', 'Creation': 'Creation',
    'Education': 'Education', 'Family': 'Famille',
    'Seven': 'Sept', 'Twelve': 'Douze',
    'Versions': 'Versions', 'Version': 'Version',
    'Apocrypha': 'Apocryphes', 'Apocalypse': 'Apocalypse',
    'Creed': 'Credo', 'Fathers': 'Peres',
    'Exaltation': 'Exaltation', 'Offices': 'Offices',
    'Letters': 'Lettres', 'Letter': 'Lettre',
    'Testament': 'Testament', 'Testaments': 'Testaments',
}

# Proper name translations
PROPER_NAMES_FR = {
    'Aaron': 'Aaron', 'Abraham': 'Abraham', 'Moses': 'Moise',
    'David': 'David', 'Solomon': 'Salomon', 'Isaiah': 'Esaie',
    'Jeremiah': 'Jeremie', 'Ezekiel': 'Ezechiel', 'Daniel': 'Daniel',
    'Elijah': 'Elie', 'Elisha': 'Elisee', 'Joshua': 'Josue',
    'Samuel': 'Samuel', 'Paul': 'Paul', 'Peter': 'Pierre',
    'John': 'Jean', 'James': 'Jacques', 'Luke': 'Luc',
    'Mark': 'Marc', 'Matthew': 'Matthieu', 'Mary': 'Marie',
    'Joseph': 'Joseph', 'Judas': 'Judas', 'Simon': 'Simon',
    'Philip': 'Philippe', 'Andrew': 'Andre', 'Timothy': 'Timothee',
    'Titus': 'Tite', 'Philemon': 'Philemon', 'Stephen': 'Etienne',
    'Barnabas': 'Barnabas', 'Herod': 'Herode',
    'Israel': 'Israel', 'Babylon': 'Babylone', 'Egypt': 'Egypte',
    'Jerusalem': 'Jerusalem', 'Samaria': 'Samarie',
    'Syria': 'Syrie', 'Persia': 'Perse', 'Rome': 'Rome',
    'Greece': 'Grece', 'Arabia': 'Arabie',
    'Jordan': 'Jourdain', 'Euphrates': 'Euphrate',
    'Galilee': 'Galilee', 'Judah': 'Juda', 'Judea': 'Judee',
    'Canaan': 'Canaan', 'Moab': 'Moab', 'Edom': 'Edom',
    'Sinai': 'Sinai', 'Zion': 'Sion', 'Lebanon': 'Liban',
    'Bethlehem': 'Bethleem', 'Nazareth': 'Nazareth',
    'Corinth': 'Corinthe', 'Ephesus': 'Ephese',
    'Thessalonica': 'Thessalonique', 'Antioch': 'Antioche',
    'Philippi': 'Philippes',
    'Genesis': 'Genese', 'Exodus': 'Exode', 'Leviticus': 'Levitique',
    'Numbers': 'Nombres', 'Deuteronomy': 'Deuteronome',
    'Judges': 'Juges', 'Ruth': 'Ruth', 'Esther': 'Esther',
    'Job': 'Job', 'Proverbs': 'Proverbes', 'Ecclesiastes': 'Ecclesiaste',
    'Lamentations': 'Lamentations', 'Ezra': 'Esdras',
    'Nehemiah': 'Nehemie', 'Chronicles': 'Chroniques',
    'Revelation': 'Apocalypse', 'Hebrews': 'Hebreux',
    'Romans': 'Romains', 'Corinthians': 'Corinthiens',
    'Galatians': 'Galates', 'Ephesians': 'Ephesiens',
    'Philippians': 'Philippiens', 'Colossians': 'Colossiens',
    'Thessalonians': 'Thessaloniciens',
    'Pentateuch': 'Pentateuque', 'Psalter': 'Psautier',
    'Septuagint': 'Septante',
}

FULL_TITLE_FR = {
    "Aaron'S Rod": "Baton d'Aaron",
    "Abomination Of Desolation": "Abomination de la desolation",
    "Abraham, Book Of": "Livre d'Abraham",
    "Acts Of Pilate": "Actes de Pilate",
    "Acts Of Solomon": "Actes de Salomon",
    "Acts Of The Apostles": "Actes des Apotres",
    "Adam In The New Testament": "Adam dans le Nouveau Testament",
    "Adam In The Old Testament": "Adam dans l'Ancien Testament",
    "Adam In The Old Testament And The Apocrypha": "Adam dans l'Ancien Testament et les Apocryphes",
    "Adam, Books Of": "Livres d'Adam",
    "Adam, City Of": "Ville d'Adam",
    "Alexander, The Great": "Alexandre le Grand",
    "Alpha And Omega": "Alpha et Omega",
    "Ancient Of Days": "Ancien des Jours",
    "Angel Of God": "Ange d'Elohim",
    "Angel Of Yahweh": "Ange de YHWH",
    "Angels Of The Seven Churches": "Anges des sept Assemblees",
    "Antioch, In Syria": "Antioche de Syrie",
    "Antioch, Of Pisidia": "Antioche de Pisidie",
    "Apocalypse Of Baruch": "Apocalypse de Baruch",
    "Apostles' Creed; The": "Credo des Apotres",
    "Apostles, Gospel Of The Twelve": "Evangile des Douze Apotres",
    "Apostolic Fathers, Epistles Of": "Epitres des Peres apostoliques",
    "Apple, Of The Eye": "Prunelle de l'oeil",
    "Apples Of Sodom": "Pommes de Sodome",
    "Ark Of Bulrushes": "Arche de joncs",
    "Ark Of Noah": "Arche de Noe",
    "Ark Of Testimony": "Arche du Temoignage",
    "Ark Of The Covenant": "Arche de l'Alliance",
    "Baptism Of The Holy Spirit": "Bapteme du Saint-Esprit",
    "Between The Testaments": "Entre les Testaments",
    "Birds Of Prey": "Oiseaux de proie",
    "Book Of Life": "Livre de Vie",
    "Book Of The Covenant": "Livre de l'Alliance",
    "Book Of The Dead": "Livre des Morts",
    "Books Of Adam": "Livres d'Adam",
    "Bread Of The Presence": "Pain de la Presence",
    "Children Of God": "Enfants d'Elohim",
    "Christ, Offices Of": "Offices du Mashiah",
    "Christ, The Exaltation Of": "Exaltation du Mashiah",
    "Church Government": "Gouvernement de l'Assemblee",
    "City Of David": "Cite de David",
    "Covenant, In The Old Testament": "Alliance dans l'Ancien Testament",
    "Covenant, The New": "Nouvelle Alliance",
    "Day Of Atonement": "Jour des Expiations",
    "Day Of The Lord (Yahweh)": "Jour de YHWH",
    "Fear Of God": "Crainte d'Elohim",
    "Feast Of Dedication": "Fete de la Dedicace",
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
    "Gospel Of The Twelve": "Evangile des Douze",
    "House Of God": "Maison d'Elohim",
    "In The Lord": "Dans le Seigneur",
    "Israel, History Of": "Histoire d'Israel",
    "Israel, Religion Of": "Religion d'Israel",
    "Jesus Christ": "Yehoshoua Mashiah",
    "Jesus Christ In The Old Testament": "Yehoshoua Mashiah dans l'Ancien Testament",
    "John, The Epistles Of": "Epitres de Jean",
    "John, The Gospel Of": "Evangile de Jean",
    "King, Christ As": "Le Mashiah comme Roi",
    "Kingdom Of God": "Royaume d'Elohim",
    "Kingdom Of Heaven": "Royaume des Cieux",
    "Lamb Of God": "Agneau d'Elohim",
    "Land Of Promise": "Terre Promise",
    "Law Of Moses": "Loi de Moise",
    "Lord'S Day, The": "Jour du Seigneur",
    "Lord'S Prayer, The": "Priere du Seigneur",
    "Lord'S Supper; (Eucharist)": "Repas du Seigneur (Eucharistie)",
    "Love Of God": "Amour d'Elohim",
    "Man Of Sin": "Homme de peche",
    "Man, Son Of": "Fils de l'Homme",
    "Mount Of Olives": "Mont des Oliviers",
    "Mountain Of God": "Montagne d'Elohim",
    "Name Of God": "Nom d'Elohim",
    "Names Of God": "Noms d'Elohim",
    "Obedience Of Christ": "Obeissance du Mashiah",
    "Paul, The Apostle": "Paul l'Apotre",
    "People Of God": "Peuple d'Elohim",
    "Peter, The First Epistle Of": "Premiere Epitre de Pierre",
    "Peter, The Second Epistle Of": "Deuxieme Epitre de Pierre",
    "Pillar Of Cloud And Fire": "Colonne de nuee et de feu",
    "Priest, High": "Grand Pretre",
    "Promised Land": "Terre Promise",
    "Psalms, Book Of": "Livre des Psaumes",
    "Red Sea": "Mer Rouge",
    "Sea Of Glass": "Mer de verre",
    "Sermon On The Mount": "Sermon sur la Montagne",
    "Song Of Solomon": "Cantique de Salomon",
    "Song Of Songs": "Cantique des Cantiques",
    "Spirit Of God": "Esprit d'Elohim",
    "Star Of The Magi": "Etoile des Mages",
    "Stone Of Stumbling": "Pierre d'achoppement",
    "Temple Of Jerusalem": "Temple de Jerusalem",
    "Tower Of Babel": "Tour de Babel",
    "Tree Of Knowledge": "Arbre de la Connaissance",
    "Tree Of Life": "Arbre de Vie",
    "Tribes Of Israel": "Tribus d'Israel",
    "Wisdom Of Solomon, The": "Sagesse de Salomon",
    "Word Of God": "Parole d'Elohim",
    "Wrath Of God": "Colere d'Elohim",
}

def translate_title(mot):
    """Translate an ISBE title to French."""
    if not mot:
        return mot

    # 1. Check full title dictionary first
    if mot in FULL_TITLE_FR:
        return FULL_TITLE_FR[mot]

    # 2. Check proper name dictionary
    if mot in PROPER_NAMES_FR:
        return PROPER_NAMES_FR[mot]

    # 3. If no English function words, keep as-is (proper name)
    if not re.search(r'\b(?:Of|The|And|In|For|To|At|By|On|Or|With|From|As)\b', mot):
        return mot

    # 4. For remaining titles with "Of", "The" etc., keep original
    # (better to keep English title than produce bad French)
    return mot


def slugify(text):
    s = unicodedata.normalize('NFD', text)
    s = re.sub(r'[\u0300-\u036f]', '', s)
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


# Build enriched entries
enriched = []
seen_slugs = set()
translated_count = 0

for i, e in enumerate(entries):
    mot = e.get('mot', '')
    defn = e.get('definition', '')
    defn_len = len(defn)

    # Translate label
    label_fr = translate_title(mot)
    if label_fr != mot:
        translated_count += 1

    # Render mode
    if defn_len <= 420:
        render_mode = 'direct'
    elif defn_len <= 1800:
        render_mode = 'preview_expand'
    else:
        render_mode = 'deep_read'

    # Slug
    slug = slugify(mot)
    if slug in seen_slugs:
        slug = f"{slug}-{i}"
    seen_slugs.add(slug)

    # Letter
    letter = mot[0].upper() if mot else '#'
    if not letter.isalpha():
        letter = '#'

    entry = {
        'id': f'isbe-{i+1:06d}',
        'dictionary': 'isbe',
        'source_order': i + 1,
        'mot': mot,
        'source_title_en': mot,
        'label_fr': label_fr,
        'mot_restore': '',
        'mot_restore_method': 'none',
        'aliases': [],
        'slug': slug,
        'letter': letter,
        'definition': defn,
        'definition_length': defn_len,
        'display_role': 'deep_read',
        'render_mode_default': render_mode,
        'category_hint': '',
        'concept_hint': '',
        'status': 'ready',
        'quality_flags': []
    }
    enriched.append(entry)

# Write
out_path = os.path.join(isbe_dir, 'isbe.entries.json')
with open(out_path, 'w', encoding='utf-8-sig') as f:
    json.dump(enriched, f, ensure_ascii=False, indent=2)

size_mb = os.path.getsize(out_path) / (1024 * 1024)
render_dist = {}
for e in enriched:
    rm = e['render_mode_default']
    render_dist[rm] = render_dist.get(rm, 0) + 1

print(f"Enriched: {len(enriched)} entries")
print(f"Titles translated: {translated_count}")
print(f"File: {out_path} ({size_mb:.1f} MB)")
print(f"Render modes: {render_dist}")

# Show samples
print("\nSample translations:")
samples = ['Aaron\'S Rod', 'Abomination Of Desolation', 'Acts Of The Apostles',
           'Alpha And Omega', 'Angel Of God', 'Ancient Of Days',
           'Book Of Life', 'Children Of God', 'Day Of The Lord (Yahweh)']
for s in samples:
    t = translate_title(s)
    if t != s:
        print(f"  {s} -> {t}")
