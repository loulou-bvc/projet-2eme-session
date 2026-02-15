#!/usr/bin/env python3
"""
Script 3: Analyse de la Qualité des Données
============================================
Analyse exhaustive de la qualité du dataset OPSD Time Series.

Auteur: Étudiant 1 - Responsable Données & Ingestion
Projet: Projet 8 - Prix Négatifs Électricité Renouvelable
Date: Février 2026
"""

import pandas as pd
import numpy as np
import json
import sys
import logging
from pathlib import Path
from datetime import timedelta

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_data_quality(file_path, focus_countries=['DE', 'DK', 'FR']):
    """
    Analyse complète de la qualité des données OPSD.
    
    Args:
        file_path: Chemin vers le fichier CSV OPSD
        focus_countries: Liste des codes pays prioritaires
    """
    
    logger.info("=" * 80)
    logger.info("ANALYSE DE QUALITÉ DES DONNÉES OPSD")
    logger.info("=" * 80)
    
    # Charger les données
    logger.info("\n⏳ Chargement des données...")
    try:
        df = pd.read_csv(file_path, parse_dates=[0], low_memory=False)
        logger.info(f"✅ {len(df):,} lignes × {len(df.columns):,} colonnes chargées")
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        sys.exit(1)
    
    # Initialiser le rapport de qualité
    quality_report = {
        "overview": {},
        "missing_values": {},
        "temporal_analysis": {},
        "price_analysis": {},
        "outliers": {},
        "recommendations": []
    }
    
    time_col = df.columns[0]
    
    # ========================================================================
    # 1. VUE D'ENSEMBLE
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("1. VUE D'ENSEMBLE")
    logger.info("=" * 80)
    
    quality_report["overview"] = {
        "rows": len(df),
        "columns": len(df.columns),
        "period_start": str(df[time_col].min()),
        "period_end": str(df[time_col].max()),
        "duration_days": (df[time_col].max() - df[time_col].min()).days,
        "memory_mb": round(df.memory_usage(deep=True).sum() / (1024**2), 2)
    }
    
    logger.info(f"   Lignes: {quality_report['overview']['rows']:,}")
    logger.info(f"   Colonnes: {quality_report['overview']['columns']:,}")
    logger.info(f"   Période: {quality_report['overview']['period_start']} → {quality_report['overview']['period_end']}")
    logger.info(f"   Durée: {quality_report['overview']['duration_days']:,} jours")
    
    # ========================================================================
    # 2. ANALYSE DES VALEURS MANQUANTES
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("2. ANALYSE DES VALEURS MANQUANTES")
    logger.info("=" * 80)
    
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100)
    
    # Statistiques globales
    total_cells = len(df) * len(df.columns)
    missing_cells = missing.sum()
    missing_pct_global = (missing_cells / total_cells) * 100
    
    logger.info(f"\n   Cellules totales: {total_cells:,}")
    logger.info(f"   Cellules manquantes: {missing_cells:,} ({missing_pct_global:.2f}%)")
    
    quality_report["missing_values"]["global"] = {
        "total_cells": int(total_cells),
        "missing_cells": int(missing_cells),
        "missing_percentage": round(missing_pct_global, 2)
    }
    
    # Colonnes par catégorie de complétude
    complete_cols = (missing_pct == 0).sum()
    partial_cols = ((missing_pct > 0) & (missing_pct < 50)).sum()
    mostly_missing_cols = ((missing_pct >= 50) & (missing_pct < 100)).sum()
    empty_cols = (missing_pct == 100).sum()
    
    logger.info(f"\n   Colonnes complètes (0% manquant): {complete_cols}")
    logger.info(f"   Colonnes partielles (<50% manquant): {partial_cols}")
    logger.info(f"   Colonnes majoritairement vides (≥50%): {mostly_missing_cols}")
    logger.info(f"   Colonnes entièrement vides (100%): {empty_cols}")
    
    quality_report["missing_values"]["column_categories"] = {
        "complete": int(complete_cols),
        "partial": int(partial_cols),
        "mostly_missing": int(mostly_missing_cols),
        "empty": int(empty_cols)
    }
    
    # Top 20 colonnes avec valeurs manquantes
    logger.info(f"\n   Top 20 colonnes avec le plus de valeurs manquantes:")
    top_missing = missing_pct[missing_pct > 0].sort_values(ascending=False).head(20)
    quality_report["missing_values"]["top_missing_columns"] = {}
    
    for col, pct in top_missing.items():
        count = missing[col]
        logger.info(f"      {col[:60]:60s}: {count:6,} ({pct:5.1f}%)")
        quality_report["missing_values"]["top_missing_columns"][col] = {
            "count": int(count),
            "percentage": round(pct, 2)
        }
    
    # ========================================================================
    # 3. ANALYSE TEMPORELLE
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("3. COHÉRENCE TEMPORELLE")
    logger.info("=" * 80)
    
    # Vérifier les gaps temporels
    df_sorted = df.sort_values(time_col)
    time_diffs = df_sorted[time_col].diff()
    expected_diff = timedelta(hours=1)
    
    gaps = time_diffs[time_diffs > expected_diff]
    
    logger.info(f"\n   Fréquence attendue: {expected_diff}")
    logger.info(f"   Nombre de gaps détectés: {len(gaps)}")
    
    quality_report["temporal_analysis"]["expected_frequency"] = "1 hour"
    quality_report["temporal_analysis"]["gaps_count"] = len(gaps)
    
    if len(gaps) > 0:
        logger.info(f"   Gap maximum: {gaps.max()}")
        logger.info(f"\n   Premiers 5 gaps:")
        for idx, gap in gaps.head().items():
            timestamp = df_sorted.loc[idx, time_col]
            logger.info(f"      {timestamp}: gap de {gap}")
        
        quality_report["temporal_analysis"]["max_gap"] = str(gaps.max())
    else:
        logger.info("   ✅ Aucun gap temporel détecté")
    
    # Vérifier les doublons temporels
    duplicates = df[time_col].duplicated().sum()
    logger.info(f"\n   Timestamps dupliqués: {duplicates}")
    quality_report["temporal_analysis"]["duplicate_timestamps"] = int(duplicates)
    
    # ========================================================================
    # 4. ANALYSE DES PRIX (Focus pays prioritaires)
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("4. ANALYSE DES PRIX DAY-AHEAD")
    logger.info("=" * 80)
    
    price_cols = [col for col in df.columns if 'price' in col.lower() and 'day_ahead' in col.lower()]
    quality_report["price_analysis"] = {}
    
    for country in focus_countries:
        logger.info(f"\n   Analyse pour {country}:")
        country_price_cols = [col for col in price_cols if country in col]
        
        if not country_price_cols:
            logger.info(f"      ⚠️  Aucune colonne de prix trouvée")
            continue
        
        quality_report["price_analysis"][country] = {}
        
        for col in country_price_cols:
            logger.info(f"\n      {col}:")
            
            # Statistiques de base
            col_data = df[col].dropna()
            if len(col_data) == 0:
                logger.info(f"         ⚠️  Aucune donnée non-nulle")
                continue
            
            stats = {
                "count": int(len(col_data)),
                "missing": int(df[col].isnull().sum()),
                "missing_pct": round((df[col].isnull().sum() / len(df)) * 100, 2),
                "min": round(col_data.min(), 2),
                "max": round(col_data.max(), 2),
                "mean": round(col_data.mean(), 2),
                "median": round(col_data.median(), 2),
                "std": round(col_data.std(), 2)
            }
            
            logger.info(f"         Observations: {stats['count']:,}")
            logger.info(f"         Manquantes: {stats['missing']:,} ({stats['missing_pct']:.1f}%)")
            logger.info(f"         Min: {stats['min']:.2f} EUR/MWh")
            logger.info(f"         Max: {stats['max']:.2f} EUR/MWh")
            logger.info(f"         Moyenne: {stats['mean']:.2f} EUR/MWh")
            logger.info(f"         Médiane: {stats['median']:.2f} EUR/MWh")
            logger.info(f"         Écart-type: {stats['std']:.2f} EUR/MWh")
            
            # Prix négatifs
            negative_count = (col_data < 0).sum()
            negative_pct = (negative_count / len(col_data)) * 100
            
            stats["negative_count"] = int(negative_count)
            stats["negative_pct"] = round(negative_pct, 2)
            
            logger.info(f"         Prix négatifs: {negative_count:,} ({negative_pct:.2f}%)")
            
            if negative_count > 0:
                logger.info(f"         Prix négatif minimum: {col_data[col_data < 0].min():.2f} EUR/MWh")
                stats["most_negative"] = round(col_data[col_data < 0].min(), 2)
            
            # Outliers extrêmes (> 3 écart-types)
            mean = col_data.mean()
            std = col_data.std()
            outliers_high = col_data[col_data > mean + 3*std]
            outliers_low = col_data[col_data < mean - 3*std]
            
            stats["outliers_high_count"] = int(len(outliers_high))
            stats["outliers_low_count"] = int(len(outliers_low))
            
            logger.info(f"         Outliers supérieurs (>μ+3σ): {len(outliers_high)}")
            logger.info(f"         Outliers inférieurs (<μ-3σ): {len(outliers_low)}")
            
            quality_report["price_analysis"][country][col] = stats
    
    # ========================================================================
    # 5. RECOMMANDATIONS
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("5. RECOMMANDATIONS")
    logger.info("=" * 80)
    
    recommendations = []
    
    # Recommandations sur les valeurs manquantes
    if empty_cols > 0:
        rec = f"Supprimer {empty_cols} colonnes entièrement vides (100% manquant)"
        recommendations.append(rec)
        logger.info(f"   • {rec}")
    
    if mostly_missing_cols > 0:
        rec = f"Évaluer la suppression de {mostly_missing_cols} colonnes avec ≥50% de valeurs manquantes"
        recommendations.append(rec)
        logger.info(f"   • {rec}")
    
    # Recommandations sur les gaps temporels
    if len(gaps) > 0:
        rec = f"Investiguer et documenter les {len(gaps)} gaps temporels détectés"
        recommendations.append(rec)
        logger.info(f"   • {rec}")
    
    # Recommandations sur le focus
    rec = "Se concentrer sur les pays focus (DE, DK, FR) pour réduire la dimensionnalité"
    recommendations.append(rec)
    logger.info(f"   • {rec}")
    
    rec = "Utiliser forward fill pour les séries temporelles de prix et génération"
    recommendations.append(rec)
    logger.info(f"   • {rec}")
    
    quality_report["recommendations"] = recommendations
    
    # ========================================================================
    # 6. SAUVEGARDE DU RAPPORT
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("6. SAUVEGARDE DU RAPPORT")
    logger.info("=" * 80)
    
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    
    # Sauvegarder en JSON
    json_file = output_dir / "data_quality_report.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(quality_report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"   ✅ Rapport JSON sauvegardé: {json_file}")
    
    logger.info("\n" + "=" * 80)
    logger.info("ANALYSE DE QUALITÉ TERMINÉE")
    logger.info("=" * 80)
    logger.info("\n📊 Prochaines étapes:")
    logger.info("   1. Examiner: reports/data_quality_report.json")
    logger.info("   2. Créer le script de nettoyage: scripts/04_data_cleaning.py")
    logger.info("   3. Nettoyer les données selon les recommandations\n")
    
    return quality_report


def main():
    """Fonction principale."""
    data_file = "data/raw/opsd_timeseries/time_series_60min_singleindex.csv"
    
    if not Path(data_file).exists():
        logger.error(f"❌ Fichier introuvable: {data_file}")
        logger.error("   Veuillez d'abord exécuter: python scripts/01_download_opsd_data.py")
        sys.exit(1)
    
    analyze_data_quality(data_file)


if __name__ == "__main__":
    main()
