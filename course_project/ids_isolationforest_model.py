import os
import re
import glob
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

LOG_DIR = "/Users/jegadeesh/Desktop/Jegadeesh/Python/train_logs"  
MODEL_PATH = "ids_model.pkl"
SCALER_PATH = "ids_scaler.pkl"
META_PATH = "ids_meta.pkl"

log_pattern = re.compile(
    r"^(?P<date>\d{6})\s+"
    r"(?P<time>\d{6})\s+"
    r"(?P<pid>\d+)\s+"
    r"(?P<level>[A-Z]+)\s+"
    r"(?P<component>[^:]+):\s+"
    r"(?P<message>.*)$"
)

def parse_line(line: str, source_file: str) -> dict:
    m = log_pattern.match(line.strip())
    if not m:
        return {
            "raw_log": line.strip(),
            "source_file": source_file,
            "date": None,
            "time": None,
            "pid": 0,
            "level": "UNKNOWN",
            "component": "UNKNOWN",
            "message": line.strip(),
        }
    return {
        "raw_log": line.strip(),
        "source_file": source_file,
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

def normalize_message(msg: str) -> str:
    msg = re.sub(r"blk_-?\d+", "BLK_ID", str(msg))
    msg = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "IP_ADDR", msg)
    msg = re.sub(r"\b\d+\b", "NUM", msg)
    return msg

def load_all_logs(log_dir: str) -> pd.DataFrame:
    all_records = []
    files = glob.glob(os.path.join(log_dir, "*"))

    for file_path in files:
        if not os.path.isfile(file_path):
            continue

        source_file = os.path.basename(file_path)
        print(f"Reading: {source_file}")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line:
                    all_records.append(parse_line(line, source_file))

    df = pd.DataFrame(all_records)
    return df

def build_features(df: pd.DataFrame):
    df = df.copy()

    df["msg_len"] = df["message"].astype(str).apply(len)
    df["ip_count"] = df["message"].astype(str).apply(count_ips)
    df["block_count"] = df["message"].astype(str).apply(count_blocks)
    df["has_exception"] = df["message"].str.contains("exception|error|fail|failed", case=False, na=False).astype(int)
    df["has_warn"] = df["message"].str.contains("warn", case=False, na=False).astype(int)
    df["has_delete"] = df["message"].str.contains("delete|deleting|invalid", case=False, na=False).astype(int)
    df["has_success"] = df["message"].str.contains("succeeded|success", case=False, na=False).astype(int)
    df["has_terminate"] = df["message"].str.contains("terminating", case=False, na=False).astype(int)
    df["has_received"] = df["message"].str.contains("received block", case=False, na=False).astype(int)
    df["has_served"] = df["message"].str.contains("served block", case=False, na=False).astype(int)
    df["size_value"] = df["message"].astype(str).apply(extract_size)
    df["hour"] = df["time"].apply(extract_hour)

    df["template"] = df["message"].apply(normalize_message)
    df["template_freq"] = df.groupby("template")["template"].transform("count")
    df["component_freq"] = df.groupby("component")["component"].transform("count")
    df["level_freq"] = df.groupby("level")["level"].transform("count")
    df["source_freq"] = df.groupby("source_file")["source_file"].transform("count")

    # categorical encoding
    df["level_code"] = df["level"].astype("category").cat.codes
    df["component_code"] = df["component"].astype("category").cat.codes
    df["source_file_code"] = df["source_file"].astype("category").cat.codes

    feature_cols = [
        "pid",
        "msg_len",
        "ip_count",
        "block_count",
        "has_exception",
        "has_warn",
        "has_delete",
        "has_success",
        "has_terminate",
        "has_received",
        "has_served",
        "size_value",
        "hour",
        "template_freq",
        "component_freq",
        "level_freq",
        "source_freq",
        "level_code",
        "component_code",
        "source_file_code",
    ]

    X = df[feature_cols].fillna(0)
    return df, X, feature_cols

def main():
    df = load_all_logs(LOG_DIR)
    print("Total combined log rows:", len(df))
    print("Files used:", df["source_file"].nunique())

    df, X, feature_cols = build_features(df)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42
    )
    model.fit(X_scaled)

    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    joblib.dump({"feature_cols": feature_cols}, META_PATH)

    print("Training complete.")
    print("Saved model files:")
    print(MODEL_PATH)
    print(SCALER_PATH)
    print(META_PATH)
    print("\nTop 10 anomalies:")
    print(df.sort_values)
    print(
    df.sort_values("level_code", ascending=False)[
        ["source_file", "raw_log", "level_code"]
    ].head(10).to_string(index=False)
    )

if __name__ == "__main__":
    main()
