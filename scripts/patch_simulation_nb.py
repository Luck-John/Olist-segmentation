"""
Patch simulation_frequence_maj.ipynb selon les remarques de revue :
  1. Modèle de référence = pipeline de production (final_pipeline.pkl)
     au lieu d'un modèle ré-entraîné sur Q1 2017.
  2. Features de référence = toutes les données (snapshot global).
  3. Seuils ARI corrigés : 0.75 (réentraînement) / 0.5 (critique).
  4. Critères de dégradation alignés (ARI < 0.75 au lieu de < 0.3).
"""
import json, copy

NB_PATH = "notebooks/simulation_frequence_maj.ipynb"

with open(NB_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)


def replace_cell_source(nb, cell_idx, new_source):
    nb["cells"][cell_idx]["source"] = new_source.splitlines(keepends=True)
    nb["cells"][cell_idx]["outputs"] = []
    nb["cells"][cell_idx]["execution_count"] = None


# ─────────────────────────────────────────────────────────────────────────────
# Cellule 10 : remplacer l'entraînement sur Q1 2017 par le chargement
#              du pipeline de production.
# ─────────────────────────────────────────────────────────────────────────────
NEW_CELL_10 = """\
# ─────────────────────────────────────────────────────────────────────
# MODÈLE DE RÉFÉRENCE = pipeline de production (final_pipeline.pkl)
# ─────────────────────────────────────────────────────────────────────
# Pourquoi ?  Entraîner un modèle sur Q1 2017 seul (~5-8 % des données)
# ne représente pas le modèle de production réel. On mesurerait la dérive
# par rapport à un modèle sous-représentatif, et non par rapport au modèle
# déployé.  La bonne pratique MLOps est d'utiliser le modèle de production
# comme référence figée.
# ─────────────────────────────────────────────────────────────────────

PROD_PIPELINE_PATH = "../models/final_pipeline.pkl"
with open(PROD_PIPELINE_PATH, "rb") as f:
    prod = pickle.load(f)

# Vérification que les features sont identiques
assert prod["feature_cols"] == FEATURE_COLS, (
    f"Features du pipeline de production ({prod['feature_cols']}) "
    f"différentes de FEATURE_COLS ({FEATURE_COLS})"
)
assert prod["best_k"] == K, (
    f"K du pipeline ({prod['best_k']}) différent de K ({K})"
)

# Adapter les clés pour être compatibles avec predict_with_pipeline()
# (qui attend 'qt', 'scaler', 'pca', 'model')
pipeline_ref = {
    "qt":      prod["quantile_transformer"],
    "scaler":  prod["scaler"],
    "pca":     prod["pca"],
    "model":   prod["model"],
}

# Features de référence = TOUTES les données (snapshot global)
snapshot_ref = df_raw["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
features_ref = compute_features_for_window(df_raw, snapshot_ref)

labels_ref, X_pca_ref = predict_with_pipeline(pipeline_ref, features_ref)
pipeline_ref["labels"] = labels_ref
pipeline_ref["X_pca"]  = X_pca_ref

sil_ref = silhouette_score(X_pca_ref, labels_ref) if len(set(labels_ref)) > 1 else 0

print("=" * 60)
print("MODÈLE DE RÉFÉRENCE : pipeline de production")
print("=" * 60)
print(f"  Fichier          : {PROD_PIPELINE_PATH}")
print(f"  Features         : {FEATURE_COLS}")
print(f"  K                : {K}")
print(f"  Clients (base)   : {len(features_ref)}")
print(f"  Silhouette réf.  : {sil_ref:.4f}")
dist = {int(c): int((labels_ref == c).sum()) for c in range(K)}
print(f"  Distribution     : {dist}")
"""

replace_cell_source(nb, 10, NEW_CELL_10)


# ─────────────────────────────────────────────────────────────────────────────
# Cellule 14 : seuils ARI corrigés
#   0.75 → seuil de réentraînement recommandé
#   0.5  → seuil critique (segments méconnaissables)
# ─────────────────────────────────────────────────────────────────────────────
src14 = "".join(nb["cells"][14]["source"])

# Barre de couleur ARI
src14 = src14.replace(
    "color=['#27ae60' if a > 0.5 else '#f39c12' if a > 0.2 else '#e74c3c' for a in df_results['ari']]",
    "color=['#27ae60' if a > 0.75 else '#f39c12' if a > 0.5 else '#e74c3c' for a in df_results['ari']]"
)
# Ligne seuil modéré
src14 = src14.replace(
    "ax.axhline(y=0.5, color='orange', linestyle='--', alpha=0.7, label='Seuil modéré (0.5)')",
    "ax.axhline(y=0.75, color='orange', linestyle='--', alpha=0.7, label='Seuil réentraînement (0.75)')"
)
# Ligne seuil critique
src14 = src14.replace(
    "ax.axhline(y=0.2, color='red', linestyle='--', alpha=0.7, label='Seuil critique (0.2)')",
    "ax.axhline(y=0.5,  color='red',    linestyle='--', alpha=0.7, label='Seuil critique (0.5)')"
)

nb["cells"][14]["source"] = src14.splitlines(keepends=True)
nb["cells"][14]["outputs"] = []
nb["cells"][14]["execution_count"] = None


# ─────────────────────────────────────────────────────────────────────────────
# Cellule 20 : critères de déclenchement du réentraînement corrigés
#   ARI < 0.75  au lieu de < 0.3
#   Mention explicite du seuil 0.75 dans le texte de recommandation
# ─────────────────────────────────────────────────────────────────────────────
NEW_CELL_20 = """\
# ─────────────────────────────────────────────────────────────────────
# Recommandation automatique de fréquence de mise à jour
# ─────────────────────────────────────────────────────────────────────
# Seuils utilisés (alignés sur les bonnes pratiques MLOps) :
#   ARI < 0.75 → structure des clusters suffisamment modifiée pour
#                justifier un réentraînement.
#   ARI < 0.5  → seuil critique : les segments sont méconnaissables.
#   PSI > 0.25 → changement majeur de la distribution des clusters.
#   KS  > 0.2  → drift significatif des features d'entrée.
# ─────────────────────────────────────────────────────────────────────

ARI_RETRAIN   = 0.75   # En dessous → réentraînement justifié
ARI_CRITICAL  = 0.50   # En dessous → urgent
PSI_MAJOR     = 0.25
KS_MAJOR      = 0.20

first_degrade = None
for _, row in df_results.iterrows():
    if row["ari"] < ARI_RETRAIN or row["psi"] > PSI_MAJOR or row["avg_ks_stat"] > KS_MAJOR:
        first_degrade = row["quarter"]
        break

print("=" * 70)
print("RECOMMANDATION DE FRÉQUENCE DE MISE À JOUR")
print("=" * 70)

if first_degrade:
    quarters_str = [str(q) for q in quarters]
    n_q = quarters_str.index(first_degrade)  # nombre de trimestres stables
    print(f"Première dégradation détectée au : {first_degrade}")
    print(f"Trimestres stables avant dégradation : {n_q}")
    print()
    if n_q <= 1:
        print("  → Fréquence recommandée : MENSUELLE à TRIMESTRIELLE")
    elif n_q <= 2:
        print("  → Fréquence recommandée : TRIMESTRIELLE (tous les 3 mois)")
    elif n_q <= 4:
        print("  → Fréquence recommandée : SEMESTRIELLE (tous les 6 mois)")
    else:
        print("  → Fréquence recommandée : ANNUELLE")
else:
    print("Aucune dégradation détectée sur la période analysée.")
    print("  → Fréquence recommandée : SEMESTRIELLE avec monitoring continu")

print()
print("Critères de déclenchement d'un réentraînement :")
print(f"  • ARI < {ARI_RETRAIN}  (structure des clusters modifiée)")
print(f"  • ARI < {ARI_CRITICAL}  (seuil critique – segments méconnaissables)")
print(f"  • PSI > {PSI_MAJOR}  (changement majeur de distribution des clusters)")
print(f"  • KS  > {KS_MAJOR}  (drift significatif des features)")
print(f"  • Silhouette gap > 0.05 (gain significatif du ré-entraînement)")

# Tableau récapitulatif des signaux de dérive
print()
print(df_results[["quarter", "ari", "psi", "avg_ks_stat", "silhouette_gap"]].to_string(index=False))
"""

replace_cell_source(nb, 20, NEW_CELL_20)


# ─────────────────────────────────────────────────────────────────────────────
# Sauvegarder
# ─────────────────────────────────────────────────────────────────────────────
with open(NB_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook patché avec succès : {NB_PATH}")
print("Cellules modifiées : 10 (pipeline de production), 14 (seuils ARI), 20 (critères de dégradation)")
