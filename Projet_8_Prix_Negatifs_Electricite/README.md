# 🔋 Projet 8 : Prix Négatifs de l'Électricité Renouvelable en Europe

**Équipe:** Projet Data Science - Session 2  
**Période:** Hiver 2026 (14 semaines)  
**Responsable Données:** Étudiant 1 - Rôle 1**

## 📖 Concept du Projet

Prédire quand les prix de l'électricité européens deviennent **négatifs** (sous 0 €/MWh) — un phénomène fascinant qui se produit quand la production éolienne et solaire dépasse la demande. 

**On est littéralement payé pour consommer !**

Le projet combine les données horaires du marché électrique avec la météo pour construire un système de forecasting pour les opérateurs de réseau et les traders d'énergie.

---

## 🎯 Objectifs Analytiques

### Types d'Analyse Prévus

1. **Classification binaire** : Le prix day-ahead sera-t-il négatif demain ? (Problème déséquilibré — excellent défi ML)
2. **Régression** : Prédire le prix day-ahead à partir des prévisions météo et de génération
3. **Prévision temporelle multi-horizon** : 1h, 6h, 24h, 168h pour les prix et la production renouvelable
4. **Clustering** : Identifier les états typiques du réseau (fort-vent-faible-demande, canicule-forte-demande, etc.)
5. **Analyse causale** : Quantifier comment chaque GW supplémentaire de capacité renouvelable affecte la distribution des prix

---

## 📊 Sources de Données

### Source 1 — Open Power System Data (OPSD) - Time Series ⭐ PRINCIPALE

**URL:** https://data.open-power-system-data.org/time_series/2020-10-06/

**Téléchargements:**
- ZIP complet (277 Mo): https://data.open-power-system-data.org/time_series/opsd-time_series-2020-10-06.zip
- CSV horaire direct: https://data.open-power-system-data.org/time_series/2020-10-06/time_series_60min_singleindex.csv

**Volume:** ~289,000 lignes (timestamps horaires jan 2015 – mi-2020) × 500+ colonnes

**Variables clés par pays:**
- Charge réelle/prévue (MW)
- Génération solaire/éolienne réelle (MW)
- Capacités installées
- **Prix day-ahead (EUR/MWh)** ← Variable cible principale
- Profils solaire/éolien

**Pays couverts:** 32 pays (AT, BE, BG, CH, CZ, DE, DK, EE, ES, FI, FR, GB, GR, HR, HU, IE, IT, LT, LU, LV, ME, NL, NO, PL, PT, RO, RS, SE, SI, SK)

**Temporalité:** Résolutions 15 min, 30 min, 60 min | Période : 2015–2020 | Licence CC-BY 4.0

---

### Source 2 — OPSD Weather Data (ERA5)

**URL:** https://data.open-power-system-data.org/weather_data/

**Volume:** Plusieurs Go | Données météo grillées au niveau NUTS-2 pour les pays européens

**Variables clés:**
- Température (°C)
- Radiation directe/diffuse/globale (W/m²)
- Vitesse du vent (m/s)
- Précipitations
- Chutes de neige
- Densité de l'air

**Temporalité:** Horaire, correspondant à la période des séries temporelles | CC-BY 4.0

---

### Source 3 — ENTSO-E Transparency Platform (Complémentaire)

**URL:** https://transparency.entsoe.eu/

**Variables clés:**
- Génération réelle par type de production (nucléaire, gaz, charbon, éolien, solaire, hydro...)
- Flux physiques transfrontaliers
- Prix day-ahead et intraday
- Données d'équilibrage

**Volume:** Données horaires pour tous les États membres EU depuis 2015 | Millions d'enregistrements

**Temporalité:** Horaire/15 min, 2015–présent | Accès gratuit avec inscription

---

## 🔗 Stratégie de Jointure

### Fusion Temporelle Directe
- OPSD time series et weather data partagent les **mêmes timestamps horaires** et codes pays
- Merge direct sur `(timestamp, pays)`
- ENTSO-E ajoute la décomposition par type de combustible et les flux transfrontaliers

### Feature Engineering Prévu
- Ratio de pénétration renouvelable: `gen_renouvelable / charge_totale`
- Position nette d'export
- Variables temporelles: heure/jour/mois
- Prix décalés (lags)
- Moyennes glissantes de production éolienne/solaire
- Erreurs de prévision météo

---

## 🎓 Rôle 1 - Livrables Attendus (Vous)

### 1. Dictionnaire de Données 📖
Documentation complète de toutes les variables, sources, types, unités et contraintes

### 2. Scripts d'Ingestion (Python/SQL) 💻
Pipeline reproductible pour télécharger, nettoyer et préparer les données

### 3. Rapport Qualité des Données 📊
Analyse de la complétude, cohérence, valeurs manquantes et stratégies de nettoyage

---

## 📅 Timeline - Rôle 1

### S1-S4 : Phase Active
- ✅ Identification et évaluation des sources
- ✅ Analyse de la qualité des données
- ✅ Nettoyage avancé (outliers, valeurs manquantes)
- ✅ Scripts d'ingestion reproductibles

### S5-S8 : Maintenance
- Maintien et ajustements selon besoins de l'équipe
- Documentation continue des données

### Réunions Clés
- **Semaine 2:** Validation des sources
- **Semaine 4:** Qualité des données + dictionnaire complet

---

## 💡 Stratégie Recommandée

### Pays Prioritaires (Focus Initial)
1. **Allemagne (DE)** — Le plus de prix négatifs
2. **Danemark (DK)** — Plus forte pénétration éolienne
3. **France (FR)** — Dominé par le nucléaire (contraste intéressant)

### Split Temporel
- **Train:** 2015–2018
- **Validation:** 2019
- **Test:** 2020

---

## 📁 Structure du Projet

```
Projet_8_Prix_Negatifs_Electricite/
├── data/
│   ├── raw/                    # Données brutes téléchargées
│   │   ├── opsd_timeseries/
│   │   ├── opsd_weather/
│   │   └── entsoe/
│   ├── interim/                # Données intermédiaires
│   └── processed/              # Données nettoyées et prêtes pour l'analyse
├── notebooks/                  # Jupyter notebooks d'exploration
├── scripts/                    # Scripts Python d'ingestion et nettoyage
├── docs/                       # Documentation et livrables
│   ├── dictionnaire_donnees.md
│   └── rapport_qualite.md
├── reports/                    # Rapports et visualisations
└── outputs/                    # Résultats finaux
```

---

## 🚀 Pourquoi ce Projet est Motivant

✨ **Prix négatifs contre-intuitifs** — Hook parfait pour présentation orale  
🌍 **Transition énergétique** — Pertinence directe pour politique climatique  
💰 **Applications financières** — Stratégies de trading  
📈 **Visualisations riches** — Mix énergétique, heatmaps de prix, dashboards  
🎓 **Données académiques** — Pré-nettoyées par TU Berlin, ETH Zürich  
✅ **Très faisable** — Le projet le plus "prêt à l'emploi"

---

## 📚 Ressources

- [OPSD Documentation](https://data.open-power-system-data.org/)
- [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
- [ERA5 Climate Reanalysis](https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5)

---

## Lancer l'application Streamlit

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

**Licence:** CC-BY 4.0  
**Période:** Janvier 2026 - Avril 2026 (14 semaines)
