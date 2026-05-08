"""
Génère notebooks/reports/customer_orders_db.csv déjà agrégé au niveau order_id.
base_final.csv est au niveau order_item_id x payment_sequential :
  - Chaque commande peut avoir N lignes (N articles x M modes de paiement).
  - On agrège par (customer_unique_id, order_id) pour obtenir 1 ligne par commande.
"""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent
src  = ROOT / "data" / "base_final.csv"
dst  = ROOT / "notebooks" / "reports" / "customer_orders_db.csv"

needed = [
    "customer_unique_id", "order_id", "order_status",
    "order_purchase_timestamp", "order_delivered_customer_date",
    "payment_value", "payment_installments", "review_score"
]

print("Chargement de base_final.csv …")
df = pd.read_csv(src, usecols=needed, low_memory=False)
print(f"  Lignes brutes : {len(df):,}")
print(f"  Clients uniques : {df['customer_unique_id'].nunique():,}")
print(f"  Orders uniques  : {df['order_id'].nunique():,}")

# ── 1. Filtrer sur les commandes livrées (cohérent avec le pipeline) ─────────
df = df[df["order_status"] == "delivered"].copy()
print(f"  Après filtre delivered : {len(df):,} lignes, {df['order_id'].nunique():,} orders")

# ── 2. Agrégation par (customer_unique_id, order_id) ─────────────────────────
# payment_value : même valeur répétée par item → on prend max (= total commande)
# payment_installments : idem → max
# review_score : idem → max
# timestamps : idem → first
agg = (
    df.groupby(["customer_unique_id", "order_id"], sort=False)
    .agg(
        order_status=("order_status", "first"),
        order_purchase_timestamp=("order_purchase_timestamp", "first"),
        order_delivered_customer_date=("order_delivered_customer_date", "first"),
        payment_value=("payment_value", "max"),
        payment_installments=("payment_installments", "max"),
        review_score=("review_score", "max"),
    )
    .reset_index()
)

print(f"\nAprès agrégation :")
print(f"  Lignes (= commandes uniques) : {len(agg):,}")
print(f"  Clients uniques              : {agg['customer_unique_id'].nunique():,}")

# ── 3. Vérification : lignes par client ──────────────────────────────────────
orders_per_customer = agg.groupby("customer_unique_id")["order_id"].nunique()
print(f"\nDistribution du nombre de commandes par client :")
print(orders_per_customer.value_counts().sort_index().to_string())

agg.to_csv(dst, index=False)
size_mb = dst.stat().st_size / 1024 / 1024
print(f"\nFichier sauvegardé : {dst}  ({size_mb:.1f} MB)")
