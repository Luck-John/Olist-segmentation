"""
Feature engineering module - RFM and other customer features
"""
import pandas as pd
import numpy as np
from typing import Tuple
from scipy.stats import mstats

from src.utils.config import load_config, get_logger


logger = get_logger(__name__)


def calculate_rfm(df: pd.DataFrame, snapshot_date: pd.Timestamp) -> pd.DataFrame:
    """
    Calculate RFM (Recency, Frequency, Monetary) metrics for delivered orders only.
    
    Args:
        df: Raw data (must include order_purchase_timestamp, order_status, order_id, customer_unique_id, payment_value)
        snapshot_date: Reference date for recency calculation
    
    Returns:
        DataFrame with columns: customer_unique_id, Recency, Frequency, Monetary
    """
    # Filter for delivered orders only
    delivered = df[df['order_status'] == 'delivered'].copy()
    
    # Recency: days since last order
    recency = delivered.groupby('customer_unique_id')['order_purchase_timestamp'].apply(
        lambda x: (snapshot_date - x.max()).days
    ).reset_index()
    recency.columns = ['customer_unique_id', 'Recency']
    
    # Frequency: number of orders
    frequency = delivered.groupby('customer_unique_id')['order_id'].nunique().reset_index()
    frequency.columns = ['customer_unique_id', 'Frequency']
    
    # Monetary: sum of payment value (take first payment per order to avoid duplication)
    order_payment = delivered.groupby('order_id')['payment_value'].first().reset_index()
    order_payment = order_payment.merge(
        delivered[['order_id', 'customer_unique_id']].drop_duplicates(subset=['order_id']),
        on='order_id'
    )
    monetary = order_payment.groupby('customer_unique_id')['payment_value'].sum().reset_index()
    monetary.columns = ['customer_unique_id', 'Monetary']
    
    # Merge all components
    rfm = recency.merge(frequency, on='customer_unique_id')
    rfm = rfm.merge(monetary, on='customer_unique_id', how='left').fillna(0)
    
    logger.info(f"RFM calculated for {len(rfm)} customers")
    return rfm


def calculate_delivery_metrics(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate delivery quality metrics.
    
    Args:
        df: DataFrame with order_delivered_customer_date, order_estimated_delivery_date,
            order_purchase_timestamp, customer_unique_id
    
    Returns:
        Tuple of (avg_delivery_days, late_delivery_rate, avg_delivery_delta)
    """
    df_del = df[df['order_delivered_customer_date'].notna()].copy()
    
    # Average delivery time
    df_del['delivery_days'] = (
        df_del['order_delivered_customer_date'] - df_del['order_purchase_timestamp']
    ).dt.days
    avg_delivery = df_del.groupby('customer_unique_id')['delivery_days'].mean()
    
    # Late delivery rate
    df_del['is_late'] = (
        df_del['order_delivered_customer_date'] > df_del['order_estimated_delivery_date']
    ).astype(int)
    late_rate = df_del.groupby('customer_unique_id')['is_late'].mean()
    
    # Average delivery delta (negative = early, positive = late)
    df_del['delivery_delta'] = (
        df_del['order_estimated_delivery_date'] - df_del['order_delivered_customer_date']
    ).dt.days
    avg_delivery_delta = df_del.groupby('customer_unique_id')['delivery_delta'].mean()
    
    logger.info(f"Delivery metrics calculated for {len(avg_delivery)} customers")
    return avg_delivery, late_rate, avg_delivery_delta


def calculate_review_metrics(df: pd.DataFrame, snapshot_date: pd.Timestamp, latency_days: int = 7) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Calculate review-based metrics (considering latency for recent reviews).
    
    Args:
        df: DataFrame with review_score, review_creation_date, order_delivered_customer_date
        snapshot_date: Current reference date
        latency_days: Days to exclude recent reviews
    
    Returns:
        Tuple of (avg_review_score_full, has_full_review, avg_review_score_available, has_available_review)
    """
    # Get first review per order (aggregate by order_id)
    delivered = df[df['order_status'] == 'delivered'].copy()
    order_review = delivered.groupby('order_id')['review_score'].first().reset_index()
    order_review = order_review.merge(
        delivered[['order_id', 'customer_unique_id', 'review_creation_date', 'order_delivered_customer_date']].drop_duplicates(subset=['order_id']),
        on='order_id'
    )
    
    # Full reviews (all available)
    avg_review_full = order_review.groupby('customer_unique_id')['review_score'].mean()
    has_review_full = order_review.groupby('customer_unique_id')['review_score'].apply(
        lambda x: x.notna().any().astype(int)
    )
    
    # Available reviews (excluding recent ones due to latency)
    available_date = snapshot_date - pd.Timedelta(days=latency_days)
    filtered_reviews = order_review[
        (order_review['review_creation_date'] <= available_date) &
        (order_review['order_delivered_customer_date'] <= available_date)
    ]
    
    avg_review_available = filtered_reviews.groupby('customer_unique_id')['review_score'].mean()
    has_review_available = filtered_reviews.groupby('customer_unique_id')['review_score'].apply(
        lambda x: x.notna().any().astype(int)
    )
    
    logger.info(f"Review metrics calculated")
    return avg_review_full, has_review_full, avg_review_available, has_review_available


def calculate_clv(df_rfm: pd.DataFrame, dataset_duration_days: int) -> pd.Series:
    """
    Calculate Customer Lifetime Value (CLV) estimate.
    
    Args:
        df_rfm: DataFrame with Monetary and Frequency columns
        dataset_duration_days: Total duration of dataset in days
    
    Returns:
        Series with CLV values (must be positive)
    """
    dataset_duration_years = dataset_duration_days / 365.25
    clv = df_rfm['Monetary'] * (df_rfm['Frequency'] / dataset_duration_years)

    # Validate that CLV is always positive (use explicit check instead of assert)
    if not (clv >= 0).all():
        raise ValueError("CLV must always be positive — check Monetary and Frequency columns.")

    logger.info(f"CLV calculated. Mean: {clv.mean():.2f}, Max: {clv.max():.2f}")
    return clv


def apply_log_transformation(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """
    Apply log1p transformation to specified columns.
    
    Args:
        df: Input DataFrame
        columns: Columns to transform
    
    Returns:
        DataFrame with new _log columns
    """
    df = df.copy()
    
    for col in columns:
        if col in df.columns:
            df[f'{col}_log'] = np.log1p(df[col])
            logger.debug(f"Applied log1p transformation to {col}")
    
    return df


def calculate_geographic_metrics(df: pd.DataFrame, reference_coords: Tuple[float, float]) -> pd.Series:
    """
    Calculate geographic features (distance to São Paulo).
    
    Args:
        df: DataFrame with customer_lat and customer_lng
        reference_coords: Tuple of (lat, lng) reference point
    
    Returns:
        Series with distance in kilometers
    """
    try:
        import haversine as hs
        from haversine import Unit
    except ImportError:
        logger.warning("haversine not installed, skipping distance calculation")
        return pd.Series([np.nan] * len(df))
    
    customer_lat = df.groupby('customer_unique_id')['customer_lat'].mean()
    customer_lng = df.groupby('customer_unique_id')['customer_lng'].mean()
    
    distances = []
    for idx in customer_lat.index:
        lat, lng = customer_lat[idx], customer_lng[idx]
        if pd.notna(lat) and pd.notna(lng):
            customer_coords = (lat, lng)
            dist = hs.haversine(reference_coords, customer_coords, unit=Unit.KILOMETERS)
            distances.append(dist)
        else:
            distances.append(np.nan)
    
    result = pd.Series(distances, index=customer_lat.index)
    logger.info(f"Geographic metrics calculated for {len(result)} customers")
    return result


class FeatureEngineer:
    """Main class for feature engineering"""
    
    def __init__(self, config=None):
        """Initialize with configuration"""
        self.config = config or load_config()
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Main pipeline to engineer all features.
        
        Args:
            df: Preprocessed DataFrame
        
        Returns:
            DataFrame with engineered features
        """
        # Calculate snapshot date
        snapshot_date = df['order_purchase_timestamp'].max() + pd.Timedelta(days=1)
        dataset_duration = (df['order_purchase_timestamp'].max() - df['order_purchase_timestamp'].min()).days
        if dataset_duration <= 0:
            # Avoid division by zero in CLV for single-order / short windows
            dataset_duration = 1
        
        logger.info(f"Snapshot date: {snapshot_date.date()}")
        logger.info(f"Dataset duration: {dataset_duration} days")
        
        # Start with RFM
        df_client = calculate_rfm(df, snapshot_date)
        
        # Add delivery metrics
        avg_del, late_rate, avg_delta = calculate_delivery_metrics(df)
        df_client['avg_delivery_days'] = df_client['customer_unique_id'].map(avg_del)
        df_client['late_delivery_rate'] = df_client['customer_unique_id'].map(late_rate)
        df_client['avg_delivery_delta'] = df_client['customer_unique_id'].map(avg_delta)
        
        # Add review metrics
        avg_rev_full, has_rev_full, avg_rev_avail, has_rev_avail = calculate_review_metrics(
            df, snapshot_date, latency_days=self.config['data']['snapshot_lag_days']
        )
        df_client['avg_review_score_full'] = df_client['customer_unique_id'].map(avg_rev_full)
        df_client['has_full_review'] = df_client['customer_unique_id'].map(has_rev_full)
        df_client['avg_review_score_available'] = df_client['customer_unique_id'].map(avg_rev_avail)
        df_client['has_available_review'] = df_client['customer_unique_id'].map(has_rev_avail)
        
        # Add CLV
        df_client['CLV'] = calculate_clv(df_client[['Monetary', 'Frequency']], dataset_duration)
        
        # Add geographic metrics
        sao_paulo = tuple(self.config['feature_engineering']['sao_paulo_coords'])
        dist = calculate_geographic_metrics(df, sao_paulo)
        df_client['dist_sao_paulo'] = df_client['customer_unique_id'].map(dist)
        
        # Fill NaN values
        numeric_cols = df_client.select_dtypes(include='number').columns
        for col in numeric_cols:
            if df_client[col].isna().any():
                df_client[col] = df_client[col].fillna(df_client[col].median())

        # If some columns are still NaN (e.g., all-NaN medians on small samples),
        # apply safe fallbacks to keep features usable for prediction.
        if "avg_review_score_available" in df_client.columns and df_client["avg_review_score_available"].isna().any():
            df_client["avg_review_score_available"] = df_client["avg_review_score_available"].fillna(
                df_client.get("avg_review_score_full")
            )
        if "has_available_review" in df_client.columns and df_client["has_available_review"].isna().any():
            df_client["has_available_review"] = df_client["has_available_review"].fillna(
                df_client.get("has_full_review", 0)
            )
        if "dist_sao_paulo" in df_client.columns and df_client["dist_sao_paulo"].isna().any():
            df_client["dist_sao_paulo"] = df_client["dist_sao_paulo"].fillna(0)
        
        logger.info(f"Features engineered. Final shape: {df_client.shape}")
        return df_client


if __name__ == "__main__":
    # Test the feature engineer
    from src.data.preprocessing import load_data
    
    df = load_data("data/base_final.csv")
    engineer = FeatureEngineer()
    df_features = engineer.engineer_features(df)
    print(df_features.head())
