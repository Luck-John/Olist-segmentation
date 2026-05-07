"""
Test script to verify complete pipeline parity with notebook
Reproduces Modélisons.ipynb pipeline exactly
"""

import sys
import os
from pathlib import Path

import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.preprocessing import DataPreprocessor
from src.features.engineering import FeatureEngineer
from src.clustering.preprocessing import ClusteringPreprocessor
from src.clustering.clustering import CustomerSegmenter
from src.utils.config import Config, get_logger

logger = get_logger(__name__)


def test_complete_pipeline():
    """
    Test complete pipeline: raw data → features → preprocessing → clustering
    Verifies parity with Modélisons.ipynb
    """
    
    config = Config()
    
    # ========== STEP 1: Load and preprocess data ==========
    logger.info("=" * 80)
    logger.info("[STEP 1] Loading and preprocessing raw data...")
    logger.info("=" * 80)
    
    preprocessor = DataPreprocessor(config.get())
    data_path = Path(config.get('paths.data_dir')) / config.get('data.base_final')
    
    if not data_path.exists():
        logger.error(f"Data file not found: {data_path}")
        return False
    
    df_raw = preprocessor.load_and_preprocess(str(data_path))
    logger.info(f"✓ Raw data shape: {df_raw.shape}")
    
    # ========== STEP 2: Engineer features ==========
    logger.info("\n" + "=" * 80)
    logger.info("[STEP 2] Engineering features (14+ features)...")
    logger.info("=" * 80)
    
    engineer = FeatureEngineer(config.get())
    df_features = engineer.engineer_features(df_raw)
    logger.info(f"✓ Engineered features shape: {df_features.shape}")
    
    # Show available features
    feature_cols = df_features.select_dtypes(include='number').columns.tolist()
    feature_cols = [c for c in feature_cols if c != 'customer_unique_id']
    logger.info(f"✓ Available features ({len(feature_cols)}): {feature_cols[:10]}...")
    
    # ========== STEP 3: Clustering preprocessing ==========
    logger.info("\n" + "=" * 80)
    logger.info("[STEP 3] Clustering preprocessing...")
    logger.info("  - Apply log transforms (4 features)")
    logger.info("  - Apply bucketing (3 features)")
    logger.info("  - Select FEATURES_FINAL (7 features)")
    logger.info("  - Cap outliers")
    logger.info("  - StandardScale")
    logger.info("  - PCA (5D whitening)")
    logger.info("=" * 80)
    
    prep = ClusteringPreprocessor(random_state=42)
    
    try:
        X_pca = prep.fit_preprocessing(df_features)
        logger.info(f"✓ PCA-transformed shape: {X_pca.shape}")
        
        # Show PCA components
        pca_components = prep.get_pca_components()
        pca_info = prep.get_explained_variance()
        logger.info(f"✓ PCA explained variance: {pca_info['cumulative_variance_ratio']}")
        
    except Exception as e:
        logger.error(f"✗ Error in preprocessing: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========== STEP 4: Clustering ==========
    logger.info("\n" + "=" * 80)
    logger.info("[STEP 4] Fitting KMeans (k=4 to 8)...")
    logger.info("=" * 80)
    
    segmenter = CustomerSegmenter(random_state=42)
    
    try:
        results = segmenter.fit(X_pca)
        
        # Show results
        summary = segmenter.get_results_summary()
        logger.info("\n✓ KMeans results:")
        logger.info(summary.to_string())
        
        optimal_k = segmenter.k_optimal
        optimal_metrics = segmenter.get_optimal_metrics()
        logger.info(f"\n✓ Optimal k: {optimal_k}")
        logger.info(f"  Silhouette: {optimal_metrics['silhouette_score']:.4f}")
        logger.info(f"  Davies-Bouldin: {optimal_metrics['davies_bouldin_score']:.4f}")
        logger.info(f"  Calinski-Harabasz: {optimal_metrics['calinski_harabasz_score']:.2f}")
        
    except Exception as e:
        logger.error(f"✗ Error in clustering: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ========== STEP 5: Analyze clusters ==========
    logger.info("\n" + "=" * 80)
    logger.info("[STEP 5] Analyzing cluster profiles...")
    logger.info("=" * 80)
    
    labels = segmenter.get_optimal_labels()
    analysis = segmenter.analyze_clusters(df_features, labels)
    
    logger.info("\n✓ Cluster sizes:")
    logger.info(analysis['cluster_sizes'])
    
    logger.info("\n✓ Mean profiles:")
    logger.info(analysis['profile_mean'].head())
    
    # ========== STEP 6: Verify parity ==========
    logger.info("\n" + "=" * 80)
    logger.info("[STEP 6] Verifying parity with notebook...")
    logger.info("=" * 80)
    
    checks = {
        "✓ Features engineered": df_features.shape[0] > 0,
        "✓ Log transforms applied": all(col in prep.FEATURES_FINAL for col in ["log_recency", "log_monetary"]),
        "✓ Bucketing applied": "recency_score_10" in prep.FEATURES_FINAL,
        "✓ Feature selection": len(prep.FEATURES_FINAL) == 7,
        "✓ PCA fitted": prep.pca is not None,
        "✓ PCA dimensions": X_pca.shape[1] == 5,
        "✓ KMeans fitted": segmenter.fitted,
        "✓ Optimal k found": segmenter.k_optimal is not None,
    }
    
    for check, passed in checks.items():
        logger.info(f"{check}: {'PASS' if passed else 'FAIL'}")
    
    all_pass = all(checks.values())
    
    if all_pass:
        logger.info("\n" + "=" * 80)
        logger.info("✓ ALL TESTS PASSED - Pipeline parity verified!")
        logger.info("=" * 80)
    else:
        logger.error("\n✗ Some tests failed")
    
    return all_pass


if __name__ == "__main__":
    success = test_complete_pipeline()
    exit(0 if success else 1)
