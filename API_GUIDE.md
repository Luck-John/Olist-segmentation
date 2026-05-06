# 📊 Customer Segmentation Pipeline & API Guide

## Overview

Ce projet reproduit le notebook de segmentation client **"Modélisons.ipynb"** dans une **pipeline Python exécutable** et l'expose via une **API FastAPI**.

### Structure

```
scripts/
├── full_pipeline.py    # Pipeline complète (reproduit le notebook)
├── api.py              # API FastAPI
├── start_api.py        # Script de démarrage de l'API
└── run_pipeline.py     # Pipeline existant (complément)

notebooks/
├── models/
│   ├── final_pipeline.pkl      # Modèle entraîné (pickle)
│   ├── cluster_names.json      # Noms des segments
│   └── ...autres modèles...
├── reports/
│   ├── clustering_comparison.csv       # Métriques de comparaison
│   ├── cluster_profiles_mean.csv       # Profils moyens
│   ├── cluster_profiles_median.csv     # Profils médians
│   └── segmentation_finale_olist.csv   # Résultats finaux
```

---

## 🚀 Exécuter la Pipeline

### 1. Reproduire les résultats du notebook

Exécutez le script complet qui reproduit exactement le notebook :

```bash
python scripts/full_pipeline.py
```

**Résultats générés :**
- `notebooks/reports/clustering_comparison.csv` - Comparaison des k (4-8)
- `notebooks/reports/cluster_profiles_mean.csv` - Profils moyens par cluster
- `notebooks/reports/cluster_profiles_median.csv` - Profils médians par cluster
- `notebooks/reports/segmentation_finale_olist.csv` - Résultats finaux avec segments
- `notebooks/models/final_pipeline.pkl` - Pipeline entraînée (scaler + KMeans + PCA)

### 2. Vérifier les résultats

```python
import pandas as pd

# Charger les résultats finaux
df_results = pd.read_csv("notebooks/reports/segmentation_finale_olist.csv")
print(df_results.head())
print(df_results['segment'].value_counts())

# Charger les profils
profiles = pd.read_csv("notebooks/reports/cluster_profiles_mean.csv")
print(profiles)
```

---

## 🔌 API FastAPI

### Démarrer l'API

```bash
python scripts/start_api.py
```

L'API démarrera sur `http://127.0.0.1:8000`

**Interfaces disponibles :**
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Custom Docs: http://127.0.0.1:8000/docs-custom

---

## 📡 Endpoints API

### 1. Health Check
```http
GET /health
```

**Response :**
```json
{
  "status": "healthy",
  "api_ready": true,
  "model_loaded": true
}
```

---

### 2. Prédire le segment d'un client

```http
POST /predict
```

**Request Body :**
```json
{
  "customer_features": {
    "Recency": 180,
    "Monetary": 5000,
    "Frequency": 15,
    "avg_review_score": 4.5,
    "avg_delivery_days": 10,
    "avg_installments": 2.0,
    "avg_item_price": 150.0,
    "CLV_estimate": 10000.0,
    "late_delivery_rate": 0.05,
    "customer_tenure": 365
  }
}
```

**Response :**
```json
{
  "cluster": 2,
  "segment_name": "Clients Satisfaits",
  "segment_action": "Reward",
  "pca_1": 0.45,
  "pca_2": -0.82,
  "confidence": 0.78
}
```

---

### 3. Prédire pour plusieurs clients

```http
POST /predict-bulk
```

**Request Body :**
```json
{
  "customers": [
    {
      "Recency": 180,
      "Monetary": 5000,
      "Frequency": 15,
      "avg_review_score": 4.5,
      "avg_delivery_days": 10,
      "avg_installments": 2.0,
      "avg_item_price": 150.0,
      "CLV_estimate": 10000.0,
      "late_delivery_rate": 0.05,
      "customer_tenure": 365
    },
    {
      "Recency": 5,
      "Monetary": 50000,
      "Frequency": 100,
      "avg_review_score": 5.0,
      "avg_delivery_days": 5,
      "avg_installments": 1.0,
      "avg_item_price": 500.0,
      "CLV_estimate": 100000.0,
      "late_delivery_rate": 0.0,
      "customer_tenure": 730
    }
  ]
}
```

**Response :**
```json
{
  "predictions": [
    {
      "cluster": 2,
      "segment_name": "Clients Satisfaits",
      "segment_action": "Reward",
      "pca_1": 0.45,
      "pca_2": -0.82,
      "confidence": 0.78
    },
    {
      "cluster": 0,
      "segment_name": "Premium Actifs",
      "segment_action": "VIP",
      "pca_1": -1.2,
      "pca_2": 0.55,
      "confidence": 0.95
    }
  ]
}
```

---

### 4. Obtenir les profils de clusters

```http
GET /profiles
```

**Response :**
```json
[
  {
    "cluster_id": 0,
    "segment_name": "Premium Actifs",
    "segment_action": "VIP",
    "mean_features": {
      "Recency": 50,
      "Monetary": 25000,
      "Frequency": 150,
      "avg_review_score": 4.8,
      ...
    },
    "median_features": {
      "Recency": 45,
      "Monetary": 23000,
      "Frequency": 140,
      ...
    }
  },
  {
    "cluster_id": 1,
    "segment_name": "Clients Satisfaits",
    "segment_action": "Reward",
    ...
  }
]
```

---

### 5. Obtenir les métriques de clustering

```http
GET /metrics
```

**Response :**
```json
{
  "metrics": [
    {
      "n_clusters": 4,
      "algorithm": "KMeans",
      "silhouette_score": 0.45,
      "davies_bouldin_score": 1.2,
      "calinski_harabasz_score": 2500
    },
    {
      "n_clusters": 5,
      "algorithm": "KMeans",
      "silhouette_score": 0.48,
      ...
    }
  ]
}
```

---

### 6. Obtenir les statistiques de segments

```http
GET /statistics
```

**Response :**
```json
{
  "total_customers": 93358,
  "segments": {
    "Premium Actifs": {
      "count": 15000,
      "percentage": 16.08
    },
    "Clients Satisfaits": {
      "count": 25000,
      "percentage": 26.80
    },
    "Clients Dormants": {
      "count": 30000,
      "percentage": 32.15
    },
    "Nouveaux Clients": {
      "count": 23358,
      "percentage": 25.03
    }
  }
}
```

---

### 7. Infos du modèle

```http
GET /model-info
```

**Response :**
```json
{
  "best_k": 4,
  "n_features": 9,
  "feature_cols": [
    "Recency",
    "Monetary",
    "Frequency",
    "avg_review_score",
    "avg_delivery_days",
    "avg_installments",
    "avg_item_price",
    "CLV_estimate",
    "late_delivery_rate",
    "customer_tenure"
  ],
  "cluster_names": {
    "0": "Premium Actifs",
    "1": "Clients Satisfaits",
    "2": "Clients Dormants",
    "3": "Nouveaux Clients"
  },
  "segment_actions": {
    "0": "VIP",
    "1": "Reward",
    "2": "Reactivate",
    "3": "Welcome"
  },
  "n_components_pca": 2
}
```

---

## 🧪 Test de l'API (avec Python)

```python
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# 1. Health check
response = requests.get(f"{BASE_URL}/health")
print("Health:", response.json())

# 2. Prédire un segment
customer = {
    "Recency": 180,
    "Monetary": 5000,
    "Frequency": 15,
    "avg_review_score": 4.5,
    "avg_delivery_days": 10,
    "avg_installments": 2.0,
    "avg_item_price": 150.0,
    "CLV_estimate": 10000.0,
    "late_delivery_rate": 0.05,
    "customer_tenure": 365
}

response = requests.post(
    f"{BASE_URL}/predict",
    json={"customer_features": customer}
)
print("Prediction:", response.json())

# 3. Obtenir les profils
response = requests.get(f"{BASE_URL}/profiles")
print("Profiles:", response.json())

# 4. Obtenir les statistiques
response = requests.get(f"{BASE_URL}/statistics")
print("Statistics:", response.json())
```

---

## 🔄 Workflow complet

### Étape 1 : Générer les résultats du pipeline

```bash
python scripts/full_pipeline.py
```

Cela crée :
- Modèle entraîné (`final_pipeline.pkl`)
- Rapports CSV
- Metadata (cluster names, etc.)

### Étape 2 : Lancer l'API

```bash
python scripts/start_api.py
```

L'API charge automatiquement le modèle et les données.

### Étape 3 : Utiliser l'API

Via Swagger UI (http://127.0.0.1:8000/docs) ou via Python/cURL :

```bash
curl -X POST "http://127.0.0.1:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_features": {
      "Recency": 180,
      "Monetary": 5000,
      ...
    }
  }'
```

---

## 📋 Features requis pour prédiction

Les 10 features suivants sont **obligatoires** pour une prédiction :

| Feature | Type | Description |
|---------|------|-------------|
| `Recency` | float | Jours depuis dernière commande |
| `Monetary` | float | Montant total dépensé |
| `Frequency` | float | Nombre de commandes |
| `avg_review_score` | float | Score d'avis moyen (1-5) |
| `avg_delivery_days` | float | Jours moyens de livraison |
| `avg_installments` | float | Nombre de mensualités moyen |
| `avg_item_price` | float | Prix moyen des articles |
| `CLV_estimate` | float | Customer Lifetime Value estimée |
| `late_delivery_rate` | float | Taux de livraisons en retard (0-1) |
| `customer_tenure` | float | Jours depuis inscription |

---

## ⚙️ Configuration

### Variables d'environnement

```bash
# Port et hôte de l'API
export API_HOST=127.0.0.1
export API_PORT=8000

# Chemins des données
export MODEL_DIR=notebooks/models
export REPORTS_DIR=notebooks/reports
```

### Architecture de données

**Input :** Features clients → Scaler StandardScaler → Model KMeans → Cluster
**Output :** Cluster ID → Segment Name + Action + PCA Coordinates

---

## 🐛 Troubleshooting

### ModuleNotFoundError: No module named 'fastapi'

```bash
pip install fastapi uvicorn
```

### ModuleNotFoundError: No module named 'src'

Assurez-vous d'exécuter depuis le répertoire racine du projet :

```bash
cd /path/to/Projet_2026
python scripts/start_api.py
```

### API retourne "Model not loaded"

Vérifiez que `notebooks/models/final_pipeline.pkl` existe :

```bash
python scripts/full_pipeline.py
```

---

## 📚 Références

- **Notebook source :** `notebooks/Modélisons.ipynb`
- **Pipeline modules :** `src/` (preprocessing, features, clustering)
- **Configuration :** `config/config.yaml`

---

## ✅ Checklist

- ✅ Pipeline Python reproduit le notebook exactement
- ✅ API FastAPI expose tous les endpoints
- ✅ Prédictions single et bulk
- ✅ Profils de clusters disponibles
- ✅ Métriques de clustering accessibles
- ✅ Documentation complète

---

**Version :** 1.0.0  
**Date :** 2026-05-06  
**Auteur :** Customer Segmentation Team
