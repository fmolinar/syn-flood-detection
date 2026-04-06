"""Generate normal IPerf traffic flows within a running Mininet network.

The paper simulates N normal flows: random source/destination host pairs,
10 Mbps each, lasting 5 seconds, with a new flow starting every 5 seconds.
Because each flow takes exactly FLOW_DURATION seconds to complete, no
additional sleep is needed between flows — the blocking iperf client call
naturally enforces the 5-second interval.

This module is driven by fig3_topology.py via --collect-normal, but the
run_normal_traffic() function can also be called directly from other scripts.
"""

from __future__ import annotations

import random
import sys
import time

from topology_spec import HOSTS

FLOW_BANDWIDTH = "10M"   # 10 Mbps (matches paper)
FLOW_DURATION = 5        # seconds per flow (matches paper)
FLOW_INTERVAL = 5        # seconds between flow starts (matches paper)
IPERF_BASE_PORT = 5100   # each flow gets a unique port to avoid server conflicts


def run_normal_traffic(net, n_flows: int = 50, stop_event=None) -> None:
    """Run `n_flows` normal IPerf flows through the Mininet network.

    Each flow picks a random (src, dst) host pair, starts an iperf server on
    dst, then runs an iperf client on src for FLOW_DURATION seconds at
    FLOW_BANDWIDTH.  Flows are sequential: the blocking iperf client call
    provides the FLOW_INTERVAL gap between flow starts.

    Args:
        net:        Running Mininet instance.
        n_flows:    Number of flows to generate (paper uses N=50).
        stop_event: Optional threading.Event; if set, exits early.
    """
    hosts = HOSTS[:]
    print(
        f"[TrafficGen] Starting {n_flows} normal flows"
        f" (bw={FLOW_BANDWIDTH}, duration={FLOW_DURATION}s, interval={FLOW_INTERVAL}s)"
    )

    for i in range(n_flows):
        if stop_event is not None and stop_event.is_set():
            print("[TrafficGen] Stop requested — exiting early.")
            break

        src_name, dst_name = random.sample(hosts, 2)
        src = net.get(src_name)
        dst = net.get(dst_name)
        dst_ip = dst.IP()
        port = IPERF_BASE_PORT + i

        print(f"[TrafficGen] Flow {i + 1}/{n_flows}: {src_name} → {dst_name} ({dst_ip}) port={port}")

        # Start iperf server on dst in the background; capture PID for cleanup.
        pid_raw = dst.cmd(f"iperf -s -p {port} > /dev/null 2>&1 & echo $!").strip()
        time.sleep(0.2)  # small grace period for the server to bind

        # Run iperf client on src — blocks for ~FLOW_DURATION seconds.
        src.cmd(
            f"iperf -c {dst_ip} -p {port} -b {FLOW_BANDWIDTH}"
            f" -t {FLOW_DURATION} > /dev/null 2>&1"
        )

        # Tear down server.
        if pid_raw.isdigit():
            dst.cmd(f"kill {pid_raw} 2>/dev/null")

        # No extra sleep: the iperf client already blocked for FLOW_DURATION seconds,
        # matching the paper's "new flow every 5 seconds" cadence.

    print(f"[TrafficGen] Done. {n_flows} flows completed.")
