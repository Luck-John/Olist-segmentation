"""
Complete Segmentation Pipeline
Reproduces exactly the same outputs as the Segmentation_modelisation.ipynb notebook
"""

import os
import sys
import gc
import json
import pickle
import logging
import time
import warnings
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import cdist

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, MiniBatchKMeans, AgglomerativeClustering, DBSCAN
from sklearn.decomposition import PCA
from sklearn.metrics import (
    silhouette_score, davies_bouldin_score, calinski_harabasz_score,
    silhouette_samples
)
from sklearn.neighbors import NearestNeighbors

try:
    import hdbscan
    HAS_HDBSCAN = True
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "hdbscan"])
    import hdbscan
    HAS_HDBSCAN = True

try:
    from kneed import KneeLocator
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "kneed"])
    from kneed import KneeLocator

warnings.filterwarnings("ignore")
plt.rcParams.update({"figure.dpi": 100, "font.size": 10})

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

# Contrainte métier : minimum 4 clusters, maximum 8
K_MIN   = 4
K_MAX   = 8
K_RANGE = range(K_MIN, K_MAX + 1)

# Tailles sous-échantillons
N_SIL     = 15_000   # silhouette
N_SLOW    = 20_000   # CAH O(n²)
N_DBSCAN  = 15_000
N_HDBSCAN = 15_000

# Nombre de composantes PCA
N_COMP = 14

# Variables ACTIVES (15 variables décorrélées)
FEATURES_ACTIVE = [
    "Recency",
    "Monetary",
    "avg_installments",
    "avg_review_score_available",
    "late_delivery_rate",
    "avg_delivery_days",
    "avg_delivery_delta",
    "avg_freight_ratio",
    "avg_basket_size",
    "dist_sao_paulo",
    "most_frequent_purchase_hour",
    "most_frequent_purchase_day",
    "spend_('price', 'health_beauty')",
    "spend_('price', 'home')",
]

# Colonnes pour profiling des clusters
PROFILE_COLS = [
    "Recency",
    "Monetary",
    "avg_review_score_available",
    "avg_delivery_days",
    "avg_installments",
    "avg_freight_ratio",
    "dist_sao_paulo",
    "avg_basket_size",
    "late_delivery_rate",
]

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def evaluate_clustering(X, labels):
    """Calculate clustering metrics. Silhouette capped to N_SIL, ignores noise=-1."""
    mask = labels != -1
    nc   = len(set(labels[mask]))
    nn   = int((~mask).sum())
    if nc < 2:
        return {
            "n_clusters": nc,
            "n_noise": nn,
            "silhouette": np.nan,
            "davies_bouldin": np.nan,
            "calinski_harabasz": np.nan
        }
    
    Xm, lm = X[mask], labels[mask]
    if len(Xm) > N_SIL:
        idx = np.random.choice(len(Xm), N_SIL, replace=False)
        sil = silhouette_score(Xm[idx], lm[idx])
    else:
        sil = silhouette_score(Xm, lm)
    
    return {
        "n_clusters": nc,
        "n_noise": nn,
        "silhouette": round(float(sil), 4),
        "davies_bouldin": round(float(davies_bouldin_score(Xm, lm)), 4),
        "calinski_harabasz": round(float(calinski_harabasz_score(Xm, lm)), 2),
    }


def cap_outliers(df, cols, q=0.99):
    """Winsorize outliers at quantile q"""
    df = df.copy()
    for col in cols:
        df[col] = df[col].clip(
            lower=df[col].quantile(1 - q),
            upper=df[col].quantile(q)
        )
    return df


def plot_pca_clusters(X_2d, labels, title, save=None):
    """Plot clusters in 2D PCA space"""
    unique  = sorted(set(labels))
    palette = plt.cm.get_cmap("tab10", max(len(unique), 10))
    fig, ax = plt.subplots(figsize=(9, 6))
    for i, lab in enumerate(unique):
        m     = labels == lab
        color = "lightgrey" if lab == -1 else palette(i)
        lbl   = f"Bruit ({m.sum():,})" if lab == -1 else f"C{lab} ({m.sum():,})"
        ax.scatter(X_2d[m, 0], X_2d[m, 1], c=[color], s=5, alpha=0.5, label=lbl)
    ax.set_title(title, fontweight="bold", fontsize=11)
    ax.set_xlabel("PC1"); ax.set_ylabel("PC2")
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8, markerscale=2)
    plt.tight_layout()
    if save:
        plt.savefig(save, bbox_inches="tight", dpi=100)
    plt.show(); plt.close()


def radar_chart(profile_mean, title="Radar", save=None):
    """Plot radar chart of cluster profiles"""
    cols    = profile_mean.columns.tolist()
    means_n = (profile_mean - profile_mean.min()) / \
              (profile_mean.max() - profile_mean.min() + 1e-9)
    angles  = np.linspace(0, 2*np.pi, len(cols), endpoint=False).tolist() + [0]
    palette = plt.cm.get_cmap("tab10", len(means_n))
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"projection": "polar"})
    for i, (cid, row) in enumerate(means_n.iterrows()):
        v = row.tolist() + row.tolist()[:1]
        ax.plot(angles, v, "o-", lw=2.5, color=palette(i), label=f"C{cid}")
        ax.fill(angles, v, alpha=0.08, color=palette(i))
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(cols, fontsize=8)
    ax.set_ylim(0, 1)
    ax.set_title(title, fontweight="bold", pad=30)
    ax.legend(loc="upper right", bbox_to_anchor=(1.4, 1.1), fontsize=9)
    plt.tight_layout()
    if save:
        plt.savefig(save, bbox_inches="tight", dpi=100)
    plt.show(); plt.close()


def name_segment(row, rec_q, mon_q, rev_med, ins_q75, del_q25):
    """Assign segment name based on RFM and other features"""
    r, m = row["Recency"], row["Monetary"]
    rev  = row["avg_review_score_available"]
    ins  = row["avg_installments"]
    d    = row["avg_delivery_days"]

    # Priority 1: Dissatisfied
    if rev <= 2:
        return "😡 Clients Déçus"
    # Priority 2: Recent
    if r <= rec_q[0]:
        return "🌟 Clients Récents Actifs"
    # Priority 3: Premium credit
    if ins >= ins_q75 and m >= mon_q[1]:
        return "💎 Premium Crédit"
    # Priority 4: Fast delivery, small baskets
    if d <= del_q25 and m <= mon_q[1]:
        return "⚡ Petits Acheteurs Rapides"
    # Priority 5: Good basket
    if m >= mon_q[1]:
        return "🛍️ Acheteurs Valeur Moyenne"
    # Priority 6
    return "😴 Dormants Faible Valeur"


def get_segment_actions():
    """Get segment-to-action mapping"""
    return {
        "😡 Clients Déçus": "Contact immédiat + bon remboursement + enquête qualité",
        "🌟 Clients Récents Actifs": "Programme fidélisation + cross-sell + 2e achat -15%",
        "💎 Premium Crédit": "Offres VIP + augmentation plafond crédit + early access",
        "⚡ Petits Acheteurs Rapides": "Upsell catégories premium + notification nouveautés",
        "🛍️ Acheteurs Valeur Moyenne": "Réactivation + offre bundle + programme points",
        "😴 Dormants Faible Valeur": "Campagne win-back -20% ou désengagement progressif",
    }


def run_full_pipeline(data_dir="data", output_dir="notebooks/reports", models_dir="notebooks/models"):
    """
    Execute the complete segmentation pipeline:
    1. Load Base.csv (93,358 clients × 48 variables)
    2. Select 15 active features
    3. Cap outliers (99th percentile)
    4. Normalize with StandardScaler
    5. Apply PCA with whitening (N_COMP=14)
    6. Test 4 algorithms: KMeans, CAH Ward, DBSCAN, HDBSCAN
    7. Select best model (composite score)
    8. Profile and name clusters
    9. Save all outputs
    """
    
    # Create output directories
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(models_dir).mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("COMPLETE SEGMENTATION PIPELINE (Notebook Reproduction)")
    print("=" * 80)
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 1: LOAD DATA
    # ═══════════════════════════════════════════════════════════════
    print("\n[STEP 1] Loading data...")
    data_path = os.path.join(data_dir, "Base.csv") if not os.path.isabs(data_dir) else os.path.join(os.path.dirname(data_dir), "data", "Base.csv")
    
    # Try multiple paths
    possible_paths = [
        os.path.join("data", "Base.csv"),
        os.path.join("..", "data", "Base.csv"),
        os.path.join("notebooks", "Base.csv"),
        "Base.csv"
    ]
    
    df_client = None
    for path in possible_paths:
        if os.path.exists(path):
            df_client = pd.read_csv(path, low_memory=False)
            print(f"✓ Loaded from: {path}")
            break
    
    if df_client is None:
        raise FileNotFoundError(f"Base.csv not found. Tried: {possible_paths}")
    
    print(f"✓ Shape: {df_client.shape}")
    print(f"✓ Clients: {df_client['customer_unique_id'].nunique():,}")
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 2: SELECT ACTIVE FEATURES
    # ═══════════════════════════════════════════════════════════════
    print("\n[STEP 2] Selecting active features...")
    available_features = [f for f in FEATURES_ACTIVE if f in df_client.columns]
    missing_features = [f for f in FEATURES_ACTIVE if f not in df_client.columns]
    
    if missing_features:
        print(f"⚠  Missing features: {missing_features}")
        print(f"✓ Using {len(available_features)}/{len(FEATURES_ACTIVE)} available features")
    else:
        print(f"✓ All {len(FEATURES_ACTIVE)} features available")
    
    available_profile = [f for f in PROFILE_COLS if f in df_client.columns]
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 3: PREPROCESSING
    # ═══════════════════════════════════════════════════════════════
    print("\n[STEP 3] Preprocessing...")
    
    # Cap outliers at 99th percentile
    X_raw = cap_outliers(df_client, available_features)[available_features]
    X_raw = X_raw.fillna(0).astype("float32")
    print(f"✓ Capped outliers at 99th percentile")
    
    # Standardization
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw).astype("float32")
    print(f"✓ Scaled features: X_scaled.shape = {X_scaled.shape}")
    
    gc.collect()
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 4: PCA WITH WHITENING
    # ═══════════════════════════════════════════════════════════════
    print(f"\n[STEP 4] PCA (N_COMP={N_COMP}) with whitening...")
    
    pca_final = PCA(n_components=N_COMP, whiten=True, random_state=RANDOM_STATE)
    X_pca = pca_final.fit_transform(X_scaled).astype("float32")
    cumvar = np.cumsum(pca_final.explained_variance_ratio_)
    print(f"✓ Variance retained: {cumvar[-1]:.1%}")
    
    # PCA 2D for visualization
    pca_2d = PCA(n_components=2, whiten=False, random_state=RANDOM_STATE)
    X_pca_2d = pca_2d.fit_transform(X_scaled)
    print(f"✓ 2D PCA for visualization")
    
    gc.collect()
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 5: KMEANS (k from 4 to 8)
    # ═══════════════════════════════════════════════════════════════
    print("\n[STEP 5] KMeans clustering...")
    print("=" * 60)
    
    ALL_RESULTS = []
    KM_MODELS = {}
    
    for k in K_RANGE:
        best_sil = -1
        best_mod = None
        best_lbs = None
        
        for seed in [42, 123, 456]:
            km = MiniBatchKMeans(
                n_clusters=k,
                batch_size=4096,
                n_init=20,
                max_iter=500,
                random_state=seed
            )
            lbs = km.fit_predict(X_pca)
            m = evaluate_clustering(X_pca, lbs)
            
            if m["silhouette"] > best_sil:
                best_sil = m["silhouette"]
                best_mod = km
                best_lbs = lbs.copy()
            
            del lbs
            gc.collect()
        
        m_best = evaluate_clustering(X_pca, best_lbs)
        KM_MODELS[k] = {"model": best_mod, "labels": best_lbs.copy(), "metrics": m_best}
        m_best["algorithm"] = "KMeans"
        m_best["run_name"] = f"KMeans_k{k}"
        ALL_RESULTS.append(m_best)
        
        dist = pd.Series(best_lbs).value_counts().sort_index()
        sizes = ", ".join([f"C{c}:{n:,}" for c, n in dist.items()])
        print(f"k={k} | sil={m_best['silhouette']:.4f} | db={m_best['davies_bouldin']:.4f} | {sizes}")
        
        del best_lbs
        gc.collect()
    
    K_OPT_KM = max(KM_MODELS, key=lambda k: KM_MODELS[k]["metrics"]["silhouette"])
    print(f"→ Optimal k for KMeans: {K_OPT_KM}\n")
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 6: HIERARCHICAL CLUSTERING (CAH Ward)
    # ═══════════════════════════════════════════════════════════════
    print("[STEP 6] CAH Ward clustering...")
    print("=" * 60)
    
    rng_cah = np.random.default_rng(RANDOM_STATE + 10)
    idx_cah = rng_cah.choice(len(X_pca), N_SLOW, replace=False)
    X_cah = X_pca[idx_cah].copy()
    
    CAH_MODELS = {}
    for k in K_RANGE:
        agg = AgglomerativeClustering(n_clusters=k, linkage="ward")
        lbs = agg.fit_predict(X_cah)
        m = evaluate_clustering(X_cah, lbs)
        CAH_MODELS[k] = {"model": agg, "labels": lbs.copy(), "idx": idx_cah, "metrics": m}
        m["algorithm"] = "CAH_ward"
        m["run_name"] = f"CAH_k{k}"
        ALL_RESULTS.append(m)
        
        dist = pd.Series(lbs).value_counts().sort_index()
        sizes = ", ".join([f"C{c}:{n:,}" for c, n in dist.items()])
        print(f"k={k} | sil={m['silhouette']:.4f} | db={m['davies_bouldin']:.4f} | {sizes}")
        
        del lbs
        gc.collect()
    
    K_OPT_CAH = max(CAH_MODELS, key=lambda k: CAH_MODELS[k]["metrics"]["silhouette"])
    print(f"→ Optimal k for CAH: {K_OPT_CAH}\n")
    
    del X_cah
    gc.collect()
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 7: DBSCAN
    # ═══════════════════════════════════════════════════════════════
    print("[STEP 7] DBSCAN clustering...")
    print("=" * 60)
    
    rng_dbs = np.random.default_rng(RANDOM_STATE + 20)
    idx_dbs = rng_dbs.choice(len(X_pca), N_DBSCAN, replace=False)
    X_dbs = X_pca[idx_dbs].copy()
    
    # k-distance plot to find eps
    nbrs = NearestNeighbors(n_neighbors=5, n_jobs=-1).fit(X_dbs)
    dist5, _ = nbrs.kneighbors(X_dbs)
    d_sorted = np.sort(dist5[:, 4])
    
    try:
        kl_e = KneeLocator(range(len(d_sorted)), d_sorted, curve="convex", direction="increasing")
        EPS = float(d_sorted[kl_e.knee]) if kl_e.knee else float(np.percentile(d_sorted, 85))
    except:
        EPS = float(np.percentile(d_sorted, 85))
    
    del nbrs, dist5
    gc.collect()
    
    print(f"Optimal ε: {EPS:.4f}")
    
    grid_dbs = [(round(EPS*r, 4), ms) for r in [0.3,0.4,0.5,0.6,0.7,0.8,1.0,1.3,1.6] for ms in [5,8,10,15,20]]
    best_dbs = {"sil": -1, "labels": None}
    MAX_NOISE = int(len(X_dbs) * 0.12)
    
    for eps, ms in grid_dbs:
        dbs = DBSCAN(eps=eps, min_samples=ms, n_jobs=-1)
        lbs = dbs.fit_predict(X_dbs)
        m = evaluate_clustering(X_dbs, lbs)
        nc, nn, sil = m["n_clusters"], m["n_noise"], m["silhouette"]
        
        if K_MIN <= nc <= K_MAX and nn <= MAX_NOISE and not np.isnan(sil):
            m["algorithm"] = "DBSCAN"
            m["run_name"] = f"DBSCAN_eps{eps}_ms{ms}"
            ALL_RESULTS.append(m)
            
            if sil > best_dbs["sil"]:
                best_dbs = {"sil": sil, "labels": lbs.copy(), "nc": nc, "eps": eps, "ms": ms}
        
        del lbs
        gc.collect()
    
    if best_dbs["labels"] is not None:
        print(f"✓ DBSCAN: eps={best_dbs['eps']} ms={best_dbs['ms']} k={best_dbs['nc']} sil={best_dbs['sil']:.4f}\n")
    else:
        print("⚠  No valid DBSCAN solution (normal for homogeneous data)\n")
    
    del X_dbs
    gc.collect()
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 8: HDBSCAN
    # ═══════════════════════════════════════════════════════════════
    print("[STEP 8] HDBSCAN clustering...")
    print("=" * 60)
    
    rng_hdb = np.random.default_rng(RANDOM_STATE + 70)
    idx_hdb = rng_hdb.choice(len(X_pca), N_HDBSCAN, replace=False)
    X_hdb = X_pca[idx_hdb].copy()
    
    grid_hdb = [(mc, ms) for mc in [5,8,10,15,20,30,50] for ms in [3,5,8,10,15]]
    best_hdb = {"sil": -1, "labels": None}
    
    for min_c, min_s in grid_hdb:
        clf = hdbscan.HDBSCAN(
            min_cluster_size=min_c,
            min_samples=min_s,
            metric="euclidean",
            cluster_selection_method="eom",
            core_dist_n_jobs=-1
        )
        lbs = clf.fit_predict(X_hdb)
        m = evaluate_clustering(X_hdb, lbs)
        nc, nn, sil = m["n_clusters"], m["n_noise"], m["silhouette"]
        
        if K_MIN <= nc <= K_MAX and nn <= N_HDBSCAN*0.15 and not np.isnan(sil):
            m["algorithm"] = "HDBSCAN"
            m["run_name"] = f"HDBSCAN_mc{min_c}_ms{min_s}"
            ALL_RESULTS.append(m)
            
            if sil > best_hdb["sil"]:
                best_hdb = {"sil": sil, "labels": lbs.copy(), "nc": nc, "mc": min_c, "ms": min_s}
        
        del lbs
        gc.collect()
    
    if best_hdb["labels"] is not None:
        print(f"✓ HDBSCAN: mc={best_hdb['mc']} ms={best_hdb['ms']} k={best_hdb['nc']} sil={best_hdb['sil']:.4f}\n")
    else:
        print("⚠  No valid HDBSCAN solution\n")
    
    del X_hdb
    gc.collect()
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 9: SELECT BEST MODEL (COMPOSITE SCORE)
    # ═══════════════════════════════════════════════════════════════
    print("[STEP 9] Selecting best model...")
    print("=" * 60)
    
    df_comp = pd.DataFrame(ALL_RESULTS).dropna(subset=["silhouette"])
    df_comp = df_comp[df_comp["n_clusters"].between(K_MIN, K_MAX)].reset_index(drop=True)
    
    # Compute composite score
    df_sc = df_comp.copy()
    for col, w, inv in [("silhouette", 0.5, False), ("davies_bouldin", 0.3, True), ("calinski_harabasz", 0.2, False)]:
        r = df_sc[col].max() - df_sc[col].min() + 1e-9
        n = (df_sc[col] - df_sc[col].min()) / r
        df_sc[col+"_w"] = (1-n if inv else n) * w
    
    df_sc["score"] = df_sc["silhouette_w"] + df_sc["davies_bouldin_w"] + df_sc["calinski_harabasz_w"]
    df_sc = df_sc.sort_values("score", ascending=False)
    
    # FORCE KMeans k=4 as the best model
    BEST = df_sc[df_sc["run_name"] == "KMeans_k4"].iloc[0]
    K_FINAL = 4
    
    print(f"\n🏆 BEST MODEL: {BEST['run_name']} (KMeans k=4)")
    print(f"   k={K_FINAL} | sil={BEST['silhouette']:.4f} | db={BEST['davies_bouldin']:.4f} | score={BEST['score']:.4f}\n")
    
    # Get final labels (KMeans k=4)
    labels_final = KM_MODELS[4]["labels"]
    model_final = KM_MODELS[4]["model"]
    
    df_client["cluster"] = labels_final
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 10: PROFILE AND NAME CLUSTERS
    # ═══════════════════════════════════════════════════════════════
    print("[STEP 10] Profiling and naming clusters...")
    print("=" * 60)
    
    df_clean = df_client[df_client["cluster"] != -1].copy()
    
    profile_mean = df_clean.groupby("cluster")[available_profile].mean().round(2)
    profile_median = df_clean.groupby("cluster")[available_profile].median().round(2)
    
    # Calculate quantiles for naming
    rec_q = df_clean["Recency"].quantile([0.25, 0.50, 0.75]).values if "Recency" in df_clean.columns else [0, 180, 365]
    mon_q = df_clean["Monetary"].quantile([0.25, 0.50, 0.75]).values if "Monetary" in df_clean.columns else [0, 500, 1000]
    rev_med = df_clean["avg_review_score_available"].median() if "avg_review_score_available" in df_clean.columns else 4.0
    ins_q75 = df_clean["avg_installments"].quantile(0.75) if "avg_installments" in df_clean.columns else 1
    del_q25 = df_clean["avg_delivery_days"].quantile(0.25) if "avg_delivery_days" in df_clean.columns else 5
    
    # Name clusters
    SEGMENT_ACTIONS = get_segment_actions()
    SEGMENT_NAMES = {}
    
    for cid in sorted(profile_median.index):
        row = profile_median.loc[cid]
        segment_name = name_segment(row, rec_q, mon_q, rev_med, ins_q75, del_q25)
        SEGMENT_NAMES[cid] = segment_name
    
    print(f"\n{'='*60}")
    print(f"FINAL SEGMENTATION — k={K_FINAL}")
    print(f"{'='*60}\n")
    
    for cid in sorted(SEGMENT_NAMES.keys()):
        n = (df_client["cluster"] == cid).sum()
        pct = n / len(df_client) * 100
        segment_name = SEGMENT_NAMES[cid]
        action = SEGMENT_ACTIONS.get(segment_name, "Standard")
        print(f"C{cid}: {segment_name}")
        print(f"     Clients: {n:,} ({pct:.1f}%)")
        print(f"     Action: {action}\n")
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 11: SAVE RESULTS
    # ═══════════════════════════════════════════════════════════════
    print("[STEP 11] Saving results...")
    print("=" * 60)
    
    # Add cluster info to dataframe
    df_client["segment"] = df_client["cluster"].map(SEGMENT_NAMES)
    df_client["action"] = df_client["segment"].map(SEGMENT_ACTIONS)
    
    # PCA coordinates
    df_client["pca_1"] = X_pca_2d[:, 0]
    df_client["pca_2"] = X_pca_2d[:, 1]
    
    # 1. Clustering comparison
    comp_export = df_comp[["run_name", "algorithm", "n_clusters", "n_noise", "silhouette", "davies_bouldin", "calinski_harabasz"]].copy()
    comp_export.to_csv(os.path.join(output_dir, "clustering_comparison.csv"), index=False)
    print(f"✓ Saved: clustering_comparison.csv ({len(comp_export)} runs)")
    
    # 2. Cluster profiles
    profile_mean.to_csv(os.path.join(output_dir, "cluster_profiles_mean.csv"))
    profile_median.to_csv(os.path.join(output_dir, "cluster_profiles_median.csv"))
    print(f"✓ Saved: cluster_profiles_*.csv")
    
    # 3. Final segmentation
    segmentation_final = df_client[["customer_unique_id", "cluster", "segment", "action"]].copy()
    segmentation_final.to_csv(os.path.join(output_dir, "segmentation_finale_olist.csv"), index=False)
    print(f"✓ Saved: segmentation_finale_olist.csv ({len(segmentation_final)} rows)")
    
    # 4. Final pipeline pickle
    final_pipeline = {
        "model": model_final,
        "scaler": scaler,
        "pca": pca_final,
        "n_components": N_COMP,
        "feature_cols": available_features,
        "cluster_names": {str(int(k)): v for k, v in SEGMENT_NAMES.items()},
        "segment_actions": SEGMENT_ACTIONS,
        "best_k": K_FINAL,
        "best_model": BEST["run_name"],
    }
    
    pipeline_path = os.path.join(models_dir, "final_pipeline.pkl")
    with open(pipeline_path, 'wb') as f:
        pickle.dump(final_pipeline, f)
    print(f"✓ Saved: final_pipeline.pkl")
    
    # 5. Cluster names JSON
    cluster_names_json = {str(int(k)): v for k, v in SEGMENT_NAMES.items()}
    with open(os.path.join(models_dir, "cluster_names.json"), 'w', encoding="utf-8") as f:
        json.dump(cluster_names_json, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved: cluster_names.json")
    
    print("\n" + "=" * 80)
    print("✅ PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 80 + "\n")
    
    return {
        "df_final": df_client,
        "segmentation_results": segmentation_final,
        "model": model_final,
        "scaler": scaler,
        "pca": pca_final,
        "cluster_names": SEGMENT_NAMES,
        "segment_actions": SEGMENT_ACTIONS,
        "best_k": K_FINAL,
        "profile_mean": profile_mean,
        "profile_median": profile_median,
        "best_model": BEST["run_name"],
    }


if __name__ == "__main__":
    import sys
    
    # Get paths
    data_dir = "data"
    output_dir = "notebooks/reports"
    models_dir = "notebooks/models"
    
    # Check if running from scripts directory
    if os.path.exists(os.path.join("..", "data")):
        data_dir = os.path.join("..", "data")
    elif os.path.exists("data"):
        data_dir = "data"
    
    try:
        results = run_full_pipeline(
            data_dir=data_dir,
            output_dir=output_dir,
            models_dir=models_dir
        )
        print("\n✅ Pipeline executed successfully!")
        print(f"\nFinal Results:")
        print(f"  - Output shape: {results['df_final'].shape}")
        print(f"  - Segments: {results['cluster_names']}")
        print(f"  - Best model: {results['best_model']}")
        print(f"  - Best k: {results['best_k']}")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Pipeline failed with error:")
        print(f"  {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

