# Étapes Réalisées - Rôle 1 : Données & Ingestion

**Étudiant 1**  
**Projet 8 : Prix Négatifs de l'Électricité Renouvelable**

---

## 1. Création de la Structure du Projet

```bash
cd "/Users/loulou/Documents/Documents - Mac'Donald/school/s6/projet 2eme session"

mkdir -p Projet_8_Prix_Negatifs_Electricite/{data/{raw,processed,interim},notebooks,scripts,docs,reports,outputs,config}
```

## 2. Installation des Dépendances Python

Création du fichier `requirements.txt`:
```
pandas>=2.0.0
numpy>=1.24.0
matplotlib>=3.7.0
seaborn>=0.12.0
requests>=2.31.0
tqdm>=4.65.0
PyYAML>=6.0
jupyter>=1.0.0
scipy>=1.11.0
openpyxl>=3.1.0
```

Installation:
```bash
cd Projet_8_Prix_Negatifs_Electricite
python3 -m pip install --user -r requirements.txt
```

## 3. Configuration du Pipeline

Création de `config/pipeline_config.yaml` avec:
- Pays focus: DE, DK, FR
- URL source OPSD
- Paramètres de nettoyage (seuil 50% pour suppression colonnes)
- Split temporel train/val/test

## 4. Téléchargement des Données

Script `scripts/01_download_opsd_data.py`:
```bash
python3 scripts/01_download_opsd_data.py
```

Résultat: `data/raw/opsd_timeseries/time_series_60min_singleindex.csv` (124 Mo)

## 5. Exploration Initiale

Script `scripts/02_initial_exploration.py`:
```bash
python3 scripts/02_initial_exploration.py
```

Découvertes:
- 50,401 lignes × 300 colonnes
- Période: 2015-2020
- 484 prix négatifs en Allemagne détectés
- Rapport sauvegardé: `reports/initial_exploration.txt`

## 6. Analyse de Qualité

Script `scripts/03_data_quality_analysis.py`:
```bash
python3 scripts/03_data_quality_analysis.py
```

Résultats:
- 26.2% de valeurs manquantes globalement
- 0 gaps temporels (série parfaite)
- 19 colonnes avec ≥50% missing identifiées
- Rapport JSON: `reports/data_quality_report.json`

## 7. Nettoyage des Données

Script `scripts/04_data_cleaning.py`:
```bash
python3 scripts/04_data_cleaning.py
```

Transformations appliquées:
1. Filtrage pays focus (DE, DK, FR): 300 → 71 colonnes
2. Suppression 7 colonnes >50% missing
3. Forward fill + backward fill: 104,998 valeurs remplies
4. Création 7 variables temporelles (year, month, day, hour, etc.)

Résultat final:
- `data/processed/opsd_clean_focus_countries.csv` (23 Mo)
- 50,401 lignes × 71 colonnes
- 0% valeurs manquantes

## 8. Documentation

Fichiers créés:
- `docs/dictionnaire_donnees.md` - Description des 71 variables
- `docs/rapport_qualite_donnees.md` - Analyse complète de qualité
- `LIVRAISON_ROLE_1.md` - Résumé des livrables

## 9. Versioning Git

```bash
# Ajout .gitignore pour exclure data/raw/ (trop gros)
git add .
git commit -m "Projet 8 - Rôle 1 complet: données nettoyées, scripts d'ingestion, documentation"
git push
```

---

## Résultats Finaux

**Livrables produits:**
1. Dataset nettoyé (23 Mo, 0% missing)
2. 4 scripts Python d'ingestion
3. Dictionnaire de données (71 variables)
4. Rapport de qualité
5. Documentation complète

**Métriques:**
- Lignes conservées: 100% (50,401)
- Colonnes: 300 → 71 (-76%)
- Valeurs manquantes: 26.2% → 0%
- Prix négatifs confirmés: 484 en Allemagne

**Temps:** 4 semaines (S1-S4)
