"""
FastAPI Server - Customer Segmentation API

Serves the trained clustering model and provides endpoints for:
- Predicting customer segments
- Getting cluster profiles
- Getting clustering metrics
"""

import os
import sys
import pickle
from pathlib import Path
from typing import List, Dict, Optional

import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import Config, get_logger

logger = get_logger(__name__)

# ============================================================================
# DATA MODELS
# ============================================================================

class CustomerData(BaseModel):
    """Request model for single customer prediction"""
    customer_features: Dict[str, float]


class BulkPredictionRequest(BaseModel):
    """Request model for bulk predictions"""
    customers: List[Dict[str, float]]


class SegmentationResponse(BaseModel):
    """Response model for segmentation prediction"""
    customer_id: Optional[str] = None
    cluster: int
    segment_name: str
    segment_action: str
    pca_1: Optional[float] = None
    pca_2: Optional[float] = None
    confidence: Optional[float] = None


class ClusterProfile(BaseModel):
    """Response model for cluster profile"""
    cluster_id: int
    segment_name: str
    segment_action: str
    mean_features: Dict[str, float]
    median_features: Dict[str, float]


# ============================================================================
# API APPLICATION
# ============================================================================

class SegmentationAPI:
    """Main API class for customer segmentation"""

    def __init__(self, model_dir: str = "notebooks/models", reports_dir: str = "notebooks/reports"):
        self.model_dir = Path(model_dir)
        self.reports_dir = Path(reports_dir)
        self.config = Config()
        
        # Load model and data
        self.pipeline = None
        self.cluster_profiles_mean = None
        self.cluster_profiles_median = None
        self.final_results = None
        self.clustering_comparison = None
        
        self._load_model()
        self._load_data()

    def _load_model(self):
        """Load the trained pipeline from pickle"""
        pipeline_path = self.model_dir / "final_pipeline.pkl"
        
        if not pipeline_path.exists():
            raise FileNotFoundError(f"Pipeline not found at {pipeline_path}")
        
        logger.info(f"Loading pipeline from {pipeline_path}")
        
        with open(pipeline_path, 'rb') as f:
            self.pipeline = pickle.load(f)
        
        logger.info("Pipeline loaded successfully")
        logger.info(f"Features: {self.pipeline['feature_cols']}")
        logger.info(f"Cluster names: {self.pipeline['cluster_names']}")

    def _load_data(self):
        """Load CSV reports and cluster data"""
        # Load cluster profiles
        mean_path = self.reports_dir / "cluster_profiles_mean.csv"
        median_path = self.reports_dir / "cluster_profiles_median.csv"
        
        if mean_path.exists():
            self.cluster_profiles_mean = pd.read_csv(mean_path, index_col=0)
            logger.info(f"Loaded cluster profiles (mean)")
        
        if median_path.exists():
            self.cluster_profiles_median = pd.read_csv(median_path, index_col=0)
            logger.info(f"Loaded cluster profiles (median)")
        
        # Load final segmentation
        final_path = self.reports_dir / "segmentation_finale_olist.csv"
        if final_path.exists():
            self.final_results = pd.read_csv(final_path)
            logger.info(f"Loaded final results: {len(self.final_results)} customers")
        
        # Load clustering comparison
        comp_path = self.reports_dir / "clustering_comparison.csv"
        if comp_path.exists():
            self.clustering_comparison = pd.read_csv(comp_path)
            logger.info(f"Loaded clustering comparison")

    def predict_segment(self, features: Dict[str, float]) -> Dict:
        """
        Predict segment for a given set of features
        
        Args:
            features: Dictionary of feature values (must match pipeline's feature_cols)
        
        Returns:
            Dictionary with prediction results
        """
        # Validate feature keys
        required_features = set(self.pipeline['feature_cols'])
        provided_features = set(features.keys())
        
        missing = required_features - provided_features
        if missing:
            raise ValueError(f"Missing features: {missing}")
        
        # Create feature vector in correct order
        X = np.array([features[col] for col in self.pipeline['feature_cols']]).reshape(1, -1)
        
        # Scale
        scaler = self.pipeline['scaler']
        X_scaled = scaler.transform(X)
        
        # Predict cluster
        model = self.pipeline['model']
        cluster = model.predict(X_scaled)[0]
        
        # Get segment name and action
        cluster_names = self.pipeline['cluster_names']
        segment_name = cluster_names.get(str(cluster), f"Cluster {cluster}")
        
        segment_actions = self.pipeline['segment_actions']
        segment_action = segment_actions.get(str(cluster), "Standard")
        
        # Calculate PCA projection
        pca = self.pipeline['pca']
        X_pca = pca.transform(X_scaled)
        
        # Calculate distance to cluster center for confidence
        distances = np.linalg.norm(model.cluster_centers_[cluster] - X_scaled[0])
        confidence = 1.0 / (1.0 + distances)
        
        return {
            "cluster": int(cluster),
            "segment_name": segment_name,
            "segment_action": segment_action,
            "pca_1": float(X_pca[0, 0]),
            "pca_2": float(X_pca[0, 1]),
            "confidence": float(confidence),
        }

    def get_cluster_profiles(self) -> List[ClusterProfile]:
        """Get profiles for all clusters"""
        if self.cluster_profiles_mean is None:
            raise ValueError("Cluster profiles not loaded")
        
        profiles = []
        cluster_names = self.pipeline['cluster_names']
        segment_actions = self.pipeline['segment_actions']
        
        for cluster_id in sorted(self.cluster_profiles_mean.index):
            mean_features = self.cluster_profiles_mean.loc[cluster_id].to_dict()
            median_features = self.cluster_profiles_median.loc[cluster_id].to_dict()
            
            profile = ClusterProfile(
                cluster_id=int(cluster_id),
                segment_name=cluster_names.get(str(cluster_id), f"Cluster {cluster_id}"),
                segment_action=segment_actions.get(str(cluster_id), "Standard"),
                mean_features=mean_features,
                median_features=median_features,
            )
            profiles.append(profile)
        
        return profiles

    def get_clustering_metrics(self) -> Dict:
        """Get clustering metrics comparison"""
        if self.clustering_comparison is None:
            raise ValueError("Clustering comparison not loaded")
        
        return self.clustering_comparison.to_dict(orient='records')

    def get_segment_statistics(self) -> Dict:
        """Get statistics about segments in final results"""
        if self.final_results is None:
            raise ValueError("Final results not loaded")
        
        stats = {
            "total_customers": len(self.final_results),
            "segments": {}
        }
        
        for segment in self.final_results['segment'].unique():
            count = len(self.final_results[self.final_results['segment'] == segment])
            percentage = (count / len(self.final_results)) * 100
            
            stats["segments"][segment] = {
                "count": count,
                "percentage": percentage
            }
        
        return stats


# ============================================================================
# FASTAPI APPLICATION SETUP
# ============================================================================

app = FastAPI(
    title="Customer Segmentation API",
    description="API for customer clustering and segmentation",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

segmentation_api: Optional[SegmentationAPI] = None


@app.on_event("startup")
def _startup_load_assets():
    """
    Load model + reports at server startup (not at import time).
    This keeps `import scripts.api` fast and makes failures visible in /health.
    """
    global segmentation_api
    try:
        segmentation_api = SegmentationAPI(
            model_dir="notebooks/models",
            reports_dir="notebooks/reports",
        )
        logger.info("API initialized successfully")
    except Exception as e:
        logger.exception(f"Failed to initialize API: {e}")
        segmentation_api = None


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "api_ready": segmentation_api is not None,
        "model_loaded": segmentation_api.pipeline is not None if segmentation_api else False,
    }


@app.post("/predict", response_model=SegmentationResponse)
def predict(customer_data: CustomerData):
    """
    Predict customer segment
    
    Args:
        customer_data: Customer features
    
    Returns:
        Segmentation prediction with cluster, segment name, and PCA coordinates
    """
    if not segmentation_api:
        raise HTTPException(status_code=503, detail="API not initialized")
    
    try:
        result = segmentation_api.predict_segment(customer_data.customer_features)
        return SegmentationResponse(**result)
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/predict-bulk")
def predict_bulk(request: BulkPredictionRequest):
    """
    Predict segments for multiple customers
    
    Args:
        request: List of customers with features
    
    Returns:
        List of segmentation predictions
    """
    if not segmentation_api:
        raise HTTPException(status_code=503, detail="API not initialized")
    
    results = []
    for customer_features in request.customers:
        try:
            result = segmentation_api.predict_segment(customer_features)
            results.append(result)
        except Exception as e:
            logger.error(f"Error predicting customer: {e}")
            results.append({"error": str(e)})
    
    return {"predictions": results}


@app.get("/profiles", response_model=List[ClusterProfile])
def get_cluster_profiles():
    """Get detailed profiles for all clusters"""
    if not segmentation_api:
        raise HTTPException(status_code=503, detail="API not initialized")
    
    try:
        profiles = segmentation_api.get_cluster_profiles()
        return profiles
    except Exception as e:
        logger.error(f"Error getting profiles: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/metrics")
def get_clustering_metrics():
    """Get clustering evaluation metrics"""
    if not segmentation_api:
        raise HTTPException(status_code=503, detail="API not initialized")
    
    try:
        metrics = segmentation_api.get_clustering_metrics()
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/statistics")
def get_statistics():
    """Get segment statistics from final results"""
    if not segmentation_api:
        raise HTTPException(status_code=503, detail="API not initialized")
    
    try:
        stats = segmentation_api.get_segment_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/model-info")
def get_model_info():
    """Get information about the loaded model"""
    if not segmentation_api or not segmentation_api.pipeline:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    return {
        "best_k": segmentation_api.pipeline['best_k'],
        "n_features": len(segmentation_api.pipeline['feature_cols']),
        "feature_cols": segmentation_api.pipeline['feature_cols'],
        "cluster_names": segmentation_api.pipeline['cluster_names'],
        "segment_actions": segmentation_api.pipeline['segment_actions'],
        "n_components_pca": segmentation_api.pipeline['n_components'],
    }


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/docs-custom")
def custom_docs():
    """Custom API documentation"""
    return {
        "api_name": "Customer Segmentation API",
        "version": "1.0.0",
        "description": "Predict customer segments using pre-trained clustering model",
        "endpoints": {
            "GET /health": "Health check",
            "POST /predict": "Predict segment for one customer",
            "POST /predict-bulk": "Predict segments for multiple customers",
            "GET /profiles": "Get cluster profiles",
            "GET /metrics": "Get clustering metrics",
            "GET /statistics": "Get segment statistics",
            "GET /model-info": "Get model information",
        },
        "example_features": {
            "Recency": 180,
            "Monetary": 5000,
            "Frequency": 15,
            "avg_review_score": 4.5,
            "avg_delivery_days": 10,
            "avg_installments": 2.0,
            "avg_item_price": 150.0,
            "CLV_estimate": 10000.0,
            "late_delivery_rate": 0.05,
            "customer_tenure": 365
        }
    }


if __name__ == "__main__":
    # Run the API
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"Starting API on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
