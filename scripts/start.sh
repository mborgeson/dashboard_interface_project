#!/bin/bash
# =============================================================================
# B&R Capital Dashboard - Development Startup Script
# =============================================================================
# Starts both backend (FastAPI) and frontend (Vite) servers
# Usage: ./scripts/start.sh
# =============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================"
echo "B&R Capital Dashboard - Starting..."
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup function to kill background processes on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down servers...${NC}"
    kill $(jobs -p) 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# Initialize conda for script use (miniconda3)
CONDA_PATH="$HOME/miniconda3"
if [ -f "$CONDA_PATH/etc/profile.d/conda.sh" ]; then
    source "$CONDA_PATH/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
else
    echo -e "${RED}Error: Could not find conda installation${NC}"
    exit 1
fi

# Activate conda environment
echo -e "${GREEN}Activating conda environment: dashboard-backend${NC}"
conda activate dashboard-backend

# Check if PostgreSQL is accessible (optional check)
if command -v pg_isready &> /dev/null; then
    if pg_isready -q 2>/dev/null; then
        echo -e "${GREEN}PostgreSQL: Connected${NC}"
    else
        echo -e "${YELLOW}PostgreSQL: Not running (backend may fail)${NC}"
    fi
fi

# Start backend
echo -e "${GREEN}Starting Backend (FastAPI) on port 8000...${NC}"
cd "$PROJECT_ROOT/backend"
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start frontend
echo -e "${GREEN}Starting Frontend (Vite) on port 5173...${NC}"
cd "$PROJECT_ROOT"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo -e "${GREEN}Servers running:${NC}"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/api/docs"
echo "  Frontend: http://localhost:5173"
echo "========================================"
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"
echo ""

# Wait for both processes
wait
