import json

with open('uploads/dictionnaires/easton/easton.entries.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Words truly identical in French (no spelling difference) - NOT residues
true_french_too = {
    'A', 'Communion', 'Concubine', 'Concupiscence', 'Conduit',
    'Confession', 'Conscience', 'Conversion', 'Crucifixion',
    'Damnation', 'Dispersion', 'Divination',
    'Fable', 'Famine', 'Hallelujah',
    'Imputation', 'Incarnation', 'Inspiration',
    'Justification', 'Mammon', 'Millennium', 'Miracle',
    'Passion', 'Poison', 'Prison',
    'Propitiation', 'Providence', 'Purification',
    'Repentance', 'Tradition', 'Vision',
}

# All 208 single-word English common words found earlier
english_common = {
    'Abjects', 'Ablution', 'Adoption', 'Algum', 'Almug', 'Ape',
    'Archangel', 'Ascension', 'Axe',
    'Backslide', 'Bath', 'Bay', 'Beacon', 'Bear', 'Bracelet',
    'Bramble', 'Bridle',
    'Cabins', 'Calamus', 'Camphire', 'Cane', 'Cart', 'Cassia',
    'Castle', 'Centurion', 'Chain', 'Chamberlain', 'Chameleon',
    'Chamois', 'Champion', 'Chancellor', 'Charmer', 'Citizenship',
    'Cockatrice', 'Cockle', 'Communion', 'Concubine',
    'Concupiscence', 'Conduit', 'Coney', 'Confession', 'Conscience',
    'Conversion', 'Crucifixion',
    'Damnation', 'Deputy', 'Dispersion', 'Divination', 'Dulcimer',
    'Ebony', 'Exorcist',
    'Fable', 'Famine', 'Farthing', 'Flag', 'Fulness',
    'Galbanum', 'Gall', 'Garrison', 'Gopher', 'Graving',
    'Hall', 'Hallelujah', 'Harness', 'Harrow', 'Hart', 'Hatred',
    'Haven', 'Hay', 'Heath', 'Heathen', 'Heir', 'Highway', 'Hind',
    'Host', 'House', 'Husbandman', 'Hypocrite',
    'Imputation', 'Incarnation', 'Inkhorn', 'Inn', 'Inspiration',
    'Ivory',
    'Jasper', 'Jot', 'Justification',
    'Kinsman', 'Kite', 'Knife', 'Knop',
    'Ladder', 'Latchet', 'Lawyer', 'Leather', 'Legion', 'Letter',
    'Libertine', 'Lieutenant', 'Life', 'Lightning', 'Lily',
    'Magistrate', 'Mammon', 'Manslayer', 'Mantle', 'Marble',
    'Martyr', 'Mattock', 'Maul', 'Mediator', 'Melons', 'Mercy',
    'Midwife', 'Millennium', 'Millet', 'Minstrel', 'Miracle',
    'Mite', 'Mitre', 'Mole', 'Mortar', 'Mouse', 'Mulberry',
    'Murder', 'Murmuring', 'Myrrh',
    'Naked', 'Nettle', 'Nitre',
    'Offence', 'Olive', 'Onyx', 'Oracle', 'Osprey',
    'Palsy', 'Paradise', 'Passion', 'Pavilion', 'Physician',
    'Pitcher', 'Poetry', 'Poison', 'Post', 'Prison',
    'Propitiation', 'Proselyte', 'Providence', 'Publican', 'Pulse',
    'Purification',
    'Ram', 'Razor', 'Reed', 'Repentance', 'Revelation', 'Riddle',
    'Robbery', 'Roe', 'Rose', 'Rue', 'Rush', 'Rye',
    'Sadducees', 'Sanctuary', 'Sardonyx', 'Scapegoat', 'Sceptre',
    'Sepulchre', 'Servitor', 'Smith', 'Snare', 'Songs',
    'Sovereignty', 'Spices', 'Spikenard', 'Sponge', 'Stars',
    'Stork', 'Surety', 'Swan', 'Swine', 'Sycamore', 'Synagogue',
    'Tabernacle', 'Talent', 'Tares', 'Target', 'Testament',
    'Thistle', 'Thorn', 'Tin', 'Torment', 'Tradition', 'Treasury',
    'Tribute', 'Type', 'Unction', 'Vagabond', 'Vision', 'Wagon',
    'Wandering', 'Wheel', 'Willows', 'Window', 'Winefat', 'Zeal',
}

# Multi-word English residuals
multi_word_ids = {
    'easton-000080', 'easton-000365', 'easton-000609', 'easton-000801',
    'easton-000959', 'easton-001264', 'easton-001281', 'easton-001300',
    'easton-001322', 'easton-001325', 'easton-001482', 'easton-001484',
    'easton-001520', 'easton-001705', 'easton-001782', 'easton-001911',
    'easton-001988', 'easton-002128', 'easton-002135', 'easton-002136',
    'easton-002215', 'easton-002265', 'easton-002266', 'easton-002454',
    'easton-002586', 'easton-002729', 'easton-002750', 'easton-002817',
    'easton-002874', 'easton-003159', 'easton-003223', 'easton-003322',
    'easton-003409', 'easton-003446', 'easton-003475', 'easton-003516',
    'easton-003672', 'easton-003714', 'easton-003715', 'easton-003733',
}

all_residuals = {}

for entry in data:
    mot = entry['mot']
    source = entry.get('source_title_en', '')
    eid = entry['id']

    # Multi-word residuals (already verified)
    if eid in multi_word_ids:
        all_residuals[eid] = mot
        continue

    # Single word: mot == source and in english_common but NOT in true_french_too
    if mot == source and mot in english_common and mot not in true_french_too:
        all_residuals[eid] = mot

sorted_res = sorted(all_residuals.items())

print(f"=== RESIDUS ANGLAIS DANS LE CHAMP 'mot' : {len(sorted_res)} entrees ===\n")
print(f"{'#':>4s}  {'ID':20s} | mot (anglais)")
print("-" * 60)
for i, (eid, mot) in enumerate(sorted_res, 1):
    print(f"{i:4d}  {eid:20s} | {mot}")
