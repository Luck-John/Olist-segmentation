"""
Tests for feature engineering module
"""
import pytest
import pandas as pd
import numpy as np
from src.features.engineering import (
    calculate_rfm, calculate_delivery_metrics, calculate_clv, apply_log_transformation
)
from tests.fixtures import sample_raw_data, config_dict


class TestRFM:
    """Test RFM calculation"""
    
    def test_rfm_calculation(self, sample_raw_data):
        """Test RFM returns correct structure"""
        snapshot_date = sample_raw_data['order_purchase_timestamp'].max() + pd.Timedelta(days=1)
        
        rfm = calculate_rfm(sample_raw_data, snapshot_date)
        
        # Check structure
        assert 'customer_unique_id' in rfm.columns
        assert 'Recency' in rfm.columns
        assert 'Frequency' in rfm.columns
        assert 'Monetary' in rfm.columns
        
        # Check data types
        assert rfm['Recency'].dtype in [np.float64, np.int64]
        assert rfm['Frequency'].dtype in [np.float64, np.int64]
        assert rfm['Monetary'].dtype in [np.float64, np.int64]
    
    def test_rfm_values_valid(self, sample_raw_data):
        """Test RFM values are valid"""
        snapshot_date = sample_raw_data['order_purchase_timestamp'].max() + pd.Timedelta(days=1)
        
        rfm = calculate_rfm(sample_raw_data, snapshot_date)
        
        # Recency should be non-negative
        assert (rfm['Recency'] >= 0).all()
        
        # Frequency should be positive
        assert (rfm['Frequency'] > 0).all()
        
        # Monetary should be non-negative
        assert (rfm['Monetary'] >= 0).all()
    
    def test_rfm_no_customers(self):
        """Test RFM with empty data"""
        df = pd.DataFrame({
            'customer_unique_id': [],
            'order_id': [],
            'order_purchase_timestamp': pd.to_datetime([]),
            'order_status': [],
            'payment_value': []
        })
        
        snapshot_date = pd.Timestamp('2023-12-31')
        rfm = calculate_rfm(df, snapshot_date)
        
        assert len(rfm) == 0


class TestDeliveryMetrics:
    """Test delivery metrics calculation"""
    
    def test_delivery_metrics_calculation(self, sample_raw_data):
        """Test delivery metrics are calculated"""
        avg_del, late_rate, avg_delta = calculate_delivery_metrics(sample_raw_data)
        
        # Check structure
        assert isinstance(avg_del, pd.Series)
        assert isinstance(late_rate, pd.Series)
        assert isinstance(avg_delta, pd.Series)
    
    def test_delivery_metrics_values(self, sample_raw_data):
        """Test delivery metrics values are valid"""
        avg_del, late_rate, avg_delta = calculate_delivery_metrics(sample_raw_data)
        
        # Delivery days should be positive
        assert (avg_del[avg_del.notna()] >= 0).all()
        
        # Late delivery rate should be between 0 and 1
        assert (late_rate[late_rate.notna()] >= 0).all()
        assert (late_rate[late_rate.notna()] <= 1).all()


class TestCLV:
    """Test Customer Lifetime Value calculation"""
    
    def test_clv_calculation(self):
        """Test CLV is calculated and is positive"""
        df_rfm = pd.DataFrame({
            'Monetary': [100, 200, 300],
            'Frequency': [1, 2, 5]
        })
        
        clv = calculate_clv(df_rfm, dataset_duration_days=365)
        
        # CLV should be positive
        assert (clv >= 0).all()
        assert len(clv) == len(df_rfm)
    
    def test_clv_zero_frequency(self):
        """Test CLV with zero frequency"""
        df_rfm = pd.DataFrame({
            'Monetary': [100, 0],
            'Frequency': [0, 2]
        })
        
        # Zero Monetary should give zero CLV
        clv = calculate_clv(df_rfm, dataset_duration_days=365)
        assert clv.iloc[0] == 0
    
    def test_clv_increases_with_frequency(self):
        """Test CLV increases with frequency"""
        df_rfm = pd.DataFrame({
            'Monetary': [100, 100],
            'Frequency': [1, 5]
        })
        
        clv = calculate_clv(df_rfm, dataset_duration_days=365)
        assert clv.iloc[1] > clv.iloc[0]


class TestLogTransformation:
    """Test log transformation"""
    
    def test_log_transformation_applied(self):
        """Test log transformation creates new columns"""
        df = pd.DataFrame({
            'value': [1, 10, 100, 1000]
        })
        
        df_result = apply_log_transformation(df, ['value'])
        
        assert 'value_log' in df_result.columns
        assert len(df_result) == len(df)
    
    def test_log_transformation_values(self):
        """Test log transformation values are correct"""
        df = pd.DataFrame({
            'value': [1, 10, 100]
        })
        
        df_result = apply_log_transformation(df, ['value'])
        
        # log1p(1) ≈ 0.693
        assert abs(df_result.loc[0, 'value_log'] - np.log1p(1)) < 0.001
        
        # log1p(10) ≈ 2.398
        assert abs(df_result.loc[1, 'value_log'] - np.log1p(10)) < 0.001
    
    def test_log_transformation_nonexistent_column(self):
        """Test log transformation with nonexistent column"""
        df = pd.DataFrame({'value': [1, 2, 3]})
        df_result = apply_log_transformation(df, ['nonexistent'])
        
        assert 'nonexistent_log' not in df_result.columns
        assert len(df_result) == len(df)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
