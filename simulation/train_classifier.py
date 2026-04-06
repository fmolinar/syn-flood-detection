#!/usr/bin/env python3
"""Train and evaluate ML classifiers on the differential port statistics dataset.

Implements Section III-F (ML Classifier) and Section IV (Experimentation) of
the Flood Control paper.  Trains a Random Forest (primary), MLP, and SVM on
train.csv and evaluates on test.csv, reporting Accuracy, Precision, Recall,
and F-Measure — the exact metrics used in the paper.

The trained Random Forest model is saved to data/model.pkl for use by the
Threat Detection and Localization modules (Milestones 7 and 8).

Usage:
    python3 simulation/train_classifier.py
    python3 simulation/train_classifier.py --train data/train.csv \\
        --test data/test.csv --model-out data/model.pkl
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

try:
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        precision_score,
        recall_score,
    )
    from sklearn.neural_network import MLPClassifier
    from sklearn.svm import SVC
except ImportError as exc:
    raise SystemExit(
        "scikit-learn and pandas are required:\n  pip install pandas scikit-learn"
    ) from exc

from build_dataset import FEATURE_COLS

LABEL_COL = "label"

# Classifiers evaluated in the paper (Table III).
# RF is primary; MLP and SVM are comparison baselines.
CLASSIFIERS: dict[str, object] = {
    "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
    "MLP": MLPClassifier(hidden_layer_sizes=(100,), max_iter=500, random_state=42),
    "SVM": SVC(kernel="rbf", probability=True, random_state=42),
}


# ------------------------------------------------------------------
# Core logic
# ------------------------------------------------------------------

def load_split(path: Path) -> tuple[pd.DataFrame, pd.Series]:
    df = pd.read_csv(path)
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing feature columns in {path}: {missing}")
    if LABEL_COL not in df.columns:
        raise SystemExit(f"Missing '{LABEL_COL}' column in {path}")
    return df[FEATURE_COLS], df[LABEL_COL]


def evaluate(name: str, clf, X_train, y_train, X_test, y_test) -> dict:
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)

    metrics = {
        "Accuracy":  accuracy_score(y_test, y_pred),
        "Precision": precision_score(y_test, y_pred, zero_division=0),
        "Recall":    recall_score(y_test, y_pred, zero_division=0),
        "F-Measure": f1_score(y_test, y_pred, zero_division=0),
    }

    print(f"\n  {name}")
    print(f"  {'─' * 40}")
    for metric, value in metrics.items():
        bar = "█" * int(value * 30)
        print(f"  {metric:<12} {value:.4f}  {bar}")

    return metrics


def train(
    train_path: Path,
    test_path: Path,
    model_out: Path,
    results_out: Path,
) -> None:
    if not train_path.exists():
        raise SystemExit(
            f"Train file not found: {train_path}\n"
            "Run: python3 simulation/build_dataset.py"
        )
    if not test_path.exists():
        raise SystemExit(f"Test file not found: {test_path}")

    print(f"[Classifier] Loading train: {train_path}")
    X_train, y_train = load_split(train_path)
    print(f"[Classifier] Loading test : {test_path}")
    X_test, y_test = load_split(test_path)

    print(f"\n[Classifier] Train: {len(X_train):,} samples  "
          f"(normal={int((y_train==0).sum())}, attack={int((y_train==1).sum())})")
    print(f"[Classifier] Test : {len(X_test):,} samples  "
          f"(normal={int((y_test==0).sum())}, attack={int((y_test==1).sum())})")
    print(f"\n[Classifier] Training {len(CLASSIFIERS)} classifiers …\n")
    print("=" * 50)

    all_results: dict[str, dict] = {}
    trained_models: dict[str, object] = {}

    for name, clf in CLASSIFIERS.items():
        metrics = evaluate(name, clf, X_train, y_train, X_test, y_test)
        all_results[name] = metrics
        trained_models[name] = clf

    # ------------------------------------------------------------------
    # Summary table (matches Table III layout in the paper)
    # ------------------------------------------------------------------
    print("\n\n" + "=" * 50)
    print("  TABLE III — Classifier performance")
    print("=" * 50)
    print(f"  {'Classifier':<22} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F-Measure':>10}")
    print(f"  {'─' * 66}")
    for name, m in all_results.items():
        print(
            f"  {name:<22} {m['Accuracy']:>9.3%} {m['Precision']:>10.3%}"
            f" {m['Recall']:>9.3%} {m['F-Measure']:>10.3%}"
        )
    print("=" * 50)

    # ------------------------------------------------------------------
    # Save the best model (Random Forest) — used by Milestones 7 & 8
    # ------------------------------------------------------------------
    rf_model = trained_models["Random Forest"]
    model_out.parent.mkdir(parents=True, exist_ok=True)
    with open(model_out, "wb") as f:
        pickle.dump(rf_model, f)
    print(f"\n[Classifier] Random Forest model saved → {model_out}")

    # Save all metrics as JSON for downstream use
    results_out.parent.mkdir(parents=True, exist_ok=True)
    results_out.write_text(json.dumps(all_results, indent=2))
    print(f"[Classifier] Results saved            → {results_out}")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Train RF, MLP, and SVM classifiers on the port stats dataset."
    )
    p.add_argument("--train", default="data/train.csv", help="Path to train.csv.")
    p.add_argument("--test", default="data/test.csv", help="Path to test.csv.")
    p.add_argument(
        "--model-out",
        default="data/model.pkl",
        help="Output path for the saved Random Forest model (default: data/model.pkl).",
    )
    p.add_argument(
        "--results-out",
        default="data/results.json",
        help="Output path for metrics JSON (default: data/results.json).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    train(
        train_path=Path(args.train),
        test_path=Path(args.test),
        model_out=Path(args.model_out),
        results_out=Path(args.results_out),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
