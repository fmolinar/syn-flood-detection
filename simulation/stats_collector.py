"""Collect differential OpenFlow port statistics via ovs-ofctl.

Every poll interval (5 s), fetch raw cumulative port counters from all
switches using ``ovs-ofctl dump-ports``, compute the delta vs. the previous
poll, and write one JSON file per interval.  This reproduces the "differential
port statistics" method described in the Flood Control paper (Table I).

Usage (standalone):
    python3 stats_collector.py --n-samples 50 --label normal

More commonly it is driven by fig3_topology.py via --collect-normal.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from topology_spec import SWITCHES

POLL_INTERVAL = 5  # seconds between polls (matches paper)

# Table I: the 9 differential port statistics tracked per port per switch
_STAT_KEYS: tuple[str, ...] = (
    "rx_packets",
    "rx_bytes",
    "tx_packets",
    "tx_bytes",
    "duration_sec",
    "rx_dropped",
    "tx_dropped",
    "rx_errors",
    "tx_errors",
)

# Regex patterns for ovs-ofctl dump-ports output lines
_RX_PAT = re.compile(
    r"port\s+(\S+):\s+rx pkts=(\d+),\s*bytes=(\d+),\s*drop=(\d+),\s*errs=(\d+)"
)
_TX_PAT = re.compile(
    r"tx pkts=(\d+),\s*bytes=(\d+),\s*drop=(\d+),\s*errs=(\d+)"
)
_DUR_PAT = re.compile(r"duration:\s*([\d.]+)\s*sec")


def _parse_dump_ports(output: str) -> list[dict[str, Any]]:
    """Parse ``ovs-ofctl dump-ports`` text output into a list of port dicts.

    Each dict has keys matching _STAT_KEYS plus ``port_no`` (str).
    """
    ports: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in output.splitlines():
        line = line.strip()

        m = _RX_PAT.search(line)
        if m:
            # Flush any incomplete previous entry
            if current is not None:
                ports.append(current)
            port_label = m.group(1)
            # Skip the LOCAL (management) port — it doesn't carry data-plane traffic
            if port_label == "LOCAL":
                current = None
                continue
            current = {
                "port_no": int(port_label),
                "rx_packets": int(m.group(2)),
                "rx_bytes": int(m.group(3)),
                "rx_dropped": int(m.group(4)),
                "rx_errors": int(m.group(5)),
                "tx_packets": 0,
                "tx_bytes": 0,
                "tx_dropped": 0,
                "tx_errors": 0,
                "duration_sec": 0,
            }
            continue

        if current is None:
            continue

        m = _TX_PAT.search(line)
        if m:
            current["tx_packets"] = int(m.group(1))
            current["tx_bytes"] = int(m.group(2))
            current["tx_dropped"] = int(m.group(3))
            current["tx_errors"] = int(m.group(4))
            continue

        m = _DUR_PAT.search(line)
        if m:
            current["duration_sec"] = int(float(m.group(1)))

    if current is not None:
        ports.append(current)

    return ports


class StatsCollector:
    """Poll OVS switches via ovs-ofctl and save differential port stats as JSON.

    Each output file N_<i>.json contains a list of per-port delta records
    from a single polling round across all switches.
    """

    def __init__(
        self,
        output_dir: str | Path = "data/raw/normal",
        label: str = "normal",
        # kept for API compatibility with fig3_topology.py; not used
        controller_ip: str = "127.0.0.1",
        ryu_api_port: int = 8080,
        poll_interval: int = POLL_INTERVAL,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.label = label
        self.poll_interval = poll_interval
        # key: (switch_name, port_no_int) → cumulative counters dict
        self._prev: dict[tuple[str, int], dict[str, int]] = {}
        self._sample_idx = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_port_stats(self, switch: str) -> list[dict[str, Any]]:
        """Run ovs-ofctl dump-ports for one switch and parse the output."""
        result = subprocess.run(
            ["ovs-ofctl", "-O", "OpenFlow13", "dump-ports", switch],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ovs-ofctl failed for {switch}: {result.stderr.strip()}"
            )
        return _parse_dump_ports(result.stdout)

    def _extract_counters(self, port: dict[str, Any]) -> dict[str, int]:
        return {k: int(port.get(k, 0)) for k in _STAT_KEYS}

    def _prime(self) -> None:
        """First poll — establish baseline counters (no delta recorded yet)."""
        primed = 0
        for switch in SWITCHES:
            try:
                for port in self._fetch_port_stats(switch):
                    key = (switch, int(port["port_no"]))
                    self._prev[key] = self._extract_counters(port)
                    primed += 1
            except Exception as exc:
                print(
                    f"[StatsCollector] Warning: prime failed for {switch}: {exc}",
                    file=sys.stderr,
                )
        print(f"[StatsCollector] Primed {primed} (switch, port) baselines.")

    def _collect_once(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for switch in SWITCHES:
            try:
                ports = self._fetch_port_stats(switch)
            except Exception as exc:
                print(
                    f"[StatsCollector] Warning: fetch failed for {switch}: {exc}",
                    file=sys.stderr,
                )
                continue
            for port in ports:
                port_no = int(port["port_no"])
                key = (switch, port_no)
                curr = self._extract_counters(port)
                if key not in self._prev:
                    self._prev[key] = curr
                    continue
                prev = self._prev[key]
                delta: dict[str, Any] = {
                    f"delta_{k}": curr[k] - prev[k] for k in _STAT_KEYS
                }
                # Use a synthetic dpid (switch index + 1) for compatibility
                dpid = int(switch[1:]) + 1
                delta["switch"] = switch
                delta["dpid"] = dpid
                delta["port_no"] = port_no
                delta["label"] = self.label
                records.append(delta)
                self._prev[key] = curr
        return records

    def _save(self, records: list[dict[str, Any]]) -> Path:
        path = self.output_dir / f"N_{self._sample_idx}.json"
        path.write_text(json.dumps(records, indent=2))
        self._sample_idx += 1
        return path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, n_samples: int, stop_event=None) -> None:
        """Collect `n_samples` polling rounds at `poll_interval` second intervals."""
        print(
            f"[StatsCollector] label={self.label!r}  samples={n_samples}"
            f"  interval={self.poll_interval}s  output={self.output_dir}"
        )
        self._prime()
        time.sleep(self.poll_interval)

        for i in range(n_samples):
            if stop_event is not None and stop_event.is_set():
                print("[StatsCollector] Stop requested — exiting early.")
                break
            records = self._collect_once()
            if records:
                path = self._save(records)
                print(
                    f"[StatsCollector] Sample {i + 1}/{n_samples}"
                    f" → {path}  ({len(records)} port records)"
                )
            else:
                print(
                    f"[StatsCollector] Sample {i + 1}/{n_samples}"
                    " — no records (are OVS switches running?)"
                )
            if i < n_samples - 1:
                time.sleep(self.poll_interval)

        print(f"[StatsCollector] Done. {self._sample_idx} files saved to {self.output_dir}")


# ------------------------------------------------------------------
# Standalone entry point
# ------------------------------------------------------------------

def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Collect differential port stats via ovs-ofctl.")
    p.add_argument("--n-samples", type=int, default=50, help="Number of polling rounds.")
    p.add_argument("--label", default="normal", choices=("normal", "attack"))
    p.add_argument("--output-dir", default="data/raw/normal")
    p.add_argument("--controller-ip", default="127.0.0.1", help="Unused; kept for compat.")
    p.add_argument("--ryu-api-port", type=int, default=8080, help="Unused; kept for compat.")
    p.add_argument("--poll-interval", type=int, default=POLL_INTERVAL)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    collector = StatsCollector(
        output_dir=args.output_dir,
        label=args.label,
        poll_interval=args.poll_interval,
    )
    collector.run(args.n_samples)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
