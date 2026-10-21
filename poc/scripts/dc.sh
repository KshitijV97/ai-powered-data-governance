#!/usr/bin/env bash
# docker compose wrapper: official OpenMetadata 2.0.5 stack + POC overlay.
cd "$(dirname "$0")/.." || exit 1
exec docker compose --project-directory . \
  -f openmetadata/docker-compose-openmetadata-postgres.yml \
  -f docker-compose.poc.yml "$@"
