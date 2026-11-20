#!/usr/bin/env bash
# docker compose wrapper: official OpenMetadata 2.0.5 stack + POC overlay.
# Run from poc/ regardless of where the script is invoked from.
cd "$(dirname "$0")/.." || exit 1
# Replace this shell with docker compose, layering the POC overlay on the base
# OpenMetadata file and forwarding all CLI args (e.g. up -d, down, logs).
exec docker compose --project-directory . \
  -f openmetadata/docker-compose-openmetadata-postgres.yml \
  -f docker-compose.poc.yml "$@"
