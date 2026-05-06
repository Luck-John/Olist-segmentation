"""
Data loading and preprocessing module
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from scipy.stats import mstats

from src.utils.config import load_config, get_logger


logger = get_logger(__name__)


def load_data(data_path: str) -> pd.DataFrame:
    """
    Load CSV data with error handling.
    
    Args:
        data_path: Path to CSV file
    
    Returns:
        DataFrame with loaded data
    
    Raises:
        FileNotFoundError: If file not found
        pd.errors.ParserError: If CSV is malformed
    """
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    try:
        df = pd.read_csv(data_path)
        logger.info(f"Loaded {len(df)} rows from {data_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading {data_path}: {e}")
        raise


def convert_dates(df: pd.DataFrame, date_columns: list) -> pd.DataFrame:
    """
    Convert string columns to datetime.
    
    Args:
        df: Input DataFrame
        date_columns: List of column names to convert
    
    Returns:
        DataFrame with converted date columns
    """
    df = df.copy()
    for col in date_columns:
        if col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], format='mixed', errors='coerce')
            except Exception as e:
                logger.warning(f"Could not convert {col} to datetime: {e}")
    return df


def handle_missing_values(df: pd.DataFrame, strategy: str = 'report') -> pd.DataFrame:
    """
    Handle missing values in DataFrame.
    
    Args:
        df: Input DataFrame
        strategy: 'report' (just report), 'drop' (drop rows with NaN), 'impute_median'
    
    Returns:
        Cleaned DataFrame
    """
    df = df.copy()
    na_count = df.isna().sum()
    
    if (na_count > 0).any():
        logger.info(f"Found missing values:\n{na_count[na_count > 0]}")
    
    if strategy == 'report':
        return df
    elif strategy == 'drop':
        initial_len = len(df)
        df = df.dropna()
        logger.info(f"Dropped {initial_len - len(df)} rows with missing values")
        return df
    else:
        return df


def remove_duplicates(df: pd.DataFrame, subset: Optional[list] = None) -> pd.DataFrame:
    """
    Remove duplicate rows.
    
    Args:
        df: Input DataFrame
        subset: Columns to consider for identifying duplicates
    
    Returns:
        DataFrame with duplicates removed
    """
    initial_len = len(df)
    df = df.drop_duplicates(subset=subset)
    logger.info(f"Removed {initial_len - len(df)} duplicate rows")
    return df


def apply_winsorization(df: pd.DataFrame, columns: list, limits: Tuple[float, float] = (0.0, 0.005)) -> pd.DataFrame:
    """
    Apply Winsorization to specified columns to handle outliers.
    
    Args:
        df: Input DataFrame
        columns: Columns to winsorize
        limits: Tuple of (lower, upper) percentiles to clip
    
    Returns:
        DataFrame with winsorized columns
    """
    df = df.copy()
    
    for col in columns:
        if col in df.columns:
            before_max = df[col].max()
            before_mean = df[col].mean()
            
            non_nan_values = df[col].dropna()
            if not non_nan_values.empty:
                df.loc[df[col].notna(), col] = mstats.winsorize(non_nan_values, limits=limits)
                
                after_max = df[col].max()
                after_mean = df[col].mean()
                logger.info(f"Winsorized {col}: max {before_max:.0f} -> {after_max:.0f}, mean {before_mean:.1f} -> {after_mean:.1f}")
    
    return df


def validate_data(df: pd.DataFrame) -> bool:
    """
    Validate data quality.
    
    Args:
        df: DataFrame to validate
    
    Returns:
        True if data passes validation, raises exception otherwise
    """
    # Check for completely empty columns
    empty_cols = df.columns[df.isna().all()].tolist()
    if empty_cols:
        raise ValueError(f"Completely empty columns: {empty_cols}")
    
    # Check for negative monetary values
    if 'payment_value' in df.columns and (df['payment_value'] < 0).any():
        raise ValueError("Found negative payment values")
    
    logger.info("Data validation passed")
    return True


class DataPreprocessor:
    """
    Prétraitement aligné sur la chaîne « données → modèle » du notebook (après l’EDA).

    L’EDA (distributions, corrélations, graphiques) dans Jupyter est exploratoire et ne
    modifie en général pas le CSV `base_final.csv` : ce module charge ce fichier,
    convertit les dates, valide, déduplique les `order_id`, puis enchaîne avec
    `FeatureEngineer`. La winsorisation listée dans `config.yaml` (`preprocessing.cols_to_winsorize`)
    vise des colonnes agrégées / autre jeu : elle n’est pas appliquée ici sur les
    lignes commande de `base_final.csv` tant que ces colonnes n’y sont pas présentes.
    """
    
    def __init__(self, config=None):
        """
        Initialize preprocessor with configuration.
        
        Args:
            config: Configuration dictionary. If None, loads from config.yaml
        """
        self.config = config or load_config()
        self.logger = get_logger(__name__)
    
    def load_and_preprocess(self, data_path: str) -> pd.DataFrame:
        """
        Load data and apply all preprocessing steps.
        
        Args:
            data_path: Path to CSV file
        
        Returns:
            Preprocessed DataFrame
        """
        # Load data
        df = load_data(data_path)
        logger.info(f"Original shape: {df.shape}")
        
        # Convert dates
        date_cols = self.config['data']['date_columns']
        df = convert_dates(df, date_cols)
        logger.info("Dates converted")
        
        # Validate data
        validate_data(df)
        
        # Remove duplicates
        df = remove_duplicates(df, subset=['order_id'])
        logger.info(f"After deduplication: {df.shape}")
        
        # Handle missing values
        df = handle_missing_values(df, strategy='report')
        
        return df


if __name__ == "__main__":
    # Test the data loader
    preprocessor = DataPreprocessor()
    df = preprocessor.load_and_preprocess("data/base_final.csv")
    print(df.head())
