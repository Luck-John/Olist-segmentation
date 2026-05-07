# 🔴 ACTIONS À PRENDRE : Pipeline Divergence Resolution

## 📌 PROBLÈME PRINCIPAL

**Le notebook produit 7 features finales transformées pour le clustering, tandis que engineering.py produit 14+ features brutes sans transformations.**

Cette divergence implique que les modèles produits seront différents et que la segmentation client ne sera pas reproductible.

---

## 🎯 PLAN D'ACTION PRIORISÉ

### **PRIORITÉ 1 - CRITIQUE (Faire maintenant)**

#### 1.1 Créer `src/clustering/preprocessing.py`

Ajouter une classe pour les transformations manquantes :

```python
# src/clustering/preprocessing.py

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

class ClusteringPreprocessor:
    """
    Reproduire exactement le preprocessing du notebook Modélisons.ipynb
    """
    
    FEATURES_FINAL = [
        "log_recency",
        "recency_score_10", 
        "log_monetary",
        "log_item_price",
        "installment_level",
        "review_raw",
        "log_delivery",
    ]
    
    def __init__(self, random_state=42):
        self.random_state = random_state
        self.scaler = None
        self.pca = None
        
    def apply_log_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply LOG1P transformations to Recency Monetary etc."""
        df = df.copy()
        
        # Log transformations
        df["log_recency"] = np.log1p(df["Recency"])
        df["log_monetary"] = np.log1p(df["Monetary"])
        df["log_item_price"] = np.log1p(df["avg_item_price"])
        df["log_delivery"] = np.log1p(df["avg_delivery_days"])
        
        return df
    
    def apply_bucketing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply bucketing transformations."""
        df = df.copy()
        
        # Recency score (10 levels)
        df["recency_score_10"] = (
            10 - pd.qcut(df["Recency"], q=10, labels=False, duplicates="drop")
        ).astype("float32")
        
        # Installment level (4 levels)
        df["installment_level"] = pd.cut(
            df["avg_installments"],
            bins=[-0.1, 1.0, 3.0, 6.0, 100.0],
            labels=[0, 1, 2, 3]
        ).astype("float32")
        
        # Review raw (clip to 1-5)
        df["review_raw"] = df["avg_review_score"].clip(1, 5).astype("float32")
        
        return df
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all transformations: log, bucketing, selection."""
        df = self.apply_log_transforms(df)
        df = self.apply_bucketing(df)
        return df[self.FEATURES_FINAL]
    
    def fit_preprocessing(self, X: pd.DataFrame) -> np.ndarray:
        """
        Fit scaler and PCA on training data.
        
        Args:
            X: DataFrame with FEATURES_FINAL (7 columns)
        
        Returns:
            Transformed array (n, 5) after PCA
        """
        # Cap outliers to 99th percentile
        X_capped = X.copy()
        for col in X.columns:
            q99 = X_capped[col].quantile(0.99)
            q01 = X_capped[col].quantile(0.01)
            X_capped[col] = X_capped[col].clip(lower=q01, upper=q99)
        
        # Standardize
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X_capped)
        
        # PCA with whitening
        self.pca = PCA(n_components=5, whiten=True, random_state=self.random_state)
        X_pca = self.pca.fit_transform(X_scaled)
        
        return X_pca
    
    def transform_features(self, X: pd.DataFrame) -> np.ndarray:
        """Apply preprocessing to new data."""
        if self.scaler is None or self.pca is None:
            raise ValueError("Preprocessor not fitted. Call fit_preprocessing first.")
        
        X_capped = X.copy()
        for col in X.columns:
            q99 = self.scaler.data_max_  # Use fitted statistics if available
            q01 = self.scaler.data_min_
            X_capped[col] = X_capped[col].clip(lower=q01, upper=q99)
        
        X_scaled = self.scaler.transform(X_capped)
        X_pca = self.pca.transform(X_scaled)
        
        return X_pca


if __name__ == "__main__":
    from src.features.engineering import FeatureEngineer
    from src.data.preprocessing import load_data
    
    # Load data
    df = load_data("data/base_final.csv")
    
    # Engineer features (produces 14+ features)
    engineer = FeatureEngineer()
    df_features = engineer.engineer_features(df)
    
    # Preprocess for clustering (selects 7, transforms, scales, PCA)
    prep = ClusteringPreprocessor()
    X_final = prep.prepare_features(df_features)
    X_pca = prep.fit_preprocessing(X_final)
    
    print(f"Final shape: {X_pca.shape}")  # Should be (52636, 5)
```

---

#### 1.2 Créer `src/clustering/clustering.py`

Ajouter une classe pour le clustering :

```python
# src/clustering/clustering.py

import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics import silhouette_score davies_bouldin_score calinski_harabasz_score
import pickle

class CustomerSegmenter:
    """
    Segment customers using KMeans on PCA-transformed features.
    Reproduces clustering from Modélisons.ipynb
    """
    
    K_RANGE = range(4, 9)  # Business requirement: 4-8 clusters
    
    def __init__(self, random_state=42):
        self.random_state = random_state
        self.models = {}  # {k: {model, labels, metrics}}
        self.k_optimal = None
        self.segment_names = {}
        
    def fit(self, X_pca: np.ndarray) -> dict:
        """
        Find optimal number of clusters using Silhouette score.
        
        Args:
            X_pca: Preprocessed PCA data (n, 5)
        
        Returns:
            Dict with metrics for each k
        """
        results = {}
        
        for k in self.K_RANGE:
            # Train KMeans
            km = MiniBatchKMeans(
                n_clusters=k,
                batch_size=4096,
                n_init=10,
                max_iter=300,
                random_state=self.random_state
            )
            labels = km.fit_predict(X_pca)
            
            # Compute metrics
            silhouette = silhouette_score(X_pca, labels)
            davies_bouldin = davies_bouldin_score(X_pca, labels)
            calinski_harabasz = calinski_harabasz_score(X_pca, labels)
            
            self.models[k] = {
                "model": km,
                "labels": labels,
                "silhouette": silhouette,
                "davies_bouldin": davies_bouldin,
                "calinski_harabasz": calinski_harabasz,
            }
            
            results[k] = {
                "silhouette": silhouette,
                "davies_bouldin": davies_bouldin,
                "calinski_harabasz": calinski_harabasz,
            }
            
            print(f"k={k} | Silhouette={silhouette:.4f} | DB={davies_bouldin:.4f}")
        
        # Select optimal k (maximum silhouette)
        self.k_optimal = max(self.models, key=lambda k: self.models[k]["silhouette"])
        print(f"\n✅ Optimal k = {self.k_optimal}")
        
        return results
    
    def get_labels(self) -> np.ndarray:
        """Get cluster labels for optimal k."""
        if self.k_optimal is None:
            raise ValueError("Model not fitted. Call fit() first.")
        return self.models[self.k_optimal]["labels"]
    
    def get_metrics(self) -> dict:
        """Get metrics for optimal k."""
        if self.k_optimal is None:
            raise ValueError("Model not fitted. Call fit() first.")
        return {
            "k": self.k_optimal,
            **self.models[self.k_optimal]
        }
    
    def save(self, filepath: str):
        """Save fitted model to pickle."""
        with open(filepath, "wb") as f:
            pickle.dump({
                "models": self.models,
                "k_optimal": self.k_optimal,
                "segment_names": self.segment_names,
            }, f)
        print(f"✅ Model saved to {filepath}")


if __name__ == "__main__":
    from src.clustering.preprocessing import ClusteringPreprocessor
    from src.features.engineering import FeatureEngineer
    from src.data.preprocessing import load_data
    
    # Pipeline
    df = load_data("data/base_final.csv")
    engineer = FeatureEngineer()
    df_features = engineer.engineer_features(df)
    
    prep = ClusteringPreprocessor()
    X_final = prep.prepare_features(df_features)
    X_pca = prep.fit_preprocessing(X_final)
    
    segmenter = CustomerSegmenter()
    results = segmenter.fit(X_pca)
    labels = segmenter.get_labels()
    
    print(f"\nSegmentation complete. Labels shape: {labels.shape}")
    print(f"Cluster distribution:\n{pd.Series(labels).value_counts().sort_index()}")
```

---

#### 1.3 Modifier `src/features/engineering.py`

Ajouter une méthode pour compatibilité clustering :

```python
# Dans la classe FeatureEngineer, ajouter:

def engineer_features_for_clustering(self, df: pd.DataFrame) -> pd.DataFrame:
    """
    Extended engineering: add transformations needed for clustering.
    
    Returns:
        DataFrame with 7 features ready for clustering
    """
    # First do standard engineering
    df_client = self.engineer_features(df)
    
    # Then apply clustering-specific transformations
    from src.clustering.preprocessing import ClusteringPreprocessor
    
    prep = ClusteringPreprocessor()
    # Ensure required columns exist
    required = ["Recency", "Monetary", "avg_item_price", "avg_delivery_days", "avg_review_score", "avg_installments"]
    for col in required:
        if col not in df_client.columns:
            raise ValueError(f"Missing required column: {col}")
    
    # Apply transformations
    df_transformed = prep.apply_log_transforms(df_client)
    df_transformed = prep.apply_bucketing(df_transformed)
    
    return df_transformed[ClusteringPreprocessor.FEATURES_FINAL]
```

---

### **PRIORITÉ 2 - IMPORTANT (Cette semaine)**

#### 2.1 Créer tests de parity

```python
# tests/test_clustering_parity.py

import pytest
import pandas as pd
import numpy as np
from src.clustering.preprocessing import ClusteringPreprocessor
from src.clustering.clustering import CustomerSegmenter
from src.features.engineering import FeatureEngineer
from src.data.preprocessing import load_data


class TestClusteringParity:
    """Verify pipeline matches notebook results"""
    
    def test_features_final_count(self):
        """Check we have exactly 7 features for clustering"""
        df = load_data("data/base_final.csv")
        engineer = FeatureEngineer()
        df_features = engineer.engineer_features(df)
        
        prep = ClusteringPreprocessor()
        X_final = prep.prepare_features(df_features)
        
        assert X_final.shape[1] == 7, f"Expected 7 features, got {X_final.shape[1]}"
        assert list(X_final.columns) == prep.FEATURES_FINAL
    
    def test_pca_output_shape(self):
        """Check PCA output is (n, 5)"""
        df = load_data("data/base_final.csv")
        engineer = FeatureEngineer()
        df_features = engineer.engineer_features(df)
        
        prep = ClusteringPreprocessor()
        X_final = prep.prepare_features(df_features)
        X_pca = prep.fit_preprocessing(X_final)
        
        assert X_pca.shape[1] == 5, f"Expected 5 PCA components, got {X_pca.shape[1]}"
    
    def test_clustering_k_range(self):
        """Check clustering tries k=4-8"""
        df = load_data("data/base_final.csv")
        engineer = FeatureEngineer()
        df_features = engineer.engineer_features(df)
        
        prep = ClusteringPreprocessor()
        X_final = prep.prepare_features(df_features)
        X_pca = prep.fit_preprocessing(X_final)
        
        segmenter = CustomerSegmenter()
        results = segmenter.fit(X_pca)
        
        assert 4 <= segmenter.k_optimal <= 8
        assert len(results) == 5  # k = 4,5,6,7,8
    
    def test_reproducibility(self):
        """Check same seed produces same results"""
        df = load_data("data/base_final.csv")
        engineer = FeatureEngineer()
        df_features = engineer.engineer_features(df)
        
        # Run 1
        prep1 = ClusteringPreprocessor(random_state=42)
        X_final1 = prep1.prepare_features(df_features)
        X_pca1 = prep1.fit_preprocessing(X_final1)
        segmenter1 = CustomerSegmenter(random_state=42)
        results1 = segmenter1.fit(X_pca1)
        labels1 = segmenter1.get_labels()
        
        # Run 2
        prep2 = ClusteringPreprocessor(random_state=42)
        X_final2 = prep2.prepare_features(df_features)
        X_pca2 = prep2.fit_preprocessing(X_final2)
        segmenter2 = CustomerSegmenter(random_state=42)
        results2 = segmenter2.fit(X_pca2)
        labels2 = segmenter2.get_labels()
        
        # Check reproducibility
        assert segmenter1.k_optimal == segmenter2.k_optimal
        np.testing.assert_array_equal(labels1, labels2)
```

---

#### 2.2 Créer fichier de configuration

```yaml
# config/clustering.yaml

clustering:
  k_min: 4
  k_max: 8
  
  preprocessing:
    random_state: 42
    outlier_percentile: 99
    pca_components: 5
    pca_whiten: true
  
  kmeans:
    batch_size: 4096
    n_init: 10
    max_iter: 300
    
  features_final:
    - log_recency
    - recency_score_10
    - log_monetary
    - log_item_price
    - installment_level
    - review_raw
    - log_delivery

feature_engineering:
  log_transforms:
    - Recency
    - Monetary
    - avg_item_price
    - avg_delivery_days
  
  bucketing:
    recency_score_10:
      q: 10
    installment_level:
      bins: [-0.1, 1.0, 3.0, 6.0, 100.0]
```

---

### **PRIORITÉ 3 - BON À SAVOIR (Documenter)**

#### 3.1 Documenter les différences

Fichier `DIFFERENCES.md` existe déjà → à jour ! ✅

#### 3.2 Comparer métriques

```python
# scripts/compare_pipelines.py

def compare_notebook_vs_production():
    """Generate comparison report"""
    
    print("\n📊 PIPELINE COMPARISON")
    print("=" * 80)
    
    # Load data
    df = load_data("data/base_final.csv")
    
    # ====== ENGINEERING ======
    engineer = FeatureEngineer()
    df_eng = engineer.engineer_features(df)
    
    print(f"\n[ENGINEERING.PY OUTPUT]")
    print(f"  Features produced: {len(df_eng.columns)}")
    print(f"  Features: {', '.join(df_eng.columns[:5])}...")
    print(f"  Shape: {df_eng.shape}")
    
    # ====== CLUSTERING PREPROCESSING ======
    prep = ClusteringPreprocessor()
    X_final = prep.prepare_features(df_eng)
    
    print(f"\n[CLUSTERING PREPROCESSING]")
    print(f"  Features after selection: {len(X_final.columns)}")
    print(f"  Features: {list(X_final.columns)}")
    print(f"  Shape: {X_final.shape}")
    
    X_pca = prep.fit_preprocessing(X_final)
    
    print(f"\n[AFTER PCA + WHITENING]")
    print(f"  Components: {X_pca.shape[1]}")
    print(f"  Variance retained: {np.sum(prep.pca.explained_variance_ratio_):.1%}")
    
    # ====== CLUSTERING ======
    segmenter = CustomerSegmenter()
    results = segmenter.fit(X_pca)
    labels = segmenter.get_labels()
    
    print(f"\n[CLUSTERING]")
    print(f"  Optimal k: {segmenter.k_optimal}")
    metrics = segmenter.get_metrics()
    print(f"  Silhouette: {metrics['silhouette']:.4f}")
    print(f"  Davies-Bouldin: {metrics['davies_bouldin']:.4f}")
    print(f"  Cluster dist:")
    dist = pd.Series(labels).value_counts().sort_index()
    for cid, n in dist.items():
        pct = n / len(labels) * 100
        print(f"    C{cid}: {n:6d} ({pct:5.1f}%)")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    compare_notebook_vs_production()
```

---

## 📋 CHECKLIST D'IMPLÉMENTATION

- [ ] **Créer `src/clustering/preprocessing.py`** (ClusteringPreprocessor class)
  - [ ] Implémenter `apply_log_transforms()`
  - [ ] Implémenter `apply_bucketing()`
  - [ ] Implémenter `prepare_features()`
  - [ ] Implémenter `fit_preprocessing()` et `transform_features()`
  
- [ ] **Créer `src/clustering/clustering.py`** (CustomerSegmenter class)
  - [ ] Implémenter `fit()` sur k=4-8
  - [ ] Implémenter calcul de métriques (Silhouette, DB, CH)
  - [ ] Implémenter sélection k automatique
  
- [ ] **Modifier `src/features/engineering.py`**
  - [ ] Ajouter `engineer_features_for_clustering()`
  
- [ ] **Créer tests** (`tests/test_clustering_parity.py`)
  - [ ] Test shape features finales
  - [ ] Test PCA output
  - [ ] Test k_optimal range
  - [ ] Test reproducibility
  
- [ ] **Créer `config/clustering.yaml`**
  
- [ ] **Créer `scripts/compare_pipelines.py`**
  - [ ] Générer rapport de comparaison
  
- [ ] **Documenter dans README.md**
  - [ ] Pipeline étapes
  - [ ] Comment utiliser les classes
  - [ ] Différences notebook vs production
  
- [ ] **Tester sur données réelles**
  - [ ] Vérifier que clusters = notebook
  - [ ] Comparer métrique Silhouette
  - [ ] Vérifier distribution clients par cluster

---

## 🚀 UTILISATION PRÉVUE

```python
# Pipeline complet reproduisant le notebook:

from src.data.preprocessing import load_data
from src.features.engineering import FeatureEngineer
from src.clustering.preprocessing import ClusteringPreprocessor
from src.clustering.clustering import CustomerSegmenter

# Load
df = load_data("data/base_final.csv")

# Engineer
engineer = FeatureEngineer()
df_features = engineer.engineer_features(df)

# Preprocess for clustering
prep = ClusteringPreprocessor()
X_final = prep.prepare_features(df_features)
X_pca = prep.fit_preprocessing(X_final)

# Segment
segmenter = CustomerSegmenter()
segmenter.fit(X_pca)
labels = segmenter.get_labels()

# Result
print(f"Segmentation complete: {segmenter.k_optimal} clusters")
```

---

## ⏱️ ESTIMATION TEMPS

| Tâche | Temps | Priorité |
|---|---|---|
| Créer preprocessing.py | 1h | 🔴 P1 |
| Créer clustering.py | 1h | 🔴 P1 |
| Modifier engineering.py | 30min | 🔴 P1 |
| Créer tests | 1h | 🟠 P2 |
| Créer config YAML | 30min | 🟠 P2 |
| Tester parity | 1h | 🟠 P2 |
| **TOTAL** | **≈ 5h** | **This week** |

---

## ✅ VALIDATION FINALE

Après implémentation, vérifier :
1. ✅ Shape features = 7 finales
2. ✅ Shape PCA = (n, 5)
3. ✅ Silhouette proche du notebook (±0.01)
4. ✅ Distribution clusters identique
5. ✅ k_optimal = k du notebook
6. ✅ Tests tous passent
7. ✅ Reproducible avec seed=42

