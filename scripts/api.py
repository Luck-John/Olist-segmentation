"""
FastAPI Server - Customer Segmentation API

Serves the trained clustering model and provides endpoints for:
- Predicting customer segments
- Getting cluster profiles
- Getting clustering metrics
"""

import os
import sys
import json
import pickle
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Dict, Optional
from io import StringIO

import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Import / chemins relatifs robustes quel que soit le cwd (Railway, systemd, etc.)
sys.path.insert(0, str(PROJECT_ROOT))

from src.features.engineering import FeatureEngineer
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


class RawOrder(BaseModel):
    """
    Raw order-level record used to derive customer features.
    The API will compute engineered features, then run clustering prediction.
    """
    order_id: str
    customer_unique_id: str
    order_status: str

    order_purchase_timestamp: str
    payment_value: float

    # Optional-but-recommended fields for feature engineering
    order_delivered_customer_date: Optional[str] = None
    order_estimated_delivery_date: Optional[str] = None
    review_score: Optional[float] = None
    review_creation_date: Optional[str] = None
    customer_lat: Optional[float] = None
    customer_lng: Optional[float] = None


class RawPredictionRequest(BaseModel):
    """Request model for raw input prediction (order-level records)."""
    orders: List[RawOrder]


class SegmentationResponse(BaseModel):
    """Response model for segmentation prediction"""
    customer_id: Optional[str] = None
    cluster: int
    segment_name: str
    segment_action: str
    pca_1: Optional[float] = None
    pca_2: Optional[float] = None
    confidence: Optional[float] = None
    # Populated for POST /predict-raw when features are computed server-side
    engineered_features: Optional[Dict[str, float]] = None


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
        
        # segmentation_finale_olist.csv est volumineux : chargé à la demande (voir _ensure_final_results)
        self.final_results = None

        # Load clustering comparison
        comp_path = self.reports_dir / "clustering_comparison.csv"
        if comp_path.exists():
            self.clustering_comparison = pd.read_csv(comp_path)
            logger.info(f"Loaded clustering comparison")

    def _ensure_final_results(self) -> None:
        """Charge le CSV de segmentation complète seulement quand /statistics est appelé."""
        if self.final_results is not None:
            return
        final_path = self.reports_dir / "segmentation_finale_olist.csv"
        if not final_path.exists():
            raise ValueError("Final results file not found")
        self.final_results = pd.read_csv(final_path)
        logger.info(f"Loaded final results (lazy): {len(self.final_results)} customers")

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

    def predict_from_raw_orders(self, orders: List[Dict]) -> Dict:
        """
        Compute features from raw order-level records and predict.

        Expected raw columns per order:
        - order_id, customer_unique_id, order_status
        - order_purchase_timestamp, payment_value
        - optional delivery/review/geographic columns (see RawOrder)
        """
        if not orders:
            raise ValueError("No orders provided")

        df = pd.DataFrame(orders)
        if "customer_unique_id" not in df.columns:
            raise ValueError("Missing customer_unique_id in raw orders")

        customer_ids = df["customer_unique_id"].dropna().unique().tolist()
        if len(customer_ids) != 1:
            raise ValueError(f"Raw prediction expects exactly 1 customer_unique_id, got {len(customer_ids)}")

        # Convert dates to datetime where possible
        for col in [
            "order_purchase_timestamp",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
            "review_creation_date",
        ]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format="mixed", errors="coerce")

        engineer = FeatureEngineer(self.config.get())
        df_features = engineer.engineer_features(df)

        # Extract feature vector for the single customer
        customer_id = customer_ids[0]
        row = df_features[df_features["customer_unique_id"] == customer_id]
        if row.empty:
            raise ValueError("Could not compute features for customer_unique_id")

        row = row.iloc[0]
        feature_cols = self.pipeline["feature_cols"]
        features = {}
        for col in feature_cols:
            val = float(row[col])
            if not np.isfinite(val):
                raise ValueError(
                    f"Engineered feature '{col}' is invalid (NaN/inf). "
                    "Provide more raw data (more orders) and/or required fields (delivery/review/geo)."
                )
            features[col] = val

        result = self.predict_segment(features)
        result["customer_id"] = customer_id
        result["engineered_features"] = features
        return result

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
        self._ensure_final_results()
        
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

segmentation_api: Optional[SegmentationAPI] = None
_api_init_task: Optional[asyncio.Task] = None


def _build_segmentation_api() -> SegmentationAPI:
    return SegmentationAPI(
        model_dir=str(PROJECT_ROOT / "notebooks" / "models"),
        reports_dir=str(PROJECT_ROOT / "notebooks" / "reports"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Démarre l’écoute HTTP tout de suite ; charge le modèle dans un thread pour que
    Railway / Docker healthchecks ne reçoivent pas « service unavailable » pendant pickle + CSV.
    """
    global segmentation_api, _api_init_task

    async def _init():
        global segmentation_api
        try:
            loop = asyncio.get_running_loop()
            segmentation_api = await loop.run_in_executor(
                None,
                _build_segmentation_api,
            )
            logger.info("API initialized successfully (background)")
        except Exception as e:
            logger.exception("Failed to initialize API: %s", e)
            segmentation_api = None

    _api_init_task = asyncio.create_task(_init())
    yield
    if _api_init_task is not None and not _api_init_task.done():
        _api_init_task.cancel()
        try:
            await _api_init_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Customer Segmentation API",
    description="API for customer clustering and segmentation",
    version="1.0.0",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API ENDPOINTS
# ============================================================================


def _root_json(request: Request) -> Dict:
    """Métadonnées API pour clients JSON (curl, intégrations)."""
    base = str(request.base_url).rstrip("/")
    return {
        "name": "Customer Segmentation API",
        "status": "ok",
        "message": (
            "Réponse technique JSON pour la racine. Dans un navigateur, ouvrez /form ou /docs "
            "(ou rajoutez ?format=json si vous voyez encore ce JSON après redirection désactivée)."
        ),
        "workflow": {
            "step_1": "Données brutes (formulaire /form ou POST /predict-raw)",
            "step_2": "Calcul des features côté serveur",
            "step_3": "Segment KMeans",
            "endpoint": "POST /predict-raw",
        },
        "links": {
            "form_saisie_donnees_brutes": f"{base}/form",
            "swagger": f"{base}/docs",
            "health": f"{base}/health",
            "model_info": f"{base}/model-info",
            "predict_raw": f"{base}/predict-raw",
            "predict_features_deja_calculees": f"{base}/predict",
        },
        "paths": {
            "docs": "/docs",
            "health": "/health",
            "model_info": "/model-info",
            "predict": "/predict",
            "predict_raw": "/predict-raw",
            "form": "/form",
            "ui": "/ui",
            "simple": "/simple",
            "app_redirect": "/app",
            "forms_typo_redirect": f"{base}/forms",
            "discovery_json_always": f"{base}/?format=json",
        },
    }


@app.get("/")
def root(request: Request):
    """
    Les navigateurs envoient `Accept: text/html` → redirection vers le formulaire /form.
    Clients API (curl, JSON) gardent une réponse JSON ; forcez avec `/?format=json`.
    """
    accept = (request.headers.get("accept") or "").lower()
    force_json = request.query_params.get("format") == "json"
    if not force_json and "text/html" in accept:
        return RedirectResponse(url="/form", status_code=307)
    return _root_json(request)


@app.get("/app")
def app_entry():
    """Raccourci : redirige vers le formulaire données brutes → prédiction."""
    return RedirectResponse(url="/form", status_code=307)


@app.get("/forms")
def typo_forms_plural():
    """Beaucoup tentent /forms — redirige vers /form."""
    return RedirectResponse(url="/form", status_code=307)


@app.get("/ui", response_class=HTMLResponse)
def ui_home(request: Request):
    return templates.TemplateResponse(
        "ui.html",
        {
            "request": request,
            "prediction": None,
            "features": None,
            "error": None,
            "raw_json": None,
            "raw_csv": None,
            "base_url": str(request.base_url).rstrip("/"),
        },
    )


@app.get("/form", response_class=HTMLResponse)
def ui_form(request: Request):
    """Form-based UI for easier customer data input"""
    return templates.TemplateResponse(
        "ui_form.html",
        {"request": request},
    )


@app.get("/simple", response_class=HTMLResponse)
def ui_simple(request: Request):
    """Simple form-based UI for customer data input"""
    return templates.TemplateResponse(
        "ui_simple.html",
        {
            "request": request,
            "base_url": str(request.base_url).rstrip("/"),
        },
    )


@app.post("/ui/predict", response_class=HTMLResponse)
def ui_predict(request: Request, raw_json: str = Form(""), raw_csv: str = Form("")):
    if not segmentation_api:
        return templates.TemplateResponse(
            "ui.html",
            {
                "request": request,
                "prediction": None,
                "features": None,
                "error": "API not initialized (503).",
                "raw_json": raw_json,
                "raw_csv": raw_csv,
                "base_url": str(request.base_url).rstrip("/"),
            },
            status_code=503,
        )

    try:
        raw_json = (raw_json or "").strip()
        raw_csv = (raw_csv or "").strip()

        if raw_csv:
            df = pd.read_csv(StringIO(raw_csv))
            orders = df.to_dict(orient="records")
        else:
            if not raw_json:
                raise ValueError("Provide either CSV or JSON input.")
            orders = json.loads(raw_json)
            if not isinstance(orders, list):
                raise ValueError("JSON must be a list of orders (array).")

        result = segmentation_api.predict_from_raw_orders(orders)
        prediction = {
            "customer_id": result.get("customer_id"),
            "cluster": result.get("cluster"),
            "segment_name": result.get("segment_name"),
            "segment_action": result.get("segment_action"),
            "pca_1": result.get("pca_1"),
            "pca_2": result.get("pca_2"),
            "confidence": result.get("confidence"),
        }

        return templates.TemplateResponse(
            "ui.html",
            {
                "request": request,
                "prediction": prediction,
                "features": result.get("engineered_features"),
                "error": None,
                "raw_json": raw_json,
                "raw_csv": raw_csv,
                "base_url": str(request.base_url).rstrip("/"),
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            "ui.html",
            {
                "request": request,
                "prediction": None,
                "features": None,
                "error": str(e),
                "raw_json": raw_json,
                "raw_csv": raw_csv,
                "base_url": str(request.base_url).rstrip("/"),
            },
            status_code=400,
        )


@app.get("/health")
def health_check():
    """Health check endpoint (200 dès que le process répond ; voir api_ready pour le modèle)."""
    loading = (
        _api_init_task is not None
        and not _api_init_task.done()
        and segmentation_api is None
    )
    return {
        "status": "healthy",
        "api_ready": segmentation_api is not None,
        "api_loading": loading,
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


@app.post("/predict-raw", response_model=SegmentationResponse)
def predict_raw(request: RawPredictionRequest):
    """
    Predict customer segment from raw order-level records.
    The API computes engineered customer features before prediction.
    """
    if not segmentation_api:
        raise HTTPException(status_code=503, detail="API not initialized")

    try:
        orders = [o.model_dump() for o in request.orders]
        result = segmentation_api.predict_from_raw_orders(orders)
        return SegmentationResponse(**result)
    except Exception as e:
        logger.error(f"Raw prediction error: {e}")
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
            "Frequency": 15,
            "Monetary": 5000,
            "avg_delivery_days": 10,
            "late_delivery_rate": 0.05,
            "avg_delivery_delta": 2.0,
            "avg_review_score_full": 4.5,
            "has_full_review": 1,
            "avg_review_score_available": 4.5,
            "has_available_review": 1,
            "CLV": 10000.0,
            "dist_sao_paulo": 120.0,
        },
        "model_note": "Direct POST /predict expects exactly the feature_cols from GET /model-info (trained pipeline). "
        "POST /predict-raw accepts order-level rows and computes these features.",
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
