"""
ML Training Script — Random Forest Classifier
Part of: ML-Enhanced SDN Emergency Communication Network

Trains a Random Forest on CICIDS2017 (or synthetic data),
evaluates it, and saves the model artefacts.

Usage:
    python -m ml.train
"""
import json
import logging
import os
import time

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
import joblib

from ml.preprocess import (
    load_cicids2017,
    preprocess,
    RISK_CLASSES,
    RISK_TO_SCORE,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "models")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


def train():
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    # ── 1. Load data ───────────────────────────────────────────────────────
    logger.info("Loading dataset from %s ...", DATA_DIR)
    df = load_cicids2017(DATA_DIR)
    logger.info("Total records: %d", len(df))

    # ── 2. Preprocess ──────────────────────────────────────────────────────
    X_train, X_test, y_train, y_test, scaler, le, features = preprocess(df)

    # ── 3. Train Random Forest ─────────────────────────────────────────────
    logger.info("Training Random Forest ...")
    t0 = time.time()
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=5,
        n_jobs=-1,
        random_state=42,
        class_weight="balanced",
    )
    clf.fit(X_train, y_train)
    train_time = time.time() - t0
    logger.info("Training complete in %.2f s", train_time)

    # ── 4. Evaluate ────────────────────────────────────────────────────────
    y_pred = clf.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    recall = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

    report = classification_report(
        y_test, y_pred, target_names=le.classes_, output_dict=True
    )
    cm = confusion_matrix(y_test, y_pred).tolist()

    logger.info("Accuracy:  %.4f", accuracy)
    logger.info("Precision: %.4f", precision)
    logger.info("Recall:    %.4f", recall)
    logger.info("F1 Score:  %.4f", f1)

    # Feature importances
    importances = clf.feature_importances_.tolist()
    feature_importance = sorted(
        zip(features, importances), key=lambda x: x[1], reverse=True
    )

    # ── 5. Save artefacts ──────────────────────────────────────────────────
    model_path = os.path.join(MODEL_DIR, "model.pkl")
    scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
    le_path = os.path.join(MODEL_DIR, "label_encoder.pkl")
    meta_path = os.path.join(MODEL_DIR, "model_metadata.json")

    joblib.dump(clf, model_path)
    joblib.dump(scaler, scaler_path)
    joblib.dump(le, le_path)

    metadata = {
        "dataset": "CICIDS2017 (synthetic fallback if CSV missing)",
        "training_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "total_samples": int(len(X_train) + len(X_test)),
        "features": features,
        "feature_count": len(features),
        "model": "RandomForestClassifier",
        "n_estimators": 100,
        "max_depth": 15,
        "classes": list(le.classes_),
        "train_test_split": "80/20",
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "classification_report": report,
        "confusion_matrix": cm,
        "feature_importance": [
            {"feature": f, "importance": round(imp, 6)}
            for f, imp in feature_importance
        ],
        "train_time_seconds": round(train_time, 2),
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    with open(meta_path, "w") as fh:
        json.dump(metadata, fh, indent=2)

    logger.info("Model saved to %s", model_path)
    logger.info("Metadata saved to %s", meta_path)

    return metadata


if __name__ == "__main__":
    meta = train()
    print("\n=== Training Complete ===")
    print(f"  Accuracy:  {meta['accuracy']:.4f}")
    print(f"  Precision: {meta['precision']:.4f}")
    print(f"  Recall:    {meta['recall']:.4f}")
    print(f"  F1 Score:  {meta['f1_score']:.4f}")
    print(f"  Samples:   {meta['total_samples']:,}")
    print(f"  Model:     {meta['model']}")
