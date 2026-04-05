# Step 2: Start A Controller

You have two options:

## Option A: Local OVS Controller (quick start)

No external process is needed. The topology script can start a local OVS controller automatically.

Use this for quick topology bring-up.

## Option B: Remote Controller (recommended for SDN experiments)

Use a remote OpenFlow controller so later modules can collect statistics and apply logic.

Example with Ryu:

```bash
python3 -m pip install ryu
ryu-manager ryu.app.simple_switch_13 --ofp-tcp-listen-port 6653
```

Keep this terminal open.

Next step:
- `../03-run-figure3-topology/README.md`
