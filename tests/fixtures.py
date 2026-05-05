"""
Test fixtures and utilities
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path


@pytest.fixture
def sample_raw_data():
    """Create sample raw data for testing"""
    np.random.seed(42)
    
    n_rows = 100
    n_customers = 20
    
    df = pd.DataFrame({
        'order_id': np.arange(n_rows),
        'customer_unique_id': np.random.choice(n_customers, n_rows),
        'order_purchase_timestamp': pd.date_range('2023-01-01', periods=n_rows, freq='D'),
        'order_approved_at': pd.date_range('2023-01-02', periods=n_rows, freq='D'),
        'order_delivered_customer_date': pd.date_range('2023-01-10', periods=n_rows, freq='D'),
        'order_estimated_delivery_date': pd.date_range('2023-01-09', periods=n_rows, freq='D'),
        'order_status': ['delivered'] * 90 + ['canceled'] * 10,
        'payment_value': np.random.uniform(50, 500, n_rows),
        'review_score': np.random.choice([1, 2, 3, 4, 5], n_rows),
        'review_creation_date': pd.date_range('2023-01-11', periods=n_rows, freq='D'),
        'customer_lat': np.random.uniform(-25, -22, n_rows),
        'customer_lng': np.random.uniform(-48, -46, n_rows),
        'seller_id': np.random.choice(5, n_rows),
        'payment_type': np.random.choice(['credit_card', 'boleto', 'debit_card'], n_rows),
        'payment_installments': np.random.choice([1, 2, 3, 12], n_rows),
        'freight_value': np.random.uniform(5, 100, n_rows),
        'price': np.random.uniform(50, 400, n_rows),
        'order_item_id': np.arange(n_rows),
        'product_id': np.random.choice(20, n_rows),
        'super_categorie': np.random.choice(['electronics', 'books', 'home', 'sports'], n_rows),
    })
    
    return df


@pytest.fixture
def sample_engineered_features(sample_raw_data):
    """Create sample engineered features"""
    np.random.seed(42)
    n_customers = sample_raw_data['customer_unique_id'].nunique()
    
    df = pd.DataFrame({
        'customer_unique_id': range(n_customers),
        'Recency': np.random.uniform(1, 100, n_customers),
        'Frequency': np.random.randint(1, 10, n_customers),
        'Monetary': np.random.uniform(100, 5000, n_customers),
        'avg_delivery_days': np.random.uniform(5, 30, n_customers),
        'late_delivery_rate': np.random.uniform(0, 0.5, n_customers),
        'avg_review_score_available': np.random.uniform(1, 5, n_customers),
        'review_participation_rate': np.random.uniform(0, 1, n_customers),
        'avg_order_value': np.random.uniform(50, 500, n_customers),
        'dist_sao_paulo': np.random.uniform(0, 2000, n_customers),
    })
    
    return df


@pytest.fixture
def sample_scaled_data(sample_engineered_features):
    """Create scaled feature data"""
    from sklearn.preprocessing import StandardScaler
    
    X = sample_engineered_features[
        ['Recency', 'Frequency', 'Monetary', 'avg_delivery_days', 'avg_review_score_available']
    ].values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    return X_scaled


@pytest.fixture
def config_dict():
    """Sample configuration dictionary"""
    return {
        'random_state': 42,
        'data': {
            'base_final': 'base_final.csv',
            'snapshot_lag_days': 7,
            'date_columns': ['order_purchase_timestamp']
        },
        'clustering': {
            'kmeans': {'k_min': 2, 'k_max': 5, 'init': 'k-means++', 'n_init': 10, 'max_iter': 300},
            'dbscan': {'eps_min': 0.3, 'eps_max': 2.0, 'eps_step': 0.1, 'min_samples': 5},
            'hierarchical': {'linkage_methods': ['ward'], 'distance_metric': 'euclidean'}
        },
        'pca': {'n_components': 2, 'explained_variance_threshold': 0.85},
        'feature_engineering': {'sao_paulo_coords': [-23.55, -46.63]},
    }
