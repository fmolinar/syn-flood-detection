"""Topology specification for Figure 3 in the Flood Control paper.

Paper:
Flood Control: TCP-SYN Flood Detection for Software-Defined Networks
using OpenFlow Port Statistics
"""

from __future__ import annotations

HOSTS = [f"h{i}" for i in range(1, 11)]
SWITCHES = [f"s{i}" for i in range(0, 12)]

# Attack scenario in the paper.
ATTACKER_HOSTS = ("h1", "h2")
VICTIM_HOST = "h8"

# Host-to-switch attachment based on Figure 3.
HOST_TO_SWITCH_LINKS = [
    ("h1", "s2"),
    ("h2", "s2"),
    ("h3", "s1"),
    ("h4", "s0"),
    ("h5", "s0"),
    ("h6", "s11"),
    ("h7", "s11"),
    ("h8", "s10"),
    ("h9", "s9"),
    ("h10", "s9"),
]

# Inter-switch links in Figure 3.
SWITCH_TO_SWITCH_LINKS = [
    # Top chain: s10-s9-s7-s5-s3-s0
    ("s10", "s9"),
    ("s9", "s7"),
    ("s7", "s5"),
    ("s5", "s3"),
    ("s3", "s0"),
    # Bottom chain: s11-s8-s6-s4-s2-s1
    ("s11", "s8"),
    ("s8", "s6"),
    ("s6", "s4"),
    ("s4", "s2"),
    ("s2", "s1"),
    # Vertical links between rows
    ("s10", "s11"),
    ("s9", "s8"),
    ("s7", "s6"),
    ("s5", "s4"),
    ("s3", "s2"),
    ("s0", "s1"),
    # Diagonal links
    ("s11", "s7"),
    ("s8", "s5"),
    ("s6", "s3"),
    ("s4", "s0"),
]


def all_links() -> list[tuple[str, str]]:
    return [*HOST_TO_SWITCH_LINKS, *SWITCH_TO_SWITCH_LINKS]

