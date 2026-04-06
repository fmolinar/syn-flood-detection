#!/usr/bin/env python3
"""Build the labeled ML dataset from collected differential port statistics.

Reads per-port delta records from data/raw/normal/ and data/raw/attack/,
balances the two classes, shuffles, and writes:

  data/dataset.csv  — full balanced dataset (features + metadata + label)
  data/train.csv    — 80% stratified split (features + label)
  data/test.csv     — 20% stratified split (features + label)

This implements Section III-E (Dataset Creation) of the Flood Control paper.
The paper uses N=A=50 to ensure equal class representation.

Usage:
    python3 simulation/build_dataset.py
    python3 simulation/build_dataset.py --normal-dir data/raw/normal \\
        --attack-dir data/raw/attack --output-dir data
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import pandas as pd
    from sklearn.model_selection import train_test_split
except ImportError as exc:
    raise SystemExit(
        "pandas and scikit-learn are required:\n  pip install pandas scikit-learn"
    ) from exc

# The 9 differential features from Table I — these are the ML inputs.
FEATURE_COLS: list[str] = [
    "delta_rx_packets",
    "delta_rx_bytes",
    "delta_tx_packets",
    "delta_tx_bytes",
    "delta_duration_sec",
    "delta_rx_dropped",
    "delta_tx_dropped",
    "delta_rx_errors",
    "delta_tx_errors",
]

# Metadata kept in dataset.csv for reference but excluded from train/test splits.
METADATA_COLS: list[str] = ["switch", "dpid", "port_no"]


# ------------------------------------------------------------------
# Core logic
# ------------------------------------------------------------------

def load_records(json_dir: Path) -> list[dict]:
    """Flatten all per-port records from a directory of N_*.json files."""
    files = sorted(json_dir.glob("N_*.json"))
    if not files:
        print(f"[Dataset] Warning: no N_*.json files found in {json_dir}", file=sys.stderr)
        return []

    records: list[dict] = []
    for f in files:
        try:
            records.extend(json.loads(f.read_text()))
        except Exception as exc:
            print(f"[Dataset] Warning: skipping {f.name}: {exc}", file=sys.stderr)

    print(f"[Dataset] Loaded {len(records):,} records from {len(files)} files in {json_dir}")
    return records


def build_dataset(
    normal_dir: Path,
    attack_dir: Path,
    output_dir: Path,
    test_size: float = 0.2,
    random_state: int = 42,
) -> None:
    normal_records = load_records(normal_dir)
    attack_records = load_records(attack_dir)

    if not normal_records:
        raise SystemExit(
            f"No normal records found in {normal_dir}.\n"
            "Run: sudo python3 simulation/fig3_topology.py --controller remote --collect-normal 50"
        )
    if not attack_records:
        raise SystemExit(
            f"No attack records found in {attack_dir}.\n"
            "Run: sudo python3 simulation/fig3_topology.py --controller remote --collect-attack 50"
        )

    normal_df = pd.DataFrame(normal_records)
    attack_df = pd.DataFrame(attack_records)

    # Balance classes — paper ensures A = N to avoid class imbalance.
    min_count = min(len(normal_df), len(attack_df))
    if len(normal_df) != len(attack_df):
        print(
            f"[Dataset] Class imbalance detected ({len(normal_df)} normal vs "
            f"{len(attack_df)} attack). Down-sampling majority to {min_count}."
        )
    normal_df = normal_df.sample(min_count, random_state=random_state)
    attack_df = attack_df.sample(min_count, random_state=random_state)

    df = pd.concat([normal_df, attack_df], ignore_index=True)

    # Encode label: normal → 0, attack → 1
    df["label"] = df["label"].map({"normal": 0, "attack": 1})

    # Shuffle
    df = df.sample(frac=1, random_state=random_state).reset_index(drop=True)

    # ------------------------------------------------------------------
    # Write full dataset (features + metadata + label)
    # ------------------------------------------------------------------
    output_dir.mkdir(parents=True, exist_ok=True)

    available_meta = [c for c in METADATA_COLS if c in df.columns]
    full_cols = FEATURE_COLS + available_meta + ["label"]
    dataset_path = output_dir / "dataset.csv"
    df[full_cols].to_csv(dataset_path, index=False)
    print(f"[Dataset] Full dataset   → {dataset_path}  ({len(df):,} rows)")

    # ------------------------------------------------------------------
    # Stratified 80/20 train/test split (features + label only)
    # ------------------------------------------------------------------
    X = df[FEATURE_COLS]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=random_state
    )

    train_df = X_train.copy()
    train_df["label"] = y_train.values
    test_df = X_test.copy()
    test_df["label"] = y_test.values

    train_path = output_dir / "train.csv"
    test_path = output_dir / "test.csv"
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    label_map = {0: "normal", 1: "attack"}
    full_dist = df["label"].value_counts().rename(label_map).to_dict()
    train_dist = train_df["label"].value_counts().rename(label_map).to_dict()
    test_dist = test_df["label"].value_counts().rename(label_map).to_dict()

    print(f"[Dataset] Train set      → {train_path}  ({len(train_df):,} rows)  {train_dist}")
    print(f"[Dataset] Test set       → {test_path}  ({len(test_df):,} rows)  {test_dist}")
    print()
    print(f"  Total rows : {len(df):,}")
    print(f"  Features   : {FEATURE_COLS}")
    print(f"  Distribution: {full_dist}")
    print(f"  Train/test : {int((1 - test_size) * 100)}/{int(test_size * 100)} split (stratified)")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build labeled ML dataset from collected port statistics."
    )
    p.add_argument(
        "--normal-dir",
        default="data/raw/normal",
        help="Directory containing normal N_*.json files (default: data/raw/normal).",
    )
    p.add_argument(
        "--attack-dir",
        default="data/raw/attack",
        help="Directory containing attack N_*.json files (default: data/raw/attack).",
    )
    p.add_argument(
        "--output-dir",
        default="data",
        help="Output directory for dataset.csv, train.csv, test.csv (default: data).",
    )
    p.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of data reserved for the test split (default: 0.2 = 20%%).",
    )
    p.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    build_dataset(
        normal_dir=Path(args.normal_dir),
        attack_dir=Path(args.attack_dir),
        output_dir=Path(args.output_dir),
        test_size=args.test_size,
        random_state=args.random_state,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
