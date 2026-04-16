# Pipeline re-typage catégories concepts

## Contexte

Les catégories `c` de `concept-meta.json` étaient massivement mal typées (ex: "amour" → personnage, "figuier" → personnage, "Hydropisie" → rite, etc.). Impact : impossible de faire un audit automatique fiable des mappings concept → Strong.

Ce pipeline re-type les 9 873 concepts via LLM batch contre une taxonomie fermée de 20 catégories.

## Taxonomie (20 catégories)

### Noms propres (→ Strong n.pr.*)
- `personnage` — individus humains nommés (Adam, Paul, Ruth, David)
- `etre_spirituel` — divinités, anges, démons (YHWH, Gabriel, Baal, ange générique)
- `lieu` — toponymes géographiques non sacrés (Jérusalem, Eden, Canaan)
- `lieu_sacre` — lieux à fonction religieuse (Temple, Tabernacle, Sanctuaire)
- `peuple` — tribus, nations, clans (Israélites, Moabites)
- `livre_biblique` — noms de livres (Genèse, Matthieu, Psaumes)

### Noms communs / concepts (→ Strong non-proper)
- `doctrine` — concepts théologiques (foi, salut, péché, grâce, Trinité)
- `rite` — cérémonies, pratiques religieuses (baptême, circoncision)
- `institution` — structures sociales persistantes (royaume, mariage, synagogue)
- `fonction` — titres, rôles, métiers (roi, prêtre, prophète, scribe, berger)
- `objet_sacre` — objets liturgiques (arche d'alliance, autel, éphod, ménorah)
- `objets_et_vetements` — objets profanes (robe, sandale, balance, lampe)
- `plante` — flore (figuier, cèdre, blé, vigne)
- `animal` — faune (agneau, lion, aigle, serpent)
- `alimentation_et_agriculture` — aliments, techniques agri (pain, vin, miel, vendanges)
- `corps_et_sante` — parties du corps, maladies (cœur, main, lèpre, hydropisie)
- `mesures_et_temps` — unités et périodes (coudée, shekel, année, sabbat)
- `matiere` — matériaux (bronze, lin, or, sel)
- `evenement` — événements historiques (Exode, Déluge, Pentecôte)
- `nature` — phénomènes, géographie générique (désert, pluie, mer)

## Étapes du pipeline

### 1. Préparation batch (fait)

```bash
python scripts/retype_categories_prepare.py
```

- Lit `uploads/dictionnaires/concept-meta.json`
- Construit 9 873 requêtes avec prompt système + taxonomie
- Écrit `work/retype/batch_input.jsonl` (38.7 MB)
- Écrit `work/retype/taxonomy.json`

### 2. Submission batch (fait — en cours)

```bash
export OPENAI_API_KEY="sk-..."
python scripts/retype_categories_submit.py
```

- Upload fichier vers OpenAI
- Crée batch job (model: gpt-4o-mini, temperature: 0, max_tokens: 10)
- Écrit `work/retype/batch_meta.json` avec `batch_id`

**Modèle choisi** : `gpt-4o-mini` (au lieu de `gpt-4o` — quota enqueue limité à 90k tokens/org pour 4o, largement insuffisant pour 10M tokens. 4o-mini a un quota plus élevé. Pour classification en 20 catégories, la différence de qualité est minime.)

**Coût estimé** : ~$0.80 USD (avec batch discount 50%).

### 3. Check status

```bash
python scripts/retype_categories_submit.py --status
```

Statuts possibles :
- `validating` : OpenAI vérifie le format (qques min)
- `in_progress` : traitement en cours (plusieurs heures typiquement)
- `completed` : terminé, output disponible
- `failed` : erreur — check `batch.errors`
- `cancelled` / `expired` : annulé

### 4. Download + apply (à faire après `completed`)

```bash
# Dry run d'abord pour voir les stats
python scripts/retype_categories_apply.py

# Si OK, committer
python scripts/retype_categories_apply.py --commit
```

Effets :
- Télécharge `work/retype/batch_output.jsonl`
- Parse les catégories retournées, valide contre taxonomie
- Diff avec l'ancien : rapport dans `work/retype/retype_report.json`
- Backup `concept-meta.json.bak-pre-retype` + `concepts.json.bak-pre-retype`
- Met à jour `concept-meta.json` champ `c`
- Met à jour `concepts.json` champ `category`

### 5. Sync derivatives

```bash
python scripts/sync_browse_index.py
```

Régénère `browse-index.json` avec les nouvelles catégories + labels BYM.

### 6. Re-audit mappings hébreu

```bash
# Dry run
python scripts/reaudit_hebrew_mappings.py

# Vérifier les "mappings critiques" conservés (pere H1, yhwh H3068, etc.)
# Si OK, committer
python scripts/reaudit_hebrew_mappings.py --commit
```

Avec catégories propres, cette fois-ci l'audit POS-catégorie peut être appliqué sans régression. Nettoie les mappings faux positifs.

### 7. Upload + purge

```bash
scp uploads/dictionnaires/concept-meta.json figuier-prod:.../uploads/dictionnaires/
scp uploads/dictionnaires/concepts.json figuier-prod:.../uploads/dictionnaires/
scp uploads/dictionnaires/browse-index.json figuier-prod:.../uploads/dictionnaires/
scp uploads/dictionnaires/concept-hebrew-map.json figuier-prod:.../uploads/dictionnaires/

ssh figuier-prod "cd domains/alombredufiguier.org/public_html && wp litespeed-purge all && wp cache flush && touch wp-content/uploads/dictionnaires/*.json"
```

### 8. Vérification live

- `/dictionnaire-biblique/pere/` : sidebar H1 (père) seul
- `/dictionnaire-biblique/figuier/` : catégorie `plante`, sidebar H8384
- `/dictionnaire-biblique/amour/` : catégorie `doctrine`, Strong n.m/vb seuls
- `/dictionnaire-biblique/` browse : labels FR + catégories cohérentes

## Rollback

Si problème après commit :

```bash
cp uploads/dictionnaires/concept-meta.json.bak-pre-retype uploads/dictionnaires/concept-meta.json
cp uploads/dictionnaires/concepts.json.bak-pre-retype uploads/dictionnaires/concepts.json
cp uploads/dictionnaires/concept-hebrew-map.json.bak-pre-reaudit uploads/dictionnaires/concept-hebrew-map.json
# Re-upload + purge
```
