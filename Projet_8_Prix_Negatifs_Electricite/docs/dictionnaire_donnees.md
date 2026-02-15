# 📖 Dictionnaire de Données - Projet 8
**Prix Négatifs de l'Électricité Renouvelable en Europe**

**Auteur:** Étud iant 1 - Data Engineer  
**Date:** Février 2026  
**Source:** Open Power System Data (OPSD) - Time Series 2020-10-06  
**Dataset:** `data/processed/opsd_clean_focus_countries.csv`

---

## Vue d'Ensemble

**Dimensions du dataset final:**
- **Lignes (timestamps):** 50,401
- **Colonnes (variables):** 71
- **Période temporelle:** 2015-01-01 à 2020-06-30
- **Résolution temporelle:** Horaire (1 heure)
- **Pays couverts:** Allemagne (DE), Danemark (DK), France (FR)
- **Valeurs manquantes:** 0% (après nettoyage)

---

## 📅 Variables Temporelles

### timestamp  
- **Type:** datetime64[ns, UTC+00:00]
- **Source:** OPSD Time Series (colonne originale: utc_timestamp)
- **Description:** Horodatage en temps universel coordonné (UTC)
- **Format:** YYYY-MM-DD HH:MM:SS+00:00
- **Fréquence:** Horaire
- **Plage:** 2015-01-01 00:00:00 à 2020-06-30 23:00:00
- **Valeurs manquantes:** 0%

### year
- **Type:** int64
- **Source:** Dérivée de `timestamp`
- **Description:** Année d'observation
- **Plage:** 2015-2020
- **Valeurs manquantes:** 0%

### month
- **Type:** int64
- **Source:** Dérivée de `timestamp`
- **Description:** Mois de l'année (1=janvier, 12=décembre)
- **Plage:** 1-12
- **Valeurs manquantes:** 0%

### day
- **Type:** int64
- **Source:** Dérivée de `timestamp`
- **Description:** Jour du mois
- **Plage:** 1-31
- **Valeurs manquantes:** 0%

### hour
- **Type:** int64
- **Source:** Dérivée de `timestamp`
- **Description:** Heure de la journée (format 24h)
- **Plage:** 0-23
- **Valeurs manquantes:** 0%

### dayofweek
- **Type:** int64
- **Source:** Dérivée de `timestamp`
- **Description:** Jour de la semaine (0=lundi, 6=dimanche)
- **Plage:** 0-6
- **Valeurs manquantes:** 0%

### quarter
- **Type:** int64
- **Source:** Dérivée de `timestamp`
- **Description:** Trimestre de l'année
- **Plage:** 1-4
- **Valeurs manquantes:** 0%

### is_weekend
- **Type:** int64
- **Source:** Dérivée de `dayofweek`
- **Description:** Indicateur weekend (1=weekend samedi/dimanche, 0=semaine)
- **Plage:** 0-1
- **Valeurs manquantes:** 0%

---

## 💰 Variables de Prix (EUR/MWh)

### DK_1_price_day_ahead
- **Type:** float64
- **Source:** OPSD Time Series - ENTSO-E Transparency Platform
- **Unité:** EUR/MWh (euros par mégawatt-heure)
- **Description:** Prix day-ahead pour la zone de marché Danemark-1 (Est du Danemark)
- **Pays:** DK (Danemark)
- **Plage observée:** -58.80 à 200.04 EUR/MWh
- **Médiane:** 30.29 EUR/MWh
- **Occurrences de prix négatifs:** 539 (1.07%)
- **Prix négatif minimum:** -58.80 EUR/MWh
- **Valeurs manquantes (après nettoyage):** 0%
- **Notes:** Prix déterminé sur le marché day-ahead (veille pour le lendemain). Prix négatifs indiquent surproduction renouvelable.

### DK_2_price_day_ahead
- **Type:** float64
- **Source:** OPSD Time Series - ENTSO-E Transparency Platform
- **Unité:** EUR/MWh
- **Description:** Prix day-ahead pour la zone de marché Danemark-2 (Ouest du Danemark)
- **Pays:** DK (Danemark)
- **Plage observée:** -53.62 à 255.02 EUR/MWh
- **Médiane:** 31.66 EUR/MWh
- **Occurrences de prix négatifs:** 354 (0.70%)
- **Prix négatif minimum:** -53.62 EUR/MWh
- **Valeurs manquantes (après nettoyage):** 0%

### IT_NORD_FR_price_day_ahead
- **Type:** float64
- **Source:** OPSD Time Series - ENTSO-E Transparency Platform
- **Unité:** EUR/MWh
- **Description:** Prix day-ahead pour la zone transfrontalière Italie-Nord / France
- **Pays:** FR (France) - marché couplé avec IT_NORD
- **Plage observée:** 5.00 à 206.12 EUR/MWh
- **Médiane:** 47.47 EUR/MWh
- **Occurrences de prix négatifs:** 0 (0.00%)
- **Valeurs manquantes (après nettoyage):** 0%
- **Notes:** Aucun prix négatif observé - marché différent avec forte composante nucléaire française

---

## ⚡ Variables de Charge Électrique (MW)

### DE_load_actual_entsoe_transparency
- **Type:** float64
- **Source:** OPSD Time Series - ENTSO-E Transparency Platform
- **Unité:** MW (mégawatts)
- **Description:** Charge réelle (consommation) pour l'Allemagne
- **Pays:** DE (Allemagne)
- **Valeurs manquantes (après nettoyage):** 0%
- **Notes:** Donnée observée en temps réel, représente la demande électrique totale

### DE_load_forecast_entsoe_transparency
- **Type:** float64
- **Source:** OPSD Time Series - ENTSO-E Transparency Platform
- **Unité:** MW
- **Description:** Charge prévue (forecast) pour l'Allemagne
- **Pays:** DE (Allemagne)
- **Valeurs manquantes (après nettoyage):** 0%
- **Notes:** Prévision de la demande électrique, utilisée pour planification

### DK_load_actual_entsoe_transparency
- **Type:** float64
- **Source:** OPSD Time Series - ENTSO-E Transparency Platform
- **Unité:** MW
- **Description:** Charge réelle pour le Danemark (total des deux zones)
- **Pays:** DK (Danemark)
- **Valeurs manquantes (après nettoyage):** 0%

### DK_load_forecast_entsoe_transparency
- **Type:** float64
- **Source:** OPSD Time Series - ENTSO-E Transparency Platform
- **Unité:** MW
- **Description:** Charge prévue pour le Danemark
- **Pays:** DK (Danemark)
- **Valeurs manquantes (après nettoyage):** 0%

### FR_load_actual_entsoe_transparency
- **Type:** float64
- **Source:** OPSD Time Series - ENTSO-E Transparency Platform
- **Unité:** MW
- **Description:** Charge réelle pour la France
- **Pays:** FR (France)
- **Valeurs manquantes (après nettoyage):** 0%

### FR_load_forecast_entsoe_transparency
- **Type:** float64
- **Source:** OPSD Time Series - ENTSO-E Transparency Platform
- **Unité:** MW
- **Description:** Charge prévue pour la France
- **Pays:** FR (France)
- **Valeurs manquantes (après nettoyage):** 0%

**Note:** Les variables de charge par opérateur de réseau allemand (50hertz, amprion, tennet, transnetbw) et par zone danoise (DK_1, DK_2) suivent la même structure.

---

## ☀️ Variables de Génération Solaire

### DE_solar_generation_actual
- **Type:** float64
- **Source:** OPSD Time Series - ENTSO-E Transparency Platform
- **Unité:** MW
- **Description:** Génération solaire photovoltataque réelle pour l'Allemagne
- **Pays:** DE (Allemagne)
- **Valeurs manquantes (après nettoyage):** 0%
- **Notes:** Production effective des installations solaires

### DE_solar_capacity
- **Type:** float64
- **Source:** OPSD Time Series
- **Unité:** MW
- **Description:** Capacité solaire installée en Allemagne
- **Pays:** DE (Allemagne)
- **Valeurs manquantes (après nettoyage):** 0%
- **Notes:** Évolue au fil du temps avec l'ajout de nouvelles installations

### DE_solar_profile
- **Type:** float64
- **Source:** OPSD Time Series
- **Unité:** Sans dimension (ratio normalisé 0-1)
- **Description:** Profil de production solaire normalisé (ratio generation/capacity)
- **Pays:** DE (Allemagne)
- **Valeurs manquantes (après nettoyage):** 0%
- **Notes:** Permet de comparer la production relative indépendamment de la capacité installée

**Note:** Les variables DK et FR de génération solaire suivent la même structure (lorsque disponibles).

---

## 💨 Variables de Génération Éolienne

### DE_wind_generation_actual
- **Type:** float64
- **Source:** OPSD Time Series - ENTSO-E Transparency Platform
- **Un ité:** MW
- **Description:** Génération éolienne totale réelle pour l'Allemagne (onshore + offshore)
- **Pays:** DE (Allemagne)
- **Valeurs manquantes (après nettoyage):** 0%

### DE_wind_onshore_generation_actual
- **Type:** float64
- **Source:** OPSD Time Series - ENTSO-E Transparency Platform
- **Unité:** MW
- **Description:** Génération éolienne terrestre (onshore) pour l'Allemagne
- **Pays:** DE (Allemagne)
- **Valeurs manquantes (après nettoyage):** 0%

### DE_wind_offshore_generation_actual
- **Type:** float64
- **Source:** OPSD Time Series - ENTSO-E Transparency Platform
- **Unité:** MW
- **Description:** Génération éolienne en mer (offshore) pour l'Allemagne
- **Pays:** DE (Allemagne)
- **Valeurs manquantes (après nettoyage):** 0%

### DE_wind_capacity
- **Type:** float64
- **Source:** OPSD Time Series
- **Unité:** MW
- **Description:** Capacité éolienne totale installée en Allemagne
- **Pays:** DE (Allemagne)
- **Valeurs manquantes (après nettoyage):** 0%

### DE_wind_profile
- **Type:** float64
- **Source:** OPSD Time Series
- **Unité:** Sans dimension (ratio normalisé 0-1)
- **Description:** Profil de production éolienne normalisé
- **Pays:** DE (Allemagne)
- **Valeurs manquantes (après nettoyage):** 0%

**Note:** Les variables DK et FR de génération éolienne suivent une structure similaire (onshore, offshore, capacity, profile).

---

## 📊 Variables par Opérateur de Réseau (Allemagne)

L'Allemagne a 4 opérateurs de réseau de transport (TSO):
- **50hertz** - Nord-Est
- **amprion** - Ouest
- **tennet** - Nord et Centre
- **transnetbw** - Sud-Ouest

Pour chaque opérateur, les variables suivantes sont disponibles:
- `{TSO}_load_actual_entsoe_transparency` - Charge réelle
- `{TSO}_load_forecast_entsoe_transparency` - Charge prévue
- `{TSO}_solar_generation_actual` - Génération solaire
- `{TSO}_wind_generation_actual` - Génération éolienne totale
- `{TSO}_wind_offshore_generation_actual` - Génération éolienne offshore
- `{TSO}_wind_onshore_generation_actual` - Génération éolienne onshore

Toutes suivent les mêmes définitions que leurs équivalents nationaux.

---

## 📊 Variables par Zone de Marché (Danemark)

Le Danemark est divisé en 2 zones de marché:
- **DK_1** - Est du Danemark (connecté à la Suède)
- **DK_2** - Ouest du Danemark (connecté à l'Allemagne)

Variables disponibles par zone:
- `DK_{zone}_price_day_ahead` - Prix day-ahead
- `DK_{zone}_load_actual_entsoe_transparency` - Charge réelle
- `DK_{zone}_load_forecast_entsoe_transparency` - Charge prévue
- `DK_{zone}_wind_generation_actual` - Génération éolienne
- `DK_{zone}_wind_offshore_generation_actual` - Génération éolienne offshore

---

## 🗑️ Variables Supprimées du Dataset Original

Les colonnes suivantes ont été supprimées car >50% de valeurs manquantes:

1. `DE_LU_load_actual_entsoe_transparency` (65.2% manquant)
2. `DE_LU_load_forecast_entsoe_transparency` (67.0% manquant)
3. `DE_LU_price_day_ahead` (65.2% manquant)
4. `DE_LU_solar_generation_actual` (65.2% manquant)
5. `DE_LU_wind_generation_actual` (65.2% manquant)
6. `DE_LU_wind_offshore_generation_actual` (65.2% manquant)
7. `DE_LU_wind_onshore_generation_actual` (65.2% manquant)

**Raison:** Zone couplée Allemagne-Luxembourg avec données incomplètes.

---

## 🔧 Stratégies de Nettoyage Appliquées

### Valeurs Manquantes
- **Méthode:** Forward fill + backward fill pour séries temporelles
- **Raison:** Les données de prix et génération ont une continuité temporelle
- **Résultat:** 104,998 valeurs remplies, 0% de valeurs manquantes finales

### Sélection des Pays
- **Pays focus:** Allemagne (DE), Danemark (DK), France (FR)
- **Raison:** Allemagne a le plus de prix négatifs, Danemark la plus forte pénétration éolienne, France un contraste intéressant (nucléaire dominant)
- **Impact:** Réduction de 300 à 71 colonnes

### Qualité Temporelle
- **Gaps détectés:** 0
- **Timestamps dupliqués:** 0
- **Cohérence:** 100% - séries temporelles parfaitement régulières

---

## 📚 Références

- **Source principale:** Open Power System Data (OPSD)  
  URL: https://data.open-power-system-data.org/time_series/2020-10-06/
- **Plateforme ENTSO-E:** https://transparency.entsoe.eu/
- **Documentation OPSD:** https://data.open-power-system-data.org/
- **Licence:** CC-BY 4.0
- **Citation:** Open Power System Data. 2020. Data Package Time series. Version 2020-10-06.

---

**Dernière mise à jour:** 11 février 2026  
**Auteur:** Étudiant 1 - Responsable Données & Ingestion
