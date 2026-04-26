# Livraison Rôle 4 - Modélisation prédictive

## Périmètre réalisé

Le rôle 4 couvre la modélisation prédictive des prix négatifs de l'électricité au Danemark.

Objectif retenu : prédire si le prix day-ahead devient négatif dans au moins une des deux zones danoises (`DK_1` ou `DK_2`).

Quatre horizons sont comparés :

- 1h : scénario principal, alerte court terme avec les meilleures performances.
- 3h : anticipation courte, encore proche du signal récent.
- 6h : compromis intermédiaire.
- 12h : anticipation plus longue, utile pour discuter les limites du modèle.

Le rapport retient le `1h` comme scénario principal. Les horizons `3h`, `6h` et `12h` sont conservés pour montrer que la performance baisse quand on cherche à anticiper plus loin.

## Livrables à rendre

- `modeling_pipeline.py` : code complet de modélisation, entraînement, évaluation et génération du rapport.
- `rapport_performance_role4.docx` : rapport Word final.

## Fichiers de support générés

- `models/best_model.joblib` : meilleur modèle entraîné.
- `models/all_models.joblib` : modèles entraînés sur le scénario principal `1h`.
- `models/all_horizon_models.joblib` : modèles entraînés sur les horizons `1h`, `3h`, `6h` et `12h`.
- `reports/model_performance.csv` : comparaison des performances `1h`.
- `reports/horizon_comparison.csv` : comparaison `1h / 3h / 6h / 12h`.
- `reports/permutation_importance_best_model.csv` : importance par permutation.
- `figures/confusion_matrix_best_model.png` : matrice de confusion.
- `figures/precision_recall_curves.png` : courbes précision-rappel.
- `figures/feature_importance_best_model.png` : importance des variables.
- `figures/horizon_comparison.png` : compromis performance / horizon.

## Modèles comparés

- Baseline : `DummyClassifier`
- Modèle interprétable : `LogisticRegression`
- Modèle avancé : `RandomForestClassifier`
- Modèle avancé : `HistGradientBoostingClassifier`

## Résultat principal

Scénario principal : `1h`.

Meilleur modèle : `random_forest`

- Average precision : 0.6700
- ROC-AUC : 0.9741
- F1-score : 0.6667
- Précision : 0.7203
- Recall : 0.6205

La classe positive est rare, autour de 1 à 2% selon les périodes. L'average precision est donc la métrique prioritaire. Le modèle fait nettement mieux que la baseline.

## Analyse critique courte

Le modèle `1h` détecte une part importante des épisodes de prix négatif avec une précision correcte. Ce compromis est acceptable pour un système d'alerte court terme.

Les performances diminuent lorsque l'horizon augmente (`3h`, `6h`, `12h`). Pour aller plus loin, il faudrait probablement ajouter des données externes comme des prévisions météo, des flux transfrontaliers ou des variables de marché supplémentaires.

## Validation

Tests exécutés :

```bash
python3 -m pytest 'Role 4/test_modeling_pipeline.py'
```

Résultat : 2 tests passés.

Pipeline exécuté :

```bash
python3 'Role 4/modeling_pipeline.py'
```

Résultat : génération complète des modèles, rapports et figures.
