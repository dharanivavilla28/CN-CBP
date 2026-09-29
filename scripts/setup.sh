#!/bin/bash
# =============================================================================
# Setup Script for ML-Enhanced SDN Emergency Communication Network
# =============================================================================
set -e

echo "=== [1/4] Checking Python & Environment ==="
python3 --version || python --version

echo "=== [2/4] Installing Python Dependencies ==="
pip install fastapi uvicorn scikit-learn pandas numpy joblib websockets requests

echo "=== [3/4] Training ML Model on CICIDS2017 / Network Dataset ==="
cd backend
python3 -m ml.train || python -m ml.train
cd ..

echo "=== [4/4] Installing Frontend Node Dependencies ==="
cd frontend
npm install
npm run build
cd ..

echo "=== Setup Complete! You can now start the network with ./scripts/run.sh ==="
