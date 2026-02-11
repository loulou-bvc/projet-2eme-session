#!/usr/bin/env python3
"""
Script 1: Téléchargement des Données OPSD
==========================================
Télécharge automatiquement le dataset OPSD Time Series depuis le portail
Open Power System Data.

Auteur: Étudiant 1 - Responsable Données & Ingestion
Projet: Projet 8 - Prix Négatifs Électricité Renouvelable
Date: Février 2026
"""

import os
import sys
import requests
import logging
from pathlib import Path
from tqdm import tqdm
import yaml

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path='config/pipeline_config.yaml'):
    """Charge la configuration depuis le fichier YAML."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration chargée depuis {config_path}")
        return config
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la configuration: {e}")
        sys.exit(1)


def download_file(url, destination_path, chunk_size=8192):
    """
    Télécharge un fichier depuis une URL avec barre de progression.
    
    Args:
        url (str): URL du fichier à télécharger
        destination_path (Path): Chemin de destination
        chunk_size (int): Taille des chunks pour le téléchargement
    
    Returns:
        bool: True si succès, False sinon
    """
    try:
        logger.info(f"Téléchargement depuis: {url}")
        logger.info(f"Destination: {destination_path}")
        
        # Créer le dossier de destination s'il n'existe pas
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Téléchargement avec barre de progression
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Obtenir la taille totale si disponible
        total_size = int(response.headers.get('content-length', 0))
        
        with open(destination_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=destination_path.name) as pbar:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        # Vérifier la taille du fichier téléchargé
        file_size = destination_path.stat().st_size
        logger.info(f"Fichier téléchargé: {file_size / (1024*1024):.2f} Mo")
        
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors du téléchargement: {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return False


def main():
    """Fonction principale du script de téléchargement."""
    logger.info("=" * 80)
    logger.info("DÉBUT DU TÉLÉCHARGEMENT DES DONNÉES OPSD")
    logger.info("=" * 80)
    
    # Charger la configuration
    config = load_config()
    
    # Télécharger OPSD Time Series
    logger.info("\n1. Téléchargement des données OPSD Time Series (horaire)")
    opsd_config = config['data_sources']['opsd_timeseries']
    opsd_url = opsd_config['url']
    opsd_dest = Path(opsd_config['destination']) / opsd_config['filename']
    
    if opsd_dest.exists():
        logger.warning(f"Le fichier existe déjà: {opsd_dest}")
        response = input("Voulez-vous le re-télécharger? (o/n): ")
        if response.lower() != 'o':
            logger.info("Téléchargement ignoré.")
        else:
            success = download_file(opsd_url, opsd_dest)
            if success:
                logger.info("✅ Téléchargement OPSD Time Series réussi!")
            else:
                logger.error("❌ Échec du téléchargement OPSD Time Series")
                sys.exit(1)
    else:
        success = download_file(opsd_url, opsd_dest)
        if success:
            logger.info("✅ Téléchargement OPSD Time Series réussi!")
        else:
            logger.error("❌ Échec du téléchargement OPSD Time Series")
            sys.exit(1)
    
    # Information sur OPSD Weather Data
    logger.info("\n2. Données OPSD Weather (ERA5)")
    logger.info("⚠️  Les données météo sont volumineuses (plusieurs Go)")
    logger.info("    URL: https://data.open-power-system-data.org/weather_data/")
    logger.info("    Action: Vérifier manuellement la page pour téléchargement ciblé")
    logger.info("    Recommandation: Télécharger seulement les pays focus (DE, DK, FR)")
    
    # Information sur ENTSO-E
    logger.info("\n3. Données ENTSO-E Transparency Platform")
    logger.info("⚠️  Nécessite une inscription gratuite")
    logger.info("    URL: https://transparency.entsoe.eu/")
    logger.info("    Action: S'inscrire et obtenir un token API")
    logger.info("    Note: Ces données sont complémentaires (optionnelles pour démarrage)")
    
    logger.info("\n" + "=" * 80)
    logger.info("TÉLÉCHARGEMENT TERMINÉ")
    logger.info("=" * 80)
    logger.info("\n📊 Prochaines étapes:")
    logger.info("  1. Exécuter: python scripts/02_initial_exploration.py")
    logger.info("  2. Analyser les données téléchargées")
    logger.info("  3. Procéder à l'analyse de qualité\n")


if __name__ == "__main__":
    main()
