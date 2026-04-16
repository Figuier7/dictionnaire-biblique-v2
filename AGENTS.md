# AGENTS.md
Règles spécifiques pour les agents chargés de la traduction du dictionnaire biblique **Easton**.

> **Prérequis** : l'agent DOIT appliquer l'intégralité des règles de `AGENTS_COMMON.md` (socle commun).
> Le présent fichier ne contient que les règles **spécifiques à Easton** ou les précisions supplémentaires.

---

# 1. Objectif

Traduire intégralement les définitions du dictionnaire biblique Easton de l'anglais vers le français.

La traduction doit :

- être fidèle au sens du texte original
- conserver le style d'un dictionnaire biblique classique
- être adaptée à un lectorat francophone

---

# 2. Périmètre technique Easton

- Source : `eastons.json` (fichier anglais original)
- Cible : `uploads/dictionnaires/easton/easton.entries.json` (entrées enrichies V2)
- Fichier de travail intermédiaire : `eastons_traduit_complet.json`

---

# 3. Numéros de renvoi

Les numéros de renvoi internes comme `[279]` doivent être conservés tels quels.

Le texte autour du renvoi doit être traduit normalement.

---

# 4. Taille des lots

Pour garantir un traitement fiable :

- notices courtes → 3 à 5 entrées
- notices moyennes → 2 à 3 entrées
- notices longues → traitement unitaire

---

# 5. Résultat attendu

Chaque entrée doit contenir :

- un champ `mot` inchangé
- une `definition` entièrement traduite en français
- aucune altération de structure JSON

Toutes les autres règles (termes théologiques, noms propres, références bibliques, appareil savant, encodage, interdictions) sont définies dans `AGENTS_COMMON.md`.
