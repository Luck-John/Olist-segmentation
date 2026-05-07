"""
Customer clustering model - Reproduces KMeans from notebook
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (
    silhouette_score,
    davies_bouldin_score,
    calinski_harabasz_score
)
from src.utils.config import get_logger

logger = get_logger(__name__)


class CustomerSegmenter:
    """
    Segment customers using KMeans on PCA-transformed features.
    Reproduces clustering logic from Modélisons.ipynb notebook cells.
    """
    
    # Business requirement: test k from 4 to 8
    K_RANGE = range(4, 9)
    OPTIMAL_K_METHOD = "silhouette"  # Use silhouette score to find optimal k
    
    def __init__(self, random_state=42):
        self.random_state = random_state
        self.models = {}  # Dict {k: {model, labels, metrics}}
        self.k_optimal = None
        self.model_optimal = None
        self.fitted = False
    
    def evaluate_clustering(self, X: np.ndarray, labels: np.ndarray) -> dict:
        """
        Calculate clustering quality metrics.
        
        Args:
            X: PCA-transformed features (n, 5)
            labels: Cluster assignments
        
        Returns:
            Dict with silhouette, davies-bouldin, calinski-harabasz scores
        """
        metrics = {
            "silhouette_score": silhouette_score(X, labels),
            "davies_bouldin_score": davies_bouldin_score(X, labels),
            "calinski_harabasz_score": calinski_harabasz_score(X, labels),
        }
        return metrics
    
    def fit(self, X_pca: np.ndarray) -> dict:
        """
        Find optimal number of clusters by testing k=4 to 8.
        
        Args:
            X_pca: PCA-transformed features shape (n, 5)
        
        Returns:
            Dict with metrics for each k tested
        """
        results_by_k = {}
        
        logger.info(f"Testing k in range {list(self.K_RANGE)}")
        
        for k in self.K_RANGE:
            logger.info(f"  Testing k={k}...")
            
            # Train KMeans
            kmeans = KMeans(
                n_clusters=k,
                n_init=10,
                max_iter=300,
                random_state=self.random_state,
                n_jobs=-1
            )
            labels = kmeans.fit_predict(X_pca)
            
            # Calculate metrics
            metrics = self.evaluate_clustering(X_pca, labels)
            
            self.models[k] = {
                "model": kmeans,
                "labels": labels,
                "metrics": metrics,
                "inertia": kmeans.inertia_,
            }
            
            results_by_k[k] = metrics
            
            logger.info(
                f"    k={k}: silhouette={metrics['silhouette_score']:.3f}, "
                f"davies_bouldin={metrics['davies_bouldin_score']:.3f}, "
                f"calinski_harabasz={metrics['calinski_harabasz_score']:.1f}"
            )
        
        # Find optimal k using silhouette score (higher is better)
        self.k_optimal = max(
            self.models.keys(),
            key=lambda k: self.models[k]["metrics"]["silhouette_score"]
        )
        self.model_optimal = self.models[self.k_optimal]["model"]
        self.fitted = True
        
        logger.info(f"Optimal k selected: {self.k_optimal} (silhouette={self.models[self.k_optimal]['metrics']['silhouette_score']:.3f})")
        
        return results_by_k
    
    def predict(self, X_pca: np.ndarray) -> np.ndarray:
        """
        Predict cluster labels for new data.
        
        Args:
            X_pca: PCA-transformed features
        
        Returns:
            Array of cluster labels
        """
        if not self.fitted or self.model_optimal is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        return self.model_optimal.predict(X_pca)
    
    def get_optimal_labels(self) -> np.ndarray:
        """Get cluster labels from optimal model."""
        if self.k_optimal is None:
            raise ValueError("Model not fitted yet")
        return self.models[self.k_optimal]["labels"]
    
    def get_optimal_metrics(self) -> dict:
        """Get metrics from optimal model."""
        if self.k_optimal is None:
            raise ValueError("Model not fitted yet")
        return self.models[self.k_optimal]["metrics"]
    
    def get_cluster_centers(self) -> np.ndarray:
        """Get cluster centers in PCA space."""
        if self.model_optimal is None:
            raise ValueError("Model not fitted yet")
        return self.model_optimal.cluster_centers_
    
    def analyze_clusters(self, df: pd.DataFrame, labels: np.ndarray, 
                        feature_cols: list = None) -> dict:
        """
        Analyze cluster profiles using engineered features.
        
        Args:
            df: Original engineered features DataFrame
            labels: Cluster assignments
            feature_cols: Columns to use for profiling (default: all numeric)
        
        Returns:
            Dict with mean/median profiles per cluster
        """
        df_analysis = df.copy()
        df_analysis["cluster"] = labels
        
        # Select numeric columns for profiling
        if feature_cols is None:
            feature_cols = df_analysis.select_dtypes(include='number').columns.tolist()
            if "cluster" in feature_cols:
                feature_cols.remove("cluster")
        
        # Calculate profiles
        profile_mean = df_analysis.groupby("cluster")[feature_cols].mean().round(2)
        profile_median = df_analysis.groupby("cluster")[feature_cols].median().round(2)
        
        logger.info(f"Generated cluster profiles (k={self.k_optimal})")
        
        return {
            "profile_mean": profile_mean,
            "profile_median": profile_median,
            "cluster_sizes": df_analysis["cluster"].value_counts().sort_index(),
        }
    
    def get_results_summary(self) -> pd.DataFrame:
        """
        Get summary of all k tested with their metrics.
        
        Returns:
            DataFrame with k and metrics
        """
        if not self.models:
            raise ValueError("No models fitted yet")
        
        summary_data = []
        for k, model_data in sorted(self.models.items()):
            row = {"k": k}
            row.update(model_data["metrics"])
            row["inertia"] = model_data["inertia"]
            summary_data.append(row)
        
        return pd.DataFrame(summary_data)
