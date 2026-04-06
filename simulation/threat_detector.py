#!/usr/bin/env python3
"""Threat Detection module — Section III-G of the Flood Control paper.

For each observed network flow, classifies it as normal or under TCP-SYN
flood attack using the pre-trained Random Forest model and a configurable
port threshold Φ.

Algorithm (Equations 3–5 of the paper):
    For each flow u_i across all switches:
        For each port p of that flow:
            ω_p = 1 if ν(port_stats) == Attack else 0      (Eq. 3)
        η_p  = Σ ω_p   (total attacking ports)             (Eq. 4)
        flow = Attack   if η_p / W_i >= Φ else Normal      (Eq. 5)

    Where W_i = total number of ports the flow traverses
    and   Φ   = port threshold hyperparameter (paper uses Φ=0.3)

In the simulation, each polling round (one N_*.json file) represents
one observed flow snapshot — its port records are classified individually
and then aggregated under the Φ rule.

Usage:
    python3 simulation/threat_detector.py --data-dir data/raw/normal --phi 0.3
    python3 simulation/threat_detector.py --data-dir data/raw/attack  --phi 0.3
    python3 simulation/threat_detector.py --csv data/test.csv --phi 0.3
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

try:
    import pandas as pd
    import numpy as np
except ImportError as exc:
    raise SystemExit("pandas and numpy are required: pip install pandas numpy") from exc

from build_dataset import FEATURE_COLS

DEFAULT_PHI = 0.3  # port threshold (paper's optimal value)


# ------------------------------------------------------------------
# Core detection logic
# ------------------------------------------------------------------

def load_model(model_path: Path):
    if not model_path.exists():
        raise SystemExit(
            f"Model not found: {model_path}\n"
            "Run: python3 simulation/train_classifier.py"
        )
    with open(model_path, "rb") as f:
        return pickle.load(f)


def classify_ports(clf, records: list[dict]) -> tuple[int, int]:
    """Run classifier on a list of per-port records.

    Returns:
        (attacking_ports, total_ports)
    """
    df = pd.DataFrame(records)
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        # Fill missing features with 0 (graceful degradation for live data).
        for col in missing:
            df[col] = 0
    preds = clf.predict(df[FEATURE_COLS])   # 0 = normal, 1 = attack
    return int(preds.sum()), len(preds)


def detect_flow(clf, records: list[dict], phi: float) -> dict:
    """Classify a single flow (one polling round's port records).

    Returns a result dict with prediction, port counts, and ratio.
    """
    attacking, total = classify_ports(clf, records)
    ratio = attacking / total if total > 0 else 0.0
    label = "Attack" if ratio >= phi else "Normal"
    return {
        "prediction": label,
        "attacking_ports": attacking,
        "total_ports": total,
        "ratio": round(ratio, 4),
        "phi": phi,
    }


# ------------------------------------------------------------------
# Entry points
# ------------------------------------------------------------------

def detect_from_json_dir(
    clf,
    data_dir: Path,
    phi: float,
    ground_truth_label: str | None = None,
) -> list[dict]:
    """Detect threats across all N_*.json files in a directory.

    Each file = one polling round = one 'flow' in the paper's terminology.
    """
    files = sorted(data_dir.glob("N_*.json"))
    if not files:
        raise SystemExit(f"No N_*.json files found in {data_dir}")

    results = []
    for i, f in enumerate(files):
        records = json.loads(f.read_text())
        result = detect_flow(clf, records, phi)
        result["flow_id"] = i
        result["source_file"] = f.name
        if ground_truth_label is not None:
            result["ground_truth"] = ground_truth_label.capitalize()
            result["correct"] = result["prediction"] == result["ground_truth"]
        results.append(result)
    return results


def detect_from_csv(clf, csv_path: Path, phi: float) -> list[dict]:
    """Detect threats from a CSV (e.g. data/test.csv).

    Groups rows into synthetic flows — each unique (switch, port_no) pair's
    records across the file form one polling round, then we treat the entire
    file as U flows where each row is one port observation.

    For simplicity in offline evaluation, each row is treated as a single-port
    flow and aggregated in windows of all rows (one 'flow' = entire CSV batch).
    This lets us validate the Φ logic against labeled data.
    """
    df = pd.read_csv(csv_path)
    has_label = "label" in df.columns

    records = df[FEATURE_COLS].to_dict(orient="records")
    if has_label:
        # Evaluate per ground-truth label group
        results = []
        for label_val, group in df.groupby("label"):
            group_records = group[FEATURE_COLS].to_dict(orient="records")
            result = detect_flow(clf, group_records, phi)
            ground_truth = "Attack" if label_val == 1 else "Normal"
            result["ground_truth"] = ground_truth
            result["correct"] = result["prediction"] == ground_truth
            result["group_size"] = len(group_records)
            results.append(result)
        return results
    else:
        result = detect_flow(clf, records, phi)
        result["group_size"] = len(records)
        return [result]


def print_results(results: list[dict], source_label: str) -> None:
    total = len(results)
    print(f"\n{'=' * 56}")
    print(f"  Threat Detection Results — {source_label}")
    print(f"  Φ (port threshold) = {results[0]['phi']}")
    print(f"{'=' * 56}")

    has_gt = "ground_truth" in results[0]
    correct = sum(1 for r in results if r.get("correct", False))

    for r in results:
        flow_id = r.get("flow_id", r.get("group_size", "—"))
        pred = r["prediction"]
        gt = f"  (GT: {r['ground_truth']})" if has_gt else ""
        mark = "✓" if r.get("correct", True) else "✗"
        print(
            f"  [{mark}] flow {flow_id:<4}  {pred:<8}{gt}"
            f"  ports={r['attacking_ports']}/{r['total_ports']}"
            f"  ratio={r['ratio']:.3f}"
        )

    print(f"{'─' * 56}")
    attack_count = sum(1 for r in results if r["prediction"] == "Attack")
    print(f"  Flows detected as Attack : {attack_count}/{total}")
    print(f"  Flows detected as Normal : {total - attack_count}/{total}")
    if has_gt:
        print(f"  Correct classifications  : {correct}/{total}  ({correct/total:.1%})")
    print(f"{'=' * 56}\n")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Threat Detection: classify flows as normal or attack using Φ threshold."
    )
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--data-dir",
        help="Directory of N_*.json stat files (one file = one flow).",
    )
    source.add_argument(
        "--csv",
        help="Path to a labeled CSV (e.g. data/test.csv) for offline evaluation.",
    )
    p.add_argument(
        "--phi",
        type=float,
        default=DEFAULT_PHI,
        help=f"Port threshold Φ (default: {DEFAULT_PHI}). "
             "Flow is Attack if (flagged_ports / total_ports) >= Φ.",
    )
    p.add_argument(
        "--model",
        default="data/model.pkl",
        help="Path to trained Random Forest model (default: data/model.pkl).",
    )
    p.add_argument(
        "--ground-truth",
        choices=("normal", "attack"),
        default=None,
        help="Optional ground-truth label for JSON-dir mode (for accuracy reporting).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    clf = load_model(Path(args.model))
    print(f"[ThreatDetector] Loaded model: {args.model}  Φ={args.phi}")

    if args.data_dir:
        results = detect_from_json_dir(
            clf,
            Path(args.data_dir),
            phi=args.phi,
            ground_truth_label=args.ground_truth,
        )
        source_label = args.data_dir
    else:
        results = detect_from_csv(clf, Path(args.csv), phi=args.phi)
        source_label = args.csv

    print_results(results, source_label)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
