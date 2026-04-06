#!/usr/bin/env python3
"""Threat Localization module — Section III-H of the Flood Control paper.

Identifies which switch in the SDN is most frequently flagging flows as
under attack.  That switch is the one closest to the malicious hosts.

Algorithm (Equations 6–7 of the paper):

    For each flow u_i (i = 0..U-1) across all switches s:
        ζ_s = Attack  if  Σ_p ω_p  >  Θ              (Eq. 6)
              Normal   otherwise
        (where ω_p = per-port classifier prediction for this flow)

    ψ = argmax_s  Σ_i ζ_s(u_i)                        (Eq. 7)
        (switch flagged most often across all U flows)

    The attacker hosts are directly connected to switch ψ.

Paper parameters: U=100 real-time flows, Θ=3 (switch threshold).
Figure 9 of the paper shows Switch 2 flagged most often (72/100 flows)
confirming h1 and h2 are directly connected to s2.

Usage:
    # Offline — evaluate against collected JSON stat files
    python3 simulation/threat_localizer.py \\
        --attack-dir data/raw/attack --theta 3

    # Specify U real-time flows to observe (default: all files found)
    python3 simulation/threat_localizer.py \\
        --attack-dir data/raw/attack --theta 3 --u-flows 100

    # Vary Θ to reproduce Figure 8
    for theta in 0 1 2 3 4; do
        python3 simulation/threat_localizer.py --attack-dir data/raw/attack --theta $theta
    done
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path

try:
    import pandas as pd
except ImportError as exc:
    raise SystemExit("pandas is required: pip install pandas") from exc

from build_dataset import FEATURE_COLS
from topology_spec import HOST_TO_SWITCH_LINKS, SWITCHES

DEFAULT_THETA = 3   # switch threshold (paper's optimal value)
DEFAULT_U = 100     # number of real-time flows (paper uses U=100)


# ------------------------------------------------------------------
# Switch → connected hosts lookup (built from topology_spec)
# ------------------------------------------------------------------

def build_switch_host_map() -> dict[str, list[str]]:
    """Return {switch_name: [host_names]} from the topology spec."""
    m: dict[str, list[str]] = defaultdict(list)
    for host, switch in HOST_TO_SWITCH_LINKS:
        m[switch].append(host)
    return dict(m)

SWITCH_HOST_MAP = build_switch_host_map()


# ------------------------------------------------------------------
# Core localization logic
# ------------------------------------------------------------------

def load_model(model_path: Path):
    if not model_path.exists():
        raise SystemExit(
            f"Model not found: {model_path}\n"
            "Run: python3 simulation/train_classifier.py"
        )
    with open(model_path, "rb") as f:
        return pickle.load(f)


def flag_switches_for_flow(clf, records: list[dict], theta: int) -> set[str]:
    """Return the set of switches that flag this flow as under attack.

    For each switch, count how many of its ports classify the flow as
    attack (ω_p=1).  If that count exceeds Θ, the switch is flagged (ζ_s=1).
    """
    df = pd.DataFrame(records)
    for col in FEATURE_COLS:
        if col not in df.columns:
            df[col] = 0

    preds = clf.predict(df[FEATURE_COLS])   # 0=normal, 1=attack
    df["_pred"] = preds

    flagged: set[str] = set()
    for switch, group in df.groupby("switch"):
        attacking_ports = int(group["_pred"].sum())
        if attacking_ports > theta:
            flagged.add(switch)
    return flagged


def localize(
    clf,
    data_dir: Path,
    theta: int,
    u_flows: int,
) -> dict:
    """Run threat localization across U flows and find switch ψ.

    Returns a result dict containing:
        - flag_counts: {switch: times_flagged}
        - psi: the most-flagged switch name
        - connected_hosts: hosts directly attached to ψ
        - u_observed: actual number of flows processed
    """
    files = sorted(data_dir.glob("N_*.json"))
    if not files:
        raise SystemExit(f"No N_*.json files found in {data_dir}")

    # Use at most u_flows files (cycle if fewer files than u_flows)
    flow_files = [files[i % len(files)] for i in range(u_flows)]

    flag_counts: dict[str, int] = {s: 0 for s in SWITCHES}

    for f in flow_files:
        records = json.loads(f.read_text())
        flagged = flag_switches_for_flow(clf, records, theta)
        for switch in flagged:
            flag_counts[switch] = flag_counts.get(switch, 0) + 1

    # ψ = argmax Σ ζ_s  (Eq. 7)
    psi = max(flag_counts, key=lambda s: flag_counts[s])

    return {
        "flag_counts": flag_counts,
        "psi": psi,
        "connected_hosts": SWITCH_HOST_MAP.get(psi, []),
        "u_observed": len(flow_files),
        "theta": theta,
    }


def print_results(result: dict, data_dir: str) -> None:
    flag_counts = result["flag_counts"]
    psi = result["psi"]
    u = result["u_observed"]
    theta = result["theta"]

    # Sort switches by flag count descending, skip zero-count ones
    ranked = sorted(
        ((s, c) for s, c in flag_counts.items() if c > 0),
        key=lambda x: x[1],
        reverse=True,
    )

    print(f"\n{'=' * 56}")
    print(f"  Threat Localization Results — {data_dir}")
    print(f"  Θ (switch threshold) = {theta}   U (flows) = {u}")
    print(f"{'=' * 56}")
    print(f"  {'Switch':<12} {'Times Flagged':>14}  {'Bar'}")
    print(f"  {'─' * 50}")
    for switch, count in ranked:
        bar = "█" * int((count / u) * 30)
        marker = " ← ψ (most flagged)" if switch == psi else ""
        print(f"  {switch:<12} {count:>8}/{u:<6}  {bar}{marker}")

    print(f"{'─' * 56}")
    print(f"  ψ (most flagged switch) : {psi}")
    hosts = result["connected_hosts"]
    if hosts:
        print(f"  Hosts connected to ψ    : {', '.join(sorted(hosts))}")
        print(f"  → Likely attackers      : {', '.join(sorted(hosts))}")
    else:
        print(f"  No hosts directly attached to {psi} in topology spec.")
    print(f"{'=' * 56}\n")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Threat Localization: find the switch closest to the attackers."
    )
    p.add_argument(
        "--attack-dir",
        default="data/raw/attack",
        help="Directory of attack N_*.json stat files (default: data/raw/attack).",
    )
    p.add_argument(
        "--theta",
        type=int,
        default=DEFAULT_THETA,
        help=f"Switch threshold Θ (default: {DEFAULT_THETA}). "
             "Switch is flagged if its attacking port count > Θ.",
    )
    p.add_argument(
        "--u-flows",
        type=int,
        default=DEFAULT_U,
        help=f"Number of real-time flows to observe (default: {DEFAULT_U}).",
    )
    p.add_argument(
        "--model",
        default="data/model.pkl",
        help="Path to trained Random Forest model (default: data/model.pkl).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    clf = load_model(Path(args.model))
    print(f"[ThreatLocalizer] Loaded model: {args.model}  Θ={args.theta}  U={args.u_flows}")

    result = localize(
        clf,
        data_dir=Path(args.attack_dir),
        theta=args.theta,
        u_flows=args.u_flows,
    )

    print_results(result, args.attack_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
