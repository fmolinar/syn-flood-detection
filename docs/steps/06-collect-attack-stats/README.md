# Step 6: Collect Attack Traffic Statistics (Milestone 4)

This step launches a TCP-SYN flood from the paper's attacker hosts (`h1`, `h2`)
targeting the victim (`h8`), while simultaneously collecting differential port
statistics from all switches.  This produces the attack dataset X_A.

## Prerequisites

- Step 5 (normal stats) must be complete so you have the normal dataset.
- Ryu must be running with the REST API (same command as Step 5):

```bash
ryu-manager ryu.app.simple_switch_13 \
  ryu.app.ofctl_rest \
  --ofp-tcp-listen-port 6653 \
  --wsapi-port 8080
```

- scapy must be installed (see Step 1):

```bash
pip install scapy
```

## Run

```bash
sudo python3 simulation/fig3_topology.py \
  --controller remote \
  --controller-ip 127.0.0.1 \
  --controller-port 6653 \
  --collect-attack 50 \
  --ryu-api-port 8080 \
  --attack-data-dir data/raw/attack
```

This single command:
1. Brings up the Figure 3 topology
2. Launches `syn_flood.py` on `h1` and `h2` targeting `h8` (10.0.0.8) via Scapy
3. Polls all switch ports every 5 s and writes differential stats labeled `"attack"`
4. Terminates the flood and shuts down the topology when done

Expected runtime: ~260 seconds (50 samples × 5 s + small buffer).

## What the SYN flood does

`simulation/syn_flood.py` sends TCP SYN packets from each attacker host to
port 80 on `h8` without completing the three-way handshake.  Each packet uses
a randomised source port.  At ~1 kpps per attacker, this saturates the
victim's half-open connection table — the attack scenario from the paper.

## Output

```
data/raw/attack/
  N_0.json
  N_1.json
  ...
  N_49.json
```

Same schema as the normal dataset but with `"label": "attack"`.

## Verify

```bash
python3 -c "
import json, pathlib
files = sorted(pathlib.Path('data/raw/attack').glob('N_*.json'))
print(len(files), 'files')
sample = json.loads(files[0].read_text())
print(sample[0]['label'], '—', len(sample), 'port records')
"
```

Expected: `50 files`, label `attack`.

Next step:
- `../07-build-dataset/README.md` (Milestone 5: merge normal + attack into labeled CSV)
