#!/usr/bin/env bash
# Stop the POC and delete ALL of its data (OpenMetadata DB, search index, bank DB, generated files).
# Why: gives a clean slate so the next run re-initializes everything from scratch.
# (The bank DB init scripts only run on an empty data dir, so stale data would skip them.)
# How: exit on any error or unset variable, and run from poc/ whatever the caller's cwd.
set -euo pipefail
cd "$(dirname "$0")/.."
# Stop and remove all containers, including the optional "tools" profile and any
# orphans; -v also deletes the named volumes (e.g. Elasticsearch data).
scripts/dc.sh --profile tools down -v --remove-orphans
# Delete bind-mounted DB data and generated output. Destructive and not recoverable.
rm -rf docker-volume work results
echo "POC reset."
