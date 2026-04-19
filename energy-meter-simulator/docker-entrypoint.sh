#!/bin/sh
set -e
cd /app/energy-meter-simulator

if [ -n "$SIMULATOR_ID" ]; then
  sed "s/__SIMULATOR_ID__/${SIMULATOR_ID}/g" config/config.yml > config/config.runtime.yml
  exec uv run fred-ops run --config config/config.runtime.yml --script app/main.py
fi

if [ ! -f config/config.yml ]; then
  cp config/config.yml.example config/config.yml
fi
exec uv run fred-ops run --config config/config.yml --script app/main.py
