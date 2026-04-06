# Step 9: Threat Detection (Milestone 7)

Classify network flows as normal or under TCP-SYN flood attack using the
trained Random Forest model and port threshold Φ.

This implements Section III-G (Equations 3–5) of the Flood Control paper.

## Algorithm

For each observed flow across all switches:

```
For each port p the flow passes through:
    ω_p = 1  if classifier(port_stats) == Attack
          0  otherwise                              (Eq. 3)

η_p = Σ ω_p   (count of attack-flagged ports)     (Eq. 4)

flow = Attack   if  η_p / W_i  >=  Φ              (Eq. 5)
       Normal   otherwise
```

Where `W_i` = total ports for that flow, `Φ` = port threshold (paper: `Φ=0.3`).

## Prerequisites

Step 8 must be complete: `data/model.pkl` must exist.

## Usage

### Evaluate on labeled test CSV (offline)

```bash
python3 simulation/threat_detector.py --csv data/test.csv --phi 0.3
```

### Evaluate on collected normal JSON stats

```bash
python3 simulation/threat_detector.py \
  --data-dir data/raw/normal \
  --phi 0.3 \
  --ground-truth normal
```

### Evaluate on collected attack JSON stats

```bash
python3 simulation/threat_detector.py \
  --data-dir data/raw/attack \
  --phi 0.3 \
  --ground-truth attack
```

## Expected output

```
========================================================
  Threat Detection Results — data/raw/attack
  Φ (port threshold) = 0.3
========================================================
  [✓] flow 0     Attack   (GT: Attack)  ports=18/22  ratio=0.818
  [✓] flow 1     Attack   (GT: Attack)  ports=21/22  ratio=0.955
  ...
────────────────────────────────────────────────────────
  Flows detected as Attack : 50/50
  Flows detected as Normal : 0/50
  Correct classifications  : 50/50  (100.0%)
========================================================
```

## Varying Φ (Figure 7 of the paper)

Lower Φ → more false positives (normal flows flagged as attack).
Higher Φ → better precision but may miss some attacks.
Paper finds Φ=0.3 optimal for the F-Measure.

```bash
for phi in 0.05 0.1 0.15 0.2 0.25 0.3 0.35; do
  echo "--- phi=$phi ---"
  python3 simulation/threat_detector.py --data-dir data/raw/attack --phi $phi --ground-truth attack 2>/dev/null | grep "Correct"
done
```

Next step:
- `../10-threat-localization/README.md` (Milestone 8: pinpoint attacker switches using Θ)
