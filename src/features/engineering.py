"""
Feature engineering module - RFM and other customer features
"""
import pandas as pd
import numpy as np
from typing import Tuple, Dict
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
        Series with CLV values (>= 0)
    """
    # Use at least 1 day to avoid division by zero (single-order edge case)
    duration = max(int(dataset_duration_days), 1)
    dataset_duration_years = duration / 365.25
    clv = df_rfm['Monetary'] * (df_rfm['Frequency'] / dataset_duration_years)

    # Clean numerical artefacts (inf, -inf, NaN) → 0
    clv = clv.replace([np.inf, -np.inf], 0).fillna(0).clip(lower=0)

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


def calculate_payment_metrics(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate average installments and freight ratio.
    
    Args:
        df: DataFrame with payment_installments and freight_value, price columns
    
    Returns:
        Tuple of (avg_installments, avg_freight_ratio) Series
    """
    # Average installments per customer
    avg_inst = df.groupby('customer_unique_id')['payment_installments'].mean()
    avg_inst = avg_inst.fillna(1)  # Default to 1 if no payment info
    
    # Average freight ratio (freight_value / price, handling division by zero)
    df_copy = df.copy()
    df_copy['freight_ratio'] = df_copy.apply(
        lambda row: row['freight_value'] / row['price'] if row['price'] > 0 else 0,
        axis=1
    )
    avg_freight = df_copy.groupby('customer_unique_id')['freight_ratio'].mean()
    
    logger.info(f"Payment metrics calculated for {len(avg_inst)} customers")
    return avg_inst, avg_freight


def calculate_temporal_features(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """
    Extract temporal features: purchase hour and day of week.
    
    Args:
        df: DataFrame with order_purchase_timestamp
    
    Returns:
        Tuple of (most_frequent_hour, most_frequent_day) Series
    """
    df_copy = df.copy()
    df_copy['purchase_hour'] = pd.to_datetime(df_copy['order_purchase_timestamp']).dt.hour
    df_copy['purchase_day'] = pd.to_datetime(df_copy['order_purchase_timestamp']).dt.dayofweek
    
    # Most frequent purchase hour
    most_freq_hour = df_copy.groupby('customer_unique_id')['purchase_hour'].apply(
        lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0]
    )
    
    # Most frequent purchase day
    most_freq_day = df_copy.groupby('customer_unique_id')['purchase_day'].apply(
        lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0]
    )
    
    logger.info(f"Temporal features calculated for {len(most_freq_hour)} customers")
    return most_freq_hour, most_freq_day


def calculate_category_spend(df: pd.DataFrame, categories: list = None) -> Dict[str, pd.Series]:
    """
    Calculate spending by product category.
    
    Args:
        df: DataFrame with super_categorie and price
        categories: List of category names to track (e.g., ['health_beauty', 'home'])
    
    Returns:
        Dictionary mapping category name to spending Series
    """
    if categories is None:
        categories = ['health_beauty', 'home']
    
    df_copy = df.copy()
    df_copy['super_categorie'] = df_copy['super_categorie'].fillna('unknown').str.lower()
    
    result = {}
    for cat in categories:
        # Spend on specific category
        cat_mask = df_copy['super_categorie'].str.contains(cat, na=False, case=False)
        spend = df_copy[cat_mask].groupby('customer_unique_id')['price'].sum()
        spend = spend.reindex(df_copy['customer_unique_id'].unique(), fill_value=0)
        result[f"spend_('price', '{cat}')"] = spend
    
    logger.info(f"Category spend calculated for {len(result)} categories")
    return result


def calculate_basket_size(df: pd.DataFrame) -> pd.Series:
    """
    Calculate average basket size (average order value per customer).
    
    Args:
        df: DataFrame with price and order_id
    
    Returns:
        Series with average basket size (avg price per order)
    """
    # Group by order to get order totals
    order_totals = df.groupby(['customer_unique_id', 'order_id'])['price'].sum().reset_index()
    
    # Calculate average basket size per customer
    basket_size = order_totals.groupby('customer_unique_id')['price'].mean()
    basket_size = basket_size.fillna(0)
    
    logger.info(f"Basket size calculated for {len(basket_size)} customers")
    return basket_size


class FeatureEngineer:
    """Main class for feature engineering"""
    
    # Columns expected by downstream metric helpers (API / sparse JSON payloads may omit them)
    _OPTIONAL_RAW_COLUMNS = [
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
        "review_score",
        "review_creation_date",
        "customer_lat",
        "customer_lng",
    ]
    
    def __init__(self, config=None):
        """Initialize with configuration"""
        self.config = config or load_config()
    
    def _ensure_raw_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add optional Olist columns as NA so feature helpers never KeyError on sparse input."""
        df = df.copy()
        for col in self._OPTIONAL_RAW_COLUMNS:
            if col not in df.columns:
                if col in ("order_delivered_customer_date", "order_estimated_delivery_date", "review_creation_date"):
                    df[col] = pd.NaT
                else:
                    df[col] = np.nan
        return df
    
    def engineer_features(self, df: pd.DataFrame, snapshot_date: pd.Timestamp = None) -> pd.DataFrame:
        """
        Main pipeline to engineer ONLY the 5 active features needed for clustering.
        
        Features calculated:
        1. Recency
        2. avg_review_score_full
        3. avg_delivery_days
        4. avg_installments
        5. CLV_estimate
        
        Args:
            df: Preprocessed DataFrame
            snapshot_date: Reference date for RFM calculation. If None, uses max(order_purchase_timestamp) + 1 day.
                          For API single-order predictions, pass today's date.
        
        Returns:
            DataFrame with 5 engineered features
        """
        df = self._ensure_raw_columns(df)
        
        # Calculate snapshot date
        if snapshot_date is None:
            snapshot_date = df['order_purchase_timestamp'].max() + pd.Timedelta(days=1)
        else:
            snapshot_date = pd.Timestamp(snapshot_date)
        dataset_duration = (df['order_purchase_timestamp'].max() - df['order_purchase_timestamp'].min()).days
        if dataset_duration <= 0:
            dataset_duration = 1
        
        logger.info(f"Snapshot date: {snapshot_date.date()}")
        logger.info(f"Dataset duration: {dataset_duration} days")
        
        # === FEATURE 1 & 2: RFM (Recency, Frequency, Monetary) ===
        df_client = calculate_rfm(df, snapshot_date)
        if df_client.empty:
            raise ValueError(
                "Cannot calculate RFM: no orders with order_status='delivered'. "
                "Add at least one delivered order for prediction."
            )
        
        # === FEATURE 3: avg_delivery_days ===
        avg_del, late_rate, avg_delta = calculate_delivery_metrics(df)
        df_client['avg_delivery_days'] = df_client['customer_unique_id'].map(avg_del)
        
        # === FEATURE 2: avg_review_score_full ===
        avg_rev_full, has_rev_full, avg_rev_avail, has_rev_avail = calculate_review_metrics(
            df, snapshot_date, latency_days=self.config['data']['snapshot_lag_days']
        )
        df_client['avg_review_score_full'] = df_client['customer_unique_id'].map(avg_rev_full)
        
        # === FEATURE 5: CLV_estimate ===
        clv = calculate_clv(df_client[['Monetary', 'Frequency']], dataset_duration)
        df_client['CLV_estimate'] = clv
        
        # === FEATURE 4: avg_installments ===
        avg_inst, avg_freight = calculate_payment_metrics(df)
        df_client['avg_installments'] = df_client['customer_unique_id'].map(avg_inst)
        
        # === SELECT ONLY 5 FEATURES ===
        FEATURES_ACTIVE = [
            'customer_unique_id',
            'Recency',
            'avg_review_score_full',
            'avg_delivery_days',
            'avg_installments',
            'CLV_estimate'
        ]
        
        # Check all required features are present
        missing = [f for f in FEATURES_ACTIVE if f not in df_client.columns]
        if missing:
            raise ValueError(f"Missing features: {missing}")
        
        # Select only active features
        df_client = df_client[FEATURES_ACTIVE]
        
        # === FILL NaN VALUES ===
        numeric_cols = df_client.select_dtypes(include='number').columns
        for col in numeric_cols:
            if df_client[col].isna().any():
                median_val = df_client[col].median()
                if pd.isna(median_val):
                    # If median is NaN, use a default value
                    default_vals = {
                        'Recency': 365,
                        'avg_review_score_full': 3.0,
                        'avg_delivery_days': 7,
                        'avg_installments': 1,
                        'CLV_estimate': 0
                    }
                    median_val = default_vals.get(col, 0)
                df_client[col] = df_client[col].fillna(median_val)
        
        logger.info(f"Features engineered. Shape: {df_client.shape}")
        logger.info(f"Features: {list(df_client.columns)}")
        return df_client


if __name__ == "__main__":
    # Test the feature engineer
    from src.data.preprocessing import load_data
    
    df = load_data("data/base_final.csv")
    engineer = FeatureEngineer()
    df_features = engineer.engineer_features(df)
    print(df_features.head())
