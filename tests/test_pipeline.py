"""
Integration tests for the full Olist segmentation pipeline.

Tests cover:
- End-to-end flow: preprocessing → feature engineering → clustering
- MLflow tracking: verifies that params and metrics are logged at each run
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock, call
from sklearn.preprocessing import StandardScaler

from src.clustering.models import KMeansClustering, DBSCANClustering, HierarchicalClustering
from src.data.preprocessing import (
    convert_dates,
    handle_missing_values,
    remove_duplicates,
    validate_data,
)
from src.features.engineering import (
    calculate_rfm,
    calculate_clv,
    apply_log_transformation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_raw_df(n_rows: int = 60, n_customers: int = 10) -> pd.DataFrame:
    """Build a minimal raw DataFrame for integration tests."""
    np.random.seed(0)
    return pd.DataFrame(
        {
            "order_id": np.arange(n_rows),
            "customer_unique_id": np.random.choice(n_customers, n_rows),
            "order_purchase_timestamp": pd.date_range("2022-01-01", periods=n_rows, freq="D"),
            "order_approved_at": pd.date_range("2022-01-02", periods=n_rows, freq="D"),
            "order_delivered_customer_date": pd.date_range("2022-01-10", periods=n_rows, freq="D"),
            "order_estimated_delivery_date": pd.date_range("2022-01-09", periods=n_rows, freq="D"),
            "order_status": ["delivered"] * (n_rows - 5) + ["canceled"] * 5,
            "payment_value": np.random.uniform(30, 400, n_rows),
            "review_score": np.random.choice([1, 2, 3, 4, 5], n_rows),
            "review_creation_date": pd.date_range("2022-01-11", periods=n_rows, freq="D"),
            "customer_lat": np.random.uniform(-25, -22, n_rows),
            "customer_lng": np.random.uniform(-48, -46, n_rows),
            "seller_id": np.random.choice(5, n_rows),
            "payment_type": np.random.choice(["credit_card", "boleto"], n_rows),
            "payment_installments": np.random.choice([1, 2, 3], n_rows),
            "freight_value": np.random.uniform(5, 50, n_rows),
            "price": np.random.uniform(30, 300, n_rows),
            "order_item_id": np.arange(n_rows),
            "product_id": np.random.choice(10, n_rows),
            "super_categorie": np.random.choice(["electronics", "books", "home"], n_rows),
        }
    )


def _make_scaled_data(n_samples: int = 30, n_features: int = 5) -> np.ndarray:
    """Return a small scaled matrix suitable for clustering tests."""
    np.random.seed(42)
    X = np.random.randn(n_samples, n_features)
    return StandardScaler().fit_transform(X)


def _make_config() -> dict:
    """Return a minimal configuration dictionary for tests."""
    return {
        "random_state": 42,
        "data": {
            "base_final": "base_final.csv",
            "snapshot_lag_days": 7,
            "date_columns": ["order_purchase_timestamp"],
        },
        "clustering": {
            "kmeans": {
                "k_min": 2,
                "k_max": 3,
                "init": "k-means++",
                "n_init": 5,
                "max_iter": 100,
            },
            "dbscan": {
                "eps_min": 0.5,
                "eps_max": 1.0,
                "eps_step": 0.5,
                "min_samples": 3,
            },
            "hierarchical": {
                "linkage_methods": ["ward"],
                "distance_metric": "euclidean",
            },
        },
        "pca": {"n_components": 2, "explained_variance_threshold": 0.85},
        "feature_engineering": {"sao_paulo_coords": [-23.55, -46.63]},
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "log_file": "logs/test.log",
        },
    }


# ---------------------------------------------------------------------------
# 1. Integration test — preprocessing → RFM → clustering
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestFullPipeline:
    """End-to-end pipeline: raw data → RFM features → KMeans clustering."""

    def test_preprocessing_to_rfm(self):
        """Preprocessing output feeds correctly into RFM calculation."""
        df = _make_raw_df()

        # Preprocessing steps
        df = remove_duplicates(df, subset=["order_id"])
        df = handle_missing_values(df, strategy="drop")

        assert len(df) > 0, "DataFrame should not be empty after preprocessing"

        # RFM calculation
        snapshot_date = df["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
        rfm = calculate_rfm(df, snapshot_date)

        assert len(rfm) > 0, "RFM output should contain at least one customer"
        assert set(rfm.columns).issuperset({"customer_unique_id", "Recency", "Frequency", "Monetary"})
        assert (rfm["Recency"] >= 0).all(), "Recency values must be non-negative"
        assert (rfm["Frequency"] > 0).all(), "Frequency values must be positive"
        assert (rfm["Monetary"] >= 0).all(), "Monetary values must be non-negative"

    def test_rfm_to_clustering(self):
        """RFM features can be scaled and fed into KMeans without error."""
        df = _make_raw_df()
        snapshot_date = df["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
        rfm = calculate_rfm(df, snapshot_date)

        # Scale RFM features
        feature_cols = ["Recency", "Frequency", "Monetary"]
        X_scaled = StandardScaler().fit_transform(rfm[feature_cols].values)

        config = _make_config()
        with patch("mlflow.start_run"), patch("mlflow.log_param"), patch("mlflow.log_metric"), \
                patch("mlflow.sklearn.log_model"):
            kmeans = KMeansClustering(config)
            results = kmeans.fit_range(X_scaled, k_range=(2, 3))

        assert len(results) == 2, "Should have results for k=2 and k=3"
        for k, metrics in results.items():
            assert "n_clusters" in metrics
            assert metrics["n_clusters"] == k

    def test_clv_after_rfm(self):
        """CLV is positive and has the correct length after RFM calculation."""
        df = _make_raw_df()
        snapshot_date = df["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
        rfm = calculate_rfm(df, snapshot_date)

        dataset_duration = (
            df["order_purchase_timestamp"].max() - df["order_purchase_timestamp"].min()
        ).days

        clv = calculate_clv(rfm[["Monetary", "Frequency"]], dataset_duration_days=dataset_duration)

        assert len(clv) == len(rfm)
        assert (clv >= 0).all(), "All CLV values must be non-negative"

    def test_log_transform_after_rfm(self):
        """Log transformation creates _log columns for RFM metrics."""
        df = _make_raw_df()
        snapshot_date = df["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
        rfm = calculate_rfm(df, snapshot_date)

        rfm_log = apply_log_transformation(rfm, ["Recency", "Frequency", "Monetary"])

        assert "Recency_log" in rfm_log.columns
        assert "Frequency_log" in rfm_log.columns
        assert "Monetary_log" in rfm_log.columns


# ---------------------------------------------------------------------------
# 2. MLflow tracking tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestMLflowTracking:
    """Verify that MLflow logging is called correctly for each algorithm."""

    def test_kmeans_logs_params_and_metrics(self):
        """KMeans must log n_clusters, algorithm, and silhouette/inertia metrics."""
        X = _make_scaled_data()
        config = _make_config()

        with patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_param") as mock_log_param, \
             patch("mlflow.log_metric") as mock_log_metric, \
             patch("mlflow.sklearn.log_model"):

            mock_run.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_run.return_value.__exit__ = MagicMock(return_value=False)

            kmeans = KMeansClustering(config)
            kmeans.fit_range(X, k_range=(2, 3))

        # start_run called once per k value
        assert mock_run.call_count == 2

        # log_param must have been called with algorithm=kmeans
        param_calls = [c for c in mock_log_param.call_args_list if "algorithm" in str(c)]
        assert len(param_calls) > 0, "mlflow.log_param('algorithm', ...) should be called"

        # log_metric must have been called at least for inertia
        metric_calls = [c for c in mock_log_metric.call_args_list if "inertia" in str(c)]
        assert len(metric_calls) > 0, "mlflow.log_metric('inertia', ...) should be called"

    def test_dbscan_logs_eps_and_min_samples(self):
        """DBSCAN must log eps and min_samples as parameters."""
        X = _make_scaled_data()
        config = _make_config()

        with patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_param") as mock_log_param, \
             patch("mlflow.log_metric"):

            mock_run.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_run.return_value.__exit__ = MagicMock(return_value=False)

            dbscan = DBSCANClustering(config)
            dbscan.fit_range(X, eps_range=(0.5, 1.0))

        eps_calls = [c for c in mock_log_param.call_args_list if "eps" in str(c)]
        min_calls = [c for c in mock_log_param.call_args_list if "min_samples" in str(c)]

        assert len(eps_calls) > 0, "mlflow.log_param('eps', ...) should be called"
        assert len(min_calls) > 0, "mlflow.log_param('min_samples', ...) should be called"

    def test_hierarchical_logs_linkage(self):
        """Hierarchical clustering must log the linkage method as a parameter."""
        X = _make_scaled_data()
        config = _make_config()

        with patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_param") as mock_log_param, \
             patch("mlflow.log_metric"):

            mock_run.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_run.return_value.__exit__ = MagicMock(return_value=False)

            hc = HierarchicalClustering(config)
            hc.fit_linkages(X, n_clusters=3)

        linkage_calls = [c for c in mock_log_param.call_args_list if "linkage" in str(c)]
        assert len(linkage_calls) > 0, "mlflow.log_param('linkage', ...) should be called"

    def test_mlflow_run_name_contains_algorithm(self):
        """The MLflow run name must include the algorithm name and key hyperparameter."""
        X = _make_scaled_data()
        config = _make_config()

        with patch("mlflow.start_run") as mock_run, \
             patch("mlflow.log_param"), \
             patch("mlflow.log_metric"), \
             patch("mlflow.sklearn.log_model"):

            mock_run.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_run.return_value.__exit__ = MagicMock(return_value=False)

            kmeans = KMeansClustering(config)
            kmeans.fit_range(X, k_range=(2, 2))

        run_names = [
            c.kwargs.get("run_name", "") or (c.args[0] if c.args else "")
            for c in mock_run.call_args_list
        ]
        assert any("KMeans" in name for name in run_names), (
            "MLflow run name should contain 'KMeans'"
        )


# ---------------------------------------------------------------------------
# 3. Regression tests — validate data quality contracts
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDataContracts:
    """Regression tests that ensure data quality contracts are respected."""

    def test_remove_duplicates_is_idempotent(self):
        """Calling remove_duplicates twice should yield the same result."""
        df = _make_raw_df()
        df_once = remove_duplicates(df, subset=["order_id"])
        df_twice = remove_duplicates(df_once, subset=["order_id"])
        assert len(df_once) == len(df_twice)

    def test_convert_dates_preserves_row_count(self):
        """Date conversion must not drop any rows."""
        df = _make_raw_df()
        df["order_purchase_timestamp"] = df["order_purchase_timestamp"].astype(str)
        df_converted = convert_dates(df, ["order_purchase_timestamp"])
        assert len(df_converted) == len(df)

    def test_clv_clips_negative_monetary_to_zero(self):
        """calculate_clv must clip negative Monetary to 0 (no ValueError raised)."""
        df_bad = pd.DataFrame({"Monetary": [-100, 200], "Frequency": [1, 2]})
        clv = calculate_clv(df_bad, dataset_duration_days=365)
        # Negative Monetary is clipped to 0; positive Monetary yields positive CLV
        assert clv.iloc[0] == 0.0, "Negative Monetary must produce CLV = 0"
        assert clv.iloc[1] > 0, "Positive Monetary must produce positive CLV"

    def test_validate_data_rejects_negative_payment(self):
        """validate_data must raise ValueError for negative payment_value."""
        df = pd.DataFrame({"payment_value": [100, -10, 50]})
        with pytest.raises(ValueError):
            validate_data(df)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not integration"])
