# =============================================================================
# test_validation.py - Regression tests for Traffic Monitor
# Run after experiment: python3 test_validation.py
# =============================================================================

import os

REPORT_FILE = "traffic_report.txt"


def test_report_file_exists():
    if os.path.exists(REPORT_FILE):
        print("[PASS] Report file exists")
        return True
    print("[FAIL] Report file not found - run the controller first")
    return False


def test_report_not_empty():
    size = os.path.getsize(REPORT_FILE)
    if size > 100:
        print("[PASS] Report file has content ({} bytes)".format(size))
        return True
    print("[FAIL] Report file too small ({} bytes)".format(size))
    return False


def test_report_has_switch_entry():
    with open(REPORT_FILE) as f:
        content = f.read()
    if "Switch DPID" in content:
        print("[PASS] Report contains switch DPID entries")
        return True
    print("[FAIL] No switch DPID entries found")
    return False


def test_report_has_packet_counts():
    with open(REPORT_FILE) as f:
        content = f.read()
    if "Packets" in content and "Bytes" in content:
        print("[PASS] Report contains Packets and Bytes columns")
        return True
    print("[FAIL] Packet/Byte columns missing")
    return False


def test_report_has_summary():
    with open(REPORT_FILE) as f:
        content = f.read()
    if "TOTAL:" in content:
        print("[PASS] Report contains TOTAL summary lines")
        return True
    print("[FAIL] No TOTAL summary lines found")
    return False


def test_controller_files_exist():
    required = ["ext/traffic_monitor.py", "topology.py"]
    all_present = True
    for f in required:
        if os.path.exists(f):
            print("[PASS] Required file '{}' exists".format(f))
        else:
            print("[FAIL] Required file '{}' MISSING".format(f))
            all_present = False
    return all_present


if __name__ == "__main__":
    print("=" * 50)
    print("  Traffic Monitor - Validation Tests")
    print("=" * 50)

    results = []
    results.append(test_controller_files_exist())

    if test_report_file_exists():
        results.append(test_report_not_empty())
        results.append(test_report_has_switch_entry())
        results.append(test_report_has_packet_counts())
        results.append(test_report_has_summary())
    else:
        results.append(False)

    print("=" * 50)
    if all(results):
        print("  All {} tests passed.".format(len(results)))
    else:
        print("  {}/{} tests passed.".format(sum(results), len(results)))
    print("=" * 50)
