# Traduction Easton - Mode 100% Codex App local

## Perimetre

Ce document decrit le mode `100% Codex App local`, sans appel API explicite depuis le projet.

Ce mode suppose :

- que Codex App est utilise pour lire et ecrire des fichiers locaux,
- que les traductions sont produites chunk par chunk dans la conversation,
- que toute la preparation, la validation, la QA et la fusion sont locales.

Ce mode ne suppose pas :

- `OPENAI_API_KEY`,
- `curl`,
- fichiers `batch_input.jsonl`,
- reponses `results.jsonl` provenant d'une API.

## Ce qu'il manque aujourd'hui

Le pipeline local est maintenant implemente dans `scripts/codex_local/` en PowerShell, parce que `python` n'est pas disponible directement dans cette session Windows.

Les scripts batch existants restent separes et ne sont pas requis pour ce mode.

Depuis cette revision, le mode local suit une methode hybride :

- chunks pour les entrees simples,
- isolement automatique des entrees longues,
- isolement automatique des entrees sensibles,
- repair par entree quand le chunk n'est pas structurellement casse.

## Structure cible du mode local

```text
work/codex_local/
  manifests/
    chunk_manifest.json
    repair_manifest.json
  source_chunks/
    chunk_0001.source.json
    chunk_0002.source.json
  translated_chunks/
    chunk_0001.fr.json
    chunk_0002.fr.json
  reports/
    chunk_0001.qa.json
    chunk_0002.qa.json
    qa_summary.csv
```

## Scripts implementes

### `build_chunk_manifest.ps1`

Entree :

- `eastons.json`

Sorties :

- `work/codex_local/manifests/chunk_manifest.json`

Role :

- attribuer ou reprendre les IDs source,
- calculer les longueurs et metriques structurelles,
- detecter les entrees sensibles,
- repartir les entrees en chunks hybrides,
- figer le plan de travail.

### `export_source_chunks.ps1`

Entrees :

- `eastons.json`
- `chunk_manifest.json`

Sorties :

- `work/codex_local/source_chunks/chunk_XXXX.source.json`

Role :

- ecrire les fichiers source a traduire par chunk,
- garantir que chaque chunk est independant et tracable.

### `validate_translated_chunk.ps1`

Entrees :

- un chunk source,
- un chunk traduit correspondant

Sortie :

- `work/codex_local/reports/chunk_XXXX.qa.json`

Role :

- verifier le JSON,
- verifier les IDs,
- verifier le nombre d'entrees,
- verifier l'ordre,
- verifier les cles requises,
- detecter les signes forts de troncage ou de derive.

### `qa_local_chunks.ps1`

Entrees :

- tous les rapports chunk QA,
- tous les chunks traduits

Sortie :

- `work/codex_local/reports/qa_summary.csv`

Role :

- consolider l'etat de tous les chunks,
- consolider l'etat de toutes les entrees,
- lister les chunks valides,
- lister les chunks a reparer,
- lister les entrees a reparer,
- fournir une vue d'avancement.

### `build_repair_manifest.ps1`

Entree :

- `qa_summary.csv`

Sortie :

- `work/codex_local/manifests/repair_manifest.json`

Role :

- produire des taches de repair,
- descendre au niveau de l'entree quand c'est possible,
- ne garder le repair par chunk que pour les erreurs structurelles.

### `merge_local_chunks.ps1`

Entrees :

- `chunk_manifest.json`
- tous les chunks traduits valides

Sorties :

- `eastons_fr.json`
- `proper_nouns_unknown.json`

Role :

- reconstituer le tableau final dans l'ordre exact de la source,
- refuser la fusion si un chunk manque ou si un ID est duplique,
- agreger les noms propres inconnus.

## Mode operatoire recommande

### 1. Segmenter

Regles recommandees :

- ne jamais couper une entree en deux,
- isoler toute entree dont `definition.length > 6000`,
- isoler toute entree declenchant un motif sensible explicite,
- isoler aussi les entrees structurellement complexes si plusieurs signaux se cumulent,
- pour les autres, remplir des chunks jusqu'a `10000` caracteres source max,
- limiter a `20` entrees par chunk.

Motifs explicites d'isolement sensible :

- `A.V.`
- `R.V.`
- `Authorized Version`
- `Revised Version`
- `Jesus Christ`
- `Christ Jesus`
- `Jesus the Christ`
- `the Christ`
- `Messiah`
- `LORD God`
- `the LORD` / `LORD`
- `Jehovah`
- `Yahweh`

Signaux structurels utilises :

- `paragraph_count >= 4`
- `reference_count >= 12`
- `source_chars >= 3500`
- `cross_reference_count >= 1`

Une entree est isolee par complexite structurelle si au moins `2` de ces signaux sont vrais.

Pourquoi :

- chunk trop grand = risque accru de troncage ou d'omission silencieuse,
- chunk trop petit = workflow interminable,
- l'isolement des cas sensibles reduit les faux positifs et rend le repair plus propre,
- cette strategie garde les cas simples groupables sans melanger les cas fragiles.

### 2. Traduire chunk par chunk dans Codex App

Pour chaque chunk source :

- lire uniquement `chunk_XXXX.source.json`,
- produire `chunk_XXXX.fr.json`,
- conserver strictement l'ordre et les IDs,
- ne pas fusionner a la main dans le fichier final a ce stade.

### 3. Valider le JSON immediatement

Chaque chunk traduit doit etre valide des sa production :

- JSON parseable,
- tableau attendu,
- memes IDs et meme ordre,
- memes comptes d'entrees que le chunk source,
- champs requis presents.

Validation minimale recommandee par entree :

- `id`
- `mot`
- `definition`
- `proper_nouns_unknown`

Le manifest hybride ajoute aussi un suivi local utile :

- `entries[]` : un enregistrement par ID avec `chunk_id`, `chunk_position`, `chunk_mode`, `isolation_mode`, triggers et raisons,
- `chunks[]` : un enregistrement par chunk avec `chunk_mode`, `entry_ids` et raisons d'isolement.

## Controles anti-troncage

Le mode local ne peut pas prouver semantiquement le `zero ajout`, mais il peut fortement reduire les risques de troncage.

Controles recommandes :

- ratio `len(definition_fr) / len(definition_source)` :
  - echec dur si `< 0.55`
  - alerte si `< 0.75`
- meme nombre de paragraphes,
- meme nombre de references de type `chapitre:verset`,
- meme nombre de guillemets,
- meme nombre de renvois de type `[123]ENTRY`,
- meme nombre de marqueurs `Comp.` et `marg.`,
- absence de fin brutalement coupee sur une entree longue,
- absence d'ID manquant ou en trop.

## QA locale

La QA locale doit verifier au minimum :

- residus interdits : `Dieu`, `l'Eternel`, `A.V.`, `R.V.`, `Authorized Version`, `Revised Version`,
- eventuels residus anglais manifestes sur des segments longs,
- forme interdite `Yehoshoua (...) Mashiah (Christ)` quand la source est `Jesus Christ`,
- conformite du schema JSON,
- ordre source conserve,
- chunks manquants,
- doublons d'IDs,
- `proper_nouns_unknown` de type liste,
- statut par entree meme quand un chunk est bloque,
- recommandation de repair `entry` ou `chunk`.

Quand un chunk entier est invalide, la QA doit aussi marquer les entrees concernees comme `blocked` pour conserver la tracabilite des IDs.

## Fusion finale

La fusion finale ne doit intervenir qu'apres QA.

Conditions de merge :

- tous les chunks requis presents,
- tous les chunks requis valides,
- aucun trou d'ID,
- aucun doublon,
- ordre exact restaure.

Sorties finales :

- `eastons_fr.json` : uniquement `mot` et `definition`
- `proper_nouns_unknown.json` : liste unique triee

## Ce qu'un workflow local fiable permet honnetement

Oui :

- une traduction integrale en plusieurs tours,
- des fichiers locaux a chaque etape,
- une validation forte contre le troncage structurel,
- une reparabilite fine au niveau de l'entree dans les chunks groupes,
- une fusion deterministe.

Non :

- une garantie absolue de fidelite semantique sans relecture ciblee,
- une traduction sure de tout le fichier en une seule passe,
- l'usage direct des scripts batch actuels comme s'ils etaient deja compatibles avec le mode local.

## Decision d'architecture recommandee

Le mode local doit etre traite comme un pipeline autonome.

Il faut donc :

- une documentation separee,
- des scripts separes,
- un espace de travail separe,
- des formats de chunks separes,
- une QA separee du mode batch.
