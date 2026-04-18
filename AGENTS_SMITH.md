# AGENTS_SMITH.md
Règles spécifiques pour les agents chargés de la traduction du dictionnaire biblique **Smith**.

> **Prérequis** : l'agent DOIT appliquer l'intégralité des règles de `AGENTS_COMMON.md` (socle commun).
> Le présent fichier ne contient que les règles **spécifiques à Smith** ou les précisions supplémentaires.

---

# 1. Objectif

Traduire intégralement les définitions du dictionnaire biblique Smith de l'anglais vers le français.

La traduction doit :

- être fidèle au sens du texte original
- conserver le ton d'un dictionnaire biblique classique
- rester exploitable par le pipeline Bible V2 déjà préparé
- être lisible pour un lectorat francophone sans anglicismes résiduels inutiles

---

# 2. Périmètre technique Smith

Le flux Smith repose sur deux niveaux de source :

- source brute : `Smith.jsonl` avec les champs `term` et `definitions[]`
- source de travail normalisée : `uploads/dictionnaires/smith/smith.json`

Les traductions par lots doivent être produites sur la source normalisée.

La sortie cible de traduction est :

- `uploads/dictionnaires/smith/smith.fr.json`

Contraintes liées au pipeline Bible V2 :

- `mot` sert d'invariant source
- les renvois internes et les correspondances Smith/Easton/BYM ne doivent pas être cassés

---

# 3. Renvois internes et crochets (spécificité Smith)

Smith contient des marqueurs éditoriaux riches :

- renvois directs : `See [1]Alpha`
- renvois doubles : `[[2]Armenia]`
- renvois internes composés : `[[26]Abia, Course Of, [27]Abia, Abiah, Or Abijah]`
- cibles en majuscules : `[EN-ROGEL]`

Règle essentielle : les ancres internes doivent rester stables.

- on traduit le texte autour du renvoi
- on conserve l'ancre elle-même

Exemples :

- `See [1]Alpha.` → `Voir [1]Alpha.`
- `Same as [33]Abner.` → `Même que [33]Abner.`
- `For details, see [34]Korah` → `Pour plus de détails, voir [34]Korah`

Interdictions absolues :

- ne jamais renuméroter une ancre
- ne jamais remplacer la cible d'une ancre par une traduction française
- ne jamais supprimer un renvoi interne

---

# 4. Notices à sous-entrées, listes et numérotations

Smith contient régulièrement plusieurs sous-entrées dans une seule `definition`.

Marqueurs fréquents :

- `+`
- `(1.)`, `(2.)`, `(3.)`
- suites de sens séparés par des points, points-virgules ou renvois

Règles :

- conserver l'ordre exact des sous-entrées
- conserver la logique de liste
- traduire chaque sous-entrée intégralement
- ne jamais transformer les sous-entrées en nouvelles entrées JSON
- ne jamais scinder une entrée Smith en plusieurs entrées JSON

---

# 5. Interdiction absolue de troncage (renforcement)

En plus des interdictions du socle commun :

- ne jamais abréger une liste
- ne jamais supprimer une parenthèse ou une incise
- ne jamais supprimer un paragraphe
- ne jamais remplacer un passage par `...` si le source ne contient pas déjà `...`
- ne jamais développer ou compléter un `...` déjà présent dans le source

Si le source contient déjà une ellipse éditoriale `...`, elle doit être préservée comme contenu source.

---

# 6. Coquilles, OCR et irrégularités du source

Smith contient des coquilles du source anglais (espaces fautifs, frappe, ponctuation).

Règle :

- on ne reproduit pas mécaniquement la coquille anglaise
- on traduit le sens visé quand il est récupérable avec certitude
- on n'ajoute aucun commentaire éditorial personnel

## 6.1 Formes latines, érudites ou antiquisantes

- forme latine servant de citation savante → conserver
- forme latine désignant un lieu/peuple ayant une forme française stable → employer la forme française
- ne pas moderniser abusivement une forme ancienne citée comme témoignage érudit

---

# 7. Taille des lots

Le dictionnaire Smith comporte beaucoup de notices longues et historiques.

- renvois purs ou notices très courtes → 4 à 5 entrées
- notices courtes simples → 3 à 4 entrées
- notices moyennes ou notices avec plusieurs `+` → 1 à 2 entrées
- notices longues, historiques, géographiques ou très chargées → traitement unitaire

---

# 8. Résultat attendu

Chaque entrée finale doit contenir :

- un champ `mot` strictement inchangé
- une `definition` intégralement traduite en français
- les renvois internes préservant leurs ancres
- les notations savantes traitées selon les règles du socle commun
- aucune altération de structure JSON
- aucune perte de contenu

Toutes les autres règles (termes théologiques, noms propres, références bibliques, appareil savant, encodage, interdictions) sont définies dans `AGENTS_COMMON.md`.
