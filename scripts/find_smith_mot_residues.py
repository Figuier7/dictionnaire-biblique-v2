#!/usr/bin/env python3
"""Identifie les residus anglais dans le champ 'mot' de smith.entries.json."""

import json, re

with open("uploads/dictionnaires/smith/smith.entries.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Words identical in French (NOT residues)
true_french_too = {
    "A", "Ablution", "Adoption", "Ascension", "Calamus", "Cassia",
    "Centurion", "Chamois", "Champion", "Communion", "Concubine",
    "Concupiscence", "Conduit", "Confession", "Conscience", "Conversion",
    "Crucifixion", "Damnation", "Dispersion", "Divination", "Fable",
    "Famine", "Hallelujah", "Imputation", "Incarnation", "Inspiration",
    "Justification", "Mammon", "Millennium", "Miracle", "Passion",
    "Poison", "Prison", "Propitiation", "Providence", "Purification",
    "Repentance", "Tradition", "Vision", "Galbanum", "Martyr", "Millet",
    "Olive", "Onyx", "Oracle", "Rue", "Sceptre", "Synagogue",
    "Tabernacle", "Talent", "Testament", "Type", "Ablation",
    "Abstinence", "Agriculture", "Alliance", "Amen", "Antioche",
    "Canon", "Caravane", "Castration", "Commerce",
    "Construction", "Corail", "Diamant",
    "Esclave", "Exorcisme",
    "Fondation", "Gaze", "Idole",
    "Incantation", "Justice", "Latitude",
    "Longitude", "Massacre",
    "Nation", "Navigation", "Oblation",
    "Organisation", "Palestine",
    "Quarantaine", "Religion",
    "Sabbat", "Sacrifice", "Salutation",
    "Sanctification", "Sel", "Servitude",
    "Signal", "Superstition", "Suspension",
    "Tiare",
}

# Comprehensive list of English common words likely to appear
english_common_single = {
    "Abjects", "Ablution", "Ape", "Apes", "Armor", "Arms", "Arrow",
    "Arrows", "Axe",
    "Backslide", "Badger", "Bags", "Baking", "Banner", "Baptism",
    "Barn", "Basket", "Bath", "Bathing", "Bay", "Beacon", "Beam",
    "Bear", "Bed", "Bee", "Beetle", "Beggar", "Begging", "Bells",
    "Bellows", "Birth", "Bishop", "Blasphemy", "Blessing", "Blind",
    "Blindness", "Blood", "Boar", "Bondage", "Bottle", "Bow", "Bowl",
    "Bracelet", "Bramble", "Brass", "Bread", "Brick", "Bride",
    "Bridegroom", "Bridle", "Brimstone", "Brotherhood", "Buckler",
    "Bull", "Bullock", "Burial", "Butter",
    "Cabins", "Caldron", "Calf", "Calling", "Camel", "Camp",
    "Camphire", "Candle", "Candlestick", "Cane", "Captain", "Captive",
    "Captivity", "Cart", "Castle", "Caterpillar", "Cattle", "Cave",
    "Cedar", "Census", "Chain", "Chalk", "Chamberlain", "Chameleon",
    "Chancellor", "Chariot", "Charmer", "Cheese", "Chestnut",
    "Cinnamon", "Circumcision", "Cistern", "Citizenship", "Clay",
    "Closet", "Cloth", "Cloud", "Coal", "Coat", "Cock", "Cockatrice",
    "Cockle", "Coffin", "Collar", "Colors", "Colt", "Comb", "Coney",
    "Copper", "Coral", "Cord", "Corn", "Cotton", "Couch", "Council",
    "Coulter", "Covenant", "Cow", "Crane", "Creature", "Crib",
    "Cricket", "Crown", "Crystal", "Cuckoo", "Cucumber", "Cummin",
    "Cup", "Curtain", "Cymbal", "Cypress",
    "Dagger", "Darkness", "Dawn", "Deacon", "Deaconess", "Dead",
    "Deaf", "Death", "Debt", "Deer", "Deputy", "Desert", "Dew",
    "Diadem", "Dial", "Dog", "Door", "Dove", "Dragon", "Dream",
    "Dress", "Drink", "Dromedary", "Dross", "Drum", "Dulcimer",
    "Dumb", "Dungeon", "Dust", "Dwarf", "Dye", "Dyeing",
    "Eagle", "Ear", "Earring", "Earthquake", "Eating", "Ebony",
    "Eclipse", "Egg", "Elder", "Election", "Elm", "Embalming",
    "Emerald", "Emerods", "Enchantment", "Exorcist",
    "Fan", "Farthing", "Fasting", "Father", "Feast", "Feasts",
    "Fence", "Fetter", "Fever", "Fig", "File", "Fir", "Fire",
    "Firebrand", "Firstborn", "Fish", "Fishing", "Flag", "Flax",
    "Flea", "Flies", "Flint", "Flood", "Floor", "Flour", "Fly",
    "Foam", "Fool", "Foot", "Footman", "Ford", "Foreigner",
    "Forest", "Forge", "Fork", "Fortress", "Fountain", "Fowl", "Fox",
    "Frankincense", "Freedom", "Frog", "Frontlets", "Frost", "Fruit",
    "Fuel", "Fuller", "Fulness", "Funerals", "Furnace", "Furniture",
    "Gall", "Games", "Garden", "Garlic", "Garment", "Garner",
    "Garrison", "Gate", "Gazelle", "Genealogy", "Gift", "Girdle",
    "Glass", "Gleaning", "Glory", "Gnat", "Goad", "Goat", "Gold",
    "Goldsmith", "Goose", "Gopher", "Gourd", "Governor", "Grace",
    "Grape", "Grasshopper", "Grave", "Graving", "Greyhound",
    "Grinding", "Grove", "Guard", "Guest",
    "Hail", "Hair", "Hall", "Hammer", "Handkerchief", "Handmaid",
    "Hare", "Harlot", "Harp", "Harness", "Harrow", "Hart", "Harvest",
    "Hatred", "Haven", "Hawk", "Hay", "Hazel", "Heart", "Heath",
    "Heathen", "Heaven", "Hedgehog", "Heir", "Helmet", "Hemlock",
    "Hen", "Henna", "Herald", "Herbs", "Heresy", "Heron", "Highway",
    "Hind", "Hinge", "Hole", "Honey", "Hood", "Hook", "Hooks",
    "Hornet", "Horse", "Hospitality", "Host", "House", "Hunting",
    "Husband", "Husbandman", "Husks", "Hymn", "Hypocrite", "Hyssop",
    "Idol", "Idolatry", "Image", "Immortality", "Incense", "Ink",
    "Inkhorn", "Inn", "Iron", "Ivory",
    "Jackal", "Jasper", "Javelin", "Jealousy", "Jewel", "Jewels",
    "Jot", "Judge", "Juniper",
    "Kettle", "Key", "Kidnapping", "Kiln", "Kindness", "King",
    "Kingdom", "Kinsman", "Kiss", "Kite", "Knife", "Knop",
    "Lace", "Ladder", "Lamb", "Lamp", "Lance", "Language", "Lantern",
    "Latchet", "Laughter", "Law", "Lawyer", "Lead", "Leaf", "Leaven",
    "Leek", "Leeks", "Lentils", "Leopard", "Leprosy", "Letter",
    "Libertine", "Lieutenant", "Life", "Lightning", "Lily", "Lime",
    "Linen", "Lion", "Litter", "Lizard", "Lock", "Locust", "Loom",
    "Lord", "Lots",
    "Magic", "Magistrate", "Mail", "Mallow", "Mandrake", "Manslayer",
    "Mantle", "Marble", "Market", "Marriage", "Mattock", "Maul",
    "Meadow", "Meals", "Meat", "Mediator", "Melon", "Melons",
    "Merchant", "Mercy", "Midwife", "Mill", "Millstone", "Minstrel",
    "Mint", "Mirror", "Mite", "Mitre", "Mole", "Money", "Moon",
    "Mortar", "Moth", "Mound", "Mounds", "Mourning", "Mouse",
    "Mulberry", "Mule", "Murder", "Murmuring", "Music", "Mustard",
    "Myrrh", "Myrtle",
    "Nail", "Naked", "Nativity", "Needle", "Net", "Nettle", "Night",
    "Nitre", "Nobleman", "Nurse", "Nut", "Nuts",
    "Oak", "Oath", "Oats", "Offence", "Officer", "Oil", "Ointment",
    "Onion", "Osprey", "Ostrich", "Oven", "Owl", "Ox",
    "Paddle", "Palace", "Palm", "Paper", "Papyrus", "Parable",
    "Paradise", "Parchment", "Partridge", "Pavilion", "Peacock",
    "Pearl", "Pelican", "Pen", "Penny", "Perfume", "Pestle",
    "Pharisee", "Physician", "Pillar", "Pillow", "Pin", "Pine",
    "Pipe", "Pit", "Pitcher", "Plague", "Plaster", "Plough", "Plumb",
    "Plumbline", "Poetry", "Pomegranate", "Pool", "Poplar", "Post",
    "Pot", "Potter", "Pottery", "Pound", "Prayer", "Priest",
    "Priesthood", "Prince", "Proselyte", "Proverb", "Publican",
    "Pulse", "Punishment",
    "Quarry", "Quail", "Quiver",
    "Rabbit", "Raft", "Rain", "Rainbow", "Ram", "Ransom", "Raven",
    "Razor", "Reed", "Riddle", "Ring", "River", "Robe", "Rod",
    "Roe", "Roller", "Roof", "Rope", "Rose", "Ruby", "Rush", "Rye",
    "Sabbath", "Sack", "Sackcloth", "Saddle", "Sadducees", "Salt",
    "Salvation", "Sand", "Sandal", "Sapphire", "Sardine", "Sardonyx",
    "Saw", "Scapegoat", "Scarlet", "Scorpion", "Scourging", "Scribe",
    "Scripture", "Scroll", "Seal", "Seer", "Senator", "Sepulchre",
    "Serpent", "Servant", "Servitor", "Sheath", "Sheep", "Shekel",
    "Shepherd", "Shield", "Ship", "Ships", "Shoe", "Shovel",
    "Showbread", "Shuttle", "Sickle", "Sieve", "Silk", "Silver",
    "Silverling", "Skin", "Skins", "Slag", "Slavery", "Sling",
    "Smith", "Snail", "Snake", "Snare", "Snow", "Soap", "Socket",
    "Soldier", "Songs", "Soothsayer", "Sorcery", "Sovereignty",
    "Sower", "Span", "Sparrow", "Spear", "Spice", "Spices", "Spider",
    "Spikenard", "Spindle", "Sponge", "Staff", "Stall", "Star",
    "Stars", "Statute", "Steel", "Steps", "Steward", "Stocks",
    "Stork", "Stranger", "Straw", "Stream", "Stumbling", "Stuff",
    "Suffering", "Sun", "Surety", "Swallow", "Swan", "Swine",
    "Sword", "Sycamore", "Sycamine",
    "Tanner", "Tapestry", "Tares", "Target", "Taskmaster", "Tax",
    "Teacher", "Tent", "Teraphim", "Thief", "Thistle", "Thorn",
    "Thorns", "Throne", "Thunder", "Tile", "Timber", "Tin",
    "Tithe", "Tithes", "Toad", "Tomb", "Tongue", "Tongues", "Topaz",
    "Torch", "Torment", "Tower", "Treasure", "Treasury", "Tree",
    "Trespass", "Tribe", "Tribes", "Tribune", "Tribute", "Trumpet",
    "Trumpets", "Truth", "Turtle",
    "Unction", "Unicorn",
    "Vagabond", "Valley", "Vanity", "Veil", "Vermilion", "Vessel",
    "Vine", "Vinegar", "Vineyard", "Vintage", "Viper", "Virgin",
    "Vow",
    "Wafer", "Wages", "Wagon", "Wall", "Wandering", "War", "Warfare",
    "Washing", "Watchman", "Watchtower", "Water", "Wax", "Wealth",
    "Weapons", "Weaving", "Wedding", "Weeks", "Well", "Whale",
    "Wheat", "Wheel", "Whip", "Widow", "Wilderness", "Will",
    "Willows", "Wind", "Window", "Wine", "Winepress", "Winefat",
    "Wisdom", "Witch", "Witchcraft", "Witness", "Wizard", "Woe",
    "Wolf", "Wolves", "Wood", "Wool", "Worm", "Wormwood",
    "Worship", "Wrath", "Writing",
    "Yoke", "Zeal", "Zealot",
    # Additional for Smith
    "Funerals", "Sanctuary", "Archangel", "Revelation",
    "Legion", "Chameleon",
}

# English words/phrases in multi-word entries
english_multi_indicators = [
    " Of ", " of ", " The ", " the ", " And ", " and ", " Or ", " or ",
    " In ", " in ", " To ", " to ", " At ", " at ", " For ", " for ",
    " By ", " by ", " With ", " with ", " From ", " from ",
    "'s ", "Upon ", " upon ",
    "Stone Of", "Valley Of", "Course Of", "Book Of", "Gate Of",
    "Land Of", "Tribe Of", "Mount ", "Sea Of", "Hill ", "Brook ",
    "Tower Of", "House Of", "Sons Of", "Day Of", "Epistle",
    "Children Of", "City Of", "Pillar Of", "Field ",
    "Band", "Trees", "Tree", "Skins", "Herbs", "Garment",
    "Serpent", "Offering", "Deer", "Cities", "Hooks", "Dung",
    "Stones", "Flesh", "Pins", "Flies", "Running",
    "High ", "Old ", "First ", "Second ", "Dead ",
    "Bloody", "Brazen", "Burnt", "Bitter", "Fallow", "Fenced",
    "Strong", "General", "Greek", "Hebrew", "Italian",
    "Prophecy Of", "Prophecies Of",
    "The Epistle", "The Book", "The Tribe",
    "Additions To",
]

residuals_single = []
residuals_multi = []

for entry in data:
    mot = entry["mot"]
    source = entry.get("source_title_en", "")
    eid = entry["id"]

    if mot != source:
        continue

    # Single word
    if " " not in mot and "," not in mot and "'" not in mot:
        if mot in english_common_single and mot not in true_french_too:
            residuals_single.append((eid, mot))
    else:
        # Multi-word: check if it contains English indicators
        has_english = False
        for indicator in english_multi_indicators:
            if indicator in mot:
                has_english = True
                break
        if has_english:
            residuals_multi.append((eid, mot))

print(f"=== SMITH: RESIDUS ANGLAIS DANS 'mot' ===\n")
print(f"Mots simples: {len(residuals_single)}")
print(f"Expressions multi-mots: {len(residuals_multi)}")
print(f"TOTAL: {len(residuals_single) + len(residuals_multi)}\n")

print("--- MOTS SIMPLES ---")
for i, (eid, mot) in enumerate(residuals_single, 1):
    print(f"  {i:3d}. {eid:20s} | {mot}")

print(f"\n--- EXPRESSIONS MULTI-MOTS ---")
for i, (eid, mot) in enumerate(residuals_multi, 1):
    print(f"  {i:3d}. {eid:20s} | {mot}")
