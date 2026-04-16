import json

with open('uploads/dictionnaires/easton/easton.entries.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Comprehensive list of English common words (not biblical proper nouns)
# that should have been translated to French
english_common = set("""
A Abjects Ablution Atonement Adoption Adversary Allegory Alms Ambassador
Anchor Anger Annunciation Antichrist Apostasy Apostle Archangel Armour
Arrow Arrows Ascension Assembly Axe
Backslide Bags Banner Baptism Barn Basket Bath Beacon Beam
Beatitudes Bed Bee Beetle Believer Bells Bellows Bishop Blasphemy
Blessing Blood Bolster Bondage Bottle Bow Bowl Bracelet Brass Bread
Brick Bridle Brimstone Brotherhood Buckler Bull Bullock Burial Butter
Cabins Caldron Calling Candle Candlestick Captain Captive Captivity
Cart Casement Castle Caul Cave Centurion Chain Chamberlain Champion
Chancellor Chariot Charmer Chastisement Cheese Circumcision Citizenship
Clay Closet Cloth Cloud Coal Coat Coffin Collar Colors Comb
Commandment Communion Concubine Concupiscence Conduit Confession
Congregation Conscience Consecration Conversion Conviction Copper
Coral Cord Cornerstone Couch Council Coulter Covenant Covetousness
Creation Creature Creed Crib Crown Crucifixion Crystal Cup Curse
Curtain Cymbal
Dagger Damnation Darkness Deacon Deaconess Death Debt Decalogue
Decree Dedication Demoniac Deputy Dew Diadem Dispersion Divination
Doctrine Dream Dress Dross Drum Dulcimer Dungeon Dust Dwarf Dye Dyeing
Earnest Earring Earthquake Eclipse Elder Election Embalmment Emerods
Enchantment Endowment Epistle Espousal Evangelist Exorcist
Fable Famine Fan Farthing Fasting Father Feast Fetter Fellowship Fence
Fever File Firebrand Firstborn Flint Flood Floor Fool Footman
Foreknowledge Forerunner Forgiveness Fork Fortress Fountain Freedom
Friendship Frontlet Fuel Fuller Fulness Fullness Furnace Furniture
Gainsay Gall Garden Garment Garner Garrison Gate Genealogy Generation
Gift Girdle Glass Gleaning Glory Goad Gold Governor Grace Grave Graving
Grove Guard Guest Gutter
Hail Hair Hall Hallelujah Hammer Handkerchief Handmaid Harp Harness
Harrow Harvest Hatred Haven Hay Healing Heart Heathen Heaven Heir Hell
Helmet Herald Heresy Hewn Highway Holiness Hope Horn Hospitality Host
House Hunger Hunting Husband Husbandman Hymn Hypocrite
Idolatry Image Immortality Imputation Incarnation Incense Inheritance
Inn Innocents Ink Inkhorn Inspiration Intercession Iron Ivory
Jackal Jasper Jealousy Jewel Jewels Jot Judge Judgment Justification
Key Kettle Kidnapping Kiln Kindness King Kingdom Kinsman Kiss
Kite Knife Knop Knowledge
Labour Lace Ladder Lamp Lancet Language Lantern Latchet Laughter Laver
Law Lawyer Lead Leather Leaven Legion Leprosy Letter Liar Libertine
Liberty Lieutenant Life Lightning Lily Linen Litter Lock Loom Lord
Lots Love Lunatic
Magic Magistrate Malefactor Mammon Manslayer Mantle Marble Marriage
Martyr Master Mattock Maul Meadow Mediation Mediator Meekness Mercy
Messenger Midwife Mill Millennium Millstone Minister Ministry Minstrel
Miracle Mirror Mischief Mite Mitre Mocker Money Monogamy Moon
Mortar Mourning Murder Murmuring Music Mystery
Nail Naked Nativity Necromancer Needle Net Nitre Nobleman Number Nurse
Oath Obedience Oblation Offence Officer Oil Onyx Oracle Oracles
Ordination Ornament Oven
Paddle Palace Palanquin Palsy Paper Papyrus Parable Paradise Parchment
Passion Passover Patriarch Pattern Pavilion Pearl Pen Penny Pentateuch
Pentecost Perdition Perfume Persecution Pestle Pestilence Petition
Phylactery Physician Pilgrimage Pillar Pin Pipe Pit Pitcher Plague
Plagues Plaster Plate Plough Plumbline Poetry Poison Poll Polygamy
Pommel Possession Post Pot Potsherd Potter Pottery Pouch Pound Praise
Prayer Preaching Predestination Presbytery Priest Priesthood Prison
Proclamation Prodigal Profanity Promise Prophecy Prophet Prophetess
Propitiation Proselyte Providence Provocation Psalm Psalms Publican
Pulse Punishment Purification Purse
Quarry Quiver
Raft Raiment Rain Rainbow Ransom Razor Rebuke Reconciliation Redeemer
Redemption Regeneration Remission Remnant Repentance Reprobate
Resurrection Revelation Revenge Reviling Reward Riddle Righteousness
Ring Robbery Robe Rod Roller Roof Rope Ruby
Sabbath Sack Sackcloth Sacrilege Saddle Sadducees Salt Salvation Sand
Sanctuary Sandal Sapphire Sardius Sardonyx Saw Scapegoat Sceptre
Scourging Scribe Scripture Scriptures Scroll Seal Seer Selvedge
Senator Sepulchre Seraph Seraphim Servant Servitor Sheath Sheepfold
Shekel Shepherd Shield Ship Shoe Showbread Shuttle Sickle Sieve Silk
Silver Sin Skin Slag Slander Slavery Sling Smith Snare Snow Soap Socket
Songs Soothsayer Sorcery Soul Sovereignty Sower Span Spear Spice Spices
Spindle Spirit Spoil Spy Staff Stall Star Stars Statute Steel Steps
Steward Stocks Stoics Stone Stones Stove Stranger Straw Stream String
Stumbling Stuff Suffering Sun Superstition Surety Swearing Sword
Synagogue
Tabernacle Talent Tanner Tapestry Target Taskmaster Tax Teacher
Tent Testament Testimony Thanksgiving Theocracy Thief Thistle Thorns
Throne Thunder Tile Timber Tin Tire Tithe Tithes Tomb Tongue Tongues
Tongs Topaz Torch Torment Tower Tradition Trance Transgression Treason
Treasure Treasury Tree Trespass Tribe Tribes Tribune Tribute Trinity
Triumph Trumpet Trumpets Truth Type Tyranny
Unbelief Unction Unicorn Unity Unleavened Uprightness Usury
Vagabond Valley Vanity Veil Vermilion Vessel Vessels Vestibule Vesture
Village Vine Vineyard Vintage Viper Virgin Vision Vocation Voice Vow
Wafer Wages Wagon Wandering Wall War Warfare Washing Watchman
Watchtower Water Wax Wealth Weapons Weaving Wedding Weeks Well Whale
Wheel Whip Wick Widow Wilderness Will Willows Wind Window Wine
Winefat Winepress Wisdom Witch Witchcraft Witness Wizard Woe Wolves
Wood Wool Worm Worship Wrath Writing
Yoke Zeal Zealot
Ape Apes Ass Bat Bear Boar Camel Caterpillar Chameleon Chamois Cock
Cockatrice Colt Coney Cormorant Cow Crane Cricket Cuckoo Deer Dog Dove
Dromedary Eagle Ewe Falcon Fawn Fish Flea Fly Fox Frog Gazelle Goat
Goose Grasshopper Greyhound Hare Hart Hawk Hen Heron Hind Hornet Horse
Horseleach Hyena Lamb Leopard Leviathan Lion Lizard Locust Mole Moth
Mouse Mule Osprey Ostrich Owl Ox Partridge Peacock Pelican Pygarg Quail
Ram Raven Roe Roebuck Scorpion Sheep Snail Snake Sparrow Spider Sponge
Stork Swallow Swan Swine Vulture Weasel Wolf
Almond Algum Almug Aloes Anise Apple Balm Barley Bay Bean Beans
Box Bramble Brier Bulrush Bush Calamus Camphire Cane Cassia Cedar
Chestnut Cinnamon Citron Cockle Coriander Corn Cotton Cucumber Cummin
Cypress Dill Ebony Elm Fig Fir Fitches Flag Flax Frankincense Galbanum
Garlic Gourd Grape Grapes Gopher Heath Hemlock Henna Herbs Husk Husks
Hyssop Juniper Leek Leeks Lentils Mallow Mandrake Manna Melon Melons
Millet Mint Mulberry Mustard Myrrh Myrtle Nettle Nettles Nut Nuts Oak
Olive Onion Onions Palm Pine Pomegranate Poplar Reed Rice Rose Rue Rush
Rushes Rye Saffron Spikenard Sycamine Sycamore Tare Tares Teil Thorn
Vine Vinegar Wheat Willow Wormwood
""".split())

residuals = []
for entry in data:
    mot = entry['mot']
    source = entry.get('source_title_en', '')
    if mot != source:
        continue
    if mot in english_common:
        residuals.append((entry['id'], mot))

print(f"Mots anglais courants non traduits dans 'mot': {len(residuals)}\n")
for eid, mot in residuals:
    print(f"{eid:20s} | {mot}")
