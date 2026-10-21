#!/usr/bin/env bash
# Creates the two Borealis Bank databases (OLTP + OLAP warehouse) and the
# service / analyst roles used by the POC. Runs once, on first container start.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-SQL
  CREATE DATABASE core_banking;
  CREATE DATABASE bank_dw;

  -- Read-only principal used by OpenMetadata connectors (metadata, profiler,
  -- auto-classification, data quality). Least privilege: SELECT only.
  CREATE ROLE om_reader LOGIN PASSWORD '${OM_READER_PASSWORD}';
  GRANT pg_read_all_data TO om_reader;
  GRANT pg_read_all_stats TO om_reader;

  -- ETL service account that moves data from OLTP to the warehouse.
  CREATE ROLE etl_service LOGIN PASSWORD '${ETL_PASSWORD}';

  -- Business roles. Their warehouse privileges are NOT granted here: they are
  -- generated from OpenMetadata classifications by poc/toolbox/poc/enforce_from_catalog.py
  CREATE ROLE marketing_analyst LOGIN PASSWORD '${ANALYST_PASSWORD}';
  CREATE ROLE fraud_analyst LOGIN PASSWORD '${ANALYST_PASSWORD}';
SQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname core_banking -f /docker-entrypoint-initdb.d/sql/01_core_banking_oltp.sql
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname bank_dw      -f /docker-entrypoint-initdb.d/sql/02_bank_dw_olap.sql

for db in core_banking bank_dw; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" <<-SQL
    GRANT CONNECT ON DATABASE $db TO om_reader, etl_service;
    DO \$\$
    DECLARE s text;
    BEGIN
      FOR s IN SELECT schema_name FROM information_schema.schemata
               WHERE schema_name NOT IN ('pg_catalog','information_schema','pg_toast','public')
      LOOP
        EXECUTE format('GRANT USAGE ON SCHEMA %I TO etl_service', s);
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA %I TO etl_service', s);
        EXECUTE format('GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA %I TO etl_service', s);
      END LOOP;
    END \$\$;
SQL
done
