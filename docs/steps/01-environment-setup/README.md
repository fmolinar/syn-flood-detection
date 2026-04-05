# Step 1: Environment Setup

This simulation is intended for Linux with Mininet + Open vSwitch.
If you are on macOS/Windows, use an Ubuntu VM.

## 1. Install system packages (Ubuntu)

```bash
sudo apt update
sudo apt install -y mininet openvswitch-switch python3 python3-pip git
```

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
