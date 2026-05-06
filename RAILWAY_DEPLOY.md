# Déployer l’API sur Railway

## Prérequis
- Le repo doit contenir les artefacts nécessaires (sinon l’API répondra 503) :
  - `notebooks/models/final_pipeline.pkl`
  - `notebooks/reports/clustering_comparison.csv`
  - `notebooks/reports/cluster_profiles_mean.csv`
  - `notebooks/reports/cluster_profiles_median.csv`
  - `notebooks/reports/segmentation_finale_olist.csv`

Railway ne “voit” que ce qui est versionné dans Git (ou téléchargé au runtime).

## 1) Push sur GitHub
Pousse ton projet sur GitHub (public ou privé).

## 2) Déploiement Railway
1. Railway → **New Project**
2. **Deploy from GitHub Repo**
3. Sélectionne le repo

Railway va détecter le `Dockerfile` à la racine et builder une image qui lance :

- `uvicorn scripts.api:app --host 0.0.0.0 --port $PORT`

## 3) Récupérer le lien public
Dans Railway, ouvre le service → **Domains** → copie l’URL.

Ensuite :
- Swagger UI : `https://<ton-domaine>/docs`
- Healthcheck : `https://<ton-domaine>/health`

## 4) Test rapide
Avec Python :

```python
import requests

base = "https://<ton-domaine>"
print(requests.get(base + "/health").json())
print(requests.get(base + "/model-info").json()["feature_cols"])
```

