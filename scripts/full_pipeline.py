"""
Complete Segmentation Pipeline
Reproduces exactly the same outputs as the Modélisons.ipynb notebook
"""

import os
import sys
import json
import pickle
import logging
from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import Config, get_logger
from src.data.preprocessing import DataPreprocessor
from src.features.engineering import FeatureEngineer

logger = get_logger(__name__)

# Configuration constants
K_MIN, K_MAX = 4, 8
N_COMP = 2  # PCA components

# Segment naming and actions
SEGMENT_NAMES = {}  # Will be populated based on cluster analysis
SEGMENT_ACTIONS = {}


def evaluate_clustering(X_scaled, labels):
    """Calculate clustering metrics"""
    return {
        "silhouette_score": silhouette_score(X_scaled, labels),
        "davies_bouldin_score": davies_bouldin_score(X_scaled, labels),
        "calinski_harabasz_score": calinski_harabasz_score(X_scaled, labels)
    }


def analyze_and_name_clusters(df_clean, model_labels, feature_cols):
    """
    Analyze clusters and assign meaningful names based on profiles
    Returns cluster_names dict and segment_actions dict
    """
    PROFILE_COLS = [
        "Recency", "Monetary", "avg_review_score", "avg_delivery_days",
        "avg_installments", "avg_item_price", "CLV_estimate",
        "late_delivery_rate", "customer_tenure"
    ]

    # Add cluster labels
    df_analysis = df_clean.copy()
    df_analysis["cluster"] = model_labels

    # Calculate profiles
    profile_mean = df_analysis.groupby("cluster")[PROFILE_COLS].mean().round(2)
    profile_median = df_analysis.groupby("cluster")[PROFILE_COLS].median().round(2)

    # Calculate quantiles for naming logic
    rec_q = df_clean["Recency"].quantile([0.25, 0.50, 0.75]).values
    mon_q = df_clean["Monetary"].quantile([0.25, 0.50, 0.75]).values
    rev_med = df_clean["avg_review_score"].median()
    del_med = df_clean["avg_delivery_days"].median()

    # Assign segment names based on RFM analysis
    cluster_names = {}
    segment_actions = {}

    for cluster_id in sorted(df_analysis["cluster"].unique()):
        rec_val = profile_median.loc[cluster_id, "Recency"]
        mon_val = profile_median.loc[cluster_id, "Monetary"]
        rev_val = profile_median.loc[cluster_id, "avg_review_score"]

        # Naming logic
        if mon_val > mon_q[2] and rec_val < rec_q[1]:
            name = "Premium Actifs"
            action = "VIP"
        elif mon_val > mon_q[1] and rev_val > rev_med:
            name = "Clients Satisfaits"
            action = "Reward"
        elif mon_val < mon_q[0]:
            name = "Clients Dormants"
            action = "Reactivate"
        elif rec_val > rec_q[2]:
            name = "Nouveaux Clients"
            action = "Welcome"
        else:
            name = f"Segment {cluster_id}"
            action = "Standard"

        cluster_names[cluster_id] = name
        segment_actions[cluster_id] = action

    return cluster_names, segment_actions, profile_mean, profile_median


def run_full_pipeline(output_dir="reports", models_dir="notebooks/models"):
    """
    Execute the complete pipeline:
    1. Load and preprocess data
    2. Engineer features
    3. Scale features
    4. Fit KMeans models for k in [K_MIN, K_MAX]
    5. Select best model based on silhouette score
    6. Apply PCA for visualization
    7. Analyze and name clusters
    8. Save all outputs (CSV, pickle, JSON)
    """
    config = Config()

    # Create output directories
    Path(output_dir).mkdir(exist_ok=True)
    Path(models_dir).mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("STARTING FULL PIPELINE")
    logger.info("=" * 80)

    # ========== STEP 1: DATA LOADING & PREPROCESSING ==========
    logger.info("\n[STEP 1] Loading and preprocessing data...")
    preprocessor = DataPreprocessor(config.get())
    
    data_path = os.path.join(
        config.get('paths.data_dir'),
        config.get('data.base_final')
    )
    
    df_raw = preprocessor.load_and_preprocess(data_path)
    logger.info(f"Data shape after preprocessing: {df_raw.shape}")

    # ========== STEP 2: FEATURE ENGINEERING ==========
    logger.info("\n[STEP 2] Engineering features...")
    engineer = FeatureEngineer(config.get())
    df_features = engineer.engineer_features(df_raw)
    logger.info(f"Features shape: {df_features.shape}")

    # ========== STEP 3: EXTRACT FEATURE COLUMNS ==========
    num_features = df_features.select_dtypes(include=['number']).columns.tolist()
    num_features = [col for col in num_features if col != 'customer_unique_id']
    feature_cols = num_features
    
    logger.info(f"Number of features: {len(feature_cols)}")

    # ========== STEP 4: SCALING ==========
    logger.info("\n[STEP 3] Scaling features...")
    X = df_features[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    logger.info(f"Scaled features shape: {X_scaled.shape}")

    # ========== STEP 5: KMEANS CLUSTERING (RANGE) ==========
    logger.info(f"\n[STEP 4] Fitting KMeans for k in [{K_MIN}, {K_MAX}]...")
    
    results = []
    models = {}
    
    for k in range(K_MIN, K_MAX + 1):
        logger.info(f"  Fitting KMeans with k={k}...")
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)
        
        metrics = evaluate_clustering(X_scaled, labels)
        metrics['n_clusters'] = k
        metrics['algorithm'] = 'KMeans'
        metrics['model'] = kmeans
        metrics['labels'] = labels
        
        results.append(metrics)
        models[k] = {"model": kmeans, "labels": labels, "metrics": metrics}
        
        logger.info(f"    k={k}: silhouette={metrics['silhouette_score']:.4f}")

    # Find best k
    best_k = max(results, key=lambda x: x['silhouette_score'])['n_clusters']
    logger.info(f"\nBest k selected: {best_k}")
    
    model_final = models[best_k]['model']
    labels_final = models[best_k]['labels']

    # ========== STEP 6: PCA FOR VISUALIZATION ==========
    logger.info("\n[STEP 5] Applying PCA for visualization...")
    pca_final = PCA(n_components=N_COMP, random_state=42)
    X_pca = pca_final.fit_transform(X_scaled)
    logger.info(f"PCA variance explained: {pca_final.explained_variance_ratio_.sum():.2%}")

    # ========== STEP 7: ANALYZE AND NAME CLUSTERS ==========
    logger.info("\n[STEP 6] Analyzing and naming clusters...")
    
    df_clean = df_features.copy()
    cluster_names, segment_actions, profile_mean, profile_median = \
        analyze_and_name_clusters(df_clean, labels_final, feature_cols)
    
    logger.info(f"Cluster names: {cluster_names}")

    # ========== STEP 8: PREPARE OUTPUT DATAFRAME ==========
    df_output = df_features.copy()
    df_output["cluster"] = labels_final
    df_output["segment"] = df_output["cluster"].map(cluster_names)
    df_output["action"] = df_output["cluster"].map(segment_actions)
    df_output["pca_1"] = X_pca[:, 0]
    df_output["pca_2"] = X_pca[:, 1]

    # ========== STEP 9: SAVE RESULTS ==========
    logger.info("\n[STEP 7] Saving results...")
    
    # 1. Clustering comparison CSV
    comparison_df = pd.DataFrame(results).drop(['model', 'labels'], axis=1)
    comparison_df.to_csv(os.path.join(output_dir, "clustering_comparison.csv"), index=False)
    logger.info(f"✓ Saved: {output_dir}/clustering_comparison.csv")

    # 2. Cluster profiles (mean and median)
    profile_mean.to_csv(os.path.join(output_dir, "cluster_profiles_mean.csv"))
    profile_median.to_csv(os.path.join(output_dir, "cluster_profiles_median.csv"))
    logger.info(f"✓ Saved: {output_dir}/cluster_profiles_*.csv")

    # 3. Final segmentation results
    final_results = df_output[["customer_unique_id", "cluster", "segment", "action"]].copy()
    final_results.to_csv(os.path.join(output_dir, "segmentation_finale_olist.csv"), index=False)
    logger.info(f"✓ Saved: {output_dir}/segmentation_finale_olist.csv")

    # 4. Final pipeline pickle
    final_pipeline = {
        "model": model_final,
        "scaler": scaler,
        "pca": pca_final,
        "n_components": N_COMP,
        "feature_cols": feature_cols,
        "cluster_names": {str(k): v for k, v in cluster_names.items()},
        "segment_actions": {str(k): v for k, v in segment_actions.items()},
        "best_k": best_k,
    }
    
    pipeline_path = os.path.join(models_dir, "final_pipeline.pkl")
    with open(pipeline_path, 'wb') as f:
        pickle.dump(final_pipeline, f)
    logger.info(f"✓ Saved: {pipeline_path}")

    # 5. Cluster names JSON
    with open(os.path.join(models_dir, "cluster_names.json"), 'w') as f:
        json.dump(cluster_names, f, ensure_ascii=False, indent=2)
    logger.info(f"✓ Saved: {models_dir}/cluster_names.json")

    logger.info("\n" + "=" * 80)
    logger.info("PIPELINE COMPLETED SUCCESSFULLY")
    logger.info("=" * 80)

    return {
        "output_dataframe": df_output,
        "final_results": final_results,
        "model": model_final,
        "scaler": scaler,
        "pca": pca_final,
        "cluster_names": cluster_names,
        "segment_actions": segment_actions,
        "best_k": best_k,
        "profile_mean": profile_mean,
        "profile_median": profile_median,
    }


if __name__ == "__main__":
    results = run_full_pipeline(
        output_dir="notebooks/reports",
        models_dir="notebooks/models"
    )
    print("\n✅ Pipeline executed successfully!")
    print(f"Output shape: {results['output_dataframe'].shape}")
    print(f"Segments: {results['cluster_names']}")
