#!/bin/bash
# BambuNFC Bridge — Termux Setup Script
# Run this inside Termux on your Android phone

echo "============================================"
echo "  BambuNFC Bridge — Termux Setup"
echo "============================================"
echo ""

# Update packages
echo "[1/3] Updating packages..."
pkg update -y

# Install dependencies
echo "[2/3] Installing Python and Termux API..."
pkg install -y python termux-api

# Install Python dependencies
echo "[3/3] Installing Python packages..."
pip install websocket-client

echo ""
echo "============================================"
echo "  Setup Complete!"
echo "============================================"
echo ""
echo "IMPORTANT: Also install the 'Termux:API' app"
echo "from F-Droid (not Play Store) for NFC access."
echo ""
echo "Usage:"
echo "  python nfc_bridge.py <your_pc_ip>:8000"
echo ""
echo "Example:"
echo "  python nfc_bridge.py 192.168.1.197:8000"
echo ""
