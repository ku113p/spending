#!/bin/bash

# Get absolute path to script dir
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/spending"
ENV_FILE="$APP_DIR/.env"

# Check that .env exists
if [ ! -f "$ENV_FILE" ]; then
  echo "Error: .env file not found at $ENV_FILE"
  exit 1
fi

# Change to app dir and run
cd "$APP_DIR" || exit 1

# Source the .env file to load environment variables
set -a
# shellcheck source=/dev/null
. "$ENV_FILE"
set +a

# Run the command passed as arguments, or default to python main.py
if [ -z "$1" ]; then
  uv run python main.py
else
  uv run "$@"
fi
