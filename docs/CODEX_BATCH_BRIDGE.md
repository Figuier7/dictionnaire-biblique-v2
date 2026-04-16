# Bridge batch/API sur pipeline local Easton

## But

Ce document decrit le bridge `manifest-first, executor-agnostic`.

La logique metier locale reste la source de verite :

- segmentation canonique,
- export des `source_chunks`,
- validation locale,
- QA locale,
- `repair_manifest`,
- merge final.

La couche batch/API ne sert qu'a executer les traductions a grande echelle.

## Scripts

Scripts concernes dans `scripts/codex_local/` :

- `build_chunk_batch_requests.ps1`
- `ingest_batch_results.ps1`
- `build_repair_batch_requests.ps1`
- `batch_bridge_common.ps1`

## Flux recommande

1. Generer le manifest canonique avec `build_chunk_manifest.ps1`.
2. Exporter les chunks source avec `export_source_chunks.ps1`.
3. Compiler les chunks vers JSONL batch avec `build_chunk_batch_requests.ps1`.
4. Executer le batch hors du pipeline local.
5. Telecharger les resultats JSONL.
6. Reinjecter localement avec `ingest_batch_results.ps1 -Mode chunk`.
7. Valider et faire la QA locale avec `validate_translated_chunk.ps1` et `qa_local_chunks.ps1`.
8. Produire le `repair_manifest` avec `build_repair_manifest.ps1`.
9. Compiler les repairs vers JSONL batch avec `build_repair_batch_requests.ps1`.
10. Telecharger les resultats repair.
11. Reinjecter localement avec `ingest_batch_results.ps1 -Mode repair`.
12. Fusionner uniquement via `merge_local_chunks.ps1` quand la QA est strictement propre.

## Formats attendus

### Requetes batch chunk

Fichiers de sortie par defaut :

- `work/<workspace>/batch/requests/chunk_requests.jsonl`
- `work/<workspace>/batch/requests/chunk_requests.plan.json`

Chaque ligne JSONL est une requete batch avec :

- `custom_id = chunk_XXXX`
- `messages[]`
- `response_format = json_object`

Le modele doit retourner uniquement un objet JSON de la forme :

```json
{
  "chunk_id": "chunk_0001",
  "entries": [
    {
      "id": 0,
      "mot": "A",
      "definition": "...",
      "proper_nouns_unknown": []
    }
  ]
}
```

### Resultats batch chunk

Resultat telecharge par l'executeur batch :

- `work/<workspace>/batch/results/chunk_results.jsonl`

Apres reinjection par `ingest_batch_results.ps1 -Mode chunk`, chaque reponse valide devient :

- `work/<workspace>/translated_chunks/chunk_XXXX.fr.json`

Le bridge ne change pas la logique locale : il extrait simplement `entries[]` pour reecrire le fichier local attendu.

### Requetes batch repair

Fichiers de sortie par defaut :

- `work/<workspace>/batch/requests/repair_requests.jsonl`
- `work/<workspace>/batch/requests/repair_requests.plan.json`

Chaque ligne correspond a une task du `repair_manifest` :

- `custom_id = task_id`
- `task_type = chunk` ou `entry`
- `repair_scope = full_chunk` ou `single_entry`

Le modele doit retourner uniquement :

```json
{
  "task_id": "entry_0005",
  "entries": [
    {
      "id": 5,
      "mot": "Abaddon",
      "definition": "...",
      "proper_nouns_unknown": []
    }
  ]
}
```

### Resultats batch repair

Resultat telecharge :

- `work/<workspace>/batch/results/repair_results.jsonl`

Apres reinjection par `ingest_batch_results.ps1 -Mode repair`, chaque reponse valide devient :

- `work/<workspace>/repair/translated_chunks/<task_id>.repair.fr.json`

## Rapports et dossiers

Sorties generees par les nouveaux scripts :

- `batch/requests/chunk_requests.jsonl`
- `batch/requests/chunk_requests.plan.json`
- `batch/requests/repair_requests.jsonl`
- `batch/requests/repair_requests.plan.json`
- `batch/reports/chunk_ingest_summary.json`
- `batch/reports/repair_ingest_summary.json`
- `batch/raw_errors/chunk/`
- `batch/raw_errors/repair/`

## Garanties de compatibilite

Le bridge batch ne remplace pas la validation locale.

Il se contente de :

- compiler des artefacts batch depuis les `source_chunks` et le `repair_manifest`,
- retransformer les sorties batch vers les memes fichiers `.fr.json` que le pipeline local attend deja.

Toutes les decisions de blocage restent locales :

- JSON invalide,
- ids en trop ou manquants,
- ordre incorrect,
- troncage suspect,
- residus interdits,
- repair cible,
- refus de merge si des ids manquent.
