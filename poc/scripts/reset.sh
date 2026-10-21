#!/usr/bin/env bash
# Stop the POC and delete ALL of its data (OpenMetadata DB, search index, bank DB, generated files).
set -euo pipefail
cd "$(dirname "$0")/.."
scripts/dc.sh --profile tools down -v --remove-orphans
rm -rf docker-volume work results
echo "POC reset."
