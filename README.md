# SYN Flood Detection (Flood Control Paper Reproduction)

This repository reproduces and extends:

> Flood Control: TCP-SYN Flood Detection for Software-Defined Networks using OpenFlow Port Statistics

## Milestones Implemented

### Milestone 1 — Figure 3 Topology
- 10 hosts (`h1` to `h10`), 12 switches (`s0` to `s11`)
- Paper-consistent attacker/victim mapping (`h1`, `h2` attackers; `h8` victim)
- Code: `simulation/fig3_topology.py`, `simulation/topology_spec.py`

### Milestones 2 + 3 — Normal Traffic + Differential Port Stats Collection
- IPerf flow generator: random src/dst pairs, 10 Mbps, 5 s, N=50 flows
- Ryu REST API poller: differential port stats (Table I) every 5 s → `data/raw/normal/N_*.json`
- Code: `simulation/traffic_gen.py`, `simulation/stats_collector.py`
- Triggered via: `sudo python3 simulation/fig3_topology.py --collect-normal 50 --controller remote`

### Milestone 7 — Threat Detection
- Applies port threshold Φ=0.3 (Equations 3–5) to classify each flow as normal or attack
- Works on JSON stat directories (live) or labeled CSV (offline evaluation)
- Code: `simulation/threat_detector.py`
- Run via: `python3 simulation/threat_detector.py --csv data/test.csv --phi 0.3`

### Milestone 6 — ML Classifier Training
- Trains Random Forest (primary), MLP, and SVM on `data/train.csv`
- Reports Accuracy, Precision, Recall, F-Measure (Table III of the paper)
- Saves trained Random Forest to `data/model.pkl` for Milestones 7 & 8
- Code: `simulation/train_classifier.py`
- Run via: `python3 simulation/train_classifier.py`

### Milestone 5 — Dataset Builder
- Merges `data/raw/normal/` and `data/raw/attack/` JSON files into a balanced, labeled CSV
- Stratified 80/20 train/test split → `data/dataset.csv`, `data/train.csv`, `data/test.csv`
- Code: `simulation/build_dataset.py`
- Run via: `python3 simulation/build_dataset.py`

### Milestone 4 — TCP-SYN Attack + Attack Dataset Collection
- Scapy SYN flood launched from `h1`, `h2` → victim `h8` for the full collection window
- Differential port stats collected simultaneously → `data/raw/attack/N_*.json` labeled `"attack"`
- Code: `simulation/syn_flood.py` (attack script invoked per-host via Mininet popen)
- Triggered via: `sudo python3 simulation/fig3_topology.py --collect-attack 50 --controller remote`

## Step-by-Step READMEs

Follow these in order:

1. `docs/steps/01-environment-setup/README.md`
2. `docs/steps/02-start-controller/README.md`
3. `docs/steps/03-run-figure3-topology/README.md`
4. `docs/steps/04-verify/README.md`
5. `docs/steps/05-collect-normal-stats/README.md`
6. `docs/steps/06-collect-attack-stats/README.md`
7. `docs/steps/07-build-dataset/README.md`
8. `docs/steps/08-train-classifier/README.md`
9. `docs/steps/09-threat-detection/README.md`

Additional topology details:
- `simulation/README.md`
