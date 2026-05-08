# Segmentation Client Olist

Projet de Machine Learning 2 — ISE2, Semestre 2 (2026)

## Objectif

Ce projet realise la **segmentation non supervisee** des clients de la plateforme e-commerce bresilienne Olist.
L'objectif est d'identifier des groupes de clients aux comportements distincts pour orienter les strategies marketing.

## Structure du projet

```
Projet_2026/
├── data/                        # Donnees brutes Olist (CSV)
├── notebooks/                   # Notebooks Jupyter
│   ├── segmentation_01_analyse.ipynb        # Analyse exploratoire
│   ├── segmentation_02_analyse.ipynb        # Analyse approfondie
│   ├── Segmentation_03_modelisation.ipynb   # Modelisation et clustering
│   ├── simulation_frequence_maj.ipynb       # Simulation frequence de MAJ
│   ├── models/                  # Modeles serialises (.pkl)
│   ├── figures/                 # Graphiques generes
│   └── reports/                 # Rapports CSV
├── scripts/                     # Scripts Python
│   ├── api.py                   # API FastAPI de prediction
│   ├── full_pipeline.py         # Pipeline complet d'entrainement
│   ├── start_api.py             # Lanceur de l'API
│   └── run_pipeline.py          # Execution du pipeline
├── src/                         # Code source modulaire
│   ├── data/                    # Chargement et preprocessing
│   ├── features/                # Feature engineering (RFM, CLV)
│   ├── clustering/              # Modeles de clustering
│   └── utils/                   # Configuration et utilitaires
├── templates/                   # Templates HTML (interface web)
├── static/                      # Fichiers statiques (CSS, JS)
├── tests/                       # Tests unitaires (pytest)
├── config/                      # Configuration (config.yaml)
├── Dockerfile                   # Containerisation Docker
├── railway.toml                 # Deploiement Railway
├── requirements.txt             # Dependances Python
└── requirements-api.txt         # Dependances API
```

## Methodologie

### 1. Analyse exploratoire
- Chargement et nettoyage des 11 tables Olist
- Jointures et creation du dataset client unifie (93 358 clients)

### 2. Feature Engineering
- **RFM** : Recency, Frequency, Monetary
- **Comportementaux** : delai livraison, score avis, versements, CLV
- **Geographiques** : distance a Sao Paulo
- **Categoriels** : categorie preferee, mode de paiement
- Total : 47 features par client

### 3. Modelisation
5 features retenues pour le clustering :
- `Recency` : jours depuis le dernier achat
- `avg_review_score_full` : note moyenne des avis
- `avg_delivery_days` : delai moyen de livraison
- `avg_installments` : nombre moyen de versements
- `CLV_estimate` : valeur vie client estimee

Pipeline : **QuantileTransformer → StandardScaler → PCA → KMeans (K=5)**

5 algorithmes compares : KMeans, CAH Ward, GMM, DBSCAN, HDBSCAN

### 4. Segments identifies

| Segment | Taille | Profil |
|---------|--------|--------|
| **C0 - Acheteurs Valeur Moyenne** | 19.3% | Panier moyen, satisfaction moderee, paiement echelonne |
| **C1 - Clients Satisfaits Ponctuels** | 25.7% | Review 5/5, achat unique, petit panier |
| **C2 - Nouveaux Clients Recents** | 10.5% | Tres recents, livraison rapide, satisfaits |
| **C3 - Clients Decus** | 18.3% | Review bas, livraison longue, insatisfaits |
| **C4 - Clients Fideles Premium** | 26.2% | CLV eleve, paiement echelonne, satisfaits |

### 5. Interpretabilite
- **SHAP** : importance globale et locale des features
- **LIME** : explications individuelles des predictions

### 6. Simulation de maintenance
Notebook dedie pour determiner la frequence optimale de re-entrainement du modele
(drift des features, stabilite ARI, PSI).

## API de prediction

L'API FastAPI permet de predire le segment d'un nouveau client en temps reel.

```bash
# Lancer l'API
cd scripts
python start_api.py

# Acceder a l'interface
# http://localhost:8000/form
```

### Endpoints
- `GET /form` : Interface web de prediction
- `POST /predict-raw` : Prediction via JSON

## Installation

```bash
# Cloner le depot
git clone <url-du-repo>
cd Projet_2026

# Creer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate  # Windows

# Installer les dependances
pip install -r requirements.txt
```

## Deploiement

Le projet est deploye sur **Railway** via le fichier `railway.toml`.

```bash
# Build Docker local
docker build -t olist-segmentation .

# Deploiement Railway
railway up
```

## Technologies

- **Python 3.9+**
- **Scikit-learn** : preprocessing, clustering, metriques
- **FastAPI** : API de prediction
- **MLflow** : tracking des experiences
- **SHAP / LIME** : interpretabilite
- **Pandas / NumPy** : manipulation de donnees
- **Matplotlib / Seaborn** : visualisations

## Auteurs

Projet ISE2 — Machine Learning 2 — Semestre 2, 2026
