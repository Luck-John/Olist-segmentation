"""
Tests for clustering module
"""
import pytest
import numpy as np
from sklearn.preprocessing import StandardScaler
from src.clustering.models import (
    KMeansClustering, DBSCANClustering, HierarchicalClustering, 
    ClusteringEvaluator, PCAReducer
)
from tests.fixtures import sample_scaled_data, config_dict


class TestClusteringEvaluator:
    """Test clustering evaluation metrics"""
    
    def test_evaluator_initialization(self, config_dict):
        """Test evaluator can be initialized"""
        evaluator = ClusteringEvaluator(config_dict)
        assert evaluator is not None
    
    def test_calculate_metrics(self, sample_scaled_data, config_dict):
        """Test metric calculation"""
        evaluator = ClusteringEvaluator(config_dict)
        
        # Create simple labels
        labels = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2] + [0] * (len(sample_scaled_data) - 9))
        
        metrics = evaluator.calculate_metrics(sample_scaled_data, labels)
        
        # Check structure
        assert 'n_clusters' in metrics
        assert 'silhouette_score' in metrics
        assert 'davies_bouldin_score' in metrics
        assert 'calinski_harabasz_score' in metrics
    
    def test_is_valid_clustering(self, config_dict):
        """Test clustering validity check"""
        evaluator = ClusteringEvaluator(config_dict)
        
        # Valid clustering (2 clusters)
        labels_valid = np.array([0, 0, 0, 1, 1, 1])
        assert evaluator.is_valid_clustering(labels_valid) is True
        
        # Invalid clustering (all same cluster)
        labels_invalid = np.array([0, 0, 0, 0, 0, 0])
        assert evaluator.is_valid_clustering(labels_invalid) is False


class TestKMeansClustering:
    """Test KMeans clustering"""
    
    def test_kmeans_initialization(self, config_dict):
        """Test KMeans can be initialized"""
        kmeans = KMeansClustering(config_dict)
        assert kmeans is not None
    
    def test_kmeans_fit_range(self, sample_scaled_data, config_dict):
        """Test KMeans fit for range of k"""
        kmeans = KMeansClustering(config_dict)
        results = kmeans.fit_range(sample_scaled_data, k_range=(2, 4))
        
        # Check results for each k
        assert len(results) == 3  # k=2, 3, 4
        assert 2 in results
        assert 3 in results
        assert 4 in results
        
        # Check each result has metrics
        for k, metrics in results.items():
            assert 'n_clusters' in metrics
            assert metrics['n_clusters'] == k
    
    def test_kmeans_predict(self, sample_scaled_data, config_dict):
        """Test KMeans predict"""
        kmeans = KMeansClustering(config_dict)
        kmeans.fit_range(sample_scaled_data, k_range=(2, 3))
        
        labels = kmeans.predict(sample_scaled_data, k=2)
        
        assert len(labels) == len(sample_scaled_data)
        assert set(labels) == {0, 1}
    
    def test_kmeans_get_best_model(self, sample_scaled_data, config_dict):
        """Test get best model"""
        kmeans = KMeansClustering(config_dict)
        kmeans.fit_range(sample_scaled_data, k_range=(2, 4))
        
        best_k, best_model = kmeans.get_best_model(metric='silhouette_score')
        
        assert best_k in [2, 3, 4]
        assert 'model' in best_model
        assert 'labels' in best_model
        assert 'metrics' in best_model


class TestDBSCANClustering:
    """Test DBSCAN clustering"""
    
    def test_dbscan_initialization(self, config_dict):
        """Test DBSCAN can be initialized"""
        dbscan = DBSCANClustering(config_dict)
        assert dbscan is not None
    
    def test_dbscan_fit_range(self, sample_scaled_data, config_dict):
        """Test DBSCAN fit for range of eps"""
        dbscan = DBSCANClustering(config_dict)
        results = dbscan.fit_range(sample_scaled_data, eps_range=(0.5, 1.5))
        
        # Should have results for multiple eps values
        assert len(results) > 0
        
        # Each result should have metrics
        for eps, metrics in results.items():
            assert 'n_clusters' in metrics


class TestHierarchicalClustering:
    """Test Hierarchical clustering"""
    
    def test_hierarchical_initialization(self, config_dict):
        """Test Hierarchical can be initialized"""
        hc = HierarchicalClustering(config_dict)
        assert hc is not None
    
    def test_hierarchical_fit_linkages(self, sample_scaled_data, config_dict):
        """Test Hierarchical fit for different linkages"""
        hc = HierarchicalClustering(config_dict)
        results = hc.fit_linkages(sample_scaled_data, n_clusters=3)
        
        # Should have results
        assert len(results) > 0
        
        # Each linkage should have metrics
        for linkage, metrics in results.items():
            assert 'n_clusters' in metrics
            assert metrics['n_clusters'] == 3


class TestPCAReducer:
    """Test PCA dimensionality reduction"""
    
    def test_pca_initialization(self, config_dict):
        """Test PCA can be initialized"""
        pca = PCAReducer(config_dict)
        assert pca is not None
    
    def test_pca_fit_transform(self, sample_scaled_data, config_dict):
        """Test PCA fit and transform"""
        pca = PCAReducer(config_dict)
        X_pca = pca.fit_transform(sample_scaled_data, n_components=2)
        
        # Check dimensions
        assert X_pca.shape[0] == sample_scaled_data.shape[0]
        assert X_pca.shape[1] == 2
    
    def test_pca_transform(self, sample_scaled_data, config_dict):
        """Test PCA transform on new data"""
        pca = PCAReducer(config_dict)
        pca.fit_transform(sample_scaled_data, n_components=2)
        
        # Transform the same data
        X_pca = pca.transform(sample_scaled_data)
        
        assert X_pca.shape[0] == sample_scaled_data.shape[0]
        assert X_pca.shape[1] == 2
    
    def test_pca_transform_before_fit(self, sample_scaled_data, config_dict):
        """Test transform before fit raises error"""
        pca = PCAReducer(config_dict)
        
        with pytest.raises(ValueError):
            pca.transform(sample_scaled_data)


class TestClusteringOutput:
    """Test clustering output validation"""
    
    def test_kmeans_labels_valid(self, sample_scaled_data, config_dict):
        """Test KMeans labels are valid"""
        kmeans = KMeansClustering(config_dict)
        kmeans.fit_range(sample_scaled_data, k_range=(2, 3))
        
        labels = kmeans.predict(sample_scaled_data, k=2)
        
        # Labels should be between 0 and k-1
        assert labels.min() >= 0
        assert labels.max() <= 1
        
        # All samples should be labeled
        assert len(labels) == len(sample_scaled_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
