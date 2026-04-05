# SYN Flood Detection (Flood Control Paper Reproduction)

This repository reproduces and extends:

> Flood Control: TCP-SYN Flood Detection for Software-Defined Networks using OpenFlow Port Statistics

## Milestone 1 Implemented

Figure 3 SDN topology simulation is now implemented with:
- 10 hosts (`h1` to `h10`)
- 12 switches (`s0` to `s11`)
- Paper-consistent attacker/victim mapping (`h1`, `h2` attackers; `h8` victim)

Code:
- `simulation/fig3_topology.py`
- `simulation/topology_spec.py`

## Step-by-Step READMEs

Follow these in order:

1. `docs/steps/01-environment-setup/README.md`
2. `docs/steps/02-start-controller/README.md`
3. `docs/steps/03-run-figure3-topology/README.md`
4. `docs/steps/04-verify/README.md`

Additional topology details:
- `simulation/README.md`
