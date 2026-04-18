#!/usr/bin/env python3
"""
Applique les related_concepts pedagogiques entre concepts.
55 clusters thematiques couvrant theologie, personnages, geographie, rites, nature, livres, evenements.
"""
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

INPUT = "uploads/dictionnaires/concepts.json"

clusters = {
    # ═══ A. CHAINES THEOLOGIQUES ═══
    "soteriologie": {
        "ids": ["creation", "la-chute-de-l-homme", "peche", "repentance", "conversion", "foi",
                "justification", "regeneration", "sanctification", "salut-3", "vie-eternelle"],
        "relation": "theological_chain"
    },
    "expiation_redemption": {
        "ids": ["expiation", "expiation-2", "propitiation", "redemption", "pardon",
                "pardon-des-peches", "confession", "croix"],
        "relation": "theological_chain"
    },
    "election_predestination": {
        "ids": ["predestination", "election", "election-de-la-grace", "appel-efficace",
                "perseverance-des-saints", "assurance", "decrets-de-dieu", "prescience-de-dieu"],
        "relation": "theological_chain"
    },
    "nature_divine": {
        "ids": ["yhwh", "adonai", "el", "elyon", "shaddai", "trinite", "saint-esprit",
                "divinite", "gloire", "bonte-de-dieu", "justice-de-dieu"],
        "relation": "thematic_cluster"
    },
    "noms_yhwh": {
        "ids": ["yhwh", "yhwh-jireh", "yhwh-shalom", "yhwh-shammah", "yhwh-tsidkenu",
                "sabaoth", "jah", "yah"],
        "relation": "thematic_cluster"
    },
    "christologie": {
        "ids": ["mashiah", "yehoshoua", "incarnation", "humiliation-du-christ",
                "resurrection-du-christ", "ascension", "revelation-du-christ",
                "sauveur", "seigneur", "anti-mashiah"],
        "relation": "theological_chain"
    },
    "pneumatologie": {
        "ids": ["saint-esprit", "saint-esprit-2", "esprit", "donsspirituels",
                "fruitdel-esprit", "intercession-du-saint-esprit",
                "temoignage-de-l-esprit", "inspiration", "langues"],
        "relation": "theological_chain"
    },
    "eschatologie": {
        "ids": ["derniersjours", "millenium", "grandetribulation", "anti-mashiah",
                "homme-du-peche", "resurrection-des-morts", "jugement-final",
                "jugements-de-dieu", "mort-eternelle", "apocalypse"],
        "relation": "theological_chain"
    },
    "destinations_eternelles": {
        "ids": ["ciel", "paradis", "vie-eternelle", "enfer", "sheol",
                "gehenna", "gehenne", "mort-eternelle", "le-sein-d-abraham", "abaddon"],
        "relation": "thematic_cluster"
    },
    "alliances": {
        "ids": ["alliance", "alliance-2", "alliance-3", "arc-en-ciel", "circoncision",
                "loi", "torah", "decalogue", "loi-de-moise", "nouveau-testament"],
        "relation": "theological_chain"
    },
    "vertus": {
        "ids": ["foi", "esperance", "charite", "humilite", "douceur",
                "contentement", "piete", "saintete", "perfection"],
        "relation": "thematic_cluster"
    },
    "peche_manifestations": {
        "ids": ["peche", "la-chute-de-l-homme", "concupiscence", "convoitise",
                "adultere", "fornication", "blaspheme", "apostasie", "heresie", "abomination"],
        "relation": "thematic_cluster"
    },
    "parole_revelation": {
        "ids": ["ecriture", "bible", "canon", "old_testament", "nouveau-testament",
                "evangile", "parole-de-dieu", "inspiration", "prophetie", "parabole"],
        "relation": "thematic_cluster"
    },

    # ═══ B. FAMILLES DE PERSONNAGES ═══
    "patriarches": {
        "ids": ["abraham", "sarah", "yitshaq", "rivqah", "yaacov", "leah",
                "rachel", "esav", "laban", "lot", "yishmael"],
        "relation": "family"
    },
    "12_tribus": {
        "ids": ["yaacov", "reouben", "shimeon", "levi", "yehouda", "dan",
                "naphtali", "gad", "asher", "issachar", "zebouloun",
                "yossef", "benyamin", "ephraim", "manasseh"],
        "relation": "family"
    },
    "moise_exode_perso": {
        "ids": ["moshe", "aaron", "myriam", "yehoshua", "pharaoh",
                "loi-de-moise", "exode", "sinai", "tabernacle"],
        "relation": "thematic_cluster"
    },
    "monarchie_unie": {
        "ids": ["david", "shelomoh", "nathan", "shemouel", "shaoul",
                "boaz", "routh", "psaumes"],
        "relation": "thematic_cluster"
    },
    "prophetes_majeurs": {
        "ids": ["yesha-yah", "yirmeyah", "yehezkel", "daniye-l"],
        "relation": "thematic_cluster"
    },
    "prophetes_mineurs": {
        "ids": ["hoshea-2", "yoel", "amowc", "obadyah", "yonah",
                "miykayah-miykah", "nahoum", "habaqqouq", "tsephanyah",
                "chaggay", "zekaryah", "malakhi"],
        "relation": "thematic_cluster"
    },
    "apotres": {
        "ids": ["petros", "andreas", "yaacov-2", "yohanan", "matthaios",
                "paulos", "barnabas", "timotheos", "stephanos", "apotre", "disciple"],
        "relation": "thematic_cluster"
    },
    "antediluviens": {
        "ids": ["adam", "havah", "qayin", "abel", "noah",
                "la-chute-de-l-homme", "deluge", "archedenoah"],
        "relation": "thematic_cluster"
    },
    "sacerdoce": {
        "ids": ["aaron", "levi", "levite", "levites", "pretre",
                "grand-pretre", "sacerdoce", "ordination", "melchisedek"],
        "relation": "thematic_cluster"
    },

    # ═══ C. GEOGRAPHIQUES ═══
    "jerusalem": {
        "ids": ["yeroushalaim", "sion", "temple", "temple-de-salomon",
                "mont-des-oliviers", "bethanie", "bethlehem", "gehenne"],
        "relation": "geographic"
    },
    "galilee": {
        "ids": ["galilee", "nazareth", "capernaum", "yarden", "samarie"],
        "relation": "geographic"
    },
    "empires": {
        "ids": ["egypte", "assyrie", "babylone", "ninive", "rome"],
        "relation": "thematic_cluster"
    },
    "voyages_paul": {
        "ids": ["antioche", "ephese", "corinthe", "thessalonique",
                "philippes", "athenes", "rome", "damas"],
        "relation": "geographic"
    },

    # ═══ D. RITES ET INSTITUTIONS ═══
    "sacrifices": {
        "ids": ["sacrifice", "holocauste", "oblation", "libation",
                "premices", "dime", "encens"],
        "relation": "thematic_cluster"
    },
    "fetes_yhwh": {
        "ids": ["fetesdeyhwh", "paque", "pentecote", "purim",
                "sabbat", "shabbat", "jubilee"],
        "relation": "thematic_cluster"
    },
    "sacrements": {
        "ids": ["bapteme", "bapteme-de-jean", "bapteme-du-christ",
                "cene-du-seigneur", "ablution", "onction"],
        "relation": "thematic_cluster"
    },
    "mobilier_sacre": {
        "ids": ["tabernacle", "temple", "autel", "ark_of_the_covenant",
                "cherubins", "candelabre"],
        "relation": "thematic_cluster"
    },
    "ministeres": {
        "ids": ["eglise", "apotre", "prophete", "eveque", "diacre",
                "ancien", "rabbi"],
        "relation": "thematic_cluster"
    },

    # ═══ E. NATURE ═══
    "animaux_symboliques": {
        "ids": ["agneau", "lion", "serpent", "colombe", "chevre",
                "leviathan", "behemoth", "ane", "corbeau"],
        "relation": "thematic_cluster"
    },
    "arbres_plantes": {
        "ids": ["figuier", "vigne", "olivier", "olive", "cedre",
                "arbre-de-vie", "acacia", "moutarde"],
        "relation": "thematic_cluster"
    },
    "aliments": {
        "ids": ["pain", "vin", "ble", "huile", "miel", "lait",
                "raisin", "levain", "manne"],
        "relation": "thematic_cluster"
    },

    # ═══ F. LIVRES BIBLIQUES ═══
    "pentateuque": {
        "ids": ["pentateuque", "genese", "exode", "leviticus", "numbers",
                "deuteronome", "torah", "loi-de-moise"],
        "relation": "canonical_order"
    },

    # ═══ G. EVENEMENTS ═══
    "histoire_salut": {
        "ids": ["creation", "la-chute-de-l-homme", "deluge", "babel", "abraham",
                "exode", "sinai", "captivite", "incarnation", "croix",
                "resurrection-du-christ", "ascension", "pentecote", "apocalypse"],
        "relation": "chronological"
    },
    "creation_deluge": {
        "ids": ["creation", "eden", "arbre-de-vie", "adam", "havah",
                "la-chute-de-l-homme", "qayin", "abel", "noah", "deluge",
                "archedenoah", "arc-en-ciel"],
        "relation": "chronological"
    },
    "exode_conquete": {
        "ids": ["servitude", "egypte", "moshe", "paque", "sinai",
                "tabernacle", "manne", "yarden"],
        "relation": "chronological"
    },

    # ═══ H. ETRES SPIRITUELS ═══
    "anges": {
        "ids": ["ange", "angel_of_the_lord", "archanges", "cherubins", "seraphins"],
        "relation": "thematic_cluster"
    },
    "satan_forces_mal": {
        "ids": ["satan", "diable", "belial", "beelzeboul", "demon", "demons"],
        "relation": "thematic_cluster"
    },
    "divinites_paiennes": {
        "ids": ["baal", "ashtoreth", "asherah", "dagon", "chemosh",
                "tammuz", "idole", "image"],
        "relation": "thematic_cluster"
    },

    # ═══ I. PEUPLES ═══
    "peuples_canaan": {
        "ids": ["kena-an", "philistins", "moab", "ammonites"],
        "relation": "thematic_cluster"
    },
    "gouvernance_juive": {
        "ids": ["sanhedrim", "pharisien", "synagogue"],
        "relation": "thematic_cluster"
    },
}


def main():
    with open(INPUT, "r", encoding="utf-8-sig") as f:
        concepts = json.load(f)

    valid_ids = {c["concept_id"]: c for c in concepts}

    # Validate
    total_missing = 0
    for name, cluster in clusters.items():
        for cid in cluster["ids"]:
            if cid not in valid_ids:
                print(f"  MISSING: {cid} in cluster '{name}'")
                total_missing += 1

    if total_missing > 0:
        print(f"\n{total_missing} missing IDs. Filtering them out...")

    # Build reciprocal links: for each concept, collect all related concepts from its clusters
    # A concept can appear in multiple clusters
    related_map = {}  # concept_id -> set of (related_id, relation_type)

    for name, cluster in clusters.items():
        valid_in_cluster = [cid for cid in cluster["ids"] if cid in valid_ids]
        relation = cluster["relation"]

        for cid in valid_in_cluster:
            if cid not in related_map:
                related_map[cid] = set()
            for other in valid_in_cluster:
                if other != cid:
                    related_map[cid].add((other, relation))

    # Apply to concepts
    total_links_added = 0
    concepts_touched = 0

    for c in concepts:
        cid = c["concept_id"]
        if cid not in related_map:
            continue

        existing = c.get("related_concepts", [])
        existing_ids = set(r.get("concept_id", "") for r in existing)

        new_links = []
        for (related_id, relation) in related_map[cid]:
            if related_id not in existing_ids:
                label = valid_ids[related_id].get("label", related_id)
                new_links.append({
                    "concept_id": related_id,
                    "label": label,
                    "relation_type": relation
                })
                existing_ids.add(related_id)

        if new_links:
            c["related_concepts"] = existing + new_links
            total_links_added += len(new_links)
            concepts_touched += 1

    # Write
    with open(INPUT, "w", encoding="utf-8-sig") as f:
        json.dump(concepts, f, ensure_ascii=False, indent=2)

    print(f"\nClusters traites: {len(clusters)}")
    print(f"Concepts touches: {concepts_touched}")
    print(f"Liens ajoutes: {total_links_added}")
    print(f"Concepts total: {len(concepts)}")
    print("Done.")


if __name__ == "__main__":
    main()
