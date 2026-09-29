"""
ML Pipeline: Data Preprocessing
Part of: ML-Enhanced SDN Emergency Communication Network

Dataset: CICIDS2017 (simulated/synthetic if not available)
The preprocessing pipeline:
  1. Load raw CSV data
  2. Remove invalid values (inf, NaN)
  3. Encode categorical labels
  4. Select relevant features
  5. Scale features
  6. Split into train/test sets
  7. Return ready-to-use arrays
"""
import logging
import os
from typing import Tuple, List

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib

logger = logging.getLogger(__name__)

# Features used for training (CICIDS2017 column names)
CICIDS_FEATURES = [
    "Flow Duration",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Total Length of Fwd Packets",
    "Total Length of Bwd Packets",
    "Fwd Packet Length Mean",
    "Bwd Packet Length Mean",
    "Flow Bytes/s",
    "Flow Packets/s",
    "Flow IAT Mean",
    "Fwd IAT Mean",
    "Bwd IAT Mean",
    "Packet Length Mean",
    "Packet Length Std",
    "Average Packet Size",
    "Fwd Header Length",
    "Bwd Header Length",
]

# Mapping CICIDS label → our 3-class risk
LABEL_MAP = {
    "BENIGN": "NORMAL",
    "DoS Hulk": "HIGH_RISK",
    "PortScan": "CONGESTED",
    "DDoS": "HIGH_RISK",
    "DoS GoldenEye": "HIGH_RISK",
    "FTP-Patator": "CONGESTED",
    "SSH-Patator": "CONGESTED",
    "DoS slowloris": "HIGH_RISK",
    "DoS Slowhttptest": "HIGH_RISK",
    "Bot": "HIGH_RISK",
    "Web Attack  Brute Force": "CONGESTED",
    "Web Attack  XSS": "CONGESTED",
    "Infiltration": "HIGH_RISK",
    "Web Attack  Sql Injection": "HIGH_RISK",
    "Heartbleed": "HIGH_RISK",
    "NORMAL": "NORMAL",
    "CONGESTED": "CONGESTED",
    "HIGH_RISK": "HIGH_RISK",
}

RISK_CLASSES = ["NORMAL", "CONGESTED", "HIGH_RISK"]
RISK_TO_SCORE = {"NORMAL": 0.1, "CONGESTED": 0.55, "HIGH_RISK": 0.85}


def generate_synthetic_dataset(n_samples: int = 15000) -> pd.DataFrame:
    """
    Generate a realistic synthetic network dataset when CICIDS2017 is
    not available. The features mirror CICIDS2017 columns.

    This is clearly labeled as SYNTHETIC so results are not misrepresented.
    """
    rng = np.random.default_rng(42)

    # Generate 3 traffic classes with realistic distributions
    n_normal = int(n_samples * 0.6)
    n_congested = int(n_samples * 0.25)
    n_highrisk = n_samples - n_normal - n_congested

    def make_class(n, flow_dur, pkt_rate, bps, label):
        return pd.DataFrame({
            "Flow Duration": rng.exponential(flow_dur, n).clip(1, 1e7),
            "Total Fwd Packets": rng.poisson(pkt_rate * 0.6, n).clip(1),
            "Total Backward Packets": rng.poisson(pkt_rate * 0.4, n).clip(0),
            "Total Length of Fwd Packets": rng.exponential(bps * 0.5, n).clip(0),
            "Total Length of Bwd Packets": rng.exponential(bps * 0.3, n).clip(0),
            "Fwd Packet Length Mean": rng.normal(500, 200, n).clip(0),
            "Bwd Packet Length Mean": rng.normal(300, 150, n).clip(0),
            "Flow Bytes/s": rng.exponential(bps, n).clip(0),
            "Flow Packets/s": rng.exponential(pkt_rate, n).clip(0),
            "Flow IAT Mean": rng.exponential(1e5, n).clip(0),
            "Fwd IAT Mean": rng.exponential(1e5, n).clip(0),
            "Bwd IAT Mean": rng.exponential(1.5e5, n).clip(0),
            "Packet Length Mean": rng.normal(400, 180, n).clip(0),
            "Packet Length Std": rng.exponential(200, n).clip(0),
            "Average Packet Size": rng.normal(450, 200, n).clip(0),
            "Fwd Header Length": rng.integers(20, 60, n).astype(float),
            "Bwd Header Length": rng.integers(20, 60, n).astype(float),
            "Label": label,
        })

    normal = make_class(n_normal, 5e5, 50, 1e5, "NORMAL")
    congested = make_class(n_congested, 1e6, 250, 8e5, "CONGESTED")
    highrisk = make_class(n_highrisk, 2e6, 800, 5e6, "HIGH_RISK")

    df = pd.concat([normal, congested, highrisk], ignore_index=True)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    logger.info("Synthetic dataset created: %d samples", len(df))
    return df


def load_cicids2017(data_dir: str) -> pd.DataFrame:
    """
    Try to load CICIDS2017 CSVs from data_dir.
    Falls back to synthetic data if files are not found.
    """
    csv_files = []
    if os.path.isdir(data_dir):
        csv_files = [
            os.path.join(data_dir, f)
            for f in os.listdir(data_dir)
            if f.endswith(".csv")
        ]

    if not csv_files:
        logger.warning(
            "No CICIDS2017 CSVs found in %s — using synthetic dataset.", data_dir
        )
        return generate_synthetic_dataset()

    dfs = []
    for f in csv_files:
        try:
            chunk = pd.read_csv(f, low_memory=False)
            dfs.append(chunk)
            logger.info("Loaded %d rows from %s", len(chunk), f)
        except Exception as exc:
            logger.error("Failed to read %s: %s", f, exc)

    if not dfs:
        return generate_synthetic_dataset()

    df = pd.concat(dfs, ignore_index=True)
    df.columns = [c.strip() for c in df.columns]
    return df


def preprocess(
    df: pd.DataFrame,
    features: List[str] = None,
    label_col: str = "Label",
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple:
    """
    Full preprocessing pipeline:
      1. Select features present in the dataframe
      2. Handle infinities and NaN
      3. Map labels to 3-class risk
      4. Encode labels
      5. Scale features
      6. Train/test split

    Returns:
        X_train, X_test, y_train, y_test, scaler, label_encoder, feature_names
    """
    if features is None:
        features = CICIDS_FEATURES

    # Keep only features that exist in the df
    available = [f for f in features if f in df.columns]
    if not available:
        raise ValueError("None of the expected features found in dataset.")

    logger.info("Using %d / %d features", len(available), len(features))

    X = df[available].copy()
    y_raw = df[label_col].copy() if label_col in df.columns else pd.Series(["NORMAL"] * len(df))

    # Replace inf / -inf with NaN, then fill NaN
    X.replace([np.inf, -np.inf], np.nan, inplace=True)
    X.fillna(X.median(numeric_only=True), inplace=True)

    # Clip extreme values (99th percentile)
    for col in X.columns:
        cap = X[col].quantile(0.99)
        X[col] = X[col].clip(upper=cap)

    # Map CICIDS labels → NORMAL / CONGESTED / HIGH_RISK
    y_mapped = y_raw.astype(str).str.strip().map(
        lambda lbl: LABEL_MAP.get(lbl, "NORMAL")
    )

    # Encode
    le = LabelEncoder()
    le.fit(RISK_CLASSES)
    y_encoded = le.transform(y_mapped)

    # Scale
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_encoded, test_size=test_size, random_state=random_state,
        stratify=y_encoded,
    )

    logger.info(
        "Dataset split — train: %d  test: %d", len(X_train), len(X_test)
    )
    return X_train, X_test, y_train, y_test, scaler, le, available
