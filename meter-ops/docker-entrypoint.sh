#!/bin/sh
# Wait until ener-vault HTTP API is reachable (same URL as app/ener_vault_client.py host).
set -e
url="${ENER_VAULT_HEALTH_URL:-http://ener-vault:8080/health}"
i=0
max=60
while [ "$i" -lt "$max" ]; do
  if python -c "import urllib.request; urllib.request.urlopen('${url}')" >/dev/null 2>&1; then
    exec "$@"
  fi
  i=$((i + 1))
  sleep 2
done
echo "meter-ops: timeout waiting for ener-vault at ${url}" >&2
exit 1
