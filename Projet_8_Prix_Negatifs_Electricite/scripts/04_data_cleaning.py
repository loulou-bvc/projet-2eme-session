#!/usr/bin/env python3
"""
Script 4: Nettoyage et Préparation des Données
================================================
Nettoie et prépare le dataset OPSD selon l'analyse de qualité.

Auteur: Étudiant 1 - Responsable Données & Ingestion
Projet: Projet 8 - Prix Négatifs Électricité Renouvelable
Date: Février 2026
"""

import pandas as pd
import numpy as np
import yaml
import sys
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path='config/pipeline_config.yaml'):
    """Charge la configuration du pipeline."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def clean_data(input_file, config):
    """
    Nettoie les données OPSD selon les recommandations de l'analyse de qualité.
    
    Args:
        input_file: Chemin vers le fichier CSV brut
        config: Configuration du pipeline
    """
    
    logger.info("=" * 80)
    logger.info("NETTOYAGE DES DONNÉES OPSD")
    logger.info("=" * 80)
    
    # Charger les données
    logger.info("\n⏳ Chargement des données brutes...")
    df = pd.read_csv(input_file, parse_dates=[0], low_memory=False)
    logger.info(f"✅ {len(df):,} lignes × {len(df.columns):,} colonnes chargées")
    
    time_col = df.columns[0]
    initial_rows = len(df)
    initial_cols = len(df.columns)
    
    # ========================================================================
    # 1. FOCUS SUR LES PAYS PRIORITAIRES
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("1. SÉLECTION DES COLONNES POUR PAYS FOCUS")
    logger.info("=" * 80)
    
    focus_countries = config['focus_countries']
    logger.info(f"   Pays focus: {', '.join(focus_countries)}")
    
    # Garder la colonne temporelle + colonnes des pays focus
    selected_cols = [time_col]
    
    for country in focus_countries:
        country_cols = [col for col in df.columns if country in col]
        selected_cols.extend(country_cols)
        logger.info(f"   {country}: {len(country_cols)} colonnes")
    
    # Supprimer les doublons (si une colonne est comptée plusieurs fois)
    selected_cols = list(dict.fromkeys(selected_cols))
    
    logger.info(f"\n   Total colonnes sélectionnées: {len(selected_cols)}")
    df_focus = df[selected_cols].copy()
    
    logger.info(f"   ✅ Réduction: {initial_cols} → {len(df_focus.columns)} colonnes")
    
    # ========================================================================
    # 2. SUPPRESSION DES COLONNES TRÈS INCOMPLÈTES
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("2. SUPPRESSION DES COLONNES TRÈS INCOMPLÈTES")
    logger.info("=" * 80)
    
    threshold = config['missing_values_strategy']['threshold_drop']
    logger.info(f"   Seuil: ≥{threshold*100:.0f}% de valeurs manquantes")
    
    missing_pct = (df_focus.isnull().sum() / len(df_focus))
    cols_to_drop = missing_pct[missing_pct >= threshold].index.tolist()
    
    # Ne pas supprimer la colonne temporelle
    if time_col in cols_to_drop:
        cols_to_drop.remove(time_col)
    
    logger.info(f"\n   Colonnes à supprimer ({len(cols_to_drop)}):")
    for col in cols_to_drop[:10]:  # Afficher les 10 premières
        logger.info(f"      • {col} ({missing_pct[col]*100:.1f}% manquant)")
    if len(cols_to_drop) > 10:
        logger.info(f"      ... et {len(cols_to_drop) - 10} autres")
    
    df_clean = df_focus.drop(columns=cols_to_drop)
    logger.info(f"\n   ✅ {len(df_clean.columns)} colonnes restantes")
    
    # ========================================================================
    # 3. GESTION DES VALEURS MANQUANTES
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("3. GESTION DES VALEURS MANQUANTES")
    logger.info("=" * 80)
    
    # Identifier les types de colonnes
    price_cols = [col for col in df_clean.columns if 'price' in col.lower()]
    gen_cols = [col for col in df_clean.columns if any(x in col.lower() for x in ['solar', 'wind', 'generation'])]
    load_cols = [col for col in df_clean.columns if 'load' in col.lower()]
    
    logger.info(f"\n   Types de colonnes identifiées:")
    logger.info(f"      Prix: {len(price_cols)}")
    logger.info(f"      Génération: {len(gen_cols)}")
    logger.info(f"      Charge: {len(load_cols)}")
    
    # Forward fill pour séries temporelles (prix, génération, charge)
    logger.info(f"\n   Application de forward fill pour colonnes temporelles...")
    timeseries_cols = price_cols + gen_cols + load_cols
    
    before_fill = df_clean[timeseries_cols].isnull().sum().sum()
    df_clean[timeseries_cols] = df_clean[timeseries_cols].fillna(method='ffill')
    after_fill = df_clean[timeseries_cols].isnull().sum().sum()
    
    filled = before_fill - after_fill
    logger.info(f"   ✅ {filled:,} valeurs remplies via forward fill")
    
    # Pour les valeurs encore manquantes au début, utiliser backfill
    if after_fill > 0:
        logger.info(f"   Application de backward fill pour valeurs initiales...")
        df_clean[timeseries_cols] = df_clean[timeseries_cols].fillna(method='bfill')
        final_missing = df_clean[timeseries_cols].isnull().sum().sum()
        logger.info(f"   ✅ {after_fill - final_missing:,} valeurs supplémentaires remplies")
    
    # ========================================================================
    # 4. STANDARDISATION DES NOMS DE COLONNES
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("4. STANDARDISATION DES NOMS DE COLONNES")
    logger.info("=" * 80)
    
    # Renommer pour plus de clarté
    rename_map = {}
    
    # Renommer la colonne temporelle en 'timestamp' si nécessaire
    if time_col != 'timestamp':
        rename_map[time_col] = 'timestamp'
    
    if rename_map:
        logger.info(f"   Renommage de {len(rename_map)} colonnes")
        df_clean = df_clean.rename(columns=rename_map)
    else:
        logger.info("   Pas de renommage nécessaire")
    
    # ========================================================================
    # 5. CRÉATION DE VARIABLES TEMPORELLES
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("5. CRÉATION DE VARIABLES TEMPORELLES")
    logger.info("=" * 80)
    
    timestamp_col = 'timestamp' if 'timestamp' in df_clean.columns else df_clean.columns[0]
    
    logger.info(f"   Extraction des variables temporelles depuis '{timestamp_col}'...")
    
    df_clean['year'] = df_clean[timestamp_col].dt.year
    df_clean['month'] = df_clean[timestamp_col].dt.month
    df_clean['day'] = df_clean[timestamp_col].dt.day
    df_clean['hour'] = df_clean[timestamp_col].dt.hour
    df_clean['dayofweek'] = df_clean[timestamp_col].dt.dayofweek  # 0=Lundi, 6=Dimanche
    df_clean['quarter'] = df_clean[timestamp_col].dt.quarter
    df_clean['is_weekend'] = df_clean['dayofweek'].isin([5, 6]).astype(int)
    
    logger.info(f"   ✅ 7 variables temporelles créées")
    logger.info(f"      • year, month, day, hour, dayofweek, quarter, is_weekend")
    
    # ========================================================================
    # 6. STATISTIQUES FINALES
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("6. RÉSUMÉ DU NETTOYAGE")
    logger.info("=" * 80)
    
    final_rows = len(df_clean)
    final_cols = len(df_clean.columns)
    final_missing = df_clean.isnull().sum().sum()
    final_missing_pct = (final_missing / (final_rows * final_cols)) * 100
    
    logger.info(f"\n   Dimensions:")
    logger.info(f"      Avant: {initial_rows:,} lignes × {initial_cols:,} colonnes")
    logger.info(f"      Après: {final_rows:,} lignes × {final_cols:,} colonnes")
    
    logger.info(f"\n   Valeurs manquantes:")
    logger.info(f"      Total: {final_missing:,} ({final_missing_pct:.2f}%)")
    
    # Identifier les colonnes avec encore des valeurs manquantes
    still_missing = df_clean.isnull().sum()
    cols_with_missing = still_missing[still_missing > 0]
    
    if len(cols_with_missing) > 0:
        logger.info(f"\n   ⚠️  {len(cols_with_missing)} colonnes ont encore des valeurs manquantes:")
        for col, count in cols_with_missing.head(5).items():
            pct = (count / len(df_clean)) * 100
            logger.info(f"      • {col[:60]:60s}: {count:6,} ({pct:5.1f}%)")
        if len(cols_with_missing) > 5:
            logger.info(f"      ... et {len(cols_with_missing) - 5} autres")
    else:
        logger.info(f"\n   ✅ Aucune valeur manquante restante!")
    
    # ========================================================================
    # 7. SAUVEGARDE DES DONNÉES NETTOYÉES
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("7. SAUVEGARDE DES DONNÉES NETTOYÉES")
    logger.info("=" * 80)
    
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarder en CSV
    output_file = output_dir / "opsd_clean_focus_countries.csv"
    df_clean.to_csv(output_file, index=False)
    logger.info(f"   ✅ CSV sauvegardé: {output_file}")
    
    file_size = output_file.stat().st_size / (1024 * 1024)
    logger.info(f"   Taille: {file_size:.2f} Mo")
    
    # Sauvegarder aussi un échantillon pour tests rapides
    sample_file = output_dir / "opsd_sample_1000.csv"
    df_clean.sample(min(1000, len(df_clean))).to_csv(sample_file, index=False)
    logger.info(f"   ✅ Échantillon sauvegardé: {sample_file}")
    
    logger.info("\n" + "=" * 80)
    logger.info("NETTOYAGE TERMINÉ")
    logger.info("=" * 80)
    logger.info("\n📊 Prochaines étapes:")
    logger.info("   1. Commencer la documentation: docs/dictionnaire_donnees.md")
    logger.info("   2. Rédiger le rapport qualité: docs/rapport_qualite_donnees.md")
    logger.info("   3. Analyse exploratoire avancée (rôle 2)\n")
    
    return df_clean


def main():
    """Fonction principale."""
    
    # Charger la configuration
    config = load_config()
    
    # Fichier d'entrée
    input_file = "data/raw/opsd_timeseries/time_series_60min_singleindex.csv"
    
    if not Path(input_file).exists():
        logger.error(f"❌ Fichier introuvable: {input_file}")
        logger.error("   Veuillez d'abord exécuter: python scripts/01_download_opsd_data.py")
        sys.exit(1)
    
    # Nettoyer les données
    df_clean = clean_data(input_file, config)
    
    logger.info(f"\n✅ Données nettoyées disponibles dans: data/processed/")


if __name__ == "__main__":
    main()
