# SDN Traffic Monitoring and Statistics Collector

## Problem Statement
Build an SDN controller module using POX and Mininet that collects and displays
traffic statistics from OpenFlow switches. The controller acts as a learning switch
while simultaneously polling each connected switch every 10 seconds for flow-level
statistics — packet counts, byte counts — and writes timestamped reports to a log file.

## SDN Concepts Used
- **OpenFlow 1.0** as the control protocol between controller and switches
- **packet_in events** for learning switch logic (MAC-to-port mapping)
- **ofp_stats_request / FlowStatsReceived** for periodic statistics collection
- **Flow rules** with match, action, priority, and idle_timeout
- **POX framework** as the SDN controller (Python-based, no pip install needed)

## Topology
h1 (10.0.0.1) ──┐
h2 (10.0.0.2) ──┤
s1 (OpenFlow Switch) ── POX Controller (port 6633)
h3 (10.0.0.3) ──┤
h4 (10.0.0.4) ──┘

4 hosts connected to 1 OpenFlow switch, controlled remotely by POX.
This star topology creates 12 unique source-destination flow pairs,
giving meaningful and observable traffic statistics.

## Project Structure
sdn-traffic-monitor/
├── ext/
│   └── traffic_monitor.py     # POX controller: learning switch + stats collector
├── topology.py                # Custom Mininet topology (4 hosts, 1 switch)
├── test_validation.py         # Regression and validation tests
├── traffic_report.txt         # Auto-generated report from running the controller
├── screenshots/
│   ├── flow_stats_terminal.png       # Controller polling stats every 10s
│   ├── scenario1_pingallT1.png       # Controller side during pingall
│   ├── scenario1_pingallT2.png       # Mininet side showing 0% packet loss
│   ├── scenario2_iperfT1.png         # Controller showing massive byte counts
│   ├── scenario2_iperfT2.png         # Mininet iperf throughput result
│   ├── validation_tests.png          # All 5 validation tests passing
│   └── traffic_report_screenshot.png # Generated report file content
└── README.md

## Setup Requirements

- Ubuntu 20.04 / 22.04 (or WSL2 with Ubuntu)
- Mininet: `sudo apt install mininet -y`
- POX: `git clone https://github.com/noxrepo/pox.git`
- iperf: `sudo apt install iperf -y`

No additional pip packages needed. POX runs directly with Python 3.

## How to Run

### Step 1 — Clone POX (if not already done)
```bash
git clone https://github.com/noxrepo/pox.git
cd pox
```

### Step 2 — Place controller file
Make sure `traffic_monitor.py` is inside the `ext/` folder:
```bash
ls ext/traffic_monitor.py
```

### Step 3 — Start the POX Controller (Terminal 1)
```bash
cd ~/pox
python3 pox.py log.level --DEBUG openflow.of_01 traffic_monitor
```

Expected output:
INFO:core:POX 0.7.0 is up.
DEBUG:openflow.of_01:Listening on 0.0.0.0:6633
INFO:traffic_monitor:TrafficMonitor started. Polling every 10 seconds.

### Step 4 — Start the Mininet Network (Terminal 2)
```bash
cd ~/pox
sudo mn --custom topology.py --topo monitortopo \
  --controller remote,ip=127.0.0.1,port=6633 \
  --switch ovsk,protocols=OpenFlow10
```

Expected output:
*** Adding hosts: h1 h2 h3 h4
*** Adding switches: s1
*** Starting CLI:
mininet>

### Step 5 — Run Test Scenarios (inside Mininet CLI)

**Scenario 1 — Baseline connectivity:**
mininet> pingall
Expected: `*** Results: 0% dropped (12/12 received)`

**Scenario 2 — High volume traffic:**
mininet> h2 iperf -s &
mininet> h1 iperf -c 10.0.0.2 -t 20
Watch Terminal 1 — byte counts jump to billions within seconds.

### Step 6 — View the generated report
```bash
cat ~/pox/traffic_report.txt
```

### Step 7 — Run validation tests (Terminal 3)
```bash
cd ~/pox
python3 test_validation.py
```

### Step 8 — Cleanup
```bash
sudo mn -c
```

## Test Scenarios and Results

### Scenario 1: Normal Forwarding (pingall)
- All 4 hosts successfully ping each other
- 0% packet loss (12/12 received)
- Flow table grows from 1 rule to 13 rules as MAC addresses are learned
- Controller installs per-flow rules with idle_timeout=30
- Packet and byte counts visible in stats every 10 seconds
- Demonstrates: learning switch logic and flow rule installation work correctly

### Scenario 2: High Load Traffic (iperf h1 to h2)
- TCP bulk transfer between h1 (10.0.0.1) and h2 (10.0.0.2)
- Achieved 17.4 Gbits/sec, transferring 40.6 GBytes over 20 seconds
- Byte counts in flow stats jumped from thousands to billions of bytes per interval
- Clearly demonstrates the monitoring collector tracking real traffic load
- Demonstrates: stats collector accurately reflects network conditions

## Performance Observations

| Metric | Scenario 1 (pingall) | Scenario 2 (iperf) |
|---|---|---|
| Total packets observed | ~84 packets | ~1.5 million packets |
| Total bytes observed | ~6108 bytes | ~43 billion bytes |
| Flow table entries | 13 flows | 3 flows |
| Throughput | N/A | 17.4 Gbits/sec |
| Packet loss | 0% | 0% |
| Stats polling interval | 10 seconds | 10 seconds |

## Validation Results

All 5 regression tests pass after running the experiment:
================================================
Traffic Monitor - Validation Tests
[PASS] Required file 'ext/traffic_monitor.py' exists
[PASS] Required file 'topology.py' exists
[PASS] Report file exists
[PASS] Report file has content (30151 bytes)
[PASS] Report contains switch DPID entries
[PASS] Report contains Packets and Bytes columns
[PASS] Report contains TOTAL summary lines
All 5 tests passed.

## How the Controller Works

1. When a switch connects, the controller installs a table-miss rule (priority 0)
   that sends all unmatched packets to the controller.

2. When a packet arrives (packet_in), the controller learns which port the source
   MAC came from and stores it in a MAC-to-port table.

3. If the destination MAC is already known, the controller installs a flow rule
   (priority 1, idle_timeout=30) so future packets between that pair are handled
   directly by the switch without involving the controller.

4. Every 10 seconds, a background timer sends an ofp_stats_request to every
   connected switch. The switch replies with per-flow counters (packet_count,
   byte_count) which are displayed in the terminal and written to traffic_report.txt.

## References

1. POX SDN Controller documentation — https://noxrepo.github.io/pox-doc/html/
2. POX GitHub repository — https://github.com/noxrepo/pox
3. Mininet walkthrough — https://mininet.org/walkthrough/
4. OpenFlow 1.0 specification — https://opennetworking.org
5. Mininet GitHub — https://github.com/mininet/mininet
