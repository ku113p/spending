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
dotenv -f ".env" run -- python main.py
