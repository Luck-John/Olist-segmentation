"""
Clustering preprocessing - Reproduces notebook transformations exactly
"""
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from src.utils.config import get_logger

logger = get_logger(__name__)


class ClusteringPreprocessor:
    """
    Transform raw engineered features into clustering-ready data.
    Reproduces exactly: log transforms → bucketing → selection → scaling → PCA
    """
    
    # 7 features selected for clustering in notebook (FEATURES_FINAL)
    FEATURES_FINAL = [
        "log_recency",
        "recency_score_10",
        "log_monetary",
        "log_item_price",
        "installment_level",
        "review_raw",
        "log_delivery",
    ]
    
    PCA_COMPONENTS = 5
    PCA_WHITEN = True
    OUTLIER_CLIP_QUANTILE = 0.99
    
    def __init__(self, random_state=42):
        self.random_state = random_state
        self.scaler = None
        self.pca = None
        self.fitted = False
    
    def apply_log_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply LOG1P transformations to stabilize distributions.
        Recreates notebook cell: log_recency, log_monetary, log_item_price, log_delivery
        """
        df = df.copy()
        
        # Ensure source columns exist
        required_cols = ["Recency", "Monetary", "avg_item_price", "avg_delivery_days"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns for log transforms: {missing}")
        
        df["log_recency"] = np.log1p(df["Recency"]).astype("float32")
        df["log_monetary"] = np.log1p(df["Monetary"]).astype("float32")
        df["log_item_price"] = np.log1p(df["avg_item_price"]).astype("float32")
        df["log_delivery"] = np.log1p(df["avg_delivery_days"]).astype("float32")
        
        logger.info("Applied log1p transformations (4 features)")
        return df
    
    def apply_bucketing(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply bucketing/ordinalisation transformations.
        Recreates notebook cell: recency_score_10, installment_level, review_raw
        """
        df = df.copy()
        
        # Recency score: 10-level bucketing
        if "Recency" in df.columns:
            df["recency_score_10"] = (
                10 - pd.qcut(
                    df["Recency"],
                    q=10,
                    labels=False,
                    duplicates="drop"
                )
            ).astype("float32")
        else:
            raise ValueError("Missing 'Recency' column for recency_score_10")
        
        # Installment level: 4-level binning
        if "avg_installments" in df.columns:
            df["installment_level"] = pd.cut(
                df["avg_installments"],
                bins=[-0.1, 1.0, 3.0, 6.0, 100.0],
                labels=[0, 1, 2, 3],
                include_lowest=True
            ).astype("float32")
        else:
            raise ValueError("Missing 'avg_installments' column for installment_level")
        
        # Review raw: clip to [1, 5]
        if "avg_review_score" in df.columns:
            df["review_raw"] = df["avg_review_score"].clip(1, 5).astype("float32")
        else:
            raise ValueError("Missing 'avg_review_score' column for review_raw")
        
        logger.info("Applied bucketing transformations (3 features)")
        return df
    
    def select_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Select only FEATURES_FINAL (7 active features for clustering).
        Excludes Frequency (96.9% = 1, quasi-constant).
        """
        missing = [c for c in self.FEATURES_FINAL if c not in df.columns]
        if missing:
            raise ValueError(f"Missing features for selection: {missing}")
        
        df_selected = df[self.FEATURES_FINAL].copy()
        
        # Ensure numeric type
        for col in self.FEATURES_FINAL:
            df_selected[col] = pd.to_numeric(df_selected[col], errors='coerce')
        
        # Fill any NaN that might have resulted from coercion
        df_selected = df_selected.fillna(df_selected.median())
        
        logger.info(f"Selected {len(self.FEATURES_FINAL)} features for clustering")
        return df_selected
    
    def cap_outliers(self, X: pd.DataFrame, quantile: float = None) -> pd.DataFrame:
        """
        Cap outliers at specified quantile (notebook uses q=0.99).
        """
        if quantile is None:
            quantile = self.OUTLIER_CLIP_QUANTILE
        
        X_capped = X.copy()
        for col in X.columns:
            q_lower = X_capped[col].quantile(1 - quantile)
            q_upper = X_capped[col].quantile(quantile)
            X_capped[col] = X_capped[col].clip(lower=q_lower, upper=q_upper)
        
        logger.debug(f"Capped outliers at quantiles {1-quantile:.2%} - {quantile:.2%}")
        return X_capped
    
    def fit_preprocessing(self, df: pd.DataFrame) -> np.ndarray:
        """
        Fit scaler and PCA on training features.
        Steps: cap outliers → StandardScaler → PCA(5, whiten=True)
        
        Args:
            df: DataFrame with FEATURES_FINAL columns
        
        Returns:
            Transformed array shape (n, PCA_COMPONENTS)
        """
        # Step 1: Apply all transformations to get FEATURES_FINAL
        df_transformed = self.apply_log_transforms(df)
        df_transformed = self.apply_bucketing(df_transformed)
        X = self.select_features(df_transformed)
        
        # Step 2: Cap outliers
        X_capped = self.cap_outliers(X)
        
        # Step 3: Standardize
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X_capped)
        
        # Step 4: PCA with whitening
        self.pca = PCA(
            n_components=self.PCA_COMPONENTS,
            whiten=self.PCA_WHITEN,
            random_state=self.random_state
        )
        X_pca = self.pca.fit_transform(X_scaled)
        
        self.fitted = True
        
        logger.info(
            f"Preprocessing fitted. "
            f"PCA variance explained: {self.pca.explained_variance_ratio_.sum():.2%}"
        )
        return X_pca
    
    def transform_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Apply preprocessing (transformations + scaling + PCA) to new data.
        
        Args:
            df: DataFrame with raw features
        
        Returns:
            Transformed array shape (n, PCA_COMPONENTS)
        """
        if not self.fitted:
            raise ValueError("Preprocessor not fitted. Call fit_preprocessing first.")
        
        # Step 1: Apply all transformations to get FEATURES_FINAL
        df_transformed = self.apply_log_transforms(df)
        df_transformed = self.apply_bucketing(df_transformed)
        X = self.select_features(df_transformed)
        
        # Step 2: Cap outliers (using same quantile as training)
        X_capped = self.cap_outliers(X)
        
        # Step 3: Standardize using fitted scaler
        X_scaled = self.scaler.transform(X_capped)
        
        # Step 4: PCA transform
        X_pca = self.pca.transform(X_scaled)
        
        logger.debug(f"Transformed {len(X)} samples")
        return X_pca
    
    def get_pca_components(self) -> pd.DataFrame:
        """
        Return PCA components as DataFrame for interpretability.
        """
        if self.pca is None:
            raise ValueError("PCA not fitted yet")
        
        components_df = pd.DataFrame(
            self.pca.components_,
            columns=self.FEATURES_FINAL,
            index=[f"PC{i+1}" for i in range(self.PCA_COMPONENTS)]
        )
        return components_df
    
    def get_explained_variance(self) -> dict:
        """
        Return explained variance information.
        """
        if self.pca is None:
            raise ValueError("PCA not fitted yet")
        
        return {
            "explained_variance": self.pca.explained_variance_,
            "explained_variance_ratio": self.pca.explained_variance_ratio_,
            "cumulative_variance_ratio": np.cumsum(self.pca.explained_variance_ratio_),
        }
