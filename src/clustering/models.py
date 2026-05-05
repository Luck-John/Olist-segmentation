"""
Clustering models and evaluation metrics
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

from src.utils.config import load_config, get_logger


logger = get_logger(__name__)


class ClusteringEvaluator:
    """Evaluate and compare clustering results"""
    
    def __init__(self, config=None):
        """Initialize evaluator"""
        self.config = config or load_config()
    
    def calculate_metrics(self, X: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
        """
        Calculate clustering evaluation metrics.
        
        Args:
            X: Scaled feature matrix
            labels: Cluster labels
        
        Returns:
            Dictionary with metrics
        """
        # Number of clusters
        n_clusters = len(np.unique(labels)) - (1 if -1 in labels else 0)
        
        metrics = {
            'n_clusters': n_clusters,
            'n_samples': len(labels),
            'noise_points': np.sum(labels == -1) if -1 in labels else 0
        }
        
        # Only calculate score-based metrics if we have valid clusters
        if n_clusters > 1 and (len(np.unique(labels)) > 1):
            try:
                metrics['silhouette_score'] = silhouette_score(X, labels)
            except Exception as e:
                logger.warning(f"Could not calculate silhouette score: {e}")
                metrics['silhouette_score'] = np.nan
            
            try:
                metrics['davies_bouldin_score'] = davies_bouldin_score(X, labels)
            except Exception as e:
                logger.warning(f"Could not calculate davies_bouldin score: {e}")
                metrics['davies_bouldin_score'] = np.nan
            
            try:
                metrics['calinski_harabasz_score'] = calinski_harabasz_score(X, labels)
            except Exception as e:
                logger.warning(f"Could not calculate calinski_harabasz score: {e}")
                metrics['calinski_harabasz_score'] = np.nan
        else:
            metrics['silhouette_score'] = np.nan
            metrics['davies_bouldin_score'] = np.nan
            metrics['calinski_harabasz_score'] = np.nan
        
        return metrics
    
    def is_valid_clustering(self, labels: np.ndarray) -> bool:
        """
        Check if clustering is valid (has multiple clusters and not all noise).
        
        Args:
            labels: Cluster labels
        
        Returns:
            True if clustering is valid
        """
        n_clusters = len(np.unique(labels)) - (1 if -1 in labels else 0)
        noise_ratio = np.sum(labels == -1) / len(labels) if -1 in labels else 0
        
        return n_clusters >= 2 and noise_ratio < 0.5


class KMeansClustering:
    """KMeans clustering wrapper"""
    
    def __init__(self, config=None):
        """Initialize KMeans clustering"""
        self.config = config or load_config()
        self.models = {}
        self.evaluator = ClusteringEvaluator(config)
    
    def fit_range(self, X: np.ndarray, k_range: Optional[Tuple[int, int]] = None) -> Dict[int, Dict]:
        """
        Fit KMeans for a range of k values and find optimal k.
        
        Args:
            X: Scaled feature matrix
            k_range: Tuple of (k_min, k_max). If None, uses config
        
        Returns:
            Dictionary with results for each k
        """
        if k_range is None:
            kmeans_config = self.config['clustering']['kmeans']
            k_min = kmeans_config['k_min']
            k_max = kmeans_config['k_max']
        else:
            k_min, k_max = k_range
        
        results = {}
        
        for k in range(k_min, k_max + 1):
            logger.info(f"Fitting KMeans with k={k}")
            
            kmeans = KMeans(
                n_clusters=k,
                init=self.config['clustering']['kmeans']['init'],
                n_init=self.config['clustering']['kmeans']['n_init'],
                max_iter=self.config['clustering']['kmeans']['max_iter'],
                random_state=self.config['random_state']
            )
            
            labels = kmeans.fit_predict(X)
            metrics = self.evaluator.calculate_metrics(X, labels)
            
            self.models[k] = {
                'model': kmeans,
                'labels': labels,
                'metrics': metrics,
                'inertia': kmeans.inertia_
            }
            
            results[k] = metrics
            logger.info(f"k={k}: silhouette={metrics.get('silhouette_score', np.nan):.3f}")
        
        return results
    
    def predict(self, X_new: np.ndarray, k: int) -> np.ndarray:
        """
        Predict cluster labels for new data.
        
        Args:
            X_new: New feature matrix
            k: Number of clusters
        
        Returns:
            Cluster labels
        """
        if k not in self.models:
            raise ValueError(f"Model with k={k} not trained")
        
        return self.models[k]['model'].predict(X_new)
    
    def get_best_model(self, metric: str = 'silhouette_score') -> Tuple[int, Dict]:
        """
        Get the best model according to specified metric.
        
        Args:
            metric: Metric to optimize ('silhouette_score', 'davies_bouldin_score', 'calinski_harabasz_score')
        
        Returns:
            Tuple of (best_k, model_info)
        """
        best_k = None
        best_value = -np.inf if metric != 'davies_bouldin_score' else np.inf
        
        for k, model_info in self.models.items():
            value = model_info['metrics'].get(metric)
            
            if value is not None and not np.isnan(value):
                is_better = (value > best_value) if metric != 'davies_bouldin_score' else (value < best_value)
                
                if is_better:
                    best_k = k
                    best_value = value
        
        if best_k is None:
            raise ValueError(f"Could not find best model using metric {metric}")
        
        logger.info(f"Best KMeans: k={best_k} with {metric}={best_value:.3f}")
        return best_k, self.models[best_k]


class DBSCANClustering:
    """DBSCAN clustering wrapper"""
    
    def __init__(self, config=None):
        """Initialize DBSCAN clustering"""
        self.config = config or load_config()
        self.models = {}
        self.evaluator = ClusteringEvaluator(config)
    
    def fit_range(self, X: np.ndarray, eps_range: Optional[Tuple[float, float]] = None) -> Dict[float, Dict]:
        """
        Fit DBSCAN for a range of eps values.
        
        Args:
            X: Scaled feature matrix
            eps_range: Tuple of (eps_min, eps_max). If None, uses config
        
        Returns:
            Dictionary with results for each eps
        """
        if eps_range is None:
            dbscan_config = self.config['clustering']['dbscan']
            eps_min = dbscan_config['eps_min']
            eps_max = dbscan_config['eps_max']
            eps_step = dbscan_config['eps_step']
        else:
            eps_min, eps_max = eps_range
            eps_step = (eps_max - eps_min) / 10
        
        results = {}
        eps_values = np.arange(eps_min, eps_max + eps_step, eps_step)
        
        for eps in eps_values:
            logger.info(f"Fitting DBSCAN with eps={eps:.2f}")
            
            dbscan = DBSCAN(
                eps=eps,
                min_samples=self.config['clustering']['dbscan']['min_samples']
            )
            
            labels = dbscan.fit_predict(X)
            
            # Only calculate metrics if clustering is valid
            if self.evaluator.is_valid_clustering(labels):
                metrics = self.evaluator.calculate_metrics(X, labels)
            else:
                metrics = {
                    'n_clusters': len(np.unique(labels)) - (1 if -1 in labels else 0),
                    'noise_points': np.sum(labels == -1),
                    'silhouette_score': np.nan,
                    'davies_bouldin_score': np.nan,
                    'calinski_harabasz_score': np.nan
                }
            
            self.models[eps] = {
                'model': dbscan,
                'labels': labels,
                'metrics': metrics
            }
            
            results[eps] = metrics
        
        return results


class HierarchicalClustering:
    """Hierarchical clustering wrapper"""
    
    def __init__(self, config=None):
        """Initialize Hierarchical clustering"""
        self.config = config or load_config()
        self.models = {}
        self.evaluator = ClusteringEvaluator(config)
    
    def fit_linkages(self, X: np.ndarray, n_clusters: int) -> Dict[str, Dict]:
        """
        Fit Hierarchical clustering with different linkage methods.
        
        Args:
            X: Scaled feature matrix
            n_clusters: Number of clusters to form
        
        Returns:
            Dictionary with results for each linkage method
        """
        linkages = self.config['clustering']['hierarchical']['linkage_methods']
        results = {}
        
        for linkage in linkages:
            logger.info(f"Fitting Hierarchical with linkage={linkage}")
            
            hc = AgglomerativeClustering(
                n_clusters=n_clusters,
                linkage=linkage,
                metric=self.config['clustering']['hierarchical']['distance_metric']
            )
            
            labels = hc.fit_predict(X)
            metrics = self.evaluator.calculate_metrics(X, labels)
            
            self.models[linkage] = {
                'model': hc,
                'labels': labels,
                'metrics': metrics
            }
            
            results[linkage] = metrics
            logger.info(f"Linkage={linkage}: silhouette={metrics.get('silhouette_score', np.nan):.3f}")
        
        return results


class PCAReducer:
    """PCA dimensionality reduction for visualization"""
    
    def __init__(self, config=None):
        """Initialize PCA reducer"""
        self.config = config or load_config()
        self.pca = None
    
    def fit_transform(self, X: np.ndarray, n_components: Optional[int] = None) -> np.ndarray:
        """
        Fit PCA and transform data.
        
        Args:
            X: Scaled feature matrix
            n_components: Number of components. If None, uses config
        
        Returns:
            Reduced data
        """
        if n_components is None:
            n_components = self.config['pca']['n_components']
        
        self.pca = PCA(n_components=n_components, random_state=self.config['random_state'])
        X_pca = self.pca.fit_transform(X)
        
        explained_var = np.sum(self.pca.explained_variance_ratio_)
        logger.info(f"PCA: {n_components} components explain {explained_var:.2%} of variance")
        
        return X_pca
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Transform data using fitted PCA.
        
        Args:
            X: Feature matrix
        
        Returns:
            Reduced data
        """
        if self.pca is None:
            raise ValueError("PCA not fitted. Call fit_transform first")
        
        return self.pca.transform(X)


if __name__ == "__main__":
    # Test the clustering
    from sklearn.preprocessing import StandardScaler
    
    # Create dummy data
    X = np.random.randn(100, 10)
    X_scaled = StandardScaler().fit_transform(X)
    
    # Test KMeans
    kmeans_clustering = KMeansClustering()
    results = kmeans_clustering.fit_range(X_scaled, k_range=(2, 5))
    best_k, best_model = kmeans_clustering.get_best_model()
    print(f"Best KMeans: k={best_k}")
