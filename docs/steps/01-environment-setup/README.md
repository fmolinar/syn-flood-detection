# Step 1: Environment Setup

This simulation is intended for Linux with Mininet + Open vSwitch.
If you are on macOS/Windows, use an Ubuntu VM.

## 1. Install system packages (Ubuntu)

```bash
sudo apt update
sudo apt install -y mininet openvswitch-switch python3 python3-pip git
```

## 2. Install Python dependencies

```bash
pip install requests scapy pandas scikit-learn
```

- `requests` — stats collector polls Ryu REST API
- `scapy` — SYN flood attack script
- `pandas` — dataset builder and ML pipeline
- `scikit-learn` — train/test split and Random Forest classifier

## 2. Clone the repository

```bash
git clone <your-repo-url>
cd syn-flood-detection
```

## 3. Verify Mininet works

```bash
sudo mn --test pingall
```

Expected: a successful ping test in Mininet's default topology.

Next step:
- `../02-start-controller/README.md`
