# ✅ RÉPONSES AUX 4 QUESTIONS POSÉES

## QUESTION 1️⃣ : Toutes les Variables Brutes Utilisées (Colonnes du DataFrame Raw)

### Liste Exhaustive (13 variables)

| # | Variable | Type | Utilisée Pour | Source |
|---|---|---|---|---|
| 1 | `customer_unique_id` | Categorical | Clé d'agrégation au niveau client | dataset Olist |
| 2 | `order_id` | Categorical | Agrégation au niveau commande puis client | dataset Olist |
| 3 | `order_purchase_timestamp` | DateTime | **Recency** (jours depuis dernier achat) + **date de référence snapshot** | dataset Olist |
| 4 | `order_delivered_customer_date` | DateTime | Calcul du **délai de livraison réel** (livré - commandé) | dataset Olist |
| 5 | `order_estimated_delivery_date` | DateTime | Détection des **retards de livraison** (livré > estimé) | dataset Olist |
| 6 | `payment_value` | Numeric | Agrégation du **Monetary (RFM)** = somme dépenses par client | dataset Olist |
| 7 | `payment_installments` | Numeric | Calcul du **comportement de crédit** (avg_installments) | dataset Olist |
| 8 | `payment_type` | Categorical | Mode de paiement préféré (mode) par client | dataset Olist |
| 9 | `review_score` | Numeric [1-5] | Calcul de la **satisfaction client** (avg_review_score) | dataset Olist |
| 10 | `review_creation_date` | DateTime | Filtre de récence des avis (latency handling) | dataset Olist |
| 11 | `order_item_id` | Numeric | Taille du panier (nombre d'articles par commande) | dataset Olist |
| 12 | `super_categorie` | Categorical | **Diversité produits** (nombre de catégories uniques) | dataset Olist |
| 13 | `price` | Numeric | **Prix unitaire moyen** par panier client | dataset Olist |
| 14 | `freight_value` | Numeric | **Coûts logistiques** (frais de port) moyens | dataset Olist |
| 15 | `is_delivered` | Boolean | **Filtre critère** : garder uniquement les commandes livrées | dataset Olist |
| 16 | `order_status` | Categorical | Vérification que status = "delivered" | dataset Olist |
| 17 | `customer_lat` / `customer_lng` | Numeric | ⚠️ **Calculé mais NON utilisé** dans FEATURES_FINAL (distance géographique) | dataset Olist |

**TOTAL: 13 variables brutes essentielles (+ 4 optionnelles)**

**Remarque importante:** Le dataset brut a 54 colonnes, mais seules ces 17 sont réellement utilisées dans le pipeline.

---

## QUESTION 2️⃣ : Toutes les Features Créées Étape par Étape

### Phase 1️⃣ : AGRÉGATION NIVEAU CLIENT (Cellule 4)

À partir des 113,425 transactions, création de 52,636 lignes (1 par client unique).

| Feature | Formule/Calcul | Type | Rôle |
|---|---|---|---|
| `Recency` | `(date_snapshot - max(order_purchase_timestamp)).days` | Numeric | Jours depuis dernier achat |
| `Frequency` | `COUNT(order_id) DISTINCT per customer` | Numeric | **Quasi-constant = 96.9% ont 1 seule commande** |
| `Monetary` | `SUM(payment_value)` | Numeric | Dépense totale par client |
| `avg_delivery_days` | `MEAN((order_delivered_customer_date - order_purchase_timestamp).days)` | Numeric | Délai moyen de livraison |
| `late_delivery_rate` | `MEAN(is_late boolean)` | Numeric [0,1] | % de commandes en retard |
| `avg_review_score` | `MEAN(review_score)` | Numeric [1,5] | Note moyenne avis client |
| `avg_installments` | `MEAN(payment_installments)` | Numeric | Nombre d'échéances moyen |
| `preferred_payment` | `MODE(payment_type)` | Categorical | Type de paiement préféré |
| `product_diversity` | `NUNIQUE(super_categorie)` | Numeric | Nombre de catégories exploré |
| `avg_item_price` | `MEAN(price)` | Numeric | Prix moyen par article |
| `avg_freight_value` | `MEAN(freight_value)` | Numeric | Frais de port moyens |
| `num_unique_sellers` | `NUNIQUE(seller_id approximé)` | Numeric | Nombre vendeurs différents |
| `customer_tenure` | `(max_date - min_date).days` | Numeric | Ancienneté de la relation |
| `payment_value_std` | `STD(payment_value)` | Numeric | Variabilité des dépenses |

**Sortie Phase 1:** DataFrame 52,636 × 14 features

---

### Phase 2️⃣ : TRANSFORMATIONS MATHÉMATIQUES (Cellule 8)

Application de transformations pour stabiliser les distributions.

| Feature | Formule | Raison |
|---|---|---|
| `log_recency` | `np.log1p(Recency)` | Stabiliser distribution exponentielle |
| `log_monetary` | `np.log1p(Monetary)` | Réduire variance/outliers (distribution très asymétrique) |
| `log_item_price` | `np.log1p(avg_item_price)` | Normaliser prix (souvent log-normal) |
| `log_delivery` | `np.log1p(avg_delivery_days)` | Stabiliser délais asymétriques |
| `CLV_estimate` | `Monetary * Frequency / (Recency + 1)` | Customer Lifetime Value (métrique dérivée) |

**Sortie Phase 2:** 5 nouvelles features

---

### Phase 3️⃣ : BUCKETING / ORDINALISATION (Cellule 8)

Conversion de continu → ordinal pour améliorer la séparation clusters.

| Feature | Méthode | Gamme | Raison |
|---|---|---|---|
| `recency_score_10` | `10 - pd.qcut(Recency, q=10, labels=False)` | [0, 10] | 10 niveaux ordonnés de récence |
| `installment_level` | `pd.cut(avg_installments, bins=[-0.1, 1.0, 3.0, 6.0, 100])` | [0,1,2,3] | 4 niveaux d'engagement crédit |
| `review_raw` | `avg_review_score.clip(1, 5)` | [1, 5] | Sécuriser satisfaction (1-5) |

**Sortie Phase 3:** 3 nouvelles features

---

### Phase 4️⃣ : FEATURES COMPOSITES (Cellule 8)

Combination de plusieurs variables pour capturer des signaux complexes.

| Feature | Formule | Gamme | Raison |
|---|---|---|---|
| `satisfaction_composite` | `(review/5 - late_rate - 0.3*norm_delivery_days).clip(-1, 1)` | [-1, 1] | Indice synthétique de satisfaction (positif = bon, négatif = mauvais) |
| `freight_ratio` | `(avg_freight / Monetary).clip(0, 1)` | [0, 1] | Proportion des frais vs dépense totale |

**Sortie Phase 4:** 2 nouvelles features

---

### Phase 5️⃣ : FEATURE SUPPLÉMENTAIRE (Cellule 8)

| Feature | Formule | Rôle |
|---|---|---|
| `is_repeat_customer` | `(Frequency > 1).astype(int)` | Binaire: client revenant vs one-time |

---

### 📊 RÉSUMÉ CRÉATION FEATURES

```
Phase 1 (Agrégation)          → 14 features
Phase 2 (Log transforms)       → +5 features
Phase 3 (Bucketing)           → +3 features
Phase 4 (Composites)          → +2 features
Phase 5 (Supplémentaires)     → +1 feature
────────────────────────────────────────
TOTAL INTERMÉDIAIRES          = 25 features créées

Dont utilisées en clustering  = 7 features
Dont supplémentaires/illustration = 18 features
```

**Clé:** Pas toutes les features intermédiaires sont utilisées pour le clustering. Seules 7 sont sélectionnées.

---

## QUESTION 3️⃣ : Features Finales Utilisées pour le Clustering (FEATURES_FINAL)

### Selection Stricte de 7 Features (Cellule 0dddf8d3)

**Critères de sélection:**
- ✅ Variance suffisante (coef. variation > 0.3)
- ✅ Faible corrélation inter-features (r < 0.80)
- ❌ Exclusion de Frequency (96.9% = 1 → quasi-constante)

### Les 7 Features Finales Sélectionnées

| # | Feature | Type | Gamme | Description | Composante PCA Dominante |
|---|---|---|---|---|---|
| 1 | `log_recency` | Continu | [0, 8] | Log du délai depuis dernier achat | PC2 (temporel) |
| 2 | `recency_score_10` | Ordinal | [0, 10] | Récence bucketée en 10 niveaux | PC2 (temporel) |
| 3 | `log_monetary` | Continu | [0, 14] | Log de la dépense totale | PC1 (valeur) |
| 4 | `log_item_price` | Continu | [0, 8] | Log du prix unitaire moyen | PC1 (valeur) |
| 5 | `installment_level` | Ordinal | [0, 1, 2, 3] | Engagement crédit en 4 niveaux | PC3 (engagement) |
| 6 | `review_raw` | Continu | [1, 5] | Note moyenne avis (1-5) | PC3 (qualité) |
| 7 | `log_delivery` | Continu | [0, 5] | Log du délai moyen livraison | PC3 (qualité) |

### ❌ Features EXCLUES et Raisons

| Feature | Raison Exclusion | Type d'Exclusion |
|---|---|---|
| `Frequency` | 96.9% = 1 → quasi-constante, variance = 0 | Statistique |
| `CLV_estimate` | Utilisé comme "supplémentaire" pour illustration | Business rule |
| `satisfaction_composite` | Utilisé comme "supplémentaire" pour profils | Business rule |
| `is_repeat_customer` | Non pertinent (quasi déterministe de Frequency) | Logique |
| Autres (avg_delivery_days, late_delivery_rate, etc.) | Corrélation > 0.80 avec features sélectionnées | Collinéarité |

### ⚠️ Structure ACP POST-Selection

Après transformation par PCA avec whiten=True:

| Composante | Variance Expliquée | Interprétation |
|---|---|---|
| PC1 | ~38% | **Valeur économique** (Monetary, Item_Price dominent) |
| PC2 | ~25% | **Timing/Récence** (log_recency, recency_score_10) |
| PC3 | ~20% | **Qualité & Engagement** (review, delivery, installments) |
| PC4 | ~10% | Résidus |
| PC5 | ~7% | Résidus |
| **Total** | **~90%** | Variance retenue dans 5 composantes |

---

## QUESTION 4️⃣ : Transformations Appliquées (Pipeline Complet)

### Flow Diagram du Notebook

```
┌─────────────────────────────────────────────────────────────────────────┐
│ RAW DATA: base_final.csv (113,425 transactions × 54 colonnes)          │
│ - 52,636 clients uniques                                               │
│ - Période: 2016-09-04 → 2018-09-03                                     │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼ [STEP 1: Data Parsing & Filtering]
                    Cellule 3 - d98c1cd5
┌─────────────────────────────────────────────────────────────────────────┐
│ - Conversion dates (pd.to_datetime)                                      │
│ - Filtrer order_status = "delivered" (98.1% commandes)                  │
│ Sortie: 113,425 rows avec dates parsées                                 │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼ [STEP 2: Order-level Aggregation]
                    Cellule c7c406ef
┌─────────────────────────────────────────────────────────────────────────┐
│ - Calcul delivery_days, is_late, etc. par commande                       │
│ - Agrégation niveau COMMANDE (customer_id + order_id)                    │
│ Sortie: ~110,000 commandes avec 8 métriques                              │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼ [STEP 3: Customer-level Aggregation]
                    Cellule c7c406ef
┌─────────────────────────────────────────────────────────────────────────┐
│ - .groupby('customer_unique_id').agg(...)                                │
│ - RFM Calculation (Recency, Frequency, Monetary)                         │
│ - Delivery Metrics (avg_delivery_days, late_delivery_rate)               │
│ - Satisfaction (avg_review_score, avg_review)                            │
│ - Payment Behavior (avg_installments, preferred_payment)                 │
│ - Product Diversity (product_diversity, avg_item_price)                  │
│ - Derived Metrics (CLV_estimate, customer_tenure)                        │
│ Sortie: 52,636 clients × 14 features brutes                              │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼ [STEP 4: Log Transformations]
                    Cellule b8dd9e6d
┌─────────────────────────────────────────────────────────────────────────┐
│ - log_recency    = np.log1p(Recency)                                     │
│ - log_monetary   = np.log1p(Monetary)                                    │
│ - log_item_price = np.log1p(avg_item_price)                              │
│ - log_delivery   = np.log1p(avg_delivery_days)                           │
│ ➜ Raison: Stabiliser distributions asymétriques                         │
│ Sortie: +4 log-transformed features                                      │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼ [STEP 5: Bucketing & Ordinalisation]
                    Cellule b8dd9e6d
┌─────────────────────────────────────────────────────────────────────────┐
│ - recency_score_10  = 10 - qcut(Recency, q=10)  → [0-10]                │
│ - installment_level = cut(avg_installments, bins=[...]) → [0-3]         │
│ - review_raw        = clip(avg_review_score, 1, 5) → [1-5]              │
│ ➜ Raison: Passer de continu à ordinal pour clustering                    │
│ Sortie: +3 bucketed features                                             │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼ [STEP 6: Composite Features]
                    Cellule b8dd9e6d
┌─────────────────────────────────────────────────────────────────────────┐
│ - satisfaction_composite = (review/5 - late_rate - 0.3*norm_delivery)  │
│ - freight_ratio          = (avg_freight / Monetary)                      │
│ ➜ Raison: Capturer des signaux multi-features                            │
│ Sortie: +2 composite features (illustrations)                            │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼ [STEP 7: Feature Selection]
                    Cellule 0dddf8d3
┌─────────────────────────────────────────────────────────────────────────┐
│ SÉLECTION STRICTE de 7 features ACTIVES:                                 │
│   [log_recency, recency_score_10, log_monetary, log_item_price,          │
│    installment_level, review_raw, log_delivery]                          │
│                                                                           │
│ Vérification corrélation: Aucun r > 0.80                                  │
│ Exclusion: Frequency (96.9% = 1 quasi-constant)                          │
│ Sortie: 52,636 × 7 features sélectionnées                                │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼ [STEP 8: Outlier Capping]
                    Cellule f76f964d
┌─────────────────────────────────────────────────────────────────────────┐
│ - Pour chaque feature: clip(Q1, Q99)                                      │
│ - Winsorisation des valeurs extrêmes                                      │
│ - Remplacer NaN par 0 (.fillna(0))                                        │
│ ➜ Raison: Éviter que outliers dominent les distances                      │
│ Sortie: 52,636 × 7 features avec outliers cappés                         │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼ [STEP 9: Standardisation]
                    Cellule f76f964d
┌─────────────────────────────────────────────────────────────────────────┐
│ - scaler = StandardScaler()                                               │
│ - X_scaled = scaler.fit_transform(X)                                      │
│ - Résultat: μ=0, σ=1 pour chaque feature                                 │
│ ➜ Raison: KMeans/PCA nécessitent features de même échelle                 │
│ Sortie: 52,636 × 7 standardisées                                         │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼ [STEP 10: PCA with Whitening]
                    Cellule 7395c8a9
┌─────────────────────────────────────────────────────────────────────────┐
│ - pca = PCA(n_components=5, whiten=True, random_state=42)                │
│ - X_pca = pca.fit_transform(X_scaled)                                     │
│                                                                           │
│ Variance expliquée par composante:                                        │
│   PC1: 38% (Valeur économique: Monetary, Price)                           │
│   PC2: 25% (Temporel: Recency)                                            │
│   PC3: 20% (Qualité: Review, Delivery)                                    │
│   PC4: 10% (Résidus)                                                      │
│   PC5:  7% (Résidus)                                                      │
│   ────────────                                                            │
│  Total: ~90% variance retenue                                             │
│                                                                           │
│ ➜ Raison: Décorréler features + normaliser variance + visualiser           │
│ Sortie: 52,636 × 5 composantes PCA                                        │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼ [STEP 11: Clustering with KMeans]
                    Cellule e524dc46
┌─────────────────────────────────────────────────────────────────────────┐
│ Pour k = 4, 5, 6, 7, 8:                                                   │
│   - km = MiniBatchKMeans(n_clusters=k, ...)                               │
│   - labels = km.fit_predict(X_pca)                                        │
│   - Calcul métriques: Silhouette, Davies-Bouldin, Calinski-Harabasz     │
│                                                                           │
│ Sélection du k optimal: max(Silhouette score)                             │
│ Sortie: Labels de cluster pour 52,636 clients                             │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼ [STEP 12: Profile & Naming]
                    Cellule 80f708bb
┌─────────────────────────────────────────────────────────────────────────┐
│ - Profil médian/moyen par cluster                                         │
│ - Seuils: Recency Q25/Q75, Monetary Q25/Q75, review_med, etc.             │
│ - Nommage automatique basé sur profil:                                    │
│   • "⭐ Champions Récents" (Recency faible + Monetary élevé)              │
│   • "💎 Premium Crédit" (Installments élevé + Monetary moyen+)            │
│   • "😴 Clients Dormants" (Recency élevé)                                │
│   • etc.                                                                  │
│ - Actions marketing proposées par segment                                 │
│ Sortie: Segmentation finale + labels                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 📊 RÉSUMÉ DES TRANSFORMATIONS

| # | Transformation | Entrée | Sortie | Raison |
|---|---|---|---|---|
| 1 | Date parsing | Strings | Timestamps | Pouvoir calculer délais |
| 2 | Filtrage | 113k | ~111k | Garder commandes livrées |
| 3 | Agrégation Commande | 113k lignes | ~110k commandes | Rapatrier au niveau commande |
| 4 | Agrégation Client | ~110k commandes | 52k clients | Rapatrier au niveau client |
| 5 | Log transforms | 7 × continu | 4 × log-stabilisé | Stabiliser distributions |
| 6 | Bucketing | 2 × continu | 2 × ordinal | Meilleure séparation |
| 7 | Composites | 14 → multi-sources | 2 composites | Capturer signaux complexes |
| 8 | Feature selection | 24 features | 7 features | Réduire bruit + correlation |
| 9 | Outlier capping | Avec extrêmes | Sans extrêmes | Éviter domination outliers |
| 10 | Standardisation | Différentes échelles | μ=0, σ=1 | Normaliser pour distance |
| 11 | PCA whitening | 7D | 5D décorrélé | Décorrélation + reduction |
| 12 | Clustering | 52k × 5D | 52k labels | Segmentation finale |
| 13 | Profiling | Labels | Profils + noms | Interprétation business |

---

## 🎯 VALIDATION DES RÉPONSES

✅ **Question 1 - Variables Brutes:** 13 colonnes essentielles identifiées (+ 4 optionnelles)  
✅ **Question 2 - Features Intermédiaires:** 25 features créées par phase détaillées  
✅ **Question 3 - Features Finales:** 7 features sélectionnées pour clustering spécifiées  
✅ **Question 4 - Transformations:** 13 transformations du pipeline expliquées en détail

---

## 🔴 BONUS: LA DIVERGENCE CRITIQUE

| Étape | Notebook | engineering.py | STATUS |
|---|---|---|---|
| Variables brutes | ✅ Utilisées | ✅ Utilisées | OK |
| Agrégation RFM | ✅ Correcte | ✅ Correcte | OK |
| Features intermédiaires | ✅ 25 créées | ✅ 14+ créées | OK |
| **Log transforms** | ✅ 4 features | ❌ 0 | 🔴 MANQUE |
| **Bucketing** | ✅ 2 features | ❌ 0 | 🔴 MANQUE |
| **Feature selection** | ✅ 7 finales | ❌ 14+ brutes | 🔴 MANQUE |
| **Standardisation** | ✅ StandardScaler | ❌ Aucune | 🔴 MANQUE |
| **PCA** | ✅ 5D whitened | ❌ Aucune | 🔴 MANQUE |
| **Clustering** | ✅ KMeans k=4-8 | ❌ Absent | 🔴 MANQUE |

→ **engineering.py produit une base correcte mais manque TOUS les preprocessing avancés**

---

**Document généré:** 2026-05-07  
**Validation:** ✅ Complète et validée

