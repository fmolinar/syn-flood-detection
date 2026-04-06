#!/usr/bin/env python3
"""Run the Figure 3 SDN topology in Mininet."""

from __future__ import annotations

import argparse
import sys
import threading

from topology_spec import (
    ATTACKER_HOSTS,
    HOSTS,
    HOST_TO_SWITCH_LINKS,
    SWITCHES,
    SWITCH_TO_SWITCH_LINKS,
    VICTIM_HOST,
)

try:
    from mininet.cli import CLI
    from mininet.link import TCLink
    from mininet.log import info, setLogLevel
    from mininet.net import Mininet
    from mininet.node import OVSController, OVSKernelSwitch, RemoteController
    from mininet.topo import Topo
    from mininet.util import dumpNodeConnections
except ImportError as exc:
    raise SystemExit(
        "Mininet is required. Please install Mininet on Linux and rerun.\n"
        "See docs/steps/01-environment-setup/README.md for setup."
    ) from exc


class Figure3Topology(Topo):
    """Figure 3 topology from the paper."""

    def build(self) -> None:
        for switch in SWITCHES:
            switch_num = int(switch[1:])
            # Avoid a zero DPID for s0 while keeping switch names aligned with the paper.
            dpid = f"{switch_num + 1:016x}"
            self.addSwitch(switch, dpid=dpid, protocols="OpenFlow13")

        for host in HOSTS:
            host_num = int(host[1:])
            self.addHost(host, ip=f"10.0.0.{host_num}/24")

        for host, switch in HOST_TO_SWITCH_LINKS:
            self.addLink(host, switch)

        for source, target in SWITCH_TO_SWITCH_LINKS:
            self.addLink(source, target)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Figure 3 topology from the Flood Control paper."
    )
    parser.add_argument(
        "--controller",
        choices=("ovs", "remote", "none"),
        default="ovs",
        help="Controller mode: local OVS, remote OpenFlow controller, or none.",
    )
    parser.add_argument(
        "--controller-ip",
        default="127.0.0.1",
        help="IP for --controller remote.",
    )
    parser.add_argument(
        "--controller-port",
        type=int,
        default=6653,
        help="Port for --controller remote.",
    )
    parser.add_argument(
        "--pingall",
        action="store_true",
        help="Run Mininet pingAll after startup.",
    )
    parser.add_argument(
        "--no-cli",
        action="store_true",
        help="Exit after startup checks instead of opening Mininet CLI.",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=("debug", "info", "warning", "error", "critical"),
        help="Mininet log level.",
    )
    # --- Milestone 2+3: normal traffic collection ---
    parser.add_argument(
        "--collect-normal",
        metavar="N",
        type=int,
        default=0,
        help=(
            "Generate N normal IPerf flows and collect differential port stats. "
            "Requires --controller remote (Ryu with REST API). "
            "Skips the interactive CLI. Paper uses N=50."
        ),
    )
    parser.add_argument(
        "--ryu-api-port",
        type=int,
        default=8080,
        help="Port for the Ryu REST API (default: 8080).",
    )
    parser.add_argument(
        "--data-dir",
        default="data/raw/normal",
        help="Directory for collected JSON stat files (default: data/raw/normal).",
    )
    # --- Milestone 4: attack traffic collection ---
    parser.add_argument(
        "--collect-attack",
        metavar="N",
        type=int,
        default=0,
        help=(
            "Launch TCP-SYN flood from attacker hosts and collect N rounds of "
            "differential port stats. Requires --controller remote. Paper uses N=50."
        ),
    )
    parser.add_argument(
        "--attack-data-dir",
        default="data/raw/attack",
        help="Directory for attack JSON stat files (default: data/raw/attack).",
    )
    return parser.parse_args(argv)


def add_controller(net: Mininet, args: argparse.Namespace) -> None:
    if args.controller == "ovs":
        net.addController("c0", controller=OVSController)
        info("*** Using local OVS controller\n")
        return

    if args.controller == "remote":
        net.addController(
            "c0",
            controller=RemoteController,
            ip=args.controller_ip,
            port=args.controller_port,
        )
        info(
            f"*** Using remote controller at "
            f"{args.controller_ip}:{args.controller_port}\n"
        )
        return

    info("*** Starting without a controller\n")


def print_summary(net: Mininet) -> None:
    info("\n*** Topology summary\n")
    info(f"Hosts: {len(net.hosts)} | Switches: {len(net.switches)}\n")
    info(f"Paper attack hosts: {', '.join(ATTACKER_HOSTS)} | Victim: {VICTIM_HOST}\n")
    dumpNodeConnections(net.hosts)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    setLogLevel(args.log_level)

    net = Mininet(
        topo=Figure3Topology(),
        switch=OVSKernelSwitch,
        link=TCLink,
        controller=None,
        autoSetMacs=True,
    )
    add_controller(net, args)

    try:
        net.start()
        print_summary(net)

        if args.pingall:
            info("\n*** Running pingAll\n")
            net.pingAll()

        if args.collect_normal > 0:
            _run_collection(net, args)
        elif args.collect_attack > 0:
            _run_attack_collection(net, args)
        elif not args.no_cli:
            info("\n*** Entering Mininet CLI (type 'exit' to stop)\n")
            CLI(net)
        return 0
    finally:
        info("\n*** Stopping network\n")
        net.stop()


def _run_collection(net: "Mininet", args: argparse.Namespace) -> None:
    """Orchestrate Milestone 2+3: simultaneous traffic generation and stats collection."""
    from stats_collector import StatsCollector
    from traffic_gen import run_normal_traffic

    n = args.collect_normal
    info(f"\n*** Collecting {n} normal flows + stats (this takes ~{n * 5}s)\n")

    if args.controller != "remote":
        info(
            "*** Warning: --collect-normal works best with --controller remote "
            "(Ryu REST API on port 8080). Proceeding anyway.\n"
        )

    collector = StatsCollector(
        output_dir=args.data_dir,
        label="normal",
        controller_ip=args.controller_ip,
        ryu_api_port=args.ryu_api_port,
    )

    stop_event = threading.Event()

    traffic_thread = threading.Thread(
        target=run_normal_traffic,
        kwargs={"net": net, "n_flows": n, "stop_event": stop_event},
        daemon=True,
        name="traffic-gen",
    )

    traffic_thread.start()
    # Stats collection runs on the main thread so KeyboardInterrupt is caught cleanly.
    try:
        collector.run(n_samples=n, stop_event=stop_event)
    except KeyboardInterrupt:
        info("\n*** Interrupted — stopping collection\n")
        stop_event.set()

    traffic_thread.join(timeout=30)
    info(f"*** Collection complete. Data written to {args.data_dir}\n")


def _run_attack_collection(net: "Mininet", args: argparse.Namespace) -> None:
    """Orchestrate Milestone 4: SYN flood from attackers + simultaneous stats collection."""
    from pathlib import Path

    from stats_collector import StatsCollector, POLL_INTERVAL

    n = args.collect_attack
    # Attack runs for the full collection window plus a small buffer so it covers
    # the priming poll and every subsequent sample interval.
    attack_duration = (n + 2) * POLL_INTERVAL

    script_path = Path(__file__).parent / "syn_flood.py"
    victim = net.get(VICTIM_HOST)
    victim_ip = victim.IP()

    info(
        f"\n*** Launching SYN flood: {', '.join(ATTACKER_HOSTS)} → {VICTIM_HOST}"
        f" ({victim_ip})  duration={attack_duration}s\n"
    )
    if args.controller != "remote":
        info(
            "*** Warning: --collect-attack works best with --controller remote "
            "(Ryu REST API on port 8080). Proceeding anyway.\n"
        )

    # Start the flood on each attacker host (non-blocking).
    flood_procs = []
    for attacker_name in ATTACKER_HOSTS:
        attacker = net.get(attacker_name)
        proc = attacker.popen(
            [
                "python3",
                str(script_path),
                "--target", victim_ip,
                "--duration", str(attack_duration),
            ]
        )
        flood_procs.append((attacker_name, proc))
        info(f"*** SYN flood started from {attacker_name}\n")

    collector = StatsCollector(
        output_dir=args.attack_data_dir,
        label="attack",
        controller_ip=args.controller_ip,
        ryu_api_port=args.ryu_api_port,
    )

    stop_event = threading.Event()
    try:
        collector.run(n_samples=n, stop_event=stop_event)
    except KeyboardInterrupt:
        info("\n*** Interrupted — stopping attack collection\n")
        stop_event.set()
    finally:
        for attacker_name, proc in flood_procs:
            proc.terminate()
            proc.wait()
            info(f"*** SYN flood stopped on {attacker_name}\n")

    info(f"*** Attack collection complete. Data written to {args.attack_data_dir}\n")


if __name__ == "__main__":
    raise SystemExit(main())

