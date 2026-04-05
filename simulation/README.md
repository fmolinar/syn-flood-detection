# Figure 3 Topology Simulation

This folder contains the first implementation milestone for the paper:

> Flood Control: TCP-SYN Flood Detection for Software-Defined Networks using OpenFlow Port Statistics

Implemented artifact:
- `fig3_topology.py`: Mininet topology runner for Figure 3.
- `topology_spec.py`: Node and link definitions used by the runner.

## Topology At A Glance

- Hosts: `h1` to `h10` (10 total)
- Switches: `s0` to `s11` (12 total)
- Attackers from paper: `h1`, `h2`
- Victim from paper: `h8`

Host attachments:
- `h1 -> s2`
- `h2 -> s2`
- `h3 -> s1`
- `h4 -> s0`
- `h5 -> s0`
- `h6 -> s11`
- `h7 -> s11`
- `h8 -> s10`
- `h9 -> s9`
- `h10 -> s9`

## Run

See step-by-step docs in:
- `docs/steps/01-environment-setup/README.md`
- `docs/steps/02-start-controller/README.md`
- `docs/steps/03-run-figure3-topology/README.md`
- `docs/steps/04-verify/README.md`
