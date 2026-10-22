"""Shared configuration for the POC toolbox (read from environment / .env)."""

import os
from pathlib import Path

SEED = int(os.getenv("POC_SEED", "5301"))
N_CUSTOMERS = int(os.getenv("POC_CUSTOMERS", "1500"))

BANK_DB_HOST = os.getenv("BANK_DB_HOST", "bank-db")
BANK_DB_PORT = int(os.getenv("BANK_DB_PORT", "5432"))
BANK_DB_ADMIN_USER = os.getenv("BANK_DB_ADMIN_USER", "postgres")
BANK_DB_ADMIN_PASSWORD = os.getenv("BANK_DB_ADMIN_PASSWORD", "change-me")
OM_READER_PASSWORD = os.getenv("OM_READER_PASSWORD", "change-me")
ANALYST_PASSWORD = os.getenv("ANALYST_PASSWORD", "change-me")

OM_HOST = os.getenv("OM_HOST", "http://openmetadata-server:8585")
OM_API = OM_HOST + "/api"
OM_ADMIN_EMAIL = os.getenv("OM_ADMIN_EMAIL", "admin@open-metadata.org")
OM_ADMIN_PASSWORD = os.getenv("OM_ADMIN_PASSWORD", "admin")

# Names of the two database services registered in OpenMetadata
OLTP_SERVICE = "borealis_core_banking_oltp"
OLAP_SERVICE = "borealis_enterprise_dw_olap"

WORK_DIR = Path(os.getenv("POC_WORK_DIR", "/work"))  # mounted volume, git-ignored
RESULTS_DIR = Path(os.getenv("POC_RESULTS_DIR", "/results"))


def dsn(database: str, user: str | None = None, password: str | None = None) -> str:
    return (
        f"host={BANK_DB_HOST} port={BANK_DB_PORT} dbname={database} "
        f"user={user or BANK_DB_ADMIN_USER} password={password or BANK_DB_ADMIN_PASSWORD}"
    )
