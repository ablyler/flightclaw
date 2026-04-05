#!/bin/bash
set -e

echo "Installing flightclaw dependencies..."
pip install "fli @ git+https://github.com/punitarani/fli.git" "mcp[cli]"
mkdir -p "$(dirname "$0")/data"
echo "Done. flightclaw is ready to use."
