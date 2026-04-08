import os
import re
import time
import joblib
import threading
import pandas as pd
import requests

MODEL_PATH = "ids_model.pkl"
SCALER_PATH = "ids_scaler.pkl"
META_PATH = "ids_meta.pkl"

LOG_FILES = [
    "/var/log/auth.log",
    "/var/log/kern.log",
    "/var/log/user.log",
    "/var/log/cron.log",
    "/var/log/alternatives.log",
    "/home/jegadeesh/VCC/course_project/test_ids.log"
]

ALERT_FILE = "ids_alerts.log"

log_pattern = re.compile(
    r"^(?P<date>\d{6})\s+"
    r"(?P<time>\d{6})\s+"
    r"(?P<pid>\d+)\s+"
    r"(?P<level>[A-Z]+)\s+"
    r"(?P<component>[^:]+):\s+"
    r"(?P<message>.*)$"
)

def parse_line(line: str) -> dict:
    m = log_pattern.match(line.strip())
    if not m:
        return {
            "raw_log": line.strip(),
            "date": None,
            "time": None,
            "pid": 0,
            "level": "UNKNOWN",
            "component": "UNKNOWN",
            "message": line.strip(),
        }
    return {
        "raw_log": line.strip(),
        "date": m.group("date"),
        "time": m.group("time"),
        "pid": int(m.group("pid")),
        "level": m.group("level"),
        "component": m.group("component"),
        "message": m.group("message"),
    }

def count_ips(text: str) -> int:
    return len(re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", str(text)))

def count_blocks(text: str) -> int:
    return len(re.findall(r"blk_-?\d+", str(text)))

def extract_size(text: str) -> int:
    m = re.search(r"size\s+(\d+)", str(text).lower())
    return int(m.group(1)) if m else 0

def extract_hour(t) -> int:
    if pd.isna(t) or t is None:
        return -1
    t = str(t).zfill(6)
    return int(t[:2])

def build_features_for_one(record: dict, feature_cols):
    df = pd.DataFrame([record])

    df["msg_len"] = df["message"].astype(str).apply(len)
    df["ip_count"] = df["message"].astype(str).apply(count_ips)
    df["block_count"] = df["message"].astype(str).apply(count_blocks)
    df["has_exception"] = df["message"].str.contains("exception|error|fail|failed", case=False, na=False).astype(int)
    df["has_warn"] = df["message"].str.contains("warn", case=False, na=False).astype(int)
    df["has_delete"] = df["message"].str.contains("delete|deleting|invalidSet", case=False, na=False).astype(int)
    df["has_success"] = df["message"].str.contains("succeeded|success", case=False, na=False).astype(int)
    df["has_terminate"] = df["message"].str.contains("terminating", case=False, na=False).astype(int)
    df["has_received"] = df["message"].str.contains("received block", case=False, na=False).astype(int)
    df["has_served"] = df["message"].str.contains("served block", case=False, na=False).astype(int)
    df["has_verification"] = df["message"].str.contains("verification succeeded", case=False, na=False).astype(int)
    df["size_value"] = df["message"].astype(str).apply(extract_size)
    df["hour"] = df["time"].apply(extract_hour)

    df["template_freq"] = 1
    df["component_freq"] = 1
    df["level_freq"] = 1
    df["level_code"] = 0
    df["component_code"] = 0

    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0

    return df[feature_cols].fillna(0)

def risk_decision(anomaly_score, record):
    score = anomaly_score
    msg = record["message"].lower()

    if "warn" in msg:
        score += 0.10
    if "exception" in msg or "failed" in msg or "error" in msg:
        score += 0.20
    if "verification succeeded" in msg:
        score -= 0.10

    score = max(0.0, min(score, 1.0))

    if score < 0.30:
        return score, "Normal"
    elif score < 0.55:
        return score, "Monitor"
    elif score < 0.75:
        return score, "Alert"
    else:
        return score, "Investigate"

def tail_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(1)
                continue
            yield line.rstrip("\n")
def monitor_file(path, model, scaler, feature_cols):
    print(f"Monitoring: {path}")

    try:
        for line in tail_file(path):
            if not line.strip():
                continue

            record = parse_line(line)
            record["source_file"] = path

            X = build_features_for_one(record, feature_cols)
            X_scaled = scaler.transform(X)

            pred = model.predict(X_scaled)[0]
            score_raw = model.decision_function(X_scaled)[0]
            anomaly_score = float(max(0.0, min(1.0, -score_raw + 0.5)))

            risk_score, decision = risk_decision(anomaly_score, record)

            if pred == -1 or decision in ("Alert", "Investigate"):
                alert = (
                    f"source={path} decision={decision} risk={risk_score:.3f} "
                    f"anomaly={pred == -1} log={record['raw_log']}"
                )
                print(alert)
                with open(ALERT_FILE, "a", encoding="utf-8") as af:
                    af.write(alert + "\n")
    except Exception as e:
        print(f"Error monitoring {path}: {e}")

def main():
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    meta = joblib.load(META_PATH)
    feature_cols = meta["feature_cols"]

    threads = []

    for path in LOG_FILES:
        if not os.path.exists(path):
            print(f"File not found, skipping: {path}")
            continue

        t = threading.Thread(
            target=monitor_file,
            args=(path, model, scaler, feature_cols),
            daemon=True
        )
        t.start()
        threads.append(t)

    if not threads:
        print("No valid log files found.")
        return

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
