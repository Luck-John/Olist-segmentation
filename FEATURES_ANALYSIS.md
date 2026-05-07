# 📊 ANALYSE COMPARATIVE : Notebook vs Code Python Production

## 🎯 Résumé Exécutif

Le notebook **Modélisons.ipynb** applique un pipeline complet de feature engineering et clustering avec:
- **7 features finales** pour le clustering (après transformations avancées)
- **PCA 5D whitening** pour réduction de dimension
- **KMeans** comme meilleur algorithme
- **Transformations avancées** (log, bucketing, composites, normalization)

Le fichier **src/features/engineering.py** produit uniquement **14+ features brutes** sans les transformations avancées, causant une **divergence significative** entre le notebook et le code production.

---

## 📋 TABLEAU RÉCAPITULATIF

### 1️⃣ VARIABLES BRUTES UTILISÉES (Colonnes du DataFrame Raw)

| Variable Brute | Étape d'Utilisation | Rôle Principal |
|---|---|---|
| `customer_unique_id` | Agrégation client | Clé d'agrégation |
| `order_id` | Agrégation commande/client | Identification unique commande |
| `order_purchase_timestamp` | Date de référence + Recency | Calcul de la date snapshot et Recency |
| `order_approved_at` | (Optionnel) | Suivi approbation |
| `order_delivered_customer_date` | Calcul livraison | Délai livraison réel |
| `order_estimated_delivery_date` | Calcul livraison | Délai estimé vs réel (is_late) |
| `order_delivered_carrier_date` | (Optionnel) | Suivi logistique |
| `is_delivered` | Filtrage | Filtrer seules les commandes livrées |
| `payment_value` | RFM Monetary | Agrégation au niveau commande/client |
| `payment_installments` | Feature auxiliaire | Nombre d'échéances de paiement |
| `payment_type` | Feature auxiliaire | Mode de paiement préféré |
| `review_score` | Satisfaction | Note moyenne des avis (1-5) |
| `review_creation_date` | Satisfaction filtrée | Récence des avis |
| `order_item_id` | Compléxité commande | Nombre d'articles par commande |
| `super_categorie` | Diversité produits | Nombre de catégories uniques |
| `price` | Prix produit | Prix moyen par article |
| `freight_value` | Coûts logistiques | Frais de port moyens |
| `customer_lat` / `customer_lng` | (Non utilisé dans FEATURES_FINAL) | Distance géographique |

**Remarque** : 97% des clients n'ont qu'UNE seule commande → `Frequency=1` quasi-constante (exclu de FEATURES_FINAL)

---

### 2️⃣ FEATURES INTERMÉDIAIRES CRÉÉES (Étape par Étape)

#### **Phase 1 : Agrégation au Niveau Client**
| Feature | Formule/Calcul | Type | Utilisation |
|---|---|---|---|
| `Recency` | `(date_snapshot - max(order_purchase_timestamp)).days` | Numérique | RFM base |
| `Frequency` | `COUNT(order_id) par client` | Numérique | RFM base - **EXCLU (96.9% = 1)** |
| `Monetary` | `SUM(payment_value) par client` | Numérique | RFM base |
| `avg_delivery_days` | `MEAN((order_delivered_customer_date - order_purchase_timestamp).days)` | Numérique | Qualité livraison |
| `estimated_days` | `MEAN((order_estimated_delivery_date - order_purchase_timestamp).days)` | Numérique | Baseline estimation |
| `is_late` | `ORDER_DELIVERED > ORDER_ESTIMATED` | Binaire | Retards livraison |
| `late_delivery_rate` | `MEAN(is_late)` | Numérique [0,1] | Taux de retard |
| `n_items` | `COUNT(order_item_id) par commande` | Numérique | Taille paniers |
| `avg_item_price` | `MEAN(price)` | Numérique | Valeur moyenne articles |
| `avg_freight_value` | `MEAN(freight_value)` | Numérique | Coûts logistiques |
| `n_categories` | `NUNIQUE(super_categorie)` | Numérique | Diversité produits |
| `avg_review_score` | `MEAN(review_score)` | Numérique [1,5] | Satisfaction client |
| `avg_installments` | `MEAN(payment_installments)` | Numérique | Comportement crédit |
| `preferred_payment` | `MODE(payment_type)` | Catégorique | Mode paiement principal |
| `num_unique_sellers` | `NUNIQUE(order_id) approx` | Numérique | Exposition vendeurs |
| `customer_tenure` | `(max - min)(order_purchase_timestamp).days` | Numérique | Ancienneté client |
| `payment_value_std` | `STD(payment_value)` | Numérique | Variabilité dépenses |

#### **Phase 2 : Transformations Mathématiques (Créées pour Stabilité)**
| Feature | Formule | But |
|---|---|---|
| `log_recency` | `LOG1P(Recency)` | Normaliser la distribution exponentielle |
| `log_monetary` | `LOG1P(Monetary)` | Stabiliser variance asymétrique |
| `log_item_price` | `LOG1P(avg_item_price)` | Réduire impact des outliers prix |
| `log_delivery` | `LOG1P(avg_delivery_days)` | Normaliser délais asymétriques |
| `CLV_estimate` | `Monetary * Frequency / (Recency + 1)` | Valeur prédite à vie client |

#### **Phase 3 : Bucketing/Ordinalisation (Créées pour Clustering)**
| Feature | Méthode | Valeurs | But |
|---|---|---|---|
| `recency_score_10` | `10 - QCUT(Recency, q=10)` | [0,10] | Convertir Recency continu en ordinal |
| `installment_level` | `BINS([-0.1, 1.0, 3.0, 6.0, 100.0])` | [0,1,2,3] | Catégoriser comportement crédit |
| `review_raw` | `CLIP(avg_review_score, 1, 5)` | [1,5] | Sécuriser satisfaction |
| `satisfaction_composite` | `(review/5.0 - late_rate - 0.3*norm_delay).CLIP(-1,1)` | [-1,1] | Score synthétique satisfaction |
| `freight_ratio` | `(avg_freight / Monetary).CLIP(0,1)` | [0,1] | Proportion frais vs dépense |

#### **Phase 4 : Feature Résiduelle**
| Feature | Formule | Utilisation |
|---|---|---|
| `is_repeat_customer` | `(Frequency > 1).ASTYPE(int)` | Variable supplémentaire (non clustering) |

---

### 3️⃣ FEATURES FINALES POUR CLUSTERING (FEATURES_FINAL)

**Étape clé** : Sélection de 7 features actives basées sur :
- ✅ Variance suffisante
- ✅ Faible corrélation inter-features (< 0.80)
- ❌ Exclusion de `Frequency` (quasi-constante à 96.9%)

| # | Feature | Type | Gamme | Description |
|---|---|---|---|---|
| 1 | `log_recency` | Continu | [0, ~8] | Log du délai depuis dernier achat |
| 2 | `recency_score_10` | Ordinal | [0,10] | Récence bucketée 10 niveaux |
| 3 | `log_monetary` | Continu | [0, ~14] | Log de la dépense totale |
| 4 | `log_item_price` | Continu | [0, ~8] | Log du prix unitaire moyen |
| 5 | `installment_level` | Ordinal | [0,1,2,3] | Niveau d'engagement crédit |
| 6 | `review_raw` | Continu | [1,5] | Note moyenne avis (brute) |
| 7 | `log_delivery` | Continu | [0, ~5] | Log du délai moyen livraison |

**Pas inclus (mais disponibles)** :
- `Frequency` ❌ Quasi-constante (96.9% = 1)
- `CLV_estimate` 📌 Supplémentaire (illustration)
- `satisfaction_composite` 📌 Supplémentaire (illustration)
- Autres composites, distances géographiques

---

### 4️⃣ TRANSFORMATIONS APPLIQUÉES

#### **Pipeline Complet du Notebook**

```
RAW DATA (113 425 lignes × 54 colonnes)
    ↓
[Conversion dates + Filtrage livrés]
    ↓
AGRÉGATION NIVEAU CLIENT (52 636 clients) + 21 features brutes
    ↓
[Log transformations : Recency, Monetary, Item_Price, Delivery]
    ↓
[Bucketing : Recency→10 niveaux, Installments→4 niveaux]
    ↓
[Composites : satisfaction, freight_ratio]
    ↓
FEATURES_INTERMEDIATE (21+ dimensions)
    ↓
[Cap outliers au 99e centile] → Winsorisation
    ↓
[StandardScaler] → Moyenne=0, Écart-type=1
    ↓
X_scaled : (52 636, 7) brutes standardisées
    ↓
[PCA n_components=5, whiten=True] → (52 636, 5) PCA whitened
    ↓
X_pca : Prêt pour clustering
    ↓
[KMeans k=4-8] → k_optimal=? (Silhouette maximale)
    ↓
CLUSTERING FINAL : Labels + Profils par segment
```

#### **Détail des Transformations**

| Transformation | Quand | Comment | Impact |
|---|---|---|---|
| **Conversion Dates** | Cellule 3 | `pd.to_datetime()` | Parser timestamps ISO |
| **Filtrage Livrés** | Cellule 4 | `df['is_delivered'] == 1` | Exclure commandes annulées/retournées |
| **Agrégation Client** | Cellule 4 | `.groupby('customer_unique_id').agg(...)` | Passer du niveau transactionnel au client |
| **Log Transform** | Cellule 8 | `log1p(x)` pour Recency, Monetary, etc. | Stabiliser distributions asymétriques |
| **Bucketing** | Cellule 8 | `qcut()/cut()` avec bins prédéfinis | Convertir continu → ordinal |
| **Composite Creation** | Cellule 8 | Formules multi-features | Créer indicateurs synthétiques |
| **Outlier Capping** | Cellule 9 | `clip(lower=Q1, upper=Q99)` | Winsorisation aux 1-99 centiles |
| **Standardisation** | Cellule 9 | `StandardScaler().fit_transform()` | μ=0, σ=1 sur chaque feature |
| **PCA Whitening** | Cellule 11 | `PCA(..., whiten=True)` | Décorrélation + normalisation variance |
| **Clustering** | Cellule 12+ | `KMeans/CAH/DBSCAN/HDBSCAN` | Assigner à clusters |

---

### 5️⃣ DIFFÉRENCES NOTEBOOK ↔ ENGINEERING.PY

| Aspect | Notebook | engineering.py | Impact | Risque |
|---|---|---|---|---|
| **Features Intermédiaires** | 21+ features créées | 14+ features produites | ✅ Même base | ⚠️ Incomplétude |
| **Log Transformations** | ✅ LOG1P(Recency, Monetary, Price, Delivery) | ❌ Aucune log transform | ❌ Divergence | **CRITIQUE** |
| **Bucketing/Ordinalisation** | ✅ recency_score_10, installment_level | ❌ Aucun bucketing | ❌ Divergence | **CRITIQUE** |
| **Composite Features** | ✅ satisfaction_composite, freight_ratio | ❌ Aucune composé | ❌ Divergence | **CRITIQUE** |
| **Feature Selection** | ✅ 7 features ACTIVES sélectionnées | ❌ 14+ features, pas de sélection | ❌ Divergence | **MAJEURE** |
| **Standardisation** | ✅ StandardScaler sur 7 features finales | ❌ Pas de scaling | ❌ Divergence | **MAJEURE** |
| **PCA Whitening** | ✅ 5 composantes whitened | ❌ Aucune PCA | ❌ Divergence | **MAJEURE** |
| **Distance Géographique** | ❌ Non utilisée dans FEATURES_FINAL | ✅ dist_sao_paulo calculée | ⚠️ Extra | OK pour API |
| **Review Latency Handling** | ⚠️ Implicite (une review par order) | ✅ Filtre explicite (snapshot_lag_days) | ✅ Meilleur | ✅ Bonne pratique |
| **CLV Calculation** | `Monetary * Frequency / (Recency+1)` | `Monetary * (Frequency / dataset_years)` | ❌ Divergence | **CRITIQUE** |
| **Clustering Algorithm** | ✅ KMeans (meilleur algo) | ❌ Aucune clustering | 🚫 Manquant | **CRITIQUE** |
| **Silhouette/Metrics** | ✅ Calculés complets | ❌ Absent | 🚫 Manquant | ⚠️ Pour API |

---

## 🔴 PROBLÈMES IDENTIFIÉS

### **DIVERGENCE MAJEURE 1 : Features Finales**
```
❌ NOTEBOOK (7 features pour clustering):
   [log_recency, recency_score_10, log_monetary, log_item_price, 
    installment_level, review_raw, log_delivery]

❌ ENGINEERING.PY (14+ features brutes, pas sélection):
   [Recency, Frequency, Monetary, avg_delivery_days, late_delivery_rate, 
    avg_review_score_full, has_full_review, avg_review_score_available, 
    has_available_review, CLV, dist_sao_paulo, ...]

➡️  RÉSULTAT : Pipeline production ≠ Pipeline notebook
```

### **DIVERGENCE MAJEURE 2 : Transformations Manquantes**
```
❌ ENGINEERING.PY n'applique PAS:
   - Log transformations (LOG1P)
   - Bucketing/Ordinalisation  
   - Composite features
   - Standardisation
   - PCA whitening

➡️  RÉSULTAT : Données d'entrée clustering ≠ Notebook
```

### **DIVERGENCE MAJEURE 3 : Clustering**
```
❌ ENGINEERING.PY produit les features brutes MAIS:
   - Pas de sélection features
   - Pas de preprocessing (scaling, PCA)
   - Pas d'algorithme clustering
   - Pas de sélection k
   
➡️  RÉSULTAT : Code prod ne peut pas ré-produire segments du notebook
```

---

## ✅ RECOMMANDATIONS

### **1. Créer un Pipeline Unifié (engineering.py → FeatureEngineer)**

```python
# AJOUTER à engineering.py:

def engineer_features_for_clustering(df: pd.DataFrame) -> pd.DataFrame:
    """Reproduire exactement le pipeline du notebook."""
    
    # 1. Features intermédiaires (déjà OK)
    df_client = calculate_rfm(df, snapshot_date)
    df_client.update(calculate_delivery_metrics(df))
    df_client.update(calculate_review_metrics(df, snapshot_date))
    
    # 2. AJOUTER: Transformations (LOG, bucketing, composites)
    df_client['log_recency'] = np.log1p(df_client['Recency'])
    df_client['log_monetary'] = np.log1p(df_client['Monetary'])
    df_client['log_item_price'] = np.log1p(df_client['avg_item_price'])
    df_client['log_delivery'] = np.log1p(df_client['avg_delivery_days'])
    
    df_client['recency_score_10'] = (
        10 - pd.qcut(df_client['Recency'], q=10, labels=False, duplicates='drop')
    ).astype('float32')
    
    df_client['installment_level'] = pd.cut(
        df_client['avg_installments'],
        bins=[-0.1, 1.0, 3.0, 6.0, 100.0],
        labels=[0, 1, 2, 3]
    ).astype('float32')
    
    df_client['satisfaction_composite'] = (
        df_client['avg_review_score'] / 5.0
        - df_client['late_delivery_rate'].clip(0, 1)
        - (df_client['avg_delivery_days'] / df_client['avg_delivery_days'].quantile(0.95)).clip(0, 1) * 0.3
    ).clip(-1, 1).astype('float32')
    
    df_client['freight_ratio'] = (
        df_client['avg_freight_value'] / (df_client['Monetary'] + 1e-9)
    ).clip(upper=1.0).astype('float32')
    
    # 3. AJOUTER: Feature selection
    FEATURES_FINAL = [
        'log_recency', 'recency_score_10', 'log_monetary', 'log_item_price',
        'installment_level', 'review_raw', 'log_delivery'
    ]
    
    return df_client[FEATURES_FINAL]
```

### **2. Mettre à Jour le Clustering**

```python
# AJOUTER clustering.py

def prepare_and_cluster(df_features: pd.DataFrame) -> Tuple[np.ndarray, Dict]:
    """Reprendre exactement le préprocessing du notebook."""
    
    # Winsorisation
    X = cap_outliers(df_features, df_features.columns, q=0.99)
    
    # Standardisation
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # PCA whitening
    pca = PCA(n_components=5, whiten=True, random_state=42)
    X_pca = pca.fit_transform(X_scaled)
    
    # KMeans k=4-8 (sélection via Silhouette)
    models = {}
    for k in range(4, 9):
        km = MiniBatchKMeans(n_clusters=k, n_init=10, random_state=42)
        labels = km.fit_predict(X_pca)
        sil = silhouette_score(X_pca, labels)
        models[k] = {'model': km, 'labels': labels, 'silhouette': sil}
    
    k_opt = max(models, key=lambda k: models[k]['silhouette'])
    
    return models[k_opt]['labels'], {
        'scaler': scaler,
        'pca': pca,
        'model': models[k_opt]['model'],
        'k': k_opt,
        'metrics': {k: models[k]['silhouette'] for k in models}
    }
```

### **3. Créer des Tests de Parity**

```python
# tests/test_feature_parity.py

def test_features_match_notebook():
    """Vérifier que engineering.py reproduit le notebook."""
    
    df = load_data('data/base_final.csv')
    
    # Pipeline notebook
    notebook_features = load_notebook_features('data/notebook_features.csv')
    
    # Pipeline engineering.py
    engineer = FeatureEngineer()
    produced_features = engineer.engineer_features_for_clustering(df)
    
    # Assertions
    assert len(produced_features) == len(notebook_features)
    assert list(produced_features.columns) == notebook_features.columns
    pd.testing.assert_frame_equal(produced_features, notebook_features, atol=0.01)
```

---

## 📊 TABLEAU RÉSUMÉ FINAL

| Étape | Notebook | engineering.py | Status |
|---|---|---|---|
| **Chargement données** | ✅ | ✅ | Identique |
| **Agrégation RFM** | ✅ | ✅ | Identique |
| **Livraison** | ✅ | ✅ | Identique |
| **Satisfaction** | ✅ | ✅ | Identique |
| **Log Transform** | ✅ | ❌ | **À AJOUTER** |
| **Bucketing** | ✅ | ❌ | **À AJOUTER** |
| **Composites** | ✅ | ❌ | **À AJOUTER** |
| **Feature Selection** | ✅ (7 actives) | ❌ (14+ brutes) | **À AJOUTER** |
| **Standardisation** | ✅ | ❌ | **À AJOUTER** |
| **PCA Whitening** | ✅ (5D) | ❌ | **À AJOUTER** |
| **Clustering** | ✅ KMeans k=4-8 | ❌ Absent | **À AJOUTER** |
| **Évaluation (Silhouette, DB, CH)** | ✅ | ❌ | **À AJOUTER** |

---

## 🎯 CONCLUSION

**Le code engineering.py produit les fondations (features brutes) mais manque TOUTES les transformations avancées du notebook.**

**Étapes critiques à intégrer** :
1. ✅ Log transformations (4 features)
2. ✅ Bucketing (2 features)
3. ✅ Sélection de 7 features finales (vs 14+ brutes)
4. ✅ Standardisation + PCA whitening
5. ✅ Clustering KMeans avec sélection k

**Impact** : Sans ces étapes, les clusters produits ne seront PAS identiques au notebook.

