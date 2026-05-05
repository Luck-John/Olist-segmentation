"""
Tests for data preprocessing module
"""
import pytest
import pandas as pd
import numpy as np
from src.data.preprocessing import (
    load_data, convert_dates, handle_missing_values, remove_duplicates,
    apply_winsorization, validate_data
)
from tests.fixtures import sample_raw_data, config_dict


class TestDataLoading:
    """Test data loading functions"""
    
    def test_convert_dates(self, sample_raw_data):
        """Test date conversion"""
        df = sample_raw_data.copy()
        
        # Convert to string first to simulate raw data
        df['order_purchase_timestamp'] = df['order_purchase_timestamp'].astype(str)
        
        # Convert back
        df = convert_dates(df, ['order_purchase_timestamp'])
        
        assert pd.api.types.is_datetime64_any_dtype(df['order_purchase_timestamp'])
        assert len(df) == len(sample_raw_data)
    
    def test_convert_dates_nonexistent_column(self, sample_raw_data):
        """Test converting nonexistent column doesn't fail"""
        df = sample_raw_data.copy()
        df = convert_dates(df, ['nonexistent_column'])
        assert len(df) == len(sample_raw_data)
    
    def test_handle_missing_values_report(self, sample_raw_data):
        """Test missing value reporting"""
        df = sample_raw_data.copy()
        df.loc[0, 'payment_value'] = np.nan
        
        df_result = handle_missing_values(df, strategy='report')
        assert df_result.isna().sum().sum() == 1
    
    def test_handle_missing_values_drop(self, sample_raw_data):
        """Test missing value dropping"""
        df = sample_raw_data.copy()
        df.loc[0:5, 'payment_value'] = np.nan
        
        df_result = handle_missing_values(df, strategy='drop')
        assert df_result.isna().sum().sum() == 0
        assert len(df_result) < len(df)
    
    def test_remove_duplicates(self, sample_raw_data):
        """Test duplicate removal"""
        df = sample_raw_data.copy()
        df = pd.concat([df, df.iloc[0:5]], ignore_index=True)
        
        df_result = remove_duplicates(df, subset=['order_id'])
        assert len(df_result) == len(sample_raw_data)
    
    def test_remove_duplicates_no_duplicates(self, sample_raw_data):
        """Test duplicate removal when no duplicates"""
        df = sample_raw_data.copy()
        df_result = remove_duplicates(df, subset=['order_id'])
        assert len(df_result) == len(df)


class TestWinsorization:
    """Test Winsorization functionality"""
    
    def test_apply_winsorization(self):
        """Test Winsorization caps outliers"""
        df = pd.DataFrame({
            'value': [1, 2, 3, 4, 5, 100, 200, 1000]
        })
        
        df_result = apply_winsorization(df, ['value'], limits=(0.0, 0.25))
        
        # Winsorization should have capped the extreme values
        assert df_result['value'].max() <= 1000
        assert df_result['value'].min() >= 1
    
    def test_apply_winsorization_nonexistent_column(self):
        """Test Winsorization with nonexistent column"""
        df = pd.DataFrame({'value': [1, 2, 3]})
        df_result = apply_winsorization(df, ['nonexistent'], limits=(0.0, 0.25))
        assert len(df_result) == len(df)


class TestDataValidation:
    """Test data validation"""
    
    def test_validate_data_success(self, sample_raw_data):
        """Test successful validation"""
        assert validate_data(sample_raw_data) is True
    
    def test_validate_data_empty_column(self):
        """Test validation fails with empty column"""
        df = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': [np.nan, np.nan, np.nan]
        })
        
        with pytest.raises(ValueError):
            validate_data(df)
    
    def test_validate_data_negative_payment(self):
        """Test validation fails with negative payment"""
        df = pd.DataFrame({
            'payment_value': [100, -50, 200]
        })
        
        with pytest.raises(ValueError):
            validate_data(df)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
