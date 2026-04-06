# Step 5: Collect Normal Traffic Statistics (Milestones 2 + 3)

This step generates N=50 normal IPerf flows through the topology and
simultaneously collects differential port statistics from all switches.
This produces the normal-traffic dataset X_N from the paper.

## Prerequisites

Ryu must be running with the REST API enabled (Step 2, Option B):

```bash
ryu-manager ryu.app.simple_switch_13 \
  ryu.app.ofctl_rest \
  --ofp-tcp-listen-port 6653 \
  --wsapi-port 8080
```

The `ofctl_rest` app exposes `/stats/port/<dpid>` used by the collector.

## Run

From repo root (requires root for Mininet):

```bash
sudo python3 simulation/fig3_topology.py \
  --controller remote \
  --controller-ip 127.0.0.1 \
  --controller-port 6653 \
  --collect-normal 50 \
  --ryu-api-port 8080 \
  --data-dir data/raw/normal
```

This single command:
1. Brings up the Figure 3 topology (10 hosts, 12 switches)
2. Generates 50 normal IPerf flows (random src→dst pairs, 10 Mbps, 5 s each)
3. Polls all switch ports every 5 s and writes differential stats to JSON files
4. Shuts down the topology when done

Expected runtime: ~250 seconds (50 flows × 5 s each).

## Output

One JSON file per polling interval written to `data/raw/normal/`:

```
data/raw/normal/
  N_0.json
  N_1.json
  ...
  N_49.json
```

Each file is a list of per-port delta records, e.g.:

```json
[
  {
    "delta_rx_packets": 142,
    "delta_rx_bytes": 18304,
    "delta_tx_packets": 139,
    "delta_tx_bytes": 17792,
    "delta_duration_sec": 5,
    "delta_rx_dropped": 0,
    "delta_tx_dropped": 0,
    "delta_rx_errors": 0,
    "delta_tx_errors": 0,
    "switch": "s2",
    "dpid": 3,
    "port_no": 1,
    "label": "normal"
  },
  ...
]
```

These 9 delta features correspond to Table I of the paper.

## Verify

```bash
ls data/raw/normal/     # should show N_0.json … N_49.json
python3 -c "import json; d=json.load(open('data/raw/normal/N_0.json')); print(len(d), 'records'); print(list(d[0].keys()))"
```

Next step:
- `../06-collect-attack-stats/README.md` (Milestone 4: TCP-SYN attack + attack dataset)
