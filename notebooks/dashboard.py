"""
Streamlit Dashboard - MLFlow Experiment Tracking Visualization

Run with: streamlit run notebooks/dashboard.py
"""
import os
import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import mlflow
from mlflow.tracking import MlflowClient

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import Config


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="🎯 Olist Segmentation - MLFlow Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main-header {
        font-size: 3em;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1em;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================================
# INITIALIZE
# ============================================================================

def initialize():
    """Initialize MLFlow and configuration"""
    config = Config()
    mlflow.set_tracking_uri(config.get("mlflow.tracking_uri"))
    return MlflowClient(), config


client, config = initialize()


# ============================================================================
# SIDEBAR
# ============================================================================

st.sidebar.title("🎛️ Dashboard Controls")

with st.sidebar:
    st.markdown("### Settings")
    
    # Experiment selection
    experiments = client.search_experiments()
    exp_names = [exp.name for exp in experiments]
    selected_exp = st.selectbox(
        "Select Experiment",
        exp_names,
        index=0 if exp_names else None,
    )
    
    # Refresh button
    if st.button("🔄 Refresh Data"):
        st.rerun()


# ============================================================================
# MAIN CONTENT
# ============================================================================

st.markdown("# 🎯 Olist Customer Segmentation")
st.markdown("## MLFlow Experiment Tracking Dashboard")

if not selected_exp:
    st.error("❌ No experiments found. Run the pipeline first.")
    st.stop()

# Get experiment
experiment = client.get_experiment_by_name(selected_exp)
if not experiment:
    st.error(f"❌ Experiment '{selected_exp}' not found")
    st.stop()

# Get all runs for this experiment
runs = client.search_runs(
    experiment_ids=[experiment.experiment_id],
    order_by=["start_time DESC"],
)

if not runs:
    st.warning("⚠️ No runs found for this experiment")
    st.stop()

# ============================================================================
# OVERVIEW METRICS
# ============================================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📊 Total Runs", len(runs))

with col2:
    st.metric("✅ Successful", sum(1 for r in runs if r.status == "FINISHED"))

with col3:
    st.metric("⏱️ Latest Run", f"{runs[0].end_time - runs[0].start_time:.0f}s" if runs else "N/A")

with col4:
    st.metric("🏆 Best Silhouette", f"{max([r.data.metrics.get('silhouette_score', 0) for r in runs]):.3f}")

st.divider()

# ============================================================================
# RUNS COMPARISON TABLE
# ============================================================================

st.markdown("### 📈 Runs Summary")

# Prepare data for table
runs_data = []
for run in runs:
    metrics = run.data.metrics
    params = run.data.params
    
    runs_data.append({
        "Run ID": run.info.run_id[:8],
        "Status": "✅" if run.status == "FINISHED" else "❌",
        "Algorithm": params.get("algorithm", "N/A"),
        "K Clusters": params.get("best_k", "N/A"),
        "Silhouette": f"{metrics.get('silhouette_score', 0):.3f}",
        "Davies-Bouldin": f"{metrics.get('davies_bouldin_score', 0):.3f}",
        "Calinski-Harabasz": f"{metrics.get('calinski_harabasz_score', 0):.0f}",
        "Start Time": pd.to_datetime(run.info.start_time, unit="ms").strftime("%Y-%m-%d %H:%M:%S"),
    })

df_runs = pd.DataFrame(runs_data)
st.dataframe(df_runs, use_container_width=True)

st.divider()

# ============================================================================
# METRICS VISUALIZATION
# ============================================================================

st.markdown("### 📊 Metrics Analysis")

col1, col2 = st.columns(2)

# Extract metrics
metrics_names = ["silhouette_score", "davies_bouldin_score", "calinski_harabasz_score"]
metrics_values = {name: [] for name in metrics_names}
run_ids = []

for run in runs:
    run_ids.append(run.info.run_id[:8])
    for metric_name in metrics_names:
        metrics_values[metric_name].append(run.data.metrics.get(metric_name, 0))

# Silhouette Score
with col1:
    fig_silhouette = go.Figure()
    fig_silhouette.add_trace(go.Scatter(
        x=run_ids,
        y=metrics_values["silhouette_score"],
        mode="lines+markers",
        name="Silhouette Score",
        line=dict(color="blue", width=2),
        marker=dict(size=8),
    ))
    fig_silhouette.update_layout(
        title="Silhouette Score (Higher is Better)",
        xaxis_title="Run ID",
        yaxis_title="Score",
        hovermode="x unified",
        template="plotly_white",
    )
    st.plotly_chart(fig_silhouette, use_container_width=True)

# Davies-Bouldin Index
with col2:
    fig_db = go.Figure()
    fig_db.add_trace(go.Scatter(
        x=run_ids,
        y=metrics_values["davies_bouldin_score"],
        mode="lines+markers",
        name="Davies-Bouldin Index",
        line=dict(color="orange", width=2),
        marker=dict(size=8),
    ))
    fig_db.update_layout(
        title="Davies-Bouldin Index (Lower is Better)",
        xaxis_title="Run ID",
        yaxis_title="Index",
        hovermode="x unified",
        template="plotly_white",
    )
    st.plotly_chart(fig_db, use_container_width=True)

st.divider()

# ============================================================================
# PARAMETERS ANALYSIS
# ============================================================================

st.markdown("### ⚙️ Parameters Comparison")

col1, col2 = st.columns(2)

# K values distribution
with col1:
    k_values = []
    for run in runs:
        k = run.data.params.get("best_k", None)
        if k:
            k_values.append(int(k))
    
    if k_values:
        fig_k = px.bar(
            x=k_values,
            y=[1] * len(k_values),
            title="K Values Distribution",
            labels={"x": "K Clusters", "y": "Frequency"},
            template="plotly_white",
        )
        fig_k.update_layout(showlegend=False, hovermode="x unified")
        st.plotly_chart(fig_k, use_container_width=True)

# Algorithm distribution
with col2:
    algorithms = [run.data.params.get("algorithm", "Unknown") for run in runs]
    algo_counts = pd.Series(algorithms).value_counts()
    
    fig_algo = px.pie(
        values=algo_counts.values,
        names=algo_counts.index,
        title="Algorithms Used",
        template="plotly_white",
    )
    st.plotly_chart(fig_algo, use_container_width=True)

st.divider()

# ============================================================================
# BEST RUN DETAILS
# ============================================================================

st.markdown("### 🏆 Best Run Details")

best_run = max(runs, key=lambda r: r.data.metrics.get("silhouette_score", 0))

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Run ID", best_run.info.run_id[:12])

with col2:
    st.metric("Algorithm", best_run.data.params.get("algorithm", "N/A"))

with col3:
    st.metric("K Clusters", best_run.data.params.get("best_k", "N/A"))

st.markdown("#### Metrics")
metrics_cols = st.columns(3)

with metrics_cols[0]:
    st.metric(
        "Silhouette Score",
        f"{best_run.data.metrics.get('silhouette_score', 0):.3f}",
        delta="Higher is better" if best_run.data.metrics.get('silhouette_score', 0) > 0.5 else "Needs improvement",
    )

with metrics_cols[1]:
    st.metric(
        "Davies-Bouldin Index",
        f"{best_run.data.metrics.get('davies_bouldin_score', 0):.3f}",
    )

with metrics_cols[2]:
    st.metric(
        "Calinski-Harabasz Score",
        f"{best_run.data.metrics.get('calinski_harabasz_score', 0):.0f}",
    )

st.markdown("#### Parameters")
params_df = pd.DataFrame([best_run.data.params]).T
params_df.columns = ["Value"]
st.dataframe(params_df)

st.divider()

# ============================================================================
# MODEL REGISTRY
# ============================================================================

st.markdown("### 📦 Model Registry")

try:
    model_name = config.get("mlflow.model_name")
    registered_models = client.search_registered_models()
    
    matching_models = [m for m in registered_models if m.name == model_name]
    
    if matching_models:
        model = matching_models[0]
        
        model_info = pd.DataFrame({
            "Version": [v.version for v in model.latest_versions],
            "Stage": [v.current_stage for v in model.latest_versions],
            "Status": [v.status for v in model.latest_versions],
            "Created": [pd.to_datetime(v.creation_timestamp, unit="ms").strftime("%Y-%m-%d %H:%M") 
                       for v in model.latest_versions],
        })
        
        st.dataframe(model_info, use_container_width=True)
    else:
        st.info(f"ℹ️ Model '{model_name}' not yet registered. Run pipeline to register.")
        
except Exception as e:
    st.warning(f"⚠️ Could not load model registry: {e}")

st.divider()

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("""
---
**Olist Customer Segmentation Dashboard** | 
[📖 Documentation](../README.md) | 
[🔧 Configuration](../config/config.yaml) | 
[🧪 Tests](../tests/)

*Last Updated: 2026-05-05*
""")
