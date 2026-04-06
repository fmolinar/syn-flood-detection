# Figure 3 Topology Simulation

This folder contains the first implementation milestone for the paper:

> Flood Control: TCP-SYN Flood Detection for Software-Defined Networks using OpenFlow Port Statistics

Implemented artifacts:
- `fig3_topology.py`: Mininet topology runner for Figure 3. Also orchestrates traffic generation and stats collection via `--collect-normal N`.
- `topology_spec.py`: Node and link definitions used by the runner.
- `traffic_gen.py`: Generates N normal IPerf flows (10 Mbps, 5 s, random src/dst pairs). Milestone 2.
- `stats_collector.py`: Polls Ryu REST API every 5 s and writes differential port statistics (Table I) as JSON files. Milestone 3.
- `build_dataset.py`: Merges normal and attack JSON files into a balanced, labeled CSV dataset with stratified 80/20 train/test split. Milestone 5.
- `train_classifier.py`: Trains Random Forest, MLP, and SVM; reports Table III metrics; saves `data/model.pkl` for Milestones 7 & 8. Milestone 6.

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
