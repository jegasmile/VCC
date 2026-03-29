#!/usr/bin/env python3
import os
import time
import json
import subprocess
from datetime import datetime
import psutil

CHECK_INTERVAL = 10
THRESHOLD = 75.0 
CONSECUTIVE_BREACHES = 3
COOLDOWN_SECONDS = 900
STATE_FILE = "/home/jegadeesh/local_autoscale_state.json"
SCALE_SCRIPT = "/home/jegadeesh/scale_to_gcp.sh"

# Metrics to watch
WATCH_CPU = True
WATCH_RAM = True

def read_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"breaches": 0, "last_scale_time": 0}

def write_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)

def get_metrics():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    load_pct = None
    if hasattr(os, "getloadavg"):
        one_min_load = os.getloadavg()[0]
        cpu_count = psutil.cpu_count() or 1
        load_pct = (one_min_load / cpu_count) * 100.0
    return {
        "cpu": cpu,
        "ram": ram,
        "disk": disk,
        "load_pct": load_pct
    }

def threshold_breached(metrics):
    checks = []
    if WATCH_CPU:
        checks.append(metrics["cpu"] > THRESHOLD)
    if WATCH_RAM:
        checks.append(metrics["ram"] > THRESHOLD)
    return any(checks)

def should_cooldown(last_scale_time):
    return (time.time() - last_scale_time) < COOLDOWN_SECONDS

def scale_out():
    print(f"[{datetime.now()}] Triggering scale-out...")
    result = subprocess.run(
        [SCALE_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    print(result.stdout)
    return result.returncode == 0

def main():
    state = read_state()
    print("Starting local autoscale monitor...")

    while True:
        metrics = get_metrics()
        breached = threshold_breached(metrics)

        print(
            f"[{datetime.now()}] "
            f"CPU={metrics['cpu']:.1f}% "
            f"RAM={metrics['ram']:.1f}% "
            f"BREACHED={breached} "
            f"BREACH_COUNT={state['breaches']}"
        )

        if breached:
            state["breaches"] += 1
        else:
            state["breaches"] = 0

        if state["breaches"] >= CONSECUTIVE_BREACHES:
            if should_cooldown(state["last_scale_time"]):
                print(f"[{datetime.now()}] In cooldown, skipping scale-out.")
            else:
                ok = scale_out()
                if ok:
                    state["last_scale_time"] = time.time()
                    state["breaches"] = 0

        write_state(state)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
