# Step 7: Build the ML Dataset (Milestone 5)

Merge the normal and attack JSON stat files into a single balanced, labeled
CSV dataset ready for ML training.  This implements Section III-E of the paper.

## Prerequisites

Steps 5 and 6 must be complete so that both raw directories exist:

```
data/raw/normal/N_0.json … N_49.json   (label: "normal")
data/raw/attack/N_0.json … N_49.json   (label: "attack")
```

Install Python deps if not already done:

```bash
pip install pandas scikit-learn
```

## Run

From repo root:

```bash
python3 simulation/build_dataset.py
```

With explicit paths:

```bash
python3 simulation/build_dataset.py \
  --normal-dir data/raw/normal \
  --attack-dir data/raw/attack \
  --output-dir data \
  --test-size 0.2
```

## Output

```
data/
  dataset.csv   — full balanced dataset (features + switch/dpid/port_no metadata + label)
  train.csv     — 80% stratified split  (features + label only)
  test.csv      — 20% stratified split  (features + label only)
```

### Feature columns (Table I of the paper)

| Column | Description |
|--------|-------------|
| `delta_rx_packets` | Change in packets received by the port |
| `delta_rx_bytes` | Change in bytes received |
| `delta_tx_packets` | Change in packets sent |
| `delta_tx_bytes` | Change in bytes sent |
| `delta_duration_sec` | Change in port alive duration (seconds) |
| `delta_rx_dropped` | Change in packets dropped by receiver |
| `delta_tx_dropped` | Change in packets dropped by sender |
| `delta_rx_errors` | Change in receive errors |
| `delta_tx_errors` | Change in transmit errors |
| `label` | `0` = normal, `1` = attack |

The metadata columns (`switch`, `dpid`, `port_no`) appear in `dataset.csv`
for reference but are excluded from `train.csv` and `test.csv`.

## Verify

```bash
python3 - <<'EOF'
import pandas as pd
df = pd.read_csv("data/dataset.csv")
print("Shape:", df.shape)
print("Label distribution:\n", df["label"].value_counts().rename({0:"normal",1:"attack"}))
print("\nSample row:\n", df.iloc[0])
EOF
```

Expected: equal counts for normal (0) and attack (1).

Next step:
- `../08-train-classifier/README.md` (Milestone 6: train Random Forest classifier)
