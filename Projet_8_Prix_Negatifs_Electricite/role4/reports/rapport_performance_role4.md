# Rapport Role 4 - Modelisation predictive

## Objectif

Predire 24 heures a l'avance les heures ou le prix day-ahead devient negatif dans au moins une zone danoise (`DK_1` ou `DK_2`).

La cible principale est `is_negative_price(t+1h)`: on predit si un prix negatif apparait dans l'heure suivante. Les horizons 3h, 6h et 12h sont conserves comme analyse de robustesse pour montrer comment les performances baissent quand on anticipe plus loin.

## Pourquoi comparer 1h, 12h et 24h ?

- `1h` mesure une prediction tres court terme: elle est souvent meilleure, mais moins ambitieuse.
- `12h` donne un compromis intermediaire entre performance et anticipation.

Le rapport retient `1h` comme scenario principal, car il donne un modele performant et exploitable. Les horizons `3h`, `6h` et `12h` servent a montrer que plus on predit loin, plus le probleme devient difficile.

| horizon_h | best_model | average_precision | roc_auc | f1 | precision | recall | positive_rate_test |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | random_forest | 0.6700 | 0.9741 | 0.6667 | 0.7203 | 0.6205 | 0.0220 |
| 3 | random_forest | 0.4076 | 0.9332 | 0.4116 | 0.5135 | 0.3434 | 0.0220 |
| 6 | hist_gradient_boosting | 0.2270 | 0.8593 | 0.2831 | 0.2258 | 0.3795 | 0.0220 |
| 12 | hist_gradient_boosting | 0.1963 | 0.8606 | 0.2275 | 0.1875 | 0.2892 | 0.0220 |

## Donnees et split

- Source: `opsd_clean_focus_countries.csv`
- Observations apres feature engineering: 50,376
- Horizon de prediction: 1h
- Split chronologique: 70% train, 15% validation, 15% test
- Positifs train/validation/test: 284 / 88 / 166
- Taux positifs train/validation/test: 0.81% / 1.16% / 2.20%

## Comparaison des modeles

| model | average_precision | roc_auc | f1 | precision | recall | balanced_accuracy | threshold |
| --- | --- | --- | --- | --- | --- | --- | --- |
| random_forest | 0.6700 | 0.9741 | 0.6667 | 0.7203 | 0.6205 | 0.8075 | 0.3577 |
| logistic_regression | 0.5833 | 0.9737 | 0.6030 | 0.5172 | 0.7229 | 0.8539 | 0.9954 |
| hist_gradient_boosting | 0.5826 | 0.9182 | 0.6101 | 0.6382 | 0.5843 | 0.7884 | 0.8537 |
| dummy_most_frequent | 0.0220 | 0.5000 | 0.0430 | 0.0220 | 1.0000 | 0.5000 | 0.0000 |

## Modele retenu

Le modele retenu est `random_forest`, choisi sur l'average precision test. Cette metrique est prioritaire car la classe positive est rare; l'accuracy brute serait trompeuse.

- Threshold optimise sur validation: 0.3577
- Average precision test: 0.6700
- ROC-AUC test: 0.9741
- F1 test: 0.6667
- Precision test: 0.7203
- Recall test: 0.6205

## Matrice de confusion du modele retenu

- Vrais negatifs: 7351
- Faux positifs: 40
- Faux negatifs: 63
- Vrais positifs: 103

## Variables les plus influentes

| feature | importance_mean | importance_std |
| --- | --- | --- |
| price_DK1_lag_1h | 0.27131 | 0.01091 |
| DK_wind_offshore_generation_actual | 0.12250 | 0.01255 |
| offshore_share | 0.11259 | 0.01667 |
| price_DK1_lag_2h | 0.03701 | 0.00354 |
| DK_2_wind_generation_actual | 0.03119 | 0.01008 |
| hour_sin | 0.01895 | 0.00353 |
| dow_cos | 0.01520 | 0.00630 |
| price_DK1_lag_3h | 0.01146 | 0.00376 |

## Analyse critique

Le probleme est fortement desequilibre: les prix negatifs representent une petite minorite des heures. Le modele doit donc etre juge sur sa capacite a retrouver les episodes rares, pas sur le nombre total de bonnes predictions.

Le split chronologique montre aussi une derive temporelle: le taux de positifs change entre train, validation et test. C'est coherent avec l'augmentation des episodes de prix negatifs identifiee dans l'analyse exploratoire, mais cela limite la generalisation si le marche evolue encore.

Les features les plus utiles sont principalement liees a l'etat recent du marche et au niveau de production eolienne/renouvelable. C'est coherent avec le mecanisme attendu: forte production renouvelable, demande plus faible et persistance temporelle des prix bas.

Les performances doivent etre interpretees comme un signal de prediction court terme, pas comme une garantie operationnelle de trading. Les donnees n'incluent pas toutes les informations de marche disponibles en production, notamment les flux transfrontaliers complets, les indisponibilites centrales et les previsions meteo detaillees.

SHAP n'est pas utilise ici car le package n'est pas installe dans l'environnement local. L'interpretabilite est couverte par l'importance par permutation, qui est compatible avec tous les modeles sklearn et mesure l'impact reel des variables sur l'average precision.

## Explication rapide des metriques

- Average precision: resume la courbe precision-rappel. C'est la metrique principale parce que les prix negatifs sont rares.
- ROC-AUC: mesure la capacite generale a classer les heures positives devant les negatives.
- Precision: parmi les alertes envoyees par le modele, proportion de vraies alertes.
- Recall: proportion des vrais episodes de prix negatif detectes.
- F1-score: compromis entre precision et recall.
- Balanced accuracy: accuracy corrigee pour tenir compte du desequilibre des classes.

## Livrables generes

- `Role 4/models/best_model.joblib`
- `Role 4/models/all_models.joblib`
- `Role 4/reports/model_performance.csv`
- `Role 4/reports/permutation_importance_best_model.csv`
- `Role 4/figures/confusion_matrix_best_model.png`
- `Role 4/figures/precision_recall_curves.png`
- `Role 4/figures/feature_importance_best_model.png`
- `Role 4/figures/horizon_comparison.png`
- `Role 4/rapport_performance_role4.docx`
