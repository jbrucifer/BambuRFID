#!/bin/bash
# ============================================
#  BambuRFID — Deploy Script
#  Starts the backend server and shows status
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  BambuRFID — Deploy${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

# 1. Check Python
echo -e "${CYAN}[1/4]${NC} Checking Python..."
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python not found. Install Python 3.10+ first.${NC}"
    exit 1
fi
PYTHON=$(command -v python3 || command -v python)
echo "  Using: $($PYTHON --version)"

# 2. Install dependencies
echo -e "${CYAN}[2/4]${NC} Installing Python dependencies..."
$PYTHON -m pip install -r backend/requirements.txt --quiet 2>&1 | tail -1

# 3. Kill any existing server on port 8000
echo -e "${CYAN}[3/4]${NC} Checking port 8000..."
if command -v lsof &> /dev/null; then
    PID=$(lsof -ti:8000 2>/dev/null || true)
elif command -v netstat &> /dev/null; then
    PID=$(netstat -ano 2>/dev/null | grep ":8000 " | grep "LISTENING" | awk '{print $NF}' | head -1)
else
    PID=""
fi

if [ -n "$PID" ]; then
    echo -e "  ${YELLOW}Port 8000 in use (PID: $PID). Stopping...${NC}"
    kill "$PID" 2>/dev/null || taskkill //PID "$PID" //F 2>/dev/null || true
    sleep 2
fi

# 4. Get local IP
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ipconfig 2>/dev/null | grep -oP 'IPv4.*:\s*\K[\d.]+' | head -1 || echo "localhost")

# 5. Start the server
echo -e "${CYAN}[4/4]${NC} Starting BambuRFID server..."
echo ""
$PYTHON -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!
sleep 3

# Check if server started
if kill -0 $SERVER_PID 2>/dev/null; then
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  BambuRFID is running!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo -e "  ${CYAN}Web UI:${NC}       http://localhost:8000"
    echo -e "  ${CYAN}LAN access:${NC}   http://${LOCAL_IP}:8000"
    echo -e "  ${CYAN}NFC Bridge:${NC}   ws://${LOCAL_IP}:8000/ws/nfc"
    echo ""
    echo -e "  ${YELLOW}Android App:${NC}"
    echo -e "    Download APK from GitHub Actions:"
    echo -e "    https://github.com/jbrucifer/BambuRFID/actions"
    echo -e "    Or enter this in the app: ${CYAN}${LOCAL_IP}:8000${NC}"
    echo ""
    echo -e "  Press ${RED}Ctrl+C${NC} to stop the server."
    echo ""

    # Wait for server process
    wait $SERVER_PID
else
    echo -e "${RED}Server failed to start. Check errors above.${NC}"
    exit 1
fi
