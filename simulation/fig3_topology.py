#!/usr/bin/env python3
"""Run the Figure 3 SDN topology in Mininet."""

from __future__ import annotations

import argparse
import sys

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

        if not args.no_cli:
            info("\n*** Entering Mininet CLI (type 'exit' to stop)\n")
            CLI(net)
        return 0
    finally:
        info("\n*** Stopping network\n")
        net.stop()


if __name__ == "__main__":
    raise SystemExit(main())

