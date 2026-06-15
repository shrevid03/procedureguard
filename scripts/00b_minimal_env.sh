#!/usr/bin/env bash
set -euo pipefail
RG="rg-procedureguard"

echo ">> Finding AI Search service..."
SEARCH="$(az search service list -g "$RG" --query "[0].name" -o tsv)"
SEARCH_KEY="$(az search admin-key show -g "$RG" --service-name "$SEARCH" --query primaryKey -o tsv)"
echo "   $SEARCH"

echo ">> Finding the Storage account that holds the 'sop-docs' container..."
STORAGE=""; STORAGE_KEY=""
for s in $(az storage account list -g "$RG" --query "[].name" -o tsv); do
  key="$(az storage account keys list -g "$RG" -n "$s" --query '[0].value' -o tsv)"
  if az storage container show --name sop-docs --account-name "$s" --account-key "$key" -o none 2>/dev/null; then
    STORAGE="$s"; STORAGE_KEY="$key"; break
  fi
done

if [ -z "$STORAGE" ]; then
  STORAGE="$(az storage account list -g "$RG" --query "[?starts_with(name,'stpguard')]|[0].name" -o tsv)"
  STORAGE_KEY="$(az storage account keys list -g "$RG" -n "$STORAGE" --query '[0].value' -o tsv)"
  az storage container create --name sop-docs --account-name "$STORAGE" --account-key "$STORAGE_KEY" -o none
fi
echo "   $STORAGE"

STORAGE_CONN="$(az storage account show-connection-string -g "$RG" -n "$STORAGE" -o tsv)"

cat > .env <<EOF
STORAGE_CONNECTION_STRING=$STORAGE_CONN
STORAGE_CONTAINER=sop-docs
SEARCH_ENDPOINT=https://$SEARCH.search.windows.net
SEARCH_ADMIN_KEY=$SEARCH_KEY
SEARCH_INDEX_NAME=procedureguard-sop-text
SEARCH_API_VERSION=2024-07-01
EOF

echo ""
echo "[ok] wrote .env  ->  storage=$STORAGE  search=$SEARCH"
