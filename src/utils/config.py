"""
Utilities for loading and managing configuration
"""
import yaml
import logging
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config.yaml file. If None, looks for config/config.yaml
    
    Returns:
        Dictionary with configuration
    
    Raises:
        FileNotFoundError: If config file not found
        yaml.YAMLError: If config file is malformed
    """
    if config_path is None:
        # Try to find config.yaml relative to this file
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "config.yaml"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing config file: {e}")


def get_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """
    Create a logger with consistent formatting.
    
    Args:
        name: Logger name (usually __name__)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level))
    
    if not logger.handlers:
        # Create console handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


class Config:
    """Singleton class for managing configuration"""
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._config = load_config()
    
    def get(self, key: str = None) -> Dict[str, Any]:
        """Get configuration or specific key"""
        if key is None:
            return self._config
        
        keys = key.split('.')
        value = self._config
        for k in keys:
            value = value[k]
        return value
    
    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access: config['key.subkey']"""
        return self.get(key)


if __name__ == "__main__":
    # Test the config loading
    config = Config()
    print(f"Random state: {config.get('random_state')}")
    print(f"KMeans k_min: {config.get('clustering.kmeans.k_min')}")
