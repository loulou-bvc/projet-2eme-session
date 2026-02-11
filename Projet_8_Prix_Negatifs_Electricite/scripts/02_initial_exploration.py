#!/usr/bin/env python3
"""
Script 2: Exploration Initiale des Données
==========================================
Analyse initiale du dataset OPSD Time Series téléchargé.

Auteur: Étudiant 1 - Responsable Données & Ingestion
Projet: Projet 8 - Prix Négatifs Électricité Renouvelable
Date: Février 2026
"""

import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def explore_dataset(file_path):
    """Explore le dataset OPSD et génère un rapport initial."""
    
    logger.info("=" * 80)
    logger.info("EXPLORATION INITIALE DU DATASET OPSD")
    logger.info("=" * 80)
    
    # Vérifier que le fichier existe
    if not os.path.exists(file_path):
        logger.error(f"Fichier introuvable: {file_path}")
        sys.exit(1)
    
    # Taille du fichier
    file_size = os.path.getsize(file_path) / (1024 * 1024)
    logger.info(f"\n📁 Fichier: {file_path}")
    logger.info(f"📏 Taille: {file_size:.2f} Mo")
    
    # Charger le dataset avec parsing des dates
    logger.info("\n⏳ Chargement des données (cela peut prendre quelques secondes)...")
    try:
        df = pd.read_csv(file_path, parse_dates=[0], low_memory=False)
        logger.info("✅ Données chargées avec succès!")
    except Exception as e:
        logger.error(f"❌ Erreur lors du chargement: {e}")
        sys.exit(1)
    
    # Informations générales
    logger.info("\n" + "=" * 80)
    logger.info("1. DIMENSIONS DU DATASET")
    logger.info("=" * 80)
    rows, cols = df.shape
    logger.info(f"   Lignes (timestamps): {rows:,}")
    logger.info(f"   Colonnes (variables): {cols:,}")
    memory_usage = df.memory_usage(deep=True).sum() / (1024 ** 2)
    logger.info(f"   Mémoire utilisée: {memory_usage:.2f} Mo")
    
    # Informations sur l'index temporel
    logger.info("\n" + "=" * 80)
    logger.info("2. PÉRIODE TEMPORELLE")
    logger.info("=" * 80)
    time_col = df.columns[0]
    logger.info(f"   Colonne temporelle: '{time_col}'")
    logger.info(f"   Début: {df[time_col].min()}")
    logger.info(f"   Fin: {df[time_col].max()}")
    duration = df[time_col].max() - df[time_col].min()
    logger.info(f"   Durée totale: {duration}")
    
    # Types de données
    logger.info("\n" + "=" * 80)
    logger.info("3. TYPES DE DONNÉES")
    logger.info("=" * 80)
    type_counts = df.dtypes.value_counts()
    for dtype, count in type_counts.items():
        logger.info(f"   {dtype}: {count} colonnes")
    
    # Aperçu des colonnes
    logger.info("\n" + "=" * 80)
    logger.info("4. APERÇU DES COLONNES (premières 20)")
    logger.info("=" * 80)
    for i, col in enumerate(df.columns[:20], 1):
        logger.info(f"   {i:2d}. {col}")
    if len(df.columns) > 20:
        logger.info(f"   ... et {len(df.columns) - 20} autres colonnes")
    
    # Analyse des colonnes par pays (identifiées par code à 2 lettres)
    logger.info("\n" + "=" * 80)
    logger.info("5. COLONNES PAR PAYS (Focus: DE, DK, FR)")
    logger.info("=" * 80)
    
    focus_countries = ['DE', 'DK', 'FR']
    for country in focus_countries:
        country_cols = [col for col in df.columns if country in col]
        logger.info(f"\n   {country} ({len(country_cols)} colonnes):")
        
        # Chercher les colonnes de prix
        price_cols = [col for col in country_cols if 'price' in col.lower()]
        if price_cols:
            logger.info(f"      Prix: {price_cols}")
        
        # Chercher les colonnes de génération
        gen_cols = [col for col in country_cols if any(x in col.lower() for x in ['solar', 'wind', 'generation'])]
        if gen_cols:
            logger.info(f"      Génération: {gen_cols[:5]}" + (" ..." if len(gen_cols) > 5 else ""))
        
        # Chercher les colonnes de charge
        load_cols = [col for col in country_cols if 'load' in col.lower()]
        if load_cols:
            logger.info(f"      Charge: {load_cols}")
    
    # Valeurs manquantes
    logger.info("\n" + "=" * 80)
    logger.info("6. VALEURS MANQUANTES (Top 10 colonnes)")
    logger.info("=" * 80)
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).sort_values(ascending=False)
    
    for col, pct in missing_pct.head(10).items():
        count = missing[col]
        logger.info(f"   {col[:50]:50s} : {count:6,} ({pct:5.1f}%)")
    
    # Statistiques sur les colonnes de prix (si trouvées)
    logger.info("\n" + "=" * 80)
    logger.info("7. ANALYSE DES PRIX DAY-AHEAD")
    logger.info("=" * 80)
    
    price_keywords = ['day_ahead', 'price', 'DA']
    price_cols = [col for col in df.columns if any(kw in col for kw in price_keywords)]
    
    if price_cols:
        logger.info(f"   {len(price_cols)} colonnes de prix identifiées")
        
        # Focus sur pays prioritaires
        for country in focus_countries:
            country_price_cols = [col for col in price_cols if country in col]
            if country_price_cols:
                for col in country_price_cols[:2]:  # Limiter à 2 colonnes par pays
                    if col in df.columns:
                        logger.info(f"\n   {col}:")
                        logger.info(f"      Min: {df[col].min():.2f} EUR/MWh")
                        logger.info(f"      Max: {df[col].max():.2f} EUR/MWh")
                        logger.info(f"      Médiane: {df[col].median():.2f} EUR/MWh")
                        
                        # Compter prix négatifs
                        negative_count = (df[col] < 0).sum()
                        negative_pct = (negative_count / df[col].count()) * 100
                        logger.info(f"      Prix négatifs: {negative_count:,} ({negative_pct:.2f}%)")
    
    # Sauvegarder un rapport texte
    logger.info("\n" + "=" * 80)
    logger.info("8. SAUVEGARDE DU RAPPORT")
    logger.info("=" * 80)
    
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    report_file = output_dir / "initial_exploration.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("RAPPORT D'EXPLORATION INITIALE - OPSD TIME SERIES\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Fichier: {file_path}\n")
        f.write(f"Taille: {file_size:.2f} Mo\n")
        f.write(f"Lignes: {rows:,}\n")
        f.write(f"Colonnes: {cols:,}\n")
        f.write(f"Période: {df[time_col].min()} à {df[time_col].max()}\n\n")
        
        f.write("Liste complète des colonnes:\n")
        f.write("-" * 80 + "\n")
        for i, col in enumerate(df.columns, 1):
            f.write(f"{i:4d}. {col}\n")
    
    logger.info(f"   ✅ Rapport sauvegardé: {report_file}")
    
    # Afficher les premières lignes
    logger.info("\n" + "=" * 80)
    logger.info("9. APERÇU DES DONNÉES (5 premières lignes, colonnes sélectionnées)")
    logger.info("=" * 80)
    
    # Sélectionner quelques colonnes pour l'affichage
    display_cols = [time_col]
    for country in focus_countries:
        price_col = [col for col in df.columns if country in col and 'price' in col.lower()]
        if price_col:
            display_cols.append(price_col[0])
    
    logger.info("\n" + df[display_cols].head().to_string())
    
    logger.info("\n" + "=" * 80)
    logger.info("EXPLORATION TERMINÉE")
    logger.info("=" * 80)
    logger.info("\n📊 Prochaines étapes:")
    logger.info("   1. Exécuter: python scripts/03_data_quality_analysis.py")
    logger.info("   2. Analyser la qualité des données")
    logger.info("   3. Procéder au nettoyage\n")


def main():
    """Fonction principale."""
    data_file = "data/raw/opsd_timeseries/time_series_60min_singleindex.csv"
    
    if not os.path.exists(data_file):
        logger.error(f"❌ Fichier de données introuvable: {data_file}")
        logger.error("   Veuillez d'abord exécuter: python scripts/01_download_opsd_data.py")
        sys.exit(1)
    
    explore_dataset(data_file)


if __name__ == "__main__":
    main()
