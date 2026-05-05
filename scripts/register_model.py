"""
MLFlow Model Registry - Register and manage models
"""
import sys
import os
from pathlib import Path

import mlflow
import mlflow.sklearn

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import Config, get_logger


def promote_model_to_production():
    """Promote the latest model to Production stage"""
    logger = get_logger(__name__)
    config = Config()
    
    # Setup MLFlow
    mlflow.set_tracking_uri(config.get('mlflow.tracking_uri'))
    
    model_name = config.get('mlflow.model_name')
    logger.info(f"Promoting model '{model_name}' to Production...")
    
    try:
        # Get the latest version
        client = mlflow.tracking.MlflowClient()
        
        # Get all versions of the model
        versions = client.search_model_versions(f"name='{model_name}'")
        
        if not versions:
            logger.error(f"No versions found for model '{model_name}'")
            return False
        
        # Sort by version number (descending)
        latest_version = max(versions, key=lambda x: int(x.version))
        
        logger.info(f"Latest version: {latest_version.version}")
        logger.info(f"Current stage: {latest_version.current_stage}")
        
        # Transition to Production
        if config.get('model_registry.archive_existing'):
            # Archive existing Production models
            for version in versions:
                if version.current_stage == 'Production':
                    logger.info(f"Archiving version {version.version}")
                    client.transition_model_version_stage(
                        name=model_name,
                        version=version.version,
                        stage="Archived"
                    )
        
        # Promote new model to Production
        client.transition_model_version_stage(
            name=model_name,
            version=latest_version.version,
            stage=config.get('model_registry.stage')
        )
        
        logger.info(f"✓ Model version {latest_version.version} promoted to {config.get('model_registry.stage')}")
        
        # Update description
        client.update_model_version(
            name=model_name,
            version=latest_version.version,
            description=f"Production model - version {latest_version.version}"
        )
        
        logger.info("✓ Model registered in Model Registry and ready for production!")
        return True
        
    except Exception as e:
        logger.error(f"Error promoting model: {e}")
        return False


def list_model_versions():
    """List all versions of a model"""
    logger = get_logger(__name__)
    config = Config()
    
    mlflow.set_tracking_uri(config.get('mlflow.tracking_uri'))
    
    model_name = config.get('mlflow.model_name')
    client = mlflow.tracking.MlflowClient()
    
    logger.info(f"\nModel versions for '{model_name}':")
    logger.info("-" * 60)
    
    versions = client.search_model_versions(f"name='{model_name}'")
    
    if not versions:
        logger.info("No versions found")
        return
    
    for v in sorted(versions, key=lambda x: int(x.version), reverse=True):
        logger.info(f"  Version: {v.version}")
        logger.info(f"    Stage: {v.current_stage}")
        logger.info(f"    Status: {v.status}")
        logger.info(f"    Created: {v.creation_timestamp}")
        logger.info("")


def load_production_model():
    """Load the production model"""
    logger = get_logger(__name__)
    config = Config()
    
    mlflow.set_tracking_uri(config.get('mlflow.tracking_uri'))
    
    model_name = config.get('mlflow.model_name')
    
    try:
        model_uri = f"models:/{model_name}/Production"
        model = mlflow.sklearn.load_model(model_uri)
        
        logger.info(f"✓ Loaded production model: {model_name}")
        return model
    except Exception as e:
        logger.error(f"Error loading production model: {e}")
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MLFlow Model Registry management")
    parser.add_argument("--action", choices=["promote", "list", "load"], default="list",
                        help="Action to perform")
    
    args = parser.parse_args()
    
    logger = get_logger(__name__)
    
    if args.action == "promote":
        success = promote_model_to_production()
        sys.exit(0 if success else 1)
    elif args.action == "list":
        list_model_versions()
    elif args.action == "load":
        model = load_production_model()
        sys.exit(0 if model else 1)
