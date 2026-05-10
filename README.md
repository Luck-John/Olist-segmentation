# Segmentation Client Olist

Projet de Machine Learning 2 — ISE2, Semestre 2 (2026)

## 🚀 API en Production

**L'API est déployée et accessible en ligne :**
👉 [https://olist-segmentation-api-production.up.railway.app/form](https://olist-segmentation-api-production.up.railway.app/form)

## Objectif

Ce projet réalise la **segmentation non supervisée** des clients de la plateforme e-commerce brésilienne Olist.
L'objectif est d'identifier des groupes de clients aux comportements distincts pour orienter les stratégies marketing.

## Structure du projet

```
Projet_2026/
├── data/                        # Données brutes Olist (CSV)
├── notebooks/                   # Notebooks Jupyter
│   ├── segmentation_01_analyse.ipynb        # Analyse exploratoire
│   ├── segmentation_02_analyse.ipynb        # Analyse approfondie
│   ├── Segmentation_03_modelisation.ipynb   # Modélisation et clustering final
│   ├── simulation_frequence_maj.ipynb       # Simulation fréquence de MAJ
│   ├── models/                  # Modèles sérialisés (.pkl)
│   │   ├── final_pipeline.pkl   # Pipeline de production (KMeans k=5)
│   │   ├── KMeans_k5.pkl        # Modèle KMeans seul
│   │   └── cluster_names.json   # Noms des segments
│   ├── figures/                 # Graphiques générés
│   └── reports/                 # Rapports CSV (profils, résultats)
├── scripts/                     # Scripts Python
│   ├── api.py                   # API FastAPI de prédiction
│   ├── full_pipeline.py         # Pipeline complet d'entraînement
│   ├── gen_customer_db.py       # Génération base clients optimisée
│   └── start_api.py             # Lanceur de l'API
├── src/                         # Code source modulaire
│   ├── data/                    # Chargement et preprocessing
│   ├── features/                # Feature engineering (RFM, CLV)
│   ├── clustering/              # Modèles de clustering
│   └── utils/                   # Configuration et utilitaires
├── templates/                   # Templates HTML (interface web)
├── tests/                       # Tests unitaires (pytest)
├── config/                      # Configuration (config.yaml)
├── Dockerfile                   # Conteneurisation Docker
├── railway.toml                 # Déploiement Railway
├── requirements.txt             # Dépendances Python
└── requirements-api.txt         # Dépendances API uniquement
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

## 🎯 API de Prédiction Intelligente

L'API FastAPI permet de prédire le segment d'un client avec **fusion automatique d'historique**.

### Modes de prédiction

#### 1. **Mode Commandes** (`/predict-smart`)
- Entrez des commandes + ID client (optionnel)
- **Fusion automatique** : si le client existe en base, son historique est fusionné
- **Nouveau client** : prédiction sur les commandes saisies uniquement

#### 2. **Mode Historique Direct** (`/customer/{id}/predict`)
- Entrez uniquement l'ID client existant
- Prédiction basée sur **tout l'historique** du client

### Endpoints principaux
- `GET /form` : Interface web principale
- `POST /predict-smart` : Prédiction intelligente avec fusion
- `GET /customer/{id}/predict` : Prédiction directe depuis historique
- `GET /customer/{id}/orders` : Voir l'historique d'un client

### Lancement local
```bash
cd scripts
python start_api.py
# Accès : http://localhost:8003/form
```

## Installation

```bash
# Cloner le depot
git clone https://github.com/Luck-John/Olist-segmentation
cd Projet_2026

# Creer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Installer les dependances
pip install -r requirements.txt
```

## Re-entraîner le pipeline

```bash
# Générer data/Base.csv (features engineered) puis entraîner KMeans
python scripts/full_pipeline.py

# Générer la base clients pour l'API smart
python scripts/gen_customer_db.py
```

## Deploiement

Le projet est deploye sur **Railway** via le fichier `railway.toml`.

```bash
# Build Docker local
docker build -t olist-segmentation .

# Deploiement Railway
railway up
```

## Tests

```bash
# Lancer tous les tests unitaires et d'integration
python -m pytest tests/ -v

# Tests rapides uniquement
python -m pytest tests/ -v -m "not integration"
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

| Auteur | GitHub |
|--------|--------|
| **Jean Luc BATABATI** | [@Luck-John](https://github.com/Luck-John) |
| **Fromo Francis HABA** | [@fromofrancishaba](https://github.com/fromofrancishaba) |
| **Aissatou Sega DIALLO** | [@ASegaDiallo](https://github.com/ASegaDiallo) |
| **Jeanne de la Flèche AMANA ONANENA** | [@LaFleche06](https://github.com/LaFleche06) |
