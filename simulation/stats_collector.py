"""Collect differential OpenFlow port statistics from the Ryu REST API.

Every poll interval (5 s), fetch raw cumulative port counters from all
switches, compute the delta vs. the previous poll, and write one JSON file
per interval.  This reproduces the "differential port statistics" method
described in the Flood Control paper (Table I).

Usage (standalone):
    python3 stats_collector.py --n-samples 50 --label normal

More commonly it is driven by fig3_topology.py via --collect-normal.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError as exc:
    raise SystemExit("requests is required: pip install requests") from exc

from topology_spec import SWITCHES

# DPID assignment matches fig3_topology.py: s0 -> dpid 1, s1 -> dpid 2, …
SWITCH_DPIDS: dict[str, int] = {s: int(s[1:]) + 1 for s in SWITCHES}

POLL_INTERVAL = 5  # seconds between polls (matches paper)

# Table I: the 8 differential port statistics tracked per port per switch
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


class StatsCollector:
    """Poll Ryu REST API and save differential port statistics as JSON files.

    Each output file N_<i>.json contains a list of per-port delta records
    from a single polling round across all switches.
    """

    def __init__(
        self,
        output_dir: str | Path = "data/raw/normal",
        label: str = "normal",
        controller_ip: str = "127.0.0.1",
        ryu_api_port: int = 8080,
        poll_interval: int = POLL_INTERVAL,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.label = label
        self.poll_interval = poll_interval
        self._base_url = f"http://{controller_ip}:{ryu_api_port}"
        self._prev: dict[tuple[int, int], dict[str, int]] = {}
        self._sample_idx = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_port_stats(self, dpid: int) -> list[dict[str, Any]]:
        url = f"{self._base_url}/stats/port/{dpid}"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        return resp.json().get(str(dpid), [])

    def _extract_counters(self, port: dict[str, Any]) -> dict[str, int]:
        return {k: int(port.get(k, 0)) for k in _STAT_KEYS}

    def _prime(self) -> None:
        """First poll — establish baseline counters (no delta recorded yet)."""
        primed = 0
        for switch, dpid in SWITCH_DPIDS.items():
            try:
                for port in self._fetch_port_stats(dpid):
                    key = (dpid, int(port["port_no"]))
                    self._prev[key] = self._extract_counters(port)
                    primed += 1
            except Exception as exc:
                print(
                    f"[StatsCollector] Warning: prime failed for {switch} (dpid={dpid}): {exc}",
                    file=sys.stderr,
                )
        print(f"[StatsCollector] Primed {primed} (switch, port) baselines.")

    def _collect_once(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for switch, dpid in SWITCH_DPIDS.items():
            try:
                ports = self._fetch_port_stats(dpid)
            except Exception as exc:
                print(
                    f"[StatsCollector] Warning: fetch failed for {switch}: {exc}",
                    file=sys.stderr,
                )
                continue
            for port in ports:
                port_no = int(port["port_no"])
                key = (dpid, port_no)
                curr = self._extract_counters(port)
                if key not in self._prev:
                    self._prev[key] = curr
                    continue
                prev = self._prev[key]
                delta: dict[str, Any] = {f"delta_{k}": curr[k] - prev[k] for k in _STAT_KEYS}
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
                    " — no records (is Ryu running with REST API enabled?)"
                )
            if i < n_samples - 1:
                time.sleep(self.poll_interval)

        print(f"[StatsCollector] Done. {self._sample_idx} files saved to {self.output_dir}")


# ------------------------------------------------------------------
# Standalone entry point
# ------------------------------------------------------------------

def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Collect differential port stats from Ryu.")
    p.add_argument("--n-samples", type=int, default=50, help="Number of polling rounds.")
    p.add_argument("--label", default="normal", choices=("normal", "attack"))
    p.add_argument("--output-dir", default="data/raw/normal")
    p.add_argument("--controller-ip", default="127.0.0.1")
    p.add_argument("--ryu-api-port", type=int, default=8080)
    p.add_argument("--poll-interval", type=int, default=POLL_INTERVAL)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    collector = StatsCollector(
        output_dir=args.output_dir,
        label=args.label,
        controller_ip=args.controller_ip,
        ryu_api_port=args.ryu_api_port,
        poll_interval=args.poll_interval,
    )
    collector.run(args.n_samples)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
