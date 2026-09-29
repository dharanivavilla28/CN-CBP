"""
ML Prediction Engine
Part of: ML-Enhanced SDN Emergency Communication Network

Loads the trained model and provides real-time risk prediction
for network links based on their current traffic features.
"""
import json
import logging
import os
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
import joblib

from ml.preprocess import RISK_CLASSES, RISK_TO_SCORE, CICIDS_FEATURES

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "models")


class MLPredictor:
    """
    Loads the trained Random Forest model and provides link-level
    risk predictions.

    Prediction output format:
      {
        "link_id": "S1-S2",
        "risk_score": 0.78,          # 0.0–1.0
        "risk_class": "HIGH_RISK",   # NORMAL / CONGESTED / HIGH_RISK
        "probabilities": {"NORMAL": 0.05, "CONGESTED": 0.17, "HIGH_RISK": 0.78},
        "feature_importance": [...],
        "contributing_indicators": [...],
        "timestamp": 1234567890.0
      }
    """

    def __init__(self):
        self.model = None
        self.scaler = None
        self.label_encoder = None
        self.metadata: dict = {}
        self.feature_names: List[str] = []
        self.is_loaded = False
        self._load_model()

    def _load_model(self):
        model_path = os.path.join(MODEL_DIR, "model.pkl")
        scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
        le_path = os.path.join(MODEL_DIR, "label_encoder.pkl")
        meta_path = os.path.join(MODEL_DIR, "model_metadata.json")

        if not os.path.exists(model_path):
            logger.warning("Model not found at %s — running in fallback mode", model_path)
            self.is_loaded = False
            return

        try:
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            self.label_encoder = joblib.load(le_path)

            if os.path.exists(meta_path):
                with open(meta_path) as fh:
                    self.metadata = json.load(fh)
                self.feature_names = self.metadata.get("features", CICIDS_FEATURES)
            else:
                self.feature_names = CICIDS_FEATURES

            self.is_loaded = True
            logger.info(
                "ML model loaded — accuracy=%.4f  features=%d",
                self.metadata.get("accuracy", 0),
                len(self.feature_names),
            )
        except Exception as exc:
            logger.error("Failed to load ML model: %s", exc)
            self.is_loaded = False

    def _extract_features(self, link_metrics: dict) -> np.ndarray:
        """
        Map live link metrics to the feature vector expected by the model.
        Missing features are estimated from available ones.
        """
        bps = link_metrics.get("bytes_per_sec", 0)
        pps = link_metrics.get("packets_per_sec", 0)
        latency_us = link_metrics.get("latency", 10) * 1000  # ms → µs
        fwd_pkts = pps * 0.6
        bwd_pkts = pps * 0.4
        mean_pkt_len = bps / max(pps, 1)

        feature_map = {
            "Flow Duration": link_metrics.get("flow_duration", 5e5),
            "Total Fwd Packets": fwd_pkts,
            "Total Backward Packets": bwd_pkts,
            "Total Length of Fwd Packets": bps * 0.5,
            "Total Length of Bwd Packets": bps * 0.3,
            "Fwd Packet Length Mean": mean_pkt_len,
            "Bwd Packet Length Mean": mean_pkt_len * 0.8,
            "Flow Bytes/s": bps,
            "Flow Packets/s": pps,
            "Flow IAT Mean": latency_us,
            "Fwd IAT Mean": latency_us * 0.6,
            "Bwd IAT Mean": latency_us * 0.8,
            "Packet Length Mean": mean_pkt_len,
            "Packet Length Std": mean_pkt_len * 0.3,
            "Average Packet Size": mean_pkt_len,
            "Fwd Header Length": 40.0,
            "Bwd Header Length": 40.0,
        }

        return np.array(
            [feature_map.get(f, 0.0) for f in self.feature_names],
            dtype=float,
        ).reshape(1, -1)

    def predict_link(self, link_id: str, link_metrics: dict) -> dict:
        """
        Predict the risk level for a single link based on its traffic metrics.
        """
        timestamp = time.time()

        if not self.is_loaded:
            # Fallback heuristic when model is unavailable
            return self._heuristic_predict(link_id, link_metrics, timestamp)

        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                X_raw = self._extract_features(link_metrics)
                X_scaled = self.scaler.transform(X_raw)
                proba = self.model.predict_proba(X_scaled)[0]
                class_idx = int(np.argmax(proba))
                risk_class = self.label_encoder.inverse_transform([class_idx])[0]
                risk_score = RISK_TO_SCORE[risk_class]

            classes = list(self.label_encoder.classes_)
            probabilities = {cls: round(float(p), 4) for cls, p in zip(classes, proba)}

            # Feature importance for explainability
            importances = self.model.feature_importances_
            ranked = sorted(
                zip(self.feature_names, importances, X_raw[0]),
                key=lambda x: x[1],
                reverse=True,
            )[:5]

            contributing_indicators = [
                {
                    "feature": f,
                    "importance": round(imp, 4),
                    "value": round(float(val), 2),
                    "direction": "↑" if val > 0 else "↓",
                }
                for f, imp, val in ranked
            ]

            return {
                "link_id": link_id,
                "risk_score": round(risk_score, 4),
                "risk_class": risk_class,
                "probabilities": probabilities,
                "contributing_indicators": contributing_indicators,
                "model_used": "RandomForest",
                "timestamp": timestamp,
                "note": "Model feature importance (not causal explanation)",
            }

        except Exception as exc:
            logger.error("Prediction failed for %s: %s", link_id, exc)
            return self._heuristic_predict(link_id, link_metrics, timestamp)

    def _heuristic_predict(self, link_id: str, metrics: dict, ts: float) -> dict:
        """
        Simple threshold-based fallback when the ML model is unavailable.
        Clearly labelled as heuristic — not ML inference.
        """
        util = metrics.get("utilization", 0.0)  # 0-1
        pkt_loss = metrics.get("packet_loss", 0.0)
        latency = metrics.get("latency", 10)

        score = util * 0.5 + pkt_loss * 0.3 + min(latency / 100.0, 1.0) * 0.2
        score = max(0.0, min(1.0, score))

        if score < 0.3:
            risk_class = "NORMAL"
        elif score < 0.6:
            risk_class = "CONGESTED"
        else:
            risk_class = "HIGH_RISK"

        return {
            "link_id": link_id,
            "risk_score": round(score, 4),
            "risk_class": risk_class,
            "probabilities": {
                "NORMAL": round(1 - score, 4),
                "CONGESTED": round(score * 0.4, 4),
                "HIGH_RISK": round(score * 0.6, 4),
            },
            "contributing_indicators": [
                {"feature": "Utilization", "importance": 0.5, "value": util, "direction": "↑"},
                {"feature": "Packet Loss", "importance": 0.3, "value": pkt_loss, "direction": "↑"},
                {"feature": "Latency", "importance": 0.2, "value": latency, "direction": "↑"},
            ],
            "model_used": "Heuristic (ML model not loaded)",
            "timestamp": ts,
            "note": "Heuristic prediction — install model for ML inference",
        }

    def predict_all_links(self, links: List[dict]) -> Dict[str, dict]:
        """Predict risk for every active link."""
        results = {}
        for link in links:
            if link.get("status") == "failed":
                continue
            link_id = link.get("id", f"{link['source']}-{link['target']}")
            metrics = {
                "bytes_per_sec": link.get("bytes_per_sec", link.get("bandwidth", 100) * 1000 * link.get("utilization", 0.1)),
                "packets_per_sec": link.get("packets_per_sec", 100),
                "latency": link.get("latency", 10),
                "packet_loss": link.get("packet_loss", 0.0),
                "utilization": link.get("utilization", 0.1),
                "flow_duration": link.get("flow_duration", 5e5),
            }
            results[link_id] = self.predict_link(link_id, metrics)
        return results

    def get_model_info(self) -> dict:
        if self.metadata:
            return {
                "dataset": self.metadata.get("dataset", "CICIDS2017"),
                "training_samples": self.metadata.get("training_samples", 0),
                "test_samples": self.metadata.get("test_samples", 0),
                "total_samples": self.metadata.get("total_samples", 0),
                "features": self.metadata.get("features", []),
                "feature_count": self.metadata.get("feature_count", 0),
                "model": self.metadata.get("model", "RandomForest"),
                "train_test_split": self.metadata.get("train_test_split", "80/20"),
                "accuracy": self.metadata.get("accuracy", 0.0),
                "precision": self.metadata.get("precision", 0.0),
                "recall": self.metadata.get("recall", 0.0),
                "f1_score": self.metadata.get("f1_score", 0.0),
                "feature_importance": self.metadata.get("feature_importance", []),
                "trained_at": self.metadata.get("trained_at", ""),
                "is_loaded": self.is_loaded,
            }
        return {
            "is_loaded": self.is_loaded,
            "model": "Not trained yet",
            "note": "Run ml/train.py to train the model",
        }
