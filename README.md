# SDN Traffic Monitoring and Statistics Collector

## Problem Statement
Build an SDN controller module using Ryu and Mininet that collects and displays 
traffic statistics from OpenFlow switches. The controller acts as a learning switch 
while simultaneously polling each connected switch every 10 seconds for flow-level 
statistics — packet counts, byte counts, and match fields — and writes timestamped 
reports to a log file.

## SDN Concepts Used
- **OpenFlow 1.3** as the control protocol between controller and switches
- **packet_in events** for learning switch logic (MAC-to-port mapping)
- **OFPFlowStatsRequest / OFPFlowStatsReply** for statistics collection
- **Flow rules** with match+action+priority+idle_timeout
- **Ryu framework** as the SDN controller

## Topology
```
h1 (10.0.0.1) ──┐
h2 (10.0.0.2) ──┤
                s1 (OpenFlow Switch) ── Ryu Controller
h3 (10.0.0.3) ──┤
h4 (10.0.0.4) ──┘
```
4 hosts connected to 1 OpenFlow switch, controlled remotely by Ryu.

## Project Structure
```
sdn-traffic-monitor/
├── traffic_monitor.py     # Ryu controller: learning switch + stats collector
├── topology.py            # Custom Mininet topology (4 hosts, 1 switch)
├── test_validation.py     # Regression/validation tests
├── traffic_report.txt     # Auto-generated report from running the controller
├── screenshots/           # Proof of execution
│   ├── scenario1_pingall.png
│   ├── scenario2_iperf.png
│   ├── flow_stats_terminal.png
│   ├── wireshark_openflow.png
│   └── validation_tests.png
└── README.md
```

## Setup Requirements
- Ubuntu 20.04 / 22.04 (VM recommended)
- Mininet: `sudo apt install mininet -y`
- Ryu: `pip3 install ryu`
- iperf3: `sudo apt install iperf3 -y`
- Wireshark: `sudo apt install wireshark -y`

## How to Run

### Step 1 — Start the Ryu Controller (Terminal 1)
```bash
ryu-manager traffic_monitor.py --observe-links
```
You should see: `loading app traffic_monitor.py`

### Step 2 — Start the Mininet Network (Terminal 2)
```bash
sudo mn --custom topology.py --topo monitortopo \
  --controller remote,ip=127.0.0.1,port=6633 \
  --switch ovsk,protocols=OpenFlow13
```
You should see the Mininet CLI prompt: `mininet>`

### Step 3 — Run Test Scenarios (inside Mininet CLI)

**Scenario 1 — Baseline connectivity:**
```
mininet> pingall
```

**Scenario 2 — High volume traffic with iperf:**
```
mininet> h2 iperf -s &
mininet> h1 iperf -c 10.0.0.2 -t 30
```

Watch Terminal 1 — every 10 seconds you will see per-flow packet/byte counts printed.

### Step 4 — View the generated report
```bash
cat traffic_report.txt
```

### Step 5 — Run validation tests
```bash
python3 test_validation.py
```

### Step 6 — Cleanup
```bash
sudo mn -c
```

## Expected Output

### Terminal (Controller side)
```
[2026-04-13 10:00:00] Switch DPID: 1
  Priority        Packets          Bytes               Match
         1             24           2304     OFPMatch(...)
         0              4            280     OFPMatch(...)
```

### traffic_report.txt
Same as above but saved to file with timestamps for every polling interval.

## Test Scenarios and Results

### Scenario 1: Normal Forwarding (pingall)
- All 4 hosts ping each other successfully
- 0% packet loss
- Flow rules installed per source-destination pair
- Packet counts visible in stats output
- Demonstrates: controller learning switch logic works

### Scenario 2: High Load (iperf h1 → h2)
- TCP throughput measured between h1 and h2
- Byte counts in flow stats jump significantly vs Scenario 1
- Clearly shows the monitoring capturing real traffic volume
- Demonstrates: stats collector captures meaningful traffic differences

## Performance Observations
| Metric | Scenario 1 (ping) | Scenario 2 (iperf) |
|---|---|---|
| Packet count (10s window) | ~20-30 | ~5000+ |
| Byte count (10s window) | ~2000 bytes | ~50MB+ |
| Flow table entries | 12 (4x4 pairs - 4 self) | 12 + iperf flows |
| RTT latency (ping) | < 5ms | < 5ms |

## Validation
Run `python3 test_validation.py` after an experiment session.

Tests check:
- Report file is created by the controller
- Report file contains actual content
- Report contains switch DPID entries
- Report contains packet/byte count headers

Expected output:
```
PASS: Report file exists
PASS: Report file has content
PASS: Report contains flow statistics
PASS: Report contains packet and byte count headers

All validation tests passed!
```

## References
1. Ryu SDN Framework documentation — https://ryu.readthedocs.io
2. Mininet walkthrough — https://mininet.org/walkthrough/
3. OpenFlow 1.3 specification — https://opennetworking.org
4. Mininet GitHub — https://github.com/mininet/mininet
5. Ryu simple_switch_13 example — https://github.com/faucetsdn/ryu
