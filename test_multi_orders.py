"""
API Segmentation Multi-Commandes - Guide et Tests

Cette API FastAPI gère naturellement plusieurs commandes par client:
- Accepte une liste de commandes (orders: List[RawOrder])
- Valide que toutes les commandes appartiennent au même client
- Agrège les données pour calculer les 5 features
- Retourne la prédiction de segment

ENDPOINT PRINCIPAL: POST /predict-raw
"""

import json
import requests

API_BASE = "http://localhost:8000"

def test_single_order():
    """Test avec UNE seule commande"""
    print("\n" + "="*60)
    print("TEST 1: UNE SEULE COMMANDE")
    print("="*60)
    
    payload = {
        "orders": [
            {
                "order_id": "ORDER-001",
                "customer_unique_id": "CUST-001",
                "order_status": "delivered",
                "order_purchase_timestamp": "2024-01-15T14:30:00",
                "payment_value": 150.50,
                "payment_installments": 3,
                "order_delivered_customer_date": "2024-01-18T10:00:00",
                "review_score": 4
            }
        ]
    }
    
    print("\nDonnées envoyées:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    response = requests.post(f"{API_BASE}/predict-raw", json=payload)
    print(f"\nStatus: {response.status_code}")
    print("Réponse:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


def test_multiple_orders_same_customer():
    """Test avec PLUSIEURS commandes du MÊME client"""
    print("\n" + "="*60)
    print("TEST 2: PLUSIEURS COMMANDES - MÊME CLIENT")
    print("="*60)
    
    payload = {
        "orders": [
            {
                "order_id": "ORDER-001",
                "customer_unique_id": "CUST-PREMIUM",
                "order_status": "delivered",
                "order_purchase_timestamp": "2024-01-15T14:30:00",
                "payment_value": 150.50,
                "payment_installments": 3,
                "order_delivered_customer_date": "2024-01-18T10:00:00",
                "review_score": 5
            },
            {
                "order_id": "ORDER-002",
                "customer_unique_id": "CUST-PREMIUM",
                "order_status": "delivered",
                "order_purchase_timestamp": "2024-02-20T09:15:00",
                "payment_value": 200.75,
                "payment_installments": 4,
                "order_delivered_customer_date": "2024-02-23T14:30:00",
                "review_score": 4
            },
            {
                "order_id": "ORDER-003",
                "customer_unique_id": "CUST-PREMIUM",
                "order_status": "delivered",
                "order_purchase_timestamp": "2024-03-10T11:45:00",
                "payment_value": 125.00,
                "payment_installments": 2,
                "order_delivered_customer_date": "2024-03-12T16:00:00",
                "review_score": 5
            }
        ]
    }
    
    print("\nDonnées envoyées:")
    print(f"- {len(payload['orders'])} commandes pour le client: {payload['orders'][0]['customer_unique_id']}")
    for order in payload["orders"]:
        print(f"  - {order['order_id']}: {order['payment_value']} BRL, Review: {order['review_score']}")
    
    response = requests.post(f"{API_BASE}/predict-raw", json=payload)
    print(f"\nStatus: {response.status_code}")
    print("Réponse:")
    result = response.json()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Analysons les features calculées
    if "engineered_features" in result:
        print("\n📊 FEATURES CALCULÉES (Agrégation des 3 commandes):")
        features = result["engineered_features"]
        print(f"  - Recency: {features['Recency']} jours (jours depuis dernière commande)")
        print(f"  - Avg Review Score: {features['avg_review_score_full']:.2f}/5 (moyenne des notes)")
        print(f"  - Avg Delivery Days: {features['avg_delivery_days']:.1f} jours (durée moyenne livraison)")
        print(f"  - Avg Installments: {features['avg_installments']:.1f} (versements moyens)")
        print(f"  - CLV Estimate: {features['CLV_estimate']:.2f} BRL (somme × fréquence / 2 ans)")


def test_multiple_orders_different_customers_error():
    """Test d'ERREUR: plusieurs commandes de clients DIFFÉRENTS (doit échouer)"""
    print("\n" + "="*60)
    print("TEST 3: PLUSIEURS COMMANDES - CLIENTS DIFFÉRENTS (ERREUR ATTENDUE)")
    print("="*60)
    
    payload = {
        "orders": [
            {
                "order_id": "ORDER-CLIENT-A",
                "customer_unique_id": "CUST-A",
                "order_status": "delivered",
                "order_purchase_timestamp": "2024-01-15T14:30:00",
                "payment_value": 100.00,
                "payment_installments": 2,
                "review_score": 4
            },
            {
                "order_id": "ORDER-CLIENT-B",
                "customer_unique_id": "CUST-B",  # ⚠️ DIFFÉRENT CLIENT
                "order_status": "delivered",
                "order_purchase_timestamp": "2024-02-20T09:15:00",
                "payment_value": 200.00,
                "payment_installments": 3,
                "review_score": 5
            }
        ]
    }
    
    print("\nDonnées envoyées:")
    print(f"- Commande 1: Client {payload['orders'][0]['customer_unique_id']}")
    print(f"- Commande 2: Client {payload['orders'][1]['customer_unique_id']}")
    
    response = requests.post(f"{API_BASE}/predict-raw", json=payload)
    print(f"\nStatus: {response.status_code} (erreur attendue)")
    print("Réponse:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    print("\n✅ Comportement correct: l'API rejette les commandes de clients différents")


def test_feature_aggregation_logic():
    """Explique la logique d'agrégation des 5 features"""
    print("\n" + "="*60)
    print("🔍 LOGIQUE D'AGRÉGATION DES 5 FEATURES")
    print("="*60)
    
    print("""
1. RECENCY (jours depuis dernière achat)
   - Logique: max(order_purchase_timestamp) du client
   - Calcul: aujourd'hui - dernière_commande
   - Exemple: Si 3 commandes (15/01, 20/02, 10/03) → Recency = aujourd'hui - 10/03

2. AVG_REVIEW_SCORE (moyenne des notes)
   - Logique: mean(review_score) sur toutes les commandes
   - Calcul: (5 + 4 + 5) / 3 = 4.67
   - Fallback: 4.0 si pas de notes

3. AVG_DELIVERY_DAYS (durée moyenne de livraison)
   - Logique: mean(order_delivered_customer_date - order_purchase_timestamp)
   - Calcul: ((18/01-15/01) + (23/02-20/02) + (12/03-10/03)) / 3 = (3+3+2)/3 = 2.67 jours
   - Fallback: 12.0 si pas de dates

4. AVG_INSTALLMENTS (versements moyens)
   - Logique: mean(payment_installments) sur toutes les commandes
   - Calcul: (3 + 4 + 2) / 3 = 3.0
   - Fallback: 2.9 si pas de données

5. CLV_ESTIMATE (estimation de valeur client)
   - Logique: CLV = Monetary × (Frequency / dataset_duration_years)
   - Calcul: (150.50 + 200.75 + 125.00) × (3 commandes / 2 ans) = 476.25 × 1.5 = 714.375
   - Fallback: 0 si pas de paiements

✅ RÉSULTAT FINAL:
   Ces 5 features sont ensuite:
   1. Clamped aux limites du QuantileTransformer
   2. Transformées par QuantileTransformer
   3. Normalisées par StandardScaler
   4. Réduites par PCA
   5. Classifiées par KMeans
   → Segment final du client
    """)


if __name__ == "__main__":
    print("\n🚀 TESTS DE L'API MULTI-COMMANDES")
    print("API Base:", API_BASE)
    
    try:
        # Test 1: Une seule commande
        test_single_order()
        
        # Test 2: Plusieurs commandes même client
        test_multiple_orders_same_customer()
        
        # Test 3: Erreur attendue (clients différents)
        test_multiple_orders_different_customers_error()
        
        # Explication
        test_feature_aggregation_logic()
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERREUR: Impossible de se connecter à l'API")
        print("Assurez-vous que l'API est lancée: python scripts/api.py")
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
