# 🎯 Pipeline & API - Quick Start Guide

## 📋 Sommaire rapide

Ce projet fournit :

1. **Pipeline Python** (`scripts/full_pipeline.py`) - Reproduit exactement le notebook Modélisons
2. **API REST** (`scripts/api.py`) - Expose le modèle via FastAPI
3. **Tests automatisés** (`scripts/test_suite.py`) - Valide le pipeline et l'API

---

## 🚀 Démarrage rapide

### 1️⃣ Exécuter le pipeline

```bash
python scripts/full_pipeline.py
```

**Génère :**
- `notebooks/models/final_pipeline.pkl` (modèle entraîné)
- `notebooks/reports/*.csv` (résultats et profils)

**Temps :** ~5-10 minutes (selon votre machine)

### 2️⃣ Lancer l'API

```bash
python scripts/start_api.py
```

**API disponible sur :**
- 🌐 Swagger UI: http://127.0.0.1:8000/docs
- 📚 Documentation: http://127.0.0.1:8000/redoc
- ⚙️ Info API: http://127.0.0.1:8000/docs-custom

### 3️⃣ Tester tout

```bash
python scripts/test_suite.py
```

---

## 📡 Exemples d'utilisation rapide

### Prédire le segment d'un client (Python)

```python
import requests

response = requests.post(
    "http://127.0.0.1:8000/predict",
    json={
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
)

print(response.json())
# Output:
# {
#   "cluster": 1,
#   "segment_name": "Clients Satisfaits",
#   "segment_action": "Reward",
#   "confidence": 0.78,
#   ...
# }
```

### Prédire avec cURL

```bash
curl -X POST "http://127.0.0.1:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

### Obtenir les segments

```bash
curl http://127.0.0.1:8000/statistics
```

---

## 📦 Endpoints principaux

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/health` | GET | Vérifier que l'API fonctionne |
| `/predict` | POST | Prédire le segment d'un client |
| `/predict-bulk` | POST | Prédire pour plusieurs clients |
| `/profiles` | GET | Obtenir les profils de clusters |
| `/statistics` | GET | Statistiques de distribution des segments |
| `/metrics` | GET | Métriques de clustering |
| `/model-info` | GET | Informations sur le modèle |

**Documentation complète :** Voir [API_GUIDE.md](API_GUIDE.md)

---

## 🔧 Installation des dépendances

```bash
# Si ce n'est pas déjà fait
pip install -r requirements.txt
```

Les dépendances FastAPI ont été ajoutées à `requirements.txt`.

---

## ✅ Architecture

```
Pipeline Flow:
Raw Data → Preprocessing → Feature Engineering → Scaling → KMeans → Results

API Flow:
Client Request → Load Model → Predict → Return JSON Response
```

**Résultats sauvegardés :**
- ✅ Clustering comparison (métriques k=4 à k=8)
- ✅ Cluster profiles (mean & median)
- ✅ Final segmentation (93K+ clients)
- ✅ Trained model (pickle)
- ✅ Cluster names (JSON)

---

## 🎯 Cas d'usage

### 1️⃣ Reproduire les résultats du notebook
```bash
python scripts/full_pipeline.py
# Puis comparer les fichiers CSV générés
```

### 2️⃣ Exposer le modèle via API
```bash
python scripts/start_api.py
# L'API sera disponible pour intégration
```

### 3️⃣ Prédictions batch
```python
response = requests.post(
    "http://127.0.0.1:8000/predict-bulk",
    json={
        "customers": [
            {"Recency": 180, "Monetary": 5000, ...},
            {"Recency": 5, "Monetary": 50000, ...},
        ]
    }
)
```

### 4️⃣ Analyser les segments
```bash
curl http://127.0.0.1:8000/profiles | python -m json.tool
```

---

## 📊 Structure des fichiers générés

```
notebooks/
├── models/
│   ├── final_pipeline.pkl          ← Modèle pour prédictions
│   └── cluster_names.json          ← Mapping cluster → segment
├── reports/
│   ├── clustering_comparison.csv   ← Métriques k=4..8
│   ├── cluster_profiles_mean.csv   ← Profils moyens
│   ├── cluster_profiles_median.csv ← Profils médians
│   └── segmentation_finale_olist.csv ← 93K clients avec segments
```

---

## 🐛 Troubleshooting

### Pipeline lent ?
- C'est normal (~5-10 min avec 93K clients)
- Montant de RAM disponible : vérifiez avec `free -h`

### API : "Model not found" ?
```bash
# Solution
python scripts/full_pipeline.py
python scripts/start_api.py
```

### Port 8000 déjà utilisé ?
```bash
# Changer le port
export API_PORT=8001
python scripts/start_api.py
```

### Dépendances manquantes ?
```bash
pip install fastapi uvicorn pydantic requests
```

---

## 📚 Documentation complète

Pour la documentation détaillée des endpoints et exemples complets :
👉 **Voir [API_GUIDE.md](API_GUIDE.md)**

---

## ✨ Points clés

✅ **Reproductibilité :** Pipeline produit exactement les mêmes résultats que le notebook  
✅ **Scalabilité :** API peut gérer des prédictions batch  
✅ **Production-ready :** Modèle persisté, API robuste  
✅ **Documentation :** Exemples et guide complets  

---

## 🎓 Prochaines étapes

1. **Monitoring :** Ajouter des logs + métriques Prometheus
2. **Containerization :** Créer un Dockerfile pour déployer
3. **CI/CD :** Pipeline GitHub Actions pour tests automatisés
4. **Dashboard :** Interface Streamlit pour visualiser les segments

---

**Besoin d'aide ?**  
Consultez [API_GUIDE.md](API_GUIDE.md) pour la documentation complète.
