# Step 3: Run Figure 3 Topology

From repo root:

## Quick start (local OVS controller)

```bash
sudo python3 simulation/fig3_topology.py --controller ovs --pingall
```

## Remote controller mode (for later paper pipeline)

```bash
sudo python3 simulation/fig3_topology.py \
  --controller remote \
  --controller-ip 127.0.0.1 \
  --controller-port 6653 \
  --pingall
```

What the script creates:
- 10 hosts (`h1` to `h10`)
- 12 OpenFlow 1.3 switches (`s0` to `s11`)
- Figure 3 host and inter-switch links
- Attack/victim context from paper (`h1`, `h2` attackers; `h8` victim)

The script drops you into Mininet CLI unless `--no-cli` is provided.

Next step:
- `../04-verify/README.md`
