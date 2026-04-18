# AGENTS_ISBE.md
Règles spécifiques pour les agents chargés de la traduction de l'encyclopédie biblique **ISBE** (International Standard Bible Encyclopedia).

> **Prérequis** : l'agent DOIT appliquer l'intégralité des règles de `AGENTS_COMMON.md` (socle commun).
> Le présent fichier ne contient que les règles **spécifiques à l'ISBE** ou les précisions supplémentaires.

---

# 1. Objectif

Traduire intégralement les définitions de l'ISBE de l'anglais vers le français.

La traduction doit :

- être fidèle au sens du texte original
- conserver le ton encyclopédique et savant de l'ISBE
- rester exploitable par le pipeline Bible V2 déjà préparé
- être lisible pour un lectorat francophone sans anglicismes résiduels inutiles

---

# 2. Périmètre technique ISBE

Le flux ISBE repose sur :

- source extraite : `isbe.json` (9 380 entrées, format `{"mot":"...","definition":"..."}`)
- source de travail normalisée : `uploads/dictionnaires/isbe/isbe.json`
- sortie cible de traduction : `uploads/dictionnaires/isbe/isbe.fr.json`

Contraintes liées au pipeline Bible V2 :

- `mot` sert d'invariant source
- les renvois internes et les correspondances ISBE/Easton/Smith/BYM ne doivent pas être cassés

---

# 3. Spécificités encyclopédiques de l'ISBE

L'ISBE est une **encyclopédie**, pas un simple dictionnaire. Ses articles sont souvent longs, structurés en sections numérotées, et contiennent :

- des développements historiques, archéologiques et géographiques détaillés
- des analyses étymologiques approfondies (hébreu, grec, araméen)
- des discussions critiques sur les textes et les manuscrits
- des signatures d'auteurs en fin d'article
- des translittérations systématiques entre parenthèses

Règles :

- conserver la structure numérotée des sections (1., 2., 3., etc.)
- conserver les titres de sections (ils font partie du contenu)
- traduire les signatures d'auteurs uniquement si elles contiennent du texte descriptif ; conserver les noms d'auteurs tels quels
- conserver toutes les translittérations hébraïques et grecques entre parenthèses

---

# 4. Renvois internes ISBE

L'ISBE utilise des renvois textuels sans ancres numériques :

- `See ALEPH` → `Voir ALEPH`
- `see AARON'S ROD` → `voir AARON'S ROD`
- `See also PRIEST, III.` → `Voir aussi PRIEST, III.`

Règle essentielle : les cibles de renvoi doivent rester en forme source anglaise, car elles pointent vers des clés `mot` du JSON qui ne sont pas traduites.

- on traduit le mot introducteur : `See` → `Voir`, `compare` → `comparer`, `see under` → `voir sous`
- on conserve la cible du renvoi en majuscules ou en forme source exacte
- on ne traduit JAMAIS la cible d'un renvoi interne

Exemples :

- `See ALEPH; ALPHABET.` → `Voir ALEPH ; ALPHABET.`
- `See also APOLLYON.` → `Voir aussi APOLLYON.`
- `See PRIEST, III.` → `Voir PRIEST, III.`

---

# 5. Prononciation et translittérations

L'ISBE fournit systématiquement des prononciations en début d'article :

- `ar'-un` (pour Aaron)
- `a-bad'-on` (pour Abaddon)

Règle : conserver les prononciations telles quelles. Elles font partie de l'appareil savant.

---

# 6. Coquilles et irrégularités du source

L'ISBE provient d'une extraction du format SWORD/zLD.

Règle :

- on traduit le sens visé quand il est récupérable avec certitude
- on n'ajoute aucun commentaire éditorial personnel
- si un passage est manifestement corrompu et inintelligible, le conserver tel quel

---

# 7. Taille des lots (chunking)

L'ISBE comporte des articles de taille très variable (de 30 caractères à 325 000 caractères).

Stratégie de chunking par budget de caractères :

- entrées < 2 000 chars → grouper 15-20 par chunk (~30k chars)
- entrées 2 000-8 000 chars → grouper 5-10 par chunk (~40k chars)
- entrées 8 000-30 000 chars → grouper 2-3 par chunk (~40k chars)
- entrées 30 000-80 000 chars → 1 par chunk (isolé)
- entrées > 80 000 chars → 1 par chunk (isolé_large, attention spéciale)

Budget cible par chunk : ~40 000 caractères source (pour laisser de la marge au modèle).

---

# 8. Résultat attendu

Chaque entrée finale doit contenir :

- un champ `mot` strictement inchangé
- une `definition` intégralement traduite en français
- les renvois internes préservant leurs cibles source
- les translittérations et prononciations conservées
- les notations savantes traitées selon les règles du socle commun
- aucune altération de structure JSON
- aucune perte de contenu

Toutes les autres règles (termes théologiques, noms propres, références bibliques, appareil savant, encodage, interdictions) sont définies dans `AGENTS_COMMON.md`.
