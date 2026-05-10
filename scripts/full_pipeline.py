# ============================================================
# FULL SEGMENTATION PIPELINE — FINAL VERSION
# ============================================================
# Utilise les 5 features actives du notebook Final.ipynb
# Pipeline: Cap → QuantileTransformer → StandardScaler → PCA → KMeans
# ============================================================

import os
import sys
import numpy as np
import pandas as pd
import pickle
import json
from datetime import datetime

# Sklearn imports
from sklearn.preprocessing import StandardScaler, QuantileTransformer
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

# ============================================================
# CONFIGURATION
# ============================================================
RANDOM_STATE = 42
K_MIN, K_MAX = 4, 6
K_RANGE = range(K_MIN, K_MAX + 1)

# 5 Features actives (from Final.ipynb)
FEATURES_ACTIVE = [
    "Recency",
    "avg_review_score_full",
    "avg_delivery_days",
    "avg_installments",
    "CLV_estimate"
]

# Noms des segments basés sur l'analyse des profils médians
SEGMENT_NAMES = {
    0: "Acheteurs Valeur Moyenne",
    1: "Clients Satisfaits Ponctuels",
    2: "Nouveaux Clients Recents",
    3: "Clients Decus",
    4: "Clients Fideles Premium"
}

SEGMENT_ACTIONS = {
    0: "Cross-selling et programme de fidelite",
    1: "Incitation au reachat et montee en gamme",
    2: "Programme d'accueil et recommandations",
    3: "Suivi SAV et amelioration livraison",
    4: "Programme VIP et offres exclusives"
}

print("=" * 70)
print("FULL SEGMENTATION PIPELINE")
print("=" * 70)

# ============================================================
# STEP 1: LOAD DATA
# ============================================================
print("\n[1/7] Loading data...")
df = pd.read_csv("data/Base.csv", low_memory=False)
print(f"    OK Loaded: {df.shape[0]:,} customers, {df.shape[1]} columns")

# ============================================================
# STEP 2: SELECT FEATURES & CHECK
# ============================================================
print("\n[2/7] Selecting features...")
missing = [f for f in FEATURES_ACTIVE if f not in df.columns]
if missing:
    print(f"    OK Missing features: {missing}")
    sys.exit(1)

X_raw = df[FEATURES_ACTIVE].copy()
print(f"    OK Selected {len(FEATURES_ACTIVE)} features")
print(f"       Features: {', '.join(FEATURES_ACTIVE)}")

# Check for NaN
nan_count = X_raw.isna().sum().sum()
if nan_count > 0:
    print(f"    OK Found {nan_count} NaN values - filling with median")
    for col in X_raw.columns:
        X_raw[col] = X_raw[col].fillna(X_raw[col].median())

# ============================================================
# STEP 3: CAP OUTLIERS (1% - 99%)
# ============================================================
print("\n[3/7] Capping outliers (1%-99%)...")
X_capped = X_raw.copy()
for col in X_capped.columns:
    q1, q99 = X_capped[col].quantile([0.01, 0.99])
    X_capped[col] = X_capped[col].clip(lower=q1, upper=q99)
print(f"    OK Outliers capped")

# ============================================================
# STEP 4: QUANTILE TRANSFORMER
# ============================================================
print("\n[4/7] Applying QuantileTransformer...")
qt = QuantileTransformer(
    output_distribution="normal",
    n_quantiles=min(1000, len(X_capped)),
    random_state=RANDOM_STATE
)
X_qt = qt.fit_transform(X_capped)
X_qt = pd.DataFrame(X_qt, columns=FEATURES_ACTIVE)
print(f"    OK QuantileTransformer fitted")

# ============================================================
# STEP 5: STANDARD SCALER
# ============================================================
print("\n[5/7] Applying StandardScaler...")
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_qt)
X_scaled = pd.DataFrame(X_scaled, columns=FEATURES_ACTIVE)
print(f"    OK StandardScaler fitted")

# ============================================================
# STEP 6: PCA (85% VARIANCE, WHITEN=TRUE)
# ============================================================
print("\n[6/7] PCA with whitening (85% variance)...")

# First: diagnostic PCA to find N_COMP
pca_diag = PCA(n_components=len(FEATURES_ACTIVE), random_state=RANDOM_STATE)
pca_diag.fit(X_scaled)
cumvar = np.cumsum(pca_diag.explained_variance_ratio_)

# Find N_COMP for 85% variance
N_COMP = int(np.argmax(cumvar >= 0.85)) + 1
print(f"    Info: {N_COMP} components capture 85% of variance")

# Print variance distribution
for i, (ev, cv) in enumerate(zip(pca_diag.explained_variance_ratio_[:N_COMP], cumvar[:N_COMP])):
    print(f"       PC{i+1}: {ev:.4f} (cumulative: {cv:.4f})")

# Final PCA with whitening
pca_final = PCA(n_components=N_COMP, whiten=True, random_state=RANDOM_STATE)
X_pca = pca_final.fit_transform(X_scaled)
print(f"    OK PCA fitted: {X_pca.shape}")

# ============================================================
# STEP 7: KMEANS K=4-6, SELECT BEST K
# ============================================================
print("\n[7/7] KMeans clustering (k=4-6)...")

kmeans_models = {}
results = []

# Sample for metrics calculation
SAMPLE_SIZE = min(50000, len(X_pca))
idx_sample = np.random.choice(len(X_pca), SAMPLE_SIZE, replace=False)
X_sample = X_pca[idx_sample]

for k in K_RANGE:
    print(f"    KMeans k={k}...", end=" ")
    
    km = KMeans(
        n_clusters=k,
        init="k-means++",
        n_init=10,
        max_iter=300,
        random_state=RANDOM_STATE
    )
    
    labels = km.fit_predict(X_pca)
    labels_sample = labels[idx_sample]
    
    # Metrics
    sil = silhouette_score(X_sample, labels_sample)
    db = davies_bouldin_score(X_sample, labels_sample)
    ch = calinski_harabasz_score(X_sample, labels_sample)
    
    kmeans_models[k] = {
        "model": km,
        "labels": labels,
        "metrics": {"silhouette": sil, "davies_bouldin": db, "calinski_harabasz": ch}
    }
    
    results.append({
        "k": k,
        "silhouette": sil,
        "davies_bouldin": db,
        "calinski_harabasz": ch
    })
    
    # Distribution
    unique, counts = np.unique(labels, return_counts=True)
    dist_str = " | ".join([f"C{c}:{n:,}" for c, n in zip(unique, counts)])
    
    print(f"sil={sil:.4f} | {dist_str}")

# Select best K by silhouette
results_df = pd.DataFrame(results)
best_idx = results_df["silhouette"].idxmax()
BEST_K = int(results_df.iloc[best_idx]["k"])
best_silhouette = results_df.iloc[best_idx]["silhouette"]

print(f"\n    OK Best K: {BEST_K} (silhouette={best_silhouette:.4f})")

# ============================================================
# SAVE PROCESSED BASE (BEFORE MODELING)
# ============================================================
print("\n[SAVE] Saving processed base before modeling...")
base_pip_file = "data/Base_pip.csv"
df.to_csv(base_pip_file, index=False)
print(f"    OK Base pip saved: {base_pip_file}")

# ============================================================
# PREPARE FINAL OUTPUTS
# ============================================================
print("\n" + "=" * 70)
print("SAVING PIPELINE & RESULTS")
print("=" * 70)

FINAL_MODEL = kmeans_models[BEST_K]["model"]
FINAL_LABELS = kmeans_models[BEST_K]["labels"]

# Add clusters to original dataframe
df["cluster"] = FINAL_LABELS
df["cluster_count"] = len(np.unique(FINAL_LABELS))

# Map cluster to segment name
df["segment_name"] = df["cluster"].map(lambda c: SEGMENT_NAMES.get(c, f"Cluster {c}"))
df["segment_action"] = df["cluster"].map(lambda c: SEGMENT_ACTIONS.get(c, "No action"))

# Get PCA coordinates (for visualization)
pca_2d = PCA(n_components=2, random_state=RANDOM_STATE)
X_pca_2d = pca_2d.fit_transform(X_scaled)
df["pca_1"] = X_pca_2d[:, 0]
df["pca_2"] = X_pca_2d[:, 1]

# ============================================================
# SAVE RESULTS TO CSV
# ============================================================
output_file = "notebooks/reports/segmentation_finale_olist.csv"
df.to_csv(output_file, index=False)
print(f"\nOK Segmentation saved: {output_file}")

# Cluster profiles
cluster_profiles_mean = df.groupby("cluster")[FEATURES_ACTIVE].mean()
cluster_profiles_mean.to_csv("notebooks/reports/cluster_profiles_mean.csv")
print(f"OK Cluster profiles (mean): notebooks/reports/cluster_profiles_mean.csv")

cluster_profiles_median = df.groupby("cluster")[FEATURES_ACTIVE].median()
cluster_profiles_median.to_csv("notebooks/reports/cluster_profiles_median.csv")
print(f"OK Cluster profiles (median): notebooks/reports/cluster_profiles_median.csv")

# ============================================================
# SAVE PIPELINE COMPONENTS
# ============================================================
output_dir = "notebooks/models"
os.makedirs(output_dir, exist_ok=True)

pipeline_dict = {
    "model": FINAL_MODEL,
    "scaler": scaler,
    "quantile_transformer": qt,
    "pca": pca_final,
    "feature_cols": FEATURES_ACTIVE,
    "cluster_names": {int(k): v for k, v in SEGMENT_NAMES.items()},
    "segment_actions": {int(k): v for k, v in SEGMENT_ACTIONS.items()},
    "best_k": int(BEST_K),
    "pca_2d": pca_2d,
    "n_comp": N_COMP
}

with open(f"{output_dir}/final_pipeline.pkl", "wb") as f:
    pickle.dump(pipeline_dict, f)
print(f"OK Pipeline saved: {output_dir}/final_pipeline.pkl")

# Save cluster names as JSON
with open(f"{output_dir}/cluster_names.json", "w") as f:
    json.dump(SEGMENT_NAMES, f, indent=2, ensure_ascii=False)
print(f"OK Cluster names saved: {output_dir}/cluster_names.json")

# ============================================================
# SAVE CLUSTERING COMPARISON
# ============================================================
results_df.to_csv("notebooks/reports/clustering_comparison.csv", index=False)
print(f"OK Clustering comparison: notebooks/reports/clustering_comparison.csv")

# ============================================================
# STATISTICS
# ============================================================
print("\n" + "=" * 70)
print("FINAL STATISTICS")
print("=" * 70)
print(f"\nTotal customers: {len(df):,}")
print(f"Number of clusters: {BEST_K}")
print(f"Number of features: {len(FEATURES_ACTIVE)}")

print(f"\nCluster distribution:")
for k in range(BEST_K):
    count = (FINAL_LABELS == k).sum()
    pct = 100 * count / len(df)
    name = SEGMENT_NAMES.get(k, f"Cluster {k}")
    print(f"  Cluster {k}: {count:>8,} customers ({pct:>5.1f}%) — {name}")

print(f"\nMetrics for best model (k={BEST_K}):")
metrics = kmeans_models[BEST_K]["metrics"]
print(f"  Silhouette Score:      {metrics['silhouette']:.4f}")
print(f"  Davies-Bouldin Score:  {metrics['davies_bouldin']:.4f}")
print(f"  Calinski-Harabasz:     {metrics['calinski_harabasz']:.2f}")

print("\n" + "=" * 70)
print("OK PIPELINE COMPLETED SUCCESSFULLY")
print("=" * 70)
print(f"\nAll outputs saved to:")
print(f"  - Data: notebooks/reports/")
print(f"  - Models: notebooks/models/")
print(f"\nStart API with: python scripts/api.py")
print("=" * 70)
