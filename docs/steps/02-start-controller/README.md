# Step 2: Start A Controller

You have two options:

## Option A: Local OVS Controller (quick start)

No external process is needed. The topology script can start a local OVS controller automatically.

Use this for quick topology bring-up.

## Option B: Remote Controller (recommended for SDN experiments)

Use a remote OpenFlow controller so later modules can collect statistics and apply logic.

Example with Ryu (includes REST API for stats collection):

```bash
pip install ryu
ryu-manager ryu.app.simple_switch_13 \
  ryu.app.ofctl_rest \
  --ofp-tcp-listen-port 6653 \
  --wsapi-port 8080
```

The `ofctl_rest` app exposes `/stats/port/<dpid>` at port 8080, which the
stats collector uses to poll differential port statistics.

Keep this terminal open.

Next step:
- `../03-run-figure3-topology/README.md`
