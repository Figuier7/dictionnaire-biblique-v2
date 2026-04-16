# Traduction Easton - Deux modes distincts

## But

Clarifier l'architecture du projet pour eviter de confondre :

- un mode `batch/API`,
- un mode `100% Codex App local`, sans API.

Le depot documentait surtout le premier. Le second est maintenant outille localement en PowerShell dans `scripts/codex_local/`, afin d'etre executable dans cette session Windows sans dependre de `python`.

## Ce qui depend reellement d'une API

Depend de l'API OpenAI :

- la generation de `batch_input.jsonl`,
- l'upload du JSONL,
- l'execution d'un job batch,
- le telechargement de `results.jsonl`,
- le cycle de reparation via `repair_batch.jsonl` et `repair_results.jsonl`.

Peut etre fait entierement en local :

- lire `eastons.json`,
- segmenter les entrees en chunks de travail,
- stocker ces chunks dans des fichiers JSON locaux,
- faire traduire ces chunks par Codex App au fil des tours,
- valider le JSON produit,
- detecter les soupcons de troncage,
- faire une QA locale sur les chunks traduits,
- fusionner les chunks valides en `eastons_fr.json`,
- generer `proper_nouns_unknown.json`,
- produire une liste de chunks ou d'entrees a retraduire.

Peut aussi etre execute en mode hybride `manifest-first` :

- la logique metier locale reste intacte,
- les `source_chunks` et `repair tasks` peuvent etre compiles en requetes batch/API,
- les resultats batch sont ensuite reingestes dans les memes dossiers locaux avant validation, QA et merge.

## Etat actuel du depot

Le depot contient actuellement :

- des scripts orientes `batch/API` dans `scripts/`,
- une documentation `batch/API` dans `docs/TRANSLATION_PIPELINE.md`,
- une documentation complete du mode `Codex App local`,
- un pipeline local complet dans `scripts/codex_local/` pour la segmentation, la validation chunk par chunk, la QA locale globale, la reparation ciblee et la fusion finale sans API.

Conclusion honnete :

- le mode `batch/API` reste le mode historique du depot,
- le mode `Codex App local` est maintenant scriptable et testable localement,
- la traduction elle-meme reste un travail par chunks dans Codex App, pas un traitement autonome hors conversation.

## Scripts actuels a reclasser

Scripts clairement `batch/API` :

- `scripts/build_batch_input.py`
- `scripts/build_repair_batch.py`
- `scripts/qa_results.py`
- `scripts/merge_results.py`

Scripts locaux disponibles :

- `scripts/codex_local/build_chunk_manifest.ps1`
- `scripts/codex_local/export_source_chunks.ps1`
- `scripts/codex_local/validate_translated_chunk.ps1`
- `scripts/codex_local/qa_local_chunks.ps1`
- `scripts/codex_local/build_repair_manifest.ps1`
- `scripts/codex_local/merge_local_chunks.ps1`
- `scripts/codex_local/common.ps1`

## Structure cible recommandee

La structure la plus lisible a court terme est la suivante :

```text
docs/
  TRANSLATION_MODES.md
  batch_api/
    README.md
  codex_local/
    README.md

scripts/
  batch_api/
    build_batch_input.py
    build_repair_batch.py
    qa_results.py
    merge_results.py
  codex_local/
    build_chunk_manifest.ps1
    export_source_chunks.ps1
    validate_translated_chunk.ps1
    qa_local_chunks.ps1
    build_repair_manifest.ps1
    merge_local_chunks.ps1
    common.ps1

work/
  batch_api/
    requests/
    responses/
    reports/
  codex_local/
    manifests/
    source_chunks/
    translated_chunks/
    reports/
    repair/
```

## Renommages et deplacements recommandes

Pour supprimer l'ambiguite, les scripts existants devraient etre deplaces ou renommes ainsi :

- `scripts/build_batch_input.py` -> `scripts/batch_api/build_batch_input.py`
- `scripts/build_repair_batch.py` -> `scripts/batch_api/build_repair_batch.py`
- `scripts/qa_results.py` -> `scripts/batch_api/qa_batch_results.py`
- `scripts/merge_results.py` -> `scripts/batch_api/merge_batch_results.py`

Les deux scripts prototypes locaux devraient soit :

- etre deplaces vers `scripts/codex_local/` en tant que prototypes temporaires,
- soit etre remplaces par des scripts Python generalises.

## Ce qui a ete cree pour rendre le mode local reellement exploitable

### 1. Une segmentation explicite

Crees :

- `scripts/codex_local/build_chunk_manifest.ps1`
- `scripts/codex_local/export_source_chunks.ps1`

Role :

- decouper `eastons.json` en chunks de travail,
- produire un manifeste local deterministe,
- conserver l'ordre des entrees et leurs IDs source.

### 2. Un format de chunk local clair

Format recommande pour un chunk source :

```json
[
  {
    "id": 0,
    "mot": "A",
    "definition": "..."
  }
]
```

Format recommande pour un chunk traduit :

```json
[
  {
    "id": 0,
    "mot": "A",
    "definition": "...",
    "proper_nouns_unknown": []
  }
]
```

Le champ `id` est indispensable pour le merge local fiable.

### 3. Une validation locale dediee

Crees :

- `scripts/codex_local/validate_translated_chunk.ps1`

Role :

- verifier le JSON d'un chunk traduit,
- comparer le chunk traduit au chunk source correspondant,
- detecter les ecarts structurels avant la fusion.

### 4. Une QA locale globale

Crees :

- `scripts/codex_local/qa_local_chunks.ps1`
- `scripts/codex_local/build_repair_manifest.ps1`

Role :

- consolider les validations de tous les chunks,
- lister les chunks valides,
- lister les chunks ou entrees a retraduire.

### 5. Une fusion locale finale

Crees :

- `scripts/codex_local/merge_local_chunks.ps1`

Role :

- fusionner les chunks traduits valides,
- restaurer l'ordre source,
- produire `eastons_fr.json`,
- produire `proper_nouns_unknown.json`.

## Segmentation recommandee pour Codex App local

Le mode local ne doit pas traduire tout `eastons.json` en une seule operation.

Segmentation actuellement appliquee par le pipeline hybride :

- seuil `single-entry` si `definition.length > 6000`,
- isolement explicite des entrees sensibles (`A.V.`, `R.V.`, `Authorized Version`, `Revised Version`, `Jesus Christ`, `Messiah`, `Jehovah`, etc.),
- isolement structurel si au moins `2` signaux se cumulent,
- sinon groupement par chunks de `10000` caracteres source maximum,
- avec `20` entrees maximum par chunk,
- sans jamais couper une entree en deux.

Constat sur le fichier actuel :

- `3963` entrees au total,
- ancien manifest du premier run global hybride : `1594` chunks,
- apres premier recalibrage prudent des isolements de type `A.V./R.V./Authorized/Revised` avec trigger unique et sans signal structurel : `1271` chunks,
- apres deuxieme recalibrage prudent sur tous les ensembles de triggers exclusivement de type `A.V./R.V./Authorized/Revised`, toujours sans signal structurel : `1099` chunks,
- apres troisieme recalibrage strictement selectif sur `43` entrees `Jehovah` auditees comme `candidate_prudent`, sans toucher aux cas doctrinaux, moyens ou sensibles : `1038` chunks,
- ancien manifest : `943` chunks isoles, `1100` chunks mono-entree,
- manifest recalibre niveau 1 : `721` entrees isolees, `833` chunks mono-entree,
- manifest recalibre niveau 2 : `613` entrees isolees, `693` chunks mono-entree,
- manifest recalibre niveau 3 selectif : `570` entrees isolees, `642` chunks mono-entree.

Important :

- l'estimation d'environ `295` chunks correspondait a une segmentation plus simple, anterieure, essentiellement basee sur la longueur,
- elle ne decrit ni le manifest du premier run global hybride (`1594` chunks), ni les manifests recalibres successifs (`1271`, `1099`, puis `1038` chunks),
- le script `scripts/codex_local/build_chunk_manifest.ps1` produit par defaut le calibrage prudent de niveau 2,
- le meme script peut produire un niveau 3 strictement selectif si `-SelectiveJehovahAudit` pointe vers un audit JSON borne aux cas `candidate_prudent`,
- pour toute execution locale hybride, le manifeste produit par le script doit faire foi.

Conclusion honnete :

- le pipeline hybride actuel privilegie la surete structurelle et la reparabilite,
- mais il augmente fortement le nombre de chunks a piloter dans Codex App.

## Recommandation nette

Pour le projet :

- conserver le mode `batch/API` comme mode separe et explicitement nomme,
- conserver le vrai mode `Codex App local` maintenant scripté avec docs dedies,
- ne plus presenter `scripts/` ni `docs/TRANSLATION_PIPELINE.md` comme s'ils decrivaient tout le projet de traduction.

Le batch n'est donc pas obligatoire.

Il est seulement le mode aujourd'hui le plus outille dans le depot.

Le mode recommande a terme est maintenant un bridge `manifest-first, executor-agnostic` :

- manifest et QA locales comme source de verite,
- batch/API uniquement comme couche d'execution,
- repair et merge toujours pilotes par le pipeline local.
