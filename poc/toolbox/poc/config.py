"""Shared configuration for the POC toolbox (read from environment / .env)."""

import os
from pathlib import Path

# Every value below is read from an environment variable. Inside the Docker
# toolbox container those come from poc/.env (loaded via `env_file` in
# docker-compose.poc.yml); a few are overridden in the compose `environment:`
# block. If a variable is unset, the default after the comma is used.

# --- Synthetic data generation -------------------------------------------
# Random seed for the data generator. Fixed so every run produces identical
# data, which makes the POC results reproducible (5301 = the course number).
SEED = int(os.getenv("POC_SEED", "5301"))
# How many fictional customers to generate. 1500 is big enough for realistic
# PII/classification results yet loads in seconds on a laptop.
N_CUSTOMERS = int(os.getenv("POC_CUSTOMERS", "1500"))

# --- Bank Postgres database (the fictional "Borealis" bank) ---------------
# Hostname of the Postgres container. "bank-db" is its service name in
# docker-compose, which Docker's internal DNS resolves; compose also sets it
# explicitly. Use "localhost" if running scripts outside Docker.
BANK_DB_HOST = os.getenv("BANK_DB_HOST", "bank-db")
# Postgres's standard port (inside the Docker network, no remapping needed).
BANK_DB_PORT = int(os.getenv("BANK_DB_PORT", "5432"))
# Superuser used to create schemas/roles and load data. "postgres" is the
# image's built-in superuser. Not set in .env, so this default is always used.
BANK_DB_ADMIN_USER = os.getenv("BANK_DB_ADMIN_USER", "postgres")
# Password for the admin user (from .env). "change-me" is a deliberately
# obvious placeholder so a missing .env fails loudly instead of using a real
# secret; .env.example sets a local-only value.
BANK_DB_ADMIN_PASSWORD = os.getenv("BANK_DB_ADMIN_PASSWORD", "change-me")
# Password of the read-only role OpenMetadata uses to scan the databases
# (from .env). Same placeholder default as above.
OM_READER_PASSWORD = os.getenv("OM_READER_PASSWORD", "change-me")
# Password of the analyst role(s) used to demo access enforcement (from .env).
# Same placeholder default as above.
ANALYST_PASSWORD = os.getenv("ANALYST_PASSWORD", "change-me")

# --- OpenMetadata ---------------------------------------------------------
# Base URL of the OpenMetadata server. Default is its compose service name and
# port 8585 (the UI/API port); compose sets this explicitly for the toolbox.
OM_HOST = os.getenv("OM_HOST", "http://openmetadata-server:8585")
# REST API root derived from OM_HOST (not an env var itself).
OM_API = OM_HOST + "/api"
# Login of OpenMetadata's built-in admin (from .env). Defaults are the
# quickstart image's out-of-the-box credentials, so they work with no setup.
OM_ADMIN_EMAIL = os.getenv("OM_ADMIN_EMAIL", "admin@open-metadata.org")
OM_ADMIN_PASSWORD = os.getenv("OM_ADMIN_PASSWORD", "admin")

# Names of the two database services registered in OpenMetadata
OLTP_SERVICE = "borealis_core_banking_oltp"
OLAP_SERVICE = "borealis_enterprise_dw_olap"

# Scratch directory for intermediate files. Default "/work" is where compose
# mounts ./work into the toolbox container (git-ignored). Not set in .env.
WORK_DIR = Path(os.getenv("POC_WORK_DIR", "/work"))
# Where final outputs/evidence are written. Default "/results" is where compose
# mounts ./results into the container, so they appear on the host. Not set in .env.
RESULTS_DIR = Path(os.getenv("POC_RESULTS_DIR", "/results"))


def dsn(database: str, user: str | None = None, password: str | None = None) -> str:
    """Build a libpq connection string for the bank Postgres server.

    Pass it to psycopg.connect(). `database` is required (e.g. "core_banking"
    for the OLTP db, "bank_dw" for the warehouse). `user`/`password` default to
    the admin account; callers pass a role and ANALYST_PASSWORD to connect as
    an analyst instead. Host and port always come from the module settings.
    """
    return (
        f"host={BANK_DB_HOST} port={BANK_DB_PORT} dbname={database} "
        f"user={user or BANK_DB_ADMIN_USER} password={password or BANK_DB_ADMIN_PASSWORD}"
    )
