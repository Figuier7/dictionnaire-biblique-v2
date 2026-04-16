# AGENTS_COMMON.md
Socle commun de règles pour tous les agents de traduction du projet Bible V2.
Ce fichier est référencé par `AGENTS.md` (Easton) et `AGENTS_SMITH.md` (Smith).
Toute modification ici s'applique à **toutes** les sources.

---

# 1. Structure JSON (invariant absolu)

Chaque entrée possède exactement la structure suivante :

```json
{
  "mot": "...",
  "definition": "..."
}
```

Obligations absolues :

- ne jamais modifier le champ `mot`
- ne jamais ajouter de champ
- ne jamais supprimer de champ
- ne jamais modifier l'ordre des entrées
- ne jamais modifier le nombre total d'entrées

---

# 2. Principe général de traduction

Tout texte anglais présent dans `definition` doit être traduit en français, sauf les éléments explicitement classés comme appareil savant à conserver.

Doivent être traduits :

- texte descriptif et narratif
- explications historiques, géographiques, théologiques
- citations d'auteurs et historiographiques
- remarques éditoriales rédigées en anglais
- notes sur les versions bibliques anglaises
- étymologies formulées en anglais

La présence de guillemets, de parenthèses ou de crochets descriptifs ne justifie pas la conservation de l'anglais.

---

# 3. Références bibliques

Les références bibliques doivent être converties selon la norme française définie dans `terminology-authority.json`, section `bible_references`.

Une même référence ne doit jamais apparaître sous des formes mixtes selon les lots.

Exemples courants :

- `Mark 3:16` → `Marc 3:16`
- `Luke 1:5` → `Luc 1:5`
- `John 3:23` → `Jean 3:23`
- `Acts 18:12` → `Actes 18:12`
- `1 Chronicles 24:10` → `1 Chr. 24:10`
- `1Ma 7:40` → `1 Mac. 7:40`

Les chapitres et versets restent inchangés.

---

# 4. Noms propres

Les noms propres doivent être traduits dans leur forme française classique quand une forme stable et certaine existe (voir `terminology-authority.json`, section `proper_names`).

Exemples :

- Jerusalem → Jérusalem
- Samaria → Samarie
- Nineveh → Ninive
- Damascus → Damas

Certains noms restent identiques : David, Boaz, Ruth.

Si la forme française est incertaine : conserver la forme source et signaler l'ambiguïté.

---

# 5. Termes théologiques

Les termes théologiques anglais doivent être traduits selon les conventions du projet (voir `terminology-authority.json`, section `theological_terms`).

Convention explicite :

- `God` → `Elohîm (Dieu)` si le champ `mot` contient "God" (1re occurrence, puis `Elohîm`), sinon `Elohîm` uniquement en prose courante. Dieux païens → `dieu`/`dieux` (minuscule)
- `LORD`, `Jehovah` → `YHWH`
- `the Lord` (hors tétragramme) → `le Seigneur`
- `Jesus` → `Yéhoshoua (Jésus)` à la première occurrence utile, puis `Yéhoshoua`
- `Christ` → `Mashiah (Christ)` ou `Mashiah` selon le contexte
- `Messiah` → `Mashiah`
- `Holy Spirit` / `Holy Ghost` → `Saint-Esprit`

Ne pas laisser ces termes en anglais dans la prose traduite.

---

# 6. Appareil savant, sigles et abréviations

## 6.1 À conserver tels quels

- `Heb.`, `Gr.`, `LXX`, `cf.`, `ibid.`, `comp.`, `q.v.`
- Titres d'ouvrages, noms d'auteurs (Josephus, Herodotus, Eusebius, etc.)
- Translittérations hébraïques et grecques
- Références bibliographiques

Le texte courant autour du sigle doit être traduit normalement.

## 6.2 À adapter en français

- `i.e.` → `c.-à-d.`
- `e.g.` → `par ex.`
- `viz.` → `à savoir`
- `No.` → `nᵒ`
- `B.C.` → `av. J.-C.`
- `A.D.` → `apr. J.-C.`

`etc.` peut rester `etc.` dans une phrase française correcte.

## 6.3 Mots anglais objet d'une remarque

Quand un mot anglais est lui-même l'objet d'une remarque éditoriale ou de version :

- conserver exactement la forme anglaise citée
- conserver la casse source
- le maintenir entre guillemets s'il est cité comme forme discutée
- traduire seulement la remarque qui l'encadre

## 6.4 Versions bibliques anglaises

- `Authorized Version` / `A.V.` → `Version Autorisée King James`
- `Revised Version` / `R.V.` → `King James Version Révisée`
- `in our version` → `dans notre version`
- `margin` / `in the margin` → `marge` / `en marge`

---

# 7. Classification des segments

Avant toute décision, classer chaque segment :

1. prose descriptive, narrative, géographique, historique, théologique → **traduire**
2. remarque éditoriale sur une version, une marge, une dénomination → **traduire**
3. appareil savant strict ou sigle de référence → **conserver** selon les règles
4. ancre interne ou renvoi structurel → **conserver l'ancre**, traduire le texte autour

En cas de doute, ne pas conserver l'anglais par défaut. La prudence ne doit pas empêcher la traduction.

---

# 8. Encodage

Tous les fichiers de sortie doivent être en :

**UTF-8 avec BOM**

afin d'éviter tout problème de mojibake dans les pipelines de traduction et l'intégration Bible V2.

---

# 9. Interdictions absolues

Il est interdit de :

- tronquer une définition
- résumer le texte
- reformuler de manière doctrinale
- ajouter des commentaires
- ajouter des interprétations théologiques
- paraphraser librement une notice

La traduction doit rester strictement fidèle au texte original.

---

# 10. Résultat attendu

Chaque entrée finale doit contenir :

- un champ `mot` strictement inchangé
- une `definition` intégralement traduite en français
- les notations savantes traitées selon les règles ci-dessus
- aucune altération de structure JSON
- aucune perte de contenu
