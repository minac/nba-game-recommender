#!/bin/bash
set -e

cd "$(dirname "$0")"

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "Error: uv not installed. Run: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Sync dependencies
uv sync

echo "Starting NBA Game Recommender..."
echo "Web interface at http://localhost:8080"
echo ""
echo "Other modes:"
echo "  ./run_cli.sh  - Command line interface"
echo "  ./run_api.sh  - API only (no web UI)"
echo ""
uv run python src/interfaces/web/app.py
