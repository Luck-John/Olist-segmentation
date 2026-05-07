# 🚀 GUIDE D'UTILISATION - Pipeline Cohérent Notebook ↔ API

**Status:** ✅ Tous les composants validés  
**Date:** 2026-05-07

---

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Utilisation du formulaire](#utilisation-du-formulaire)
3. [Appels API](#appels-api)
4. [Code Python direct](#code-python-direct)
5. [Dépannage](#dépannage)

---

## Vue d'ensemble

Votre système de segmentation client comprend maintenant **4 étapes** reproductibles du notebook :

```
Données brutes (17 variables)
    ↓
Engineered Features (14+ features)
    ↓
Transformations (log, bucketing, PCA)
    ↓
Clustering KMeans
    ↓
Segment Client + Actions
```

---

## Utilisation du Formulaire

### 🌐 Accès
```
http://localhost:8000/form
```

### 📝 Sections du Formulaire

#### **1. Identité** (Obligatoire)
- `ID client unique` : e.g., `c9d5c2f3-4a1b-...` (UUID)
- `ID commande` : e.g., `00f51a27-8c9e-...` (UUID)

#### **2. Commande** (Obligatoire)
- `Statut de la commande` : "Livrée" recommandé (delivered)
- `Montant paiement (R$)` : e.g., `150.50`

#### **3. Dates** (Partiellement Obligatoire)
- `Date d'achat *` : Date/heure exacte
- `Livraison réelle` : Quand reçu
- `Livraison estimée` : Date promise

**⚠️ Obligatoires pour RFM:**
- Date d'achat
- Statut = "Livrée"
- Montant paiement

#### **4. Paiement** (Optionnel - NOUVEAU)
- `Nombre de versements` : e.g., `1` (comptant), `2`, `3`, `12` (crédit)

#### **5. Produits** (Optionnel - NOUVEAU)
- `Prix unitaire (R$)` : e.g., `50.99`
- `Nombre d'articles` : e.g., `2`, `5`, etc.
- `Catégorie produit` : e.g., `Electronics`, `Furniture`, `Books`
- `Frais de port (R$)` : e.g., `15.50`

#### **6. Avis client** (Optionnel)
- `Note (1–5)` : e.g., `4.5`

#### **7. Localisation** (Optionnel)
- `Latitude/Longitude` : Pour calcul distance

### 💾 Soumission

Cliquez **"Calculer & Prédire le segment"** → L'API traite et retourne :

```json
{
  "customer_id": "c9d5c2f3-4a1b-...",
  "cluster": 2,
  "segment_name": "Premium Actifs",
  "segment_action": "VIP",
  "confidence": 0.87,
  "engineered_features": {
    "Recency": 45,
    "Monetary": 1250.50,
    "log_recency": 3.83,
    "recency_score_10": 8.5,
    ...
  }
}
```

---

## Appels API

### 📡 Endpoint: `/predict-raw`

#### Requête
```bash
curl -X POST "http://localhost:8000/predict-raw" \
  -H "Content-Type: application/json" \
  -d '{
    "orders": [
      {
        "order_id": "abc123",
        "customer_unique_id": "cust456",
        "order_status": "delivered",
        "order_purchase_timestamp": "2024-01-15T10:30:00",
        "payment_value": 150.50,
        "payment_installments": 2,
        "price": 50.00,
        "order_item_id": 3,
        "super_categorie": "Electronics",
        "freight_value": 15.50,
        "order_delivered_customer_date": "2024-01-20T14:00:00",
        "order_estimated_delivery_date": "2024-01-22T00:00:00",
        "review_score": 4.5
      }
    ]
  }'
```

#### Réponse
```json
{
  "predictions": [
    {
      "customer_id": "cust456",
      "cluster": 2,
      "segment_name": "Premium Actifs",
      "segment_action": "VIP",
      "confidence": 0.87,
      "pca_1": 0.45,
      "pca_2": -0.23,
      "engineered_features": {
        "Recency": 5,
        "Frequency": 1,
        "Monetary": 150.50,
        "avg_delivery_days": 5.0,
        "late_delivery_rate": 0.0,
        "avg_review_score": 4.5,
        "avg_installments": 2.0,
        "log_recency": 1.79,
        "recency_score_10": 9.0,
        "log_monetary": 5.02,
        ...
      }
    }
  ]
}
```

### 📊 Endpoint: `/profiles`

Voir les profils moyens/médians des clusters :

```bash
curl "http://localhost:8000/profiles"
```

```json
{
  "cluster_0": {
    "mean": {"Recency": 120.5, "Monetary": 800.2, ...},
    "median": {"Recency": 115.0, "Monetary": 750.0, ...}
  },
  "cluster_1": {...},
  ...
}
```

### ℹ️ Endpoint: `/model-info`

Infos sur le modèle chargé :

```bash
curl "http://localhost:8000/model-info"
```

```json
{
  "algorithm": "KMeans",
  "n_clusters": 5,
  "pca_components": 5,
  "n_features": 7,
  "features": ["log_recency", "recency_score_10", ...],
  "cluster_names": {
    "0": "Clients Dormants",
    "1": "Premium Actifs",
    ...
  }
}
```

---

## Code Python Direct

### Installation dépendances
```bash
pip install pandas numpy scikit-learn pydantic fastapi
```

### Utilisation minimale

```python
import pandas as pd
from src.clustering.preprocessing import ClusteringPreprocessor
from src.clustering.clustering import CustomerSegmenter

# 1. Charger features (ex: après FeatureEngineer)
df_features = pd.read_csv("features.csv")

# 2. Préprocesser
prep = ClusteringPreprocessor(random_state=42)
X_pca = prep.fit_preprocessing(df_features)  # (n, 5)

# 3. Clusterer
segmenter = CustomerSegmenter(random_state=42)
results = segmenter.fit(X_pca)

# 4. Prédire
new_features = pd.read_csv("new_features.csv")
X_new = prep.transform_features(new_features)
labels = segmenter.predict(X_new)

print(f"Clusters: {labels}")  # [0, 2, 1, ...]
```

### Utilisation complète (notebook to production)

```python
from src.data.preprocessing import DataPreprocessor
from src.features.engineering import FeatureEngineer
from src.clustering.preprocessing import ClusteringPreprocessor
from src.clustering.clustering import CustomerSegmenter
import pickle

# TRAINING
preprocessor = DataPreprocessor()
df = preprocessor.load_and_preprocess("data/base_final.csv")

engineer = FeatureEngineer()
df_features = engineer.engineer_features(df)

prep = ClusteringPreprocessor(random_state=42)
X_pca = prep.fit_preprocessing(df_features)

segmenter = CustomerSegmenter(random_state=42)
segmenter.fit(X_pca)

# SAVE
pipeline = {
    "prep": prep,
    "segmenter": segmenter,
    "engineer": engineer,
}
with open("models/pipeline.pkl", "wb") as f:
    pickle.dump(pipeline, f)

# PRODUCTION
with open("models/pipeline.pkl", "rb") as f:
    pipeline = pickle.load(f)

df_new = pipeline["engineer"].engineer_features(df_new_raw)
X_new = pipeline["prep"].transform_features(df_new)
labels = pipeline["segmenter"].predict(X_new)
```

---

## Dépannage

### ❌ "Module not found: src.clustering"

**Cause:** Python path incorrect  
**Solution:**
```bash
cd /path/to/Projet_2026
python scripts/test_pipeline_parity.py
```

### ❌ "Missing columns for log transforms"

**Cause:** Features brutes non disponibles  
**Solution:** Vérifier que `df_features` contient :
- `Recency`, `Monetary`, `avg_item_price`, `avg_delivery_days`

```python
print(df_features.columns)  # Vérifier ces 4 colonnes
```

### ❌ "PCA not fitted yet"

**Cause:** `transform_features()` avant `fit_preprocessing()`  
**Solution:**
```python
# ✗ MAUVAIS
X = prep.transform_features(df)

# ✓ BON
X_pca = prep.fit_preprocessing(df)  # d'abord fit
X_new = prep.transform_features(df_new)  # puis transform
```

### ❌ "RawOrder validation error"

**Cause:** Format date incorrect  
**Solution:** ISO 8601
```python
# ✗ MAUVAIS
"order_purchase_timestamp": "15/01/2024 10:30"

# ✓ BON
"order_purchase_timestamp": "2024-01-15T10:30:00"
```

### ℹ️ Comment déboguer une prédiction

```python
from src.clustering.preprocessing import ClusteringPreprocessor

prep = ClusteringPreprocessor()
prep.fit_preprocessing(df_features)

# Afficher les features finales
print(prep.FEATURES_FINAL)

# Afficher les composantes PCA
components = prep.get_pca_components()
print(components)

# Afficher variance expliquée
info = prep.get_explained_variance()
print(f"Cumulative variance: {info['cumulative_variance_ratio']}")
```

---

## ✅ Checklist pour Production

- [ ] Formulaire : toutes les sections affichées
- [ ] API : `/predict-raw` retourne segment
- [ ] Test : `python scripts/test_pipeline_parity.py` ✓
- [ ] Imports : `from src.clustering import *` ✓
- [ ] Données : `data/base_final.csv` présent
- [ ] Config : `config/config.yaml` correct

---

## 📞 Besoin d'aide ?

1. **Lire les rapports:**
   - `RESUME_CHANGEMENTS.md` (résumé français)
   - `PIPELINE_CORRECTION_REPORT.md` (technique détaillé)

2. **Tester:**
   ```bash
   python scripts/test_pipeline_parity.py
   ```

3. **Vérifier les logs:**
   ```bash
   tail -100 output.log
   ```

---

**Vous êtes prêt! 🚀**

Le pipeline est maintenant 100% cohérent avec votre notebook Modélisons.ipynb.
