"""
Main pipeline script - Automated execution of data processing and clustering
"""
import os
import sys
import logging
from pathlib import Path

import mlflow
import mlflow.sklearn
from sklearn.preprocessing import StandardScaler
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import Config, get_logger
from src.data.preprocessing import DataPreprocessor
from src.features.engineering import FeatureEngineer
from src.clustering.models import KMeansClustering, PCAReducer


def setup_logging(config):
    """Setup logging configuration"""
    log_dir = Path(config.get('logging.log_file')).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, config.get('logging.level')),
        format=config.get('logging.format'),
        handlers=[
            logging.FileHandler(config.get('logging.log_file')),
            logging.StreamHandler()
        ]
    )


def setup_mlflow(config):
    """Setup MLFlow tracking"""
    mlflow.set_tracking_uri(config.get('mlflow.tracking_uri'))
    mlflow.set_experiment(config.get('mlflow.experiment_name'))
    
    logger = get_logger(__name__)
    logger.info(f"MLFlow experiment: {config.get('mlflow.experiment_name')}")
    logger.info(f"MLFlow tracking URI: {config.get('mlflow.tracking_uri')}")


def run_pipeline():
    """Main pipeline execution"""
    logger = get_logger(__name__)
    config = Config()
    
    logger.info("=" * 80)
    logger.info("OLIST CUSTOMER SEGMENTATION PIPELINE")
    logger.info("=" * 80)
    
    # Setup MLFlow
    setup_mlflow(config.get())
    
    # Start MLFlow run
    with mlflow.start_run():
        try:
            # ========== STEP 1: DATA LOADING & PREPROCESSING ==========
            logger.info("\n[STEP 1] Loading and preprocessing data...")
            
            preprocessor = DataPreprocessor(config.get())
            data_path = os.path.join(
                config.get('paths.data_dir'),
                config.get('data.base_final')
            )
            
            df_raw = preprocessor.load_and_preprocess(data_path)
            logger.info(f"Data shape after preprocessing: {df_raw.shape}")
            
            # Log preprocessing metrics
            mlflow.log_param("data_rows", len(df_raw))
            mlflow.log_param("data_columns", df_raw.shape[1])
            
            # ========== STEP 2: FEATURE ENGINEERING ==========
            logger.info("\n[STEP 2] Engineering features...")
            
            engineer = FeatureEngineer(config.get())
            df_features = engineer.engineer_features(df_raw)
            logger.info(f"Features shape: {df_features.shape}")
            
            # Save engineered features
            output_path = os.path.join(
                config.get('paths.output_dir'),
                'Base.csv'
            )
            df_features.to_csv(output_path, index=False)
            logger.info(f"Features saved to {output_path}")
            
            # Log feature engineering metrics
            mlflow.log_param("n_features", df_features.shape[1])
            mlflow.log_param("n_customers", df_features.shape[0])
            
            # ========== STEP 3: DATA SCALING ==========
            logger.info("\n[STEP 3] Scaling features...")
            
            # Select numerical features for clustering
            num_features = df_features.select_dtypes(include=['number']).columns.tolist()
            # Remove customer_unique_id if present
            num_features = [col for col in num_features if col != 'customer_unique_id']
            
            X = df_features[num_features].values
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            logger.info(f"Scaled features shape: {X_scaled.shape}")
            mlflow.log_param("n_scaled_features", X_scaled.shape[1])
            
            # ========== STEP 4: KMEANS CLUSTERING ==========
            logger.info("\n[STEP 4] Performing KMeans clustering...")
            
            kmeans = KMeansClustering(config.get())
            kmeans_config = config.get('clustering.kmeans')
            
            results = kmeans.fit_range(
                X_scaled,
                k_range=(kmeans_config['k_min'], kmeans_config['k_max'])
            )
            
            # Find best k
            best_k, best_model = kmeans.get_best_model(metric='silhouette_score')
            logger.info(f"Best KMeans k: {best_k}")
            
            # Log clustering metrics
            for k, metrics in results.items():
                mlflow.log_metrics({
                    f"kmeans_k{k}_silhouette": metrics.get('silhouette_score', 0),
                    f"kmeans_k{k}_davies_bouldin": metrics.get('davies_bouldin_score', 0),
                    f"kmeans_k{k}_calinski_harabasz": metrics.get('calinski_harabasz_score', 0)
                }, step=k)
            
            # ========== STEP 5: PCA FOR VISUALIZATION ==========
            logger.info("\n[STEP 5] Applying PCA for visualization...")
            
            pca = PCAReducer(config.get())
            X_pca = pca.fit_transform(X_scaled, n_components=2)
            logger.info(f"PCA reduced to shape: {X_pca.shape}")
            
            # ========== STEP 6: SAVE RESULTS ==========
            logger.info("\n[STEP 6] Saving results...")
            
            # Add clusters to features
            df_features['cluster'] = best_model['labels']
            df_features['pca_1'] = X_pca[:, 0]
            df_features['pca_2'] = X_pca[:, 1]
            
            # Save clustered data
            clustered_path = os.path.join(
                config.get('paths.output_dir'),
                'clustered_data.csv'
            )
            df_features.to_csv(clustered_path, index=False)
            logger.info(f"Clustered data saved to {clustered_path}")
            
            # Save model
            models_dir = config.get('paths.models_dir')
            os.makedirs(models_dir, exist_ok=True)
            
            import pickle
            model_path = os.path.join(models_dir, f'kmeans_k{best_k}.pkl')
            with open(model_path, 'wb') as f:
                pickle.dump(best_model['model'], f)
            logger.info(f"Model saved to {model_path}")
            
            # ========== STEP 7: MLFLOW LOGGING ==========
            logger.info("\n[STEP 7] Logging to MLFlow...")
            
            # Log parameters
            mlflow.log_param("best_k", best_k)
            mlflow.log_param("algorithm", "KMeans")
            
            # Log metrics
            mlflow.log_metrics(best_model['metrics'])
            
            # Log artifacts
            mlflow.log_artifact(clustered_path)
            mlflow.log_artifact(model_path)
            
            # ========== STEP 8: MODEL REGISTRY ==========
            logger.info("\n[STEP 8] Registering model in MLFlow Model Registry...")
            
            mlflow.sklearn.log_model(
                best_model['model'],
                artifact_path="kmeans_model",
                registered_model_name=config.get('mlflow.model_name')
            )
            
            logger.info(f"Model registered as '{config.get('mlflow.model_name')}'")
            
            # ========== PIPELINE COMPLETE ==========
            logger.info("\n" + "=" * 80)
            logger.info("PIPELINE COMPLETED SUCCESSFULLY!")
            logger.info("=" * 80)
            
            logger.info(f"\nResults Summary:")
            logger.info(f"  - Customers clustered: {len(df_features)}")
            logger.info(f"  - Features engineered: {df_features.shape[1]}")
            logger.info(f"  - Optimal clusters: {best_k}")
            logger.info(f"  - Silhouette score: {best_model['metrics'].get('silhouette_score', 'N/A'):.3f}")
            logger.info(f"\nOutput files:")
            logger.info(f"  - Engineered features: {output_path}")
            logger.info(f"  - Clustered data: {clustered_path}")
            logger.info(f"  - Model: {model_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Pipeline failed with error: {e}", exc_info=True)
            mlflow.log_param("error", str(e))
            return False


if __name__ == "__main__":
    success = run_pipeline()
    sys.exit(0 if success else 1)
