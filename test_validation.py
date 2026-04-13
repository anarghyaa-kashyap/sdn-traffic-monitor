# =============================================================================
# test_validation.py
# Regression / validation tests for the Traffic Monitor project
# Run after completing an experiment session:
#     python3 test_validation.py
# =============================================================================

import os

REPORT_FILE = "traffic_report.txt"
PASS = "PASS"
FAIL = "FAIL"


def test_report_file_exists():
    """Controller must create traffic_report.txt when it runs."""
    if os.path.exists(REPORT_FILE):
        print("[{}] Report file '{}' exists".format(PASS, REPORT_FILE))
        return True
    else:
        print("[{}] Report file '{}' NOT found".format(FAIL, REPORT_FILE))
        print("      Make sure you ran the controller before testing.")
        return False


def test_report_not_empty():
    """Report file must contain actual content, not just be an empty file."""
    size = os.path.getsize(REPORT_FILE)
    if size > 100:
        print("[{}] Report file has content ({} bytes)".format(PASS, size))
        return True
    else:
        print("[{}] Report file is too small ({} bytes)".format(FAIL, size))
        return False


def test_report_has_switch_entry():
    """Report must contain at least one switch DPID entry."""
    with open(REPORT_FILE) as f:
        content = f.read()
    if "Switch DPID" in content:
        print("[{}] Report contains switch DPID entries".format(PASS))
        return True
    else:
        print("[{}] No switch DPID entries found in report".format(FAIL))
        return False


def test_report_has_packet_counts():
    """Report must contain packet and byte count columns."""
    with open(REPORT_FILE) as f:
        content = f.read()
    if "Packets" in content and "Bytes" in content:
        print("[{}] Report contains Packets and Bytes columns".format(PASS))
        return True
    else:
        print("[{}] Packet/Byte columns missing from report".format(FAIL))
        return False


def test_report_has_summary():
    """Report must contain the TOTAL summary line per polling cycle."""
    with open(REPORT_FILE) as f:
        content = f.read()
    if "TOTAL:" in content:
        print("[{}] Report contains summary TOTAL lines".format(PASS))
        return True
    else:
        print("[{}] No TOTAL summary lines found".format(FAIL))
        return False


def test_controller_files_exist():
    """All required project files must be present."""
    required = ["traffic_monitor.py", "topology.py"]
    all_present = True
    for f in required:
        if os.path.exists(f):
            print("[{}] Required file '{}' exists".format(PASS, f))
        else:
            print("[{}] Required file '{}' MISSING".format(FAIL, f))
            all_present = False
    return all_present


# =============================================================================
# Run all tests
# =============================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("  Traffic Monitor — Validation Tests")
    print("=" * 50)

    results = []

    # File existence tests (run regardless)
    results.append(test_controller_files_exist())

    # Report tests (only run if report file exists)
    if test_report_file_exists():
        results.append(test_report_not_empty())
        results.append(test_report_has_switch_entry())
        results.append(test_report_has_packet_counts())
        results.append(test_report_has_summary())
    else:
        results.append(False)

    # Final verdict
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    if all(results):
        print("  All {} tests passed.".format(total))
    else:
        print("  {}/{} tests passed.".format(passed, total))
    print("=" * 50)
```

---

## What Your Repo Should Look Like When Done

After uploading everything including screenshots, your repo file list should be:
```
README.md
traffic_monitor.py
topology.py
test_validation.py
traffic_report.txt          ← upload after running the experiment
screenshots/
    scenario1_pingall.png
    scenario2_iperf.png
    flow_stats_terminal.png
    wireshark_openflow.png
    validation_tests.png
