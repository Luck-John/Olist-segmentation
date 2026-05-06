"""
Test script to validate the pipeline and API
"""

import os
import sys
import json
import pickle
from pathlib import Path

import pandas as pd
import requests
import time
import subprocess

def test_pipeline_outputs():
    """Test if pipeline generated all expected outputs"""
    print("=" * 70)
    print("TEST 1: Checking Pipeline Outputs")
    print("=" * 70)
    
    expected_files = {
        "notebooks/models/final_pipeline.pkl": "Final pipeline model",
        "notebooks/models/cluster_names.json": "Cluster names mapping",
        "notebooks/reports/clustering_comparison.csv": "Clustering metrics comparison",
        "notebooks/reports/cluster_profiles_mean.csv": "Cluster profiles (mean)",
        "notebooks/reports/cluster_profiles_median.csv": "Cluster profiles (median)",
        "notebooks/reports/segmentation_finale_olist.csv": "Final segmentation results",
    }
    
    all_exist = True
    for filepath, description in expected_files.items():
        exists = Path(filepath).exists()
        status = "✅" if exists else "❌"
        print(f"{status} {description}: {filepath}")
        if not exists:
            all_exist = False
    
    if all_exist:
        print("\n✅ All pipeline outputs exist!\n")
    else:
        print("\n⚠️  Some outputs are missing. Run: python scripts/full_pipeline.py\n")
    
    return all_exist


def test_model_loading():
    """Test loading the trained model"""
    print("=" * 70)
    print("TEST 2: Loading Trained Model")
    print("=" * 70)
    
    try:
        with open("notebooks/models/final_pipeline.pkl", "rb") as f:
            pipeline = pickle.load(f)
        
        print(f"✅ Model loaded successfully")
        print(f"   - Best k: {pipeline.get('best_k')}")
        print(f"   - Number of features: {len(pipeline.get('feature_cols', []))}")
        print(f"   - Cluster names: {pipeline.get('cluster_names')}")
        print(f"   - Segment actions: {pipeline.get('segment_actions')}\n")
        
        return pipeline
    except Exception as e:
        print(f"❌ Error loading model: {e}\n")
        return None


def test_data_loading():
    """Test loading CSV reports"""
    print("=" * 70)
    print("TEST 3: Loading CSV Reports")
    print("=" * 70)
    
    try:
        # Load final results
        df_results = pd.read_csv("notebooks/reports/segmentation_finale_olist.csv")
        print(f"✅ Loaded final results: {len(df_results)} customers")
        print(f"   Columns: {list(df_results.columns)}")
        print(f"   Segments:\n{df_results['segment'].value_counts()}\n")
        
        # Load profiles
        profiles_mean = pd.read_csv("notebooks/reports/cluster_profiles_mean.csv", index_col=0)
        print(f"✅ Loaded cluster profiles (mean): {profiles_mean.shape}")
        
        # Load metrics
        metrics = pd.read_csv("notebooks/reports/clustering_comparison.csv")
        print(f"✅ Loaded clustering metrics: {len(metrics)} runs")
        print(f"   Best silhouette: {metrics['silhouette_score'].max():.4f}\n")
        
        return True
    except Exception as e:
        print(f"❌ Error loading data: {e}\n")
        return False


def test_api_health():
    """Test API health endpoint"""
    print("=" * 70)
    print("TEST 4: API Health Check")
    print("=" * 70)
    
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is healthy")
            print(f"   Status: {data.get('status')}")
            print(f"   API ready: {data.get('api_ready')}")
            print(f"   Model loaded: {data.get('model_loaded')}\n")
            return True
        else:
            print(f"❌ API returned status {response.status_code}\n")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is it running? (python scripts/start_api.py)\n")
        return False
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


def test_api_prediction():
    """Test API prediction endpoint"""
    print("=" * 70)
    print("TEST 5: API Prediction")
    print("=" * 70)
    
    # Example customer
    customer = {
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
    
    try:
        response = requests.post(
            "http://127.0.0.1:8000/predict",
            json={"customer_features": customer},
            timeout=5
        )
        
        if response.status_code == 200:
            prediction = response.json()
            print(f"✅ Prediction successful")
            print(f"   Cluster: {prediction.get('cluster')}")
            print(f"   Segment: {prediction.get('segment_name')}")
            print(f"   Action: {prediction.get('segment_action')}")
            print(f"   Confidence: {prediction.get('confidence'):.2%}")
            print(f"   PCA coords: ({prediction.get('pca_1'):.2f}, {prediction.get('pca_2'):.2f})\n")
            return True
        else:
            print(f"❌ Prediction failed with status {response.status_code}")
            print(f"   Error: {response.text}\n")
            return False
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


def test_api_profiles():
    """Test API profiles endpoint"""
    print("=" * 70)
    print("TEST 6: API Cluster Profiles")
    print("=" * 70)
    
    try:
        response = requests.get("http://127.0.0.1:8000/profiles", timeout=5)
        
        if response.status_code == 200:
            profiles = response.json()
            print(f"✅ Profiles retrieved: {len(profiles)} clusters")
            for profile in profiles:
                print(f"   - Cluster {profile['cluster_id']}: {profile['segment_name']} ({profile['segment_action']})")
            print()
            return True
        else:
            print(f"❌ Failed with status {response.status_code}\n")
            return False
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


def test_api_metrics():
    """Test API metrics endpoint"""
    print("=" * 70)
    print("TEST 7: API Clustering Metrics")
    print("=" * 70)
    
    try:
        response = requests.get("http://127.0.0.1:8000/metrics", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            metrics = data.get('metrics', [])
            print(f"✅ Metrics retrieved: {len(metrics)} configurations")
            
            # Sort by silhouette score
            sorted_metrics = sorted(metrics, key=lambda x: x.get('silhouette_score', 0), reverse=True)
            for m in sorted_metrics[:3]:
                print(f"   k={m['n_clusters']}: silhouette={m.get('silhouette_score', 0):.4f}")
            print()
            return True
        else:
            print(f"❌ Failed with status {response.status_code}\n")
            return False
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


def test_api_statistics():
    """Test API statistics endpoint"""
    print("=" * 70)
    print("TEST 8: API Segment Statistics")
    print("=" * 70)
    
    try:
        response = requests.get("http://127.0.0.1:8000/statistics", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Statistics retrieved")
            print(f"   Total customers: {data.get('total_customers')}")
            print(f"   Segments:")
            for segment, stats in data.get('segments', {}).items():
                print(f"      - {segment}: {stats['count']:,} ({stats['percentage']:.1f}%)")
            print()
            return True
        else:
            print(f"❌ Failed with status {response.status_code}\n")
            return False
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("CUSTOMER SEGMENTATION - PIPELINE & API TEST SUITE")
    print("=" * 70 + "\n")
    
    results = {}
    
    # Test 1: Pipeline outputs
    results['pipeline_outputs'] = test_pipeline_outputs()
    
    if not results['pipeline_outputs']:
        print("⚠️  Skipping remaining tests - run pipeline first\n")
        return
    
    # Test 2: Model loading
    pipeline = test_model_loading()
    results['model_loading'] = pipeline is not None
    
    # Test 3: Data loading
    results['data_loading'] = test_data_loading()
    
    # Test 4-8: API tests
    print("⏳ Checking if API is running...\n")
    
    api_running = False
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=2)
        api_running = response.status_code == 200
    except:
        pass
    
    if api_running:
        results['api_health'] = test_api_health()
        results['api_prediction'] = test_api_prediction()
        results['api_profiles'] = test_api_profiles()
        results['api_metrics'] = test_api_metrics()
        results['api_statistics'] = test_api_statistics()
    else:
        print("⚠️  API is not running. Start it with: python scripts/start_api.py\n")
        print("   API tests skipped (tests 4-8)\n")
        results['api_tests_skipped'] = True
    
    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v is True)
    total = len([v for v in results.values() if v is not True and v is not None and v is not False])
    
    print(f"\n✅ Passed: {passed}")
    print(f"❌ Failed: {sum(1 for v in results.values() if v is False)}")
    print(f"⏭️  Skipped: {sum(1 for v in results.values() if v is None)}")
    print()
    
    if results.get('api_tests_skipped'):
        print("To run full tests including API endpoints:")
        print("  1. In terminal 1: python scripts/start_api.py")
        print("  2. In terminal 2: python scripts/test_suite.py")
        print()


if __name__ == "__main__":
    main()
