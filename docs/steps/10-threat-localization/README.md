# Step 10: Threat Localization (Milestone 8)

Pinpoint which switch in the SDN is most frequently flagging flows as under
attack, then identify the attacker hosts directly connected to that switch.

This implements Section III-H (Equations 6–7) of the Flood Control paper.

## Algorithm

```
For each of U observed flows u_i:
    For each switch s:
        ζ_s = Attack  if  (# attack-flagged ports on s) > Θ   (Eq. 6)
              Normal   otherwise

ψ = argmax_s  Σ_i ζ_s(u_i)                                    (Eq. 7)
```

Switch `ψ` is flagged most often → attackers are directly connected to it.

Paper parameters: `U=100` flows, `Θ=3`.  
Paper result (Figure 9): Switch 2 flagged 72/100 times → h1 and h2 identified.

## Prerequisites

Step 8 must be complete (`data/model.pkl`) and attack stats collected
(`data/raw/attack/`).

## Run

```bash
python3 simulation/threat_localizer.py \
  --attack-dir data/raw/attack \
  --theta 3 \
  --u-flows 100
```

## Expected output

```
========================================================
  Threat Localization Results — data/raw/attack
  Θ (switch threshold) = 3   U (flows) = 100
========================================================
  Switch        Times Flagged  Bar
  ──────────────────────────────────────────────────────
  s2                  72/100   █████████████████████ ← ψ (most flagged)
  s11                 51/100   ███████████████
  s9                  51/100   ███████████████
  s0                  30/100   █████████
  ...
────────────────────────────────────────────────────────
  ψ (most flagged switch) : s2
  Hosts connected to ψ    : h1, h2
  → Likely attackers      : h1, h2
========================================================
```

This matches Figure 9 and the paper's conclusion that h1 and h2 are the
malicious hosts, both directly connected to Switch 2.

## Reproducing Figure 8 (varying Θ)

```bash
for theta in 0 1 2 3 4; do
  echo "=== Theta=$theta ==="
  python3 simulation/threat_localizer.py \
    --attack-dir data/raw/attack --theta $theta --u-flows 100 \
    2>/dev/null | grep "Times Flagged" -A 20 | head -15
done
```

Lower Θ → more switches flagged (harder to localize).  
Θ=3 minimizes flagged switches to the 4 directly connected to attackers.

## Full pipeline complete

All 8 milestones from the Flood Control paper are now implemented:

| # | Component | Script |
|---|-----------|--------|
| 1 | SDN Topology | `fig3_topology.py` |
| 2 | Normal traffic | `traffic_gen.py` |
| 3 | Stats collection | `stats_collector.py` |
| 4 | SYN flood attack | `syn_flood.py` |
| 5 | Dataset builder | `build_dataset.py` |
| 6 | ML classifier | `train_classifier.py` |
| 7 | Threat detection | `threat_detector.py` |
| 8 | Threat localization | `threat_localizer.py` |
