"""
Vérifie que `full_pipeline.py` reproduit les métriques attendues (fichier golden).

À lancer après toute modification du prétraitement, du feature engineering ou de KMeans.

Usage:
    python scripts/verify_notebook_parity.py

Le fichier de référence par défaut est `notebooks/reports/clustering_comparison.csv`
(commité dans le dépôt après une exécution validée). Pour enregistrer un nouveau
golden après changement volontaire du notebook / config, exécuter le pipeline puis
committer les CSV dans `notebooks/reports/`.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.full_pipeline import run_full_pipeline  # noqa: E402


def main() -> int:
    golden_path = ROOT / "notebooks" / "reports" / "clustering_comparison.csv"
    if not golden_path.is_file():
        print(f"Fichier golden manquant: {golden_path}")
        return 1

    golden = pd.read_csv(golden_path)
    cols = [
        "silhouette_score",
        "davies_bouldin_score",
        "calinski_harabasz_score",
        "n_clusters",
    ]

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        run_full_pipeline(output_dir=str(out), models_dir=str(out / "models"))
        new = pd.read_csv(out / "clustering_comparison.csv")

    g = golden[cols].sort_values("n_clusters").reset_index(drop=True)
    n = new[cols].sort_values("n_clusters").reset_index(drop=True)

    try:
        pd.testing.assert_frame_equal(
            n,
            g,
            check_exact=False,
            rtol=1e-4,
            atol=1e-6,
        )
    except AssertionError as e:
        print("Écart détecté entre le pipeline et le golden clustering_comparison.csv:\n")
        print(e)
        print("\n--- Nouveau ---\n", n)
        print("\n--- Golden ---\n", g)
        return 1

    print("OK — métriques de clustering (k=4..8) alignées avec le golden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
