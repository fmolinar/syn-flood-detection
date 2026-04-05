# Step 4: Verify The Simulation

Inside the Mininet CLI:

```bash
nodes
net
links
```

Basic connectivity checks:

```bash
h1 ping -c 3 h8
h2 ping -c 3 h8
h3 ping -c 3 h7
```

Check attacker/victim hosts from the paper:

```bash
h1 ifconfig
h2 ifconfig
h8 ifconfig
```

Exit the simulation:

```bash
exit
```

If Mininet gets stuck between runs:

```bash
sudo mn -c
```
