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
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Import / chemins relatifs robustes quel que soit le cwd (Railway, systemd, etc.)
sys.path.insert(0, str(PROJECT_ROOT))

# Resolve templates directory robustly
TEMPLATES_DIR = PROJECT_ROOT / "templates"
if not TEMPLATES_DIR.exists():
    # Fallback: look relative to cwd
    TEMPLATES_DIR = Path("templates")

from src.features.engineering import FeatureEngineer
from src.utils.config import Config, get_logger


def _fallback_html(title: str, message: str, status: int = 500) -> HTMLResponse:
    """Simple HTML fallback when templates are unavailable."""
    html = f"""<!doctype html><html lang='fr'><head><meta charset='utf-8'>
    <title>{title}</title>
    <style>body{{font-family:system-ui,sans-serif;background:#0f1419;color:#e2e8f0;padding:2rem;max-width:600px;margin:auto}}
    h1{{color:#818cf8}}pre{{background:#1e293b;padding:1rem;border-radius:.5rem;overflow:auto;font-size:.85rem}}
    a{{color:#818cf8}} .ok{{color:#34d399}} .err{{color:#f87171}}</style></head>
    <body><h1>{title}</h1><p>{message}</p>
    <p><a href='/docs'>📖 API Docs</a> · <a href='/health'>❤ Health</a> · <a href='/form'>📋 Form</a></p></body></html>"""
    return HTMLResponse(content=html, status_code=status)

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
    Simplified to only include fields needed for the 5 main features.
    """
    order_id: str
    customer_unique_id: str
    order_status: str

    # Champs essentiels pour calculer les 5 features
    order_purchase_timestamp: str  # Pour Recency
    payment_value: float           # Pour CLV_estimate
    payment_installments: Optional[float] = None  # Pour avg_installments
    
    # Champs optionnels mais recommandés
    order_delivered_customer_date: Optional[str] = None  # Pour avg_delivery_days
    review_score: Optional[float] = None                 # Pour avg_review_score_full


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
        logger.info(f"Step 1: Creating feature vector from {len(features)} features")
        X = np.array([features[col] for col in self.pipeline['feature_cols']], dtype=np.float64).reshape(1, -1)
        logger.info(f"Step 1 OK: X shape={X.shape}, values={X}")
        
        # STEP 1B: CLAMP features to training data range (from QuantileTransformer bounds)
        # This is CRITICAL: values outside the QT's fitted range get mapped to extreme
        # quantiles (±5.199), making very different inputs collapse to the same prediction.
        qt = self.pipeline.get('quantile_transformer')
        if qt is None:
            raise ValueError("QuantileTransformer not found in pipeline!")
        
        qt_min = qt.quantiles_[0, :]    # per-feature minimum seen during training
        qt_max = qt.quantiles_[-1, :]   # per-feature maximum seen during training
        X_clamped = np.clip(X, qt_min, qt_max)
        logger.info(f"Step 1B: Clamped to training range. Before={X}, After={X_clamped}")
        
        # STEP 2: QUANTILE TRANSFORMER
        logger.info(f"Step 2: Applying QuantileTransformer")
        X_qt = qt.transform(X_clamped)
        logger.info(f"Step 2 OK: X_qt values={X_qt}")
        
        # STEP 3: STANDARD SCALER
        logger.info(f"Step 3: Scaling with StandardScaler")
        scaler = self.pipeline['scaler']
        X_scaled = scaler.transform(X_qt)
        logger.info(f"Step 3 OK: X_scaled values={X_scaled}")
        
        # STEP 4: PCA TRANSFORM
        logger.info(f"Step 4: PCA transform")
        pca = self.pipeline['pca']
        X_pca_full = pca.transform(X_scaled)
        logger.info(f"Step 4 OK: X_pca values={X_pca_full}")
        
        # STEP 5: PREDICT CLUSTER
        logger.info(f"Step 5: Predicting with model")
        model = self.pipeline['model']
        X_for_predict = X_pca_full.astype(model.cluster_centers_.dtype, copy=False)
        
        cluster = model.predict(X_for_predict)[0]
        logger.info(f"Step 5 OK: Predicted cluster {cluster}")
        
        # Get segment name and action
        cluster_names = self.pipeline['cluster_names']
        segment_name = cluster_names.get(int(cluster), f"Cluster {cluster}")
        
        segment_actions = self.pipeline['segment_actions']
        segment_action = segment_actions.get(int(cluster), "Standard")
        
        # Get 2D PCA for visualization
        X_pca_2d = X_pca_full[:, :2]
        
        # Calculate confidence based on distance to assigned cluster center
        all_distances = [float(np.linalg.norm(center - X_for_predict[0])) for center in model.cluster_centers_]
        min_dist = all_distances[int(cluster)]
        confidence = 1.0 / (1.0 + min_dist)
        
        logger.info(f"Distances to all centers: {[f'{d:.4f}' for d in all_distances]}")
        logger.info(f"Predicted cluster={cluster}, confidence={confidence:.4f}")
        
        return {
            "cluster": int(cluster),
            "segment_name": segment_name,
            "segment_action": segment_action,
            "pca_1": float(X_pca_2d[0, 0]),
            "pca_2": float(X_pca_2d[0, 1]),
            "confidence": float(confidence),
        }

    def _compute_features_from_orders(self, orders: List[Dict]) -> Dict[str, float]:
        """
        Compute the 5 model features directly from raw order data.
        
        This replaces the old approach of generating fake historical orders
        and running the batch FeatureEngineer pipeline, which diluted user
        input with random noise and produced out-of-range feature values.
        
        Features computed:
        - Recency: days since last order (relative to snapshot)
        - avg_review_score_full: average review score across orders
        - avg_delivery_days: average delivery time in days
        - avg_installments: average payment installments
        - CLV_estimate: customer lifetime value estimate
        """
        df = pd.DataFrame(orders)
        
        # Parse dates - uniquement les colonnes nécessaires pour les 5 features
        for col in ["order_purchase_timestamp", "order_delivered_customer_date"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format="mixed", errors="coerce")
        
        # Filter delivered orders (fall back to all if none delivered)
        delivered = df[df["order_status"] == "delivered"]
        if delivered.empty:
            delivered = df
        
        # --- 1. Recency ---
        # Recency = days since last purchase, seen from TODAY.
        # In training, Recency was computed as (snapshot_date - last_order_date).days
        # where snapshot_date = max(all_dates)+1 = end of dataset period (~2018).
        # For API predictions, we use today so that recent orders → low Recency
        # and old orders → high Recency. The clamping in predict_segment()
        # ensures values stay within the QT's training range [58, 624].
        last_order = delivered["order_purchase_timestamp"].max()
        snapshot_date = pd.Timestamp.today()
        recency = (snapshot_date - last_order).days if pd.notna(last_order) else 287  # training mean
        
        # --- 2. avg_review_score_full ---
        review = 4.0  # training mean ≈ 4.16
        if "review_score" in delivered.columns:
            review_vals = pd.to_numeric(delivered["review_score"], errors="coerce").dropna()
            if len(review_vals) > 0:
                review = float(review_vals.mean())
        
        # --- 3. avg_delivery_days ---
        delivery_days = 12.0  # training mean ≈ 12.1
        if ("order_delivered_customer_date" in delivered.columns and 
            "order_purchase_timestamp" in delivered.columns):
            dd = (delivered["order_delivered_customer_date"] - 
                  delivered["order_purchase_timestamp"]).dt.days
            dd = dd.dropna()
            if len(dd) > 0:
                delivery_days = float(dd.mean())
                if delivery_days < 0:
                    delivery_days = 12.0  # fallback for bad dates
        
        # --- 4. avg_installments ---
        installments = 2.9  # training mean
        if "payment_installments" in delivered.columns:
            inst_vals = pd.to_numeric(delivered["payment_installments"], errors="coerce").dropna()
            if len(inst_vals) > 0:
                installments = float(inst_vals.mean())
        
        # --- 5. CLV_estimate ---
        # Training CLV = Monetary × (Frequency / dataset_duration_years)
        # Training dataset ≈ 2 years, most customers Frequency=1
        # So CLV ≈ Monetary × 0.5
        # We replicate this: use total payment as Monetary, frequency = n_orders,
        # and assume a 2-year observation window (matching training).
        payment_vals = pd.to_numeric(delivered["payment_value"], errors="coerce").dropna()
        monetary = float(payment_vals.sum()) if len(payment_vals) > 0 else 0
        frequency = int(delivered["order_id"].nunique()) if "order_id" in delivered.columns else 1
        TRAINING_DURATION_YEARS = 2.0  # Olist dataset ≈ 2 years
        clv = monetary * (frequency / TRAINING_DURATION_YEARS)
        
        features = {
            "Recency": recency,
            "avg_review_score_full": review,
            "avg_delivery_days": delivery_days,
            "avg_installments": installments,
            "CLV_estimate": clv,
        }
        
        logger.info(f"Computed features directly from {len(orders)} order(s): {features}")
        return features

    def predict_from_raw_orders(self, orders: List[Dict]) -> Dict:
        """
        Compute features from raw order-level records and predict.

        Expected raw columns per order (simplified to 5 features):
        - order_id, customer_unique_id, order_status
        - order_purchase_timestamp (pour Recency)
        - payment_value (pour CLV_estimate)
        - payment_installments (pour avg_installments)
        - optional: order_delivered_customer_date (pour avg_delivery_days)
        - optional: review_score (pour avg_review_score_full)
        """
        if not orders:
            raise ValueError("No orders provided")

        # Validate customer_unique_id
        customer_ids = list({o.get("customer_unique_id") for o in orders if o.get("customer_unique_id")})
        if len(customer_ids) != 1:
            raise ValueError(f"Raw prediction expects exactly 1 customer_unique_id, got {len(customer_ids)}")
        customer_id = customer_ids[0]

        logger.info(f"Predicting for customer {customer_id} with {len(orders)} order(s)")
        logger.info(f"Order details: payment={orders[0].get('payment_value')}, "
                    f"review={orders[0].get('review_score')}, "
                    f"installments={orders[0].get('payment_installments')}")

        # Compute the 5 features directly from the orders (no synthetic data)
        features = self._compute_features_from_orders(orders)
        
        # Predict
        result = self.predict_segment(features)
        logger.info(f"Prediction result: cluster={result['cluster']}, "
                    f"segment={result['segment_name']}, confidence={result['confidence']:.4f}")
        
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

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
logger.info(f"Templates directory: {TEMPLATES_DIR} (exists={TEMPLATES_DIR.exists()})")

# Mount static files
static_dir = PROJECT_ROOT / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logger.info(f"Static files mounted at /static from {static_dir}")
else:
    logger.warning(f"Static directory not found: {static_dir}")

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
    Les navigateurs envoient `Accept: text/html` → redirection vers le formulaire /simple.
    Clients API (curl, JSON) gardent une réponse JSON ; forcez avec `/?format=json`.
    """
    accept = (request.headers.get("accept") or "").lower()
    force_json = request.query_params.get("format") == "json"
    if not force_json and "text/html" in accept:
        return RedirectResponse(url="/simple", status_code=307)
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
    """Form-based UI for customer segmentation prediction — served as raw HTML (no Jinja2 needed)."""
    html_path = TEMPLATES_DIR / "segmentation_form.html"
    try:
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"), status_code=200)
    except Exception as e:
        logger.error(f"Error reading /form template: {e}")
        return _fallback_html(
            "Formulaire de Segmentation",
            f"Impossible de lire le fichier template : <code>{e}</code><br>"
            f"Chemin attendu : <code>{html_path}</code> (exists={html_path.exists()})",
        )


@app.get("/simple", response_class=HTMLResponse)
def ui_simple(request: Request):
    """Simple form-based UI — served as raw HTML (no Jinja2 needed)."""
    html_path = TEMPLATES_DIR / "form_simple.html"
    try:
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"), status_code=200)
    except Exception as e:
        logger.error(f"Error reading /simple template: {e}")
        return _fallback_html("Interface simple", f"Erreur: <code>{e}</code>")


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

@app.get("/test-prediction")
def test_prediction():
    """Test endpoint to debug prediction issues"""
    if not segmentation_api:
        return {"error": "API not initialized"}
    
    try:
        # Create test data with different scenarios
        test_scenarios = [
            {
                "name": "Premium Customer",
                "orders": [{
                    "order_id": "TEST-PREMIUM-001",
                    "customer_unique_id": "CUST-PREMIUM-TEST",
                    "order_status": "delivered",
                    "order_purchase_timestamp": "2024-01-15 14:30:00",
                    "payment_value": 850.50,
                    "price": 750.00,
                    "super_categorie": "electronics",
                    "freight_value": 25.00,
                    "payment_installments": 8,
                    "order_approved_at": "2024-01-15 14:35:00",
                    "customer_lat": -23.5505,
                    "customer_lng": -46.6333,
                    "order_estimated_delivery_date": "2024-01-20 23:59:59",
                    "order_delivered_customer_date": "2024-01-18 10:00:00",
                    "order_delivered_carrier_date": "2024-01-17 08:00:00",
                    "review_score": 5,
                    "review_creation_date": "2024-01-22 15:30:00"
                }]
            },
            {
                "name": "Unhappy Customer", 
                "orders": [{
                    "order_id": "TEST-UNHAPPY-001",
                    "customer_unique_id": "CUST-UNHAPPY-TEST",
                    "order_status": "delivered",
                    "order_purchase_timestamp": "2023-12-01 09:15:00",
                    "payment_value": 45.99,
                    "price": 35.00,
                    "super_categorie": "other",
                    "freight_value": 10.99,
                    "payment_installments": 1,
                    "order_approved_at": "2023-12-01 09:30:00",
                    "customer_lat": -23.5505,
                    "customer_lng": -46.6333,
                    "order_estimated_delivery_date": "2023-12-10 23:59:59",
                    "order_delivered_customer_date": "2023-12-15 16:00:00",
                    "order_delivered_carrier_date": "2023-12-08 14:00:00",
                    "review_score": 1,
                    "review_creation_date": "2023-12-20 11:00:00"
                }]
            }
        ]
        
        results = []
        for scenario in test_scenarios:
            logger.info(f"Testing scenario: {scenario['name']}")
            result = segmentation_api.predict_from_raw_orders(scenario["orders"])
            results.append({
                "scenario": scenario["name"],
                "customer_id": result["customer_id"],
                "cluster": result["cluster"],
                "segment": result["segment_name"],
                "confidence": result["confidence"],
                "features": result["engineered_features"]
            })
        
        return {"test_results": results}
        
    except Exception as e:
        logger.error(f"Test prediction failed: {str(e)}")
        return {"error": str(e)}

@app.get("/test-simple")
def test_simple():
    """Simple test to check if API works at all"""
    if not segmentation_api:
        return {"error": "API not initialized"}
    
    try:
        logger.info("=== SIMPLE TEST START ===")
        
        # Test with minimal data
        test_order = {
            "order_id": "SIMPLE-TEST",
            "customer_unique_id": "CUST-SIMPLE",
            "order_status": "delivered",
            "order_purchase_timestamp": "2024-01-01 12:00:00",
            "payment_value": 100.00,
            "price": 90.00,
            "super_categorie": "electronics",
            "freight_value": 10.00,
            "payment_installments": 2,
            "review_score": 3
        }
        
        logger.info(f"Test order: {test_order}")
        result = segmentation_api.predict_from_raw_orders([test_order])
        logger.info(f"Simple test result: {result}")
        
        return {
            "status": "success",
            "cluster": result["cluster"],
            "segment": result["segment_name"],
            "confidence": result["confidence"],
            "message": "Simple test completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Simple test failed: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e), "traceback": traceback.format_exc()}

@app.get("/debug-features")
def debug_features():
    """Debug endpoint to analyze feature calculation"""
    if not segmentation_api:
        return {"error": "API not initialized"}
    
    try:
        logger.info("=== DEBUG FEATURES START ===")
        
        # Test with two different scenarios
        scenarios = [
            {
                "name": "Premium Customer",
                "order": {
                    "order_id": "DEBUG-PREMIUM",
                    "customer_unique_id": "CUST-PREMIUM",
                    "order_status": "delivered",
                    "order_purchase_timestamp": "2024-01-15 14:30:00",
                    "payment_value": 850.50,
                    "price": 750.00,
                    "super_categorie": "electronics",
                    "freight_value": 25.00,
                    "payment_installments": 8,
                    "order_approved_at": "2024-01-15 14:35:00",
                    "customer_lat": -23.5505,
                    "customer_lng": -46.6333,
                    "order_estimated_delivery_date": "2024-01-20 23:59:59",
                    "order_delivered_customer_date": "2024-01-18 10:00:00",
                    "order_delivered_carrier_date": "2024-01-17 08:00:00",
                    "review_score": 5,
                    "review_creation_date": "2024-01-22 15:30:00"
                }
            },
            {
                "name": "Low Value Customer",
                "order": {
                    "order_id": "DEBUG-LOW",
                    "customer_unique_id": "CUST-LOW",
                    "order_status": "delivered",
                    "order_purchase_timestamp": "2023-12-01 09:15:00",
                    "payment_value": 45.99,
                    "price": 35.00,
                    "super_categorie": "other",
                    "freight_value": 10.99,
                    "payment_installments": 1,
                    "order_approved_at": "2023-12-01 09:30:00",
                    "customer_lat": -23.5505,
                    "customer_lng": -46.6333,
                    "order_estimated_delivery_date": "2023-12-10 23:59:59",
                    "order_delivered_customer_date": "2023-12-15 16:00:00",
                    "order_delivered_carrier_date": "2023-12-08 14:00:00",
                    "review_score": 1,
                    "review_creation_date": "2023-12-20 11:00:00"
                }
            }
        ]
        
        results = []
        for scenario in scenarios:
            logger.info(f"Testing scenario: {scenario['name']}")
            result = segmentation_api.predict_from_raw_orders([scenario["order"]])
            
            # Extract key RFM features for comparison
            features = result.get("engineered_features", {})
            key_features = {
                "Recency": features.get("Recency", "N/A"),
                "Monetary": features.get("Monetary", "N/A"),
                "Frequency": features.get("Frequency", "N/A"),
                "avg_installments": features.get("avg_installments", "N/A"),
                "avg_review_score_available": features.get("avg_review_score_available", "N/A")
            }
            
            results.append({
                "scenario": scenario["name"],
                "input_payment": scenario["order"]["payment_value"],
                "input_review": scenario["order"]["review_score"],
                "cluster": result["cluster"],
                "segment": result["segment_name"],
                "confidence": result["confidence"],
                "key_features": key_features
            })
        
        return {
            "status": "success",
            "comparison": results,
            "message": "Feature comparison completed"
        }
        
    except Exception as e:
        logger.error(f"Debug features failed: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"error": str(e), "traceback": traceback.format_exc()}


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
        "n_components_pca": segmentation_api.pipeline.get('n_comp', segmentation_api.pipeline.get('n_components', 'N/A')),
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
            "avg_review_score_full": 4.5,
            "avg_delivery_days": 10,
            "avg_installments": 2.9,
            "CLV_estimate": 2500.0,
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
