"""
Batch ETL: copies OLTP data (core_banking) into the warehouse (bank_dw: OLAP star
schema + marts). Its column mappings are reused later as lineage.

How the column mappings are reused as lineage
---------------------------------------------
This module holds two parallel descriptions of the same data movement:

1. EXTRACTS and AGGREGATES do the work. They hold the SQL that copies data, e.g.
   `first_name || ' ' || last_name` becomes `dw.dim_customer.full_name`.
2. LINEAGE and DW_LINEAGE only describe the work. They are plain dicts of the form
   `target column -> [source columns]`, e.g.
   `"full_name": ["core.customer.first_name", "core.customer.last_name"]`.

The ETL never reads the second structure. `post_ingestion.py lineage` reads it
afterwards and publishes it to OpenMetadata, so the same knowledge of which source
column feeds which target column is not written a third time somewhere else.

Caveat: LINEAGE is maintained by hand next to the SQL and nothing checks that the
two agree. If an extract changes and the dict is not updated, the catalogue's
lineage is silently wrong. That is acceptable for this POC; in production you would
parse the SQL or use OpenMetadata's lineage ingestion (query logs, views).

How OpenMetadata helps with lineage
-----------------------------------
Lineage is OpenMetadata's record of how data flows between assets: this table was
built from those tables, by this pipeline, down to individual columns. The POC
publishes it in three steps:

1. Register the producer: a pipeline service (`borealis_batch_etl`) and a pipeline
   entity (`nightly_oltp_to_dw`) with one task per target table.
2. Create the edges: for each source/target table pair, `PUT /v1/lineage` records
   "source table -> target table, via this pipeline".
3. Add the column detail: each edge carries `columnsLineage`, a list of
   `{fromColumns: [...], toColumn: ...}`, which makes it column-level. For example
   `core.customer.email` maps to both `dw.dim_customer.email` and
   `mart.marketing_campaign_audience.email`.

What this gives you without more code:
  - Graph in the UI: a table's Lineage tab shows upstream/downstream tables and,
    when expanded, columns.
  - Impact and root-cause analysis: if `core.customer.email` is wrong or changes,
    see every warehouse and mart column it reaches; trace bad mart data to its source.
  - PIPEDA Principle 4.9 (Individual Access): "where did this customer's e-mail end
    up?" is answered by following edges from the source column, including the
    marketing mart where the planted consent bug lives.
  - Tag-based reasoning: PIPEDA.HighRisk / DirectIdentifier tags sit on the same
    columns lineage connects, so you can ask whether a high-risk column leaks into
    an analytical mart.
  - AI/MCP access: `mcp_demo.py` calls the `get_entity_lineage` tool so an assistant
    can answer lineage questions from the catalogue.

See docs/data-model.md ("ETL and lineage") for the diagrams.

Planted defect: the marketing audience extract honours `granted` but ignores
`withdrawn_at`, so customers who withdrew consent are still e-mailed. The
OpenMetadata data-quality suite is expected to catch this.
"""

from __future__ import annotations

import psycopg

from poc import config

EXTRACTS = {
    "dw.dim_branch": (
        """
        SELECT branch_id, transit_number, branch_name, city, province FROM core.branch""",
        ["branch_key", "transit_number", "branch_name", "city", "province"],
    ),
    "dw.dim_customer": (
        """
        SELECT customer_id, customer_id, first_name || ' ' || last_name, email,
               EXTRACT(YEAR FROM date_of_birth)::int,
               CASE WHEN age(date_of_birth) < interval '25 years' THEN '18-24'
                    WHEN age(date_of_birth) < interval '45 years' THEN '25-44'
                    WHEN age(date_of_birth) < interval '65 years' THEN '45-64' ELSE '65+' END,
               province, left(postal_code, 3),
               CASE WHEN annual_income < 50000 THEN '<50k' WHEN annual_income < 100000 THEN '50-100k'
                    WHEN annual_income < 200000 THEN '100-200k' ELSE '200k+' END,
               customer_status, created_at::date, closed_at::date
        FROM core.customer""",
        [
            "customer_key",
            "customer_id",
            "full_name",
            "email",
            "birth_year",
            "age_band",
            "province",
            "postal_fsa",
            "income_band",
            "customer_status",
            "customer_since",
            "closed_on",
        ],
    ),
    "dw.dim_consent": (
        """
        SELECT customer_id, purpose, granted, consent_type, captured_at::date, withdrawn_at::date
        FROM core.customer_consent""",
        ["customer_key", "purpose", "granted", "consent_type", "captured_on", "withdrawn_on"],
    ),
    "dw.dim_account": (
        """
        SELECT account_id, account_id, customer_id, account_number, account_type, account_status, opened_at::date
        FROM core.account""",
        [
            "account_key",
            "account_id",
            "customer_key",
            "account_number",
            "account_type",
            "account_status",
            "opened_on",
        ],
    ),
    "dw.dim_date": (
        """
        SELECT to_char(d, 'YYYYMMDD')::int, d::date, EXTRACT(YEAR FROM d)::int, EXTRACT(QUARTER FROM d)::int,
               EXTRACT(MONTH FROM d)::int, EXTRACT(ISODOW FROM d)::int
        FROM generate_series('2024-01-01'::date, '2026-12-31'::date, interval '1 day') d""",
        ["date_key", "full_date", "year", "quarter", "month", "day_of_week"],
    ),
    "dw.fact_transaction": (
        """
        SELECT t.transaction_id, to_char(t.txn_timestamp, 'YYYYMMDD')::int, t.account_id, a.customer_id, a.branch_id,
               t.amount, t.txn_type, t.channel, t.merchant_category
        FROM core.transaction t JOIN core.account a USING (account_id)""",
        [
            "transaction_key",
            "date_key",
            "account_key",
            "customer_key",
            "branch_key",
            "amount_cad",
            "txn_type",
            "channel",
            "merchant_category",
        ],
    ),
    "mart.marketing_campaign_audience": (
        """
        SELECT c.customer_id, c.first_name || ' ' || c.last_name, c.email,
               CASE WHEN c.annual_income >= 150000 THEN 'PREMIUM' WHEN age(c.date_of_birth) < interval '30 years'
                    THEN 'YOUNG_PROFESSIONAL' ELSE 'MASS_MARKET' END,
               cc.granted, now()
        FROM core.customer c
        JOIN core.customer_consent cc ON cc.customer_id = c.customer_id AND cc.purpose = 'MARKETING_EMAIL'
        WHERE cc.granted AND c.customer_status = 'ACTIVE'      -- BUG: withdrawn_at not checked
        """,
        ["customer_key", "full_name", "email", "segment", "consent_marketing", "extracted_at"],
    ),
    "mart.aml_large_cash_txn": (
        """
        SELECT t.transaction_id, c.customer_id, c.first_name || ' ' || c.last_name, c.date_of_birth, c.occupation,
               t.amount, t.txn_timestamp::date, b.transit_number
        FROM core.transaction t JOIN core.account a USING (account_id)
        JOIN core.customer c ON c.customer_id = a.customer_id JOIN core.branch b ON b.branch_id = a.branch_id
        WHERE t.txn_type = 'CASH_DEPOSIT' AND t.amount >= 10000""",
        [
            "transaction_key",
            "customer_key",
            "full_name",
            "date_of_birth",
            "occupation",
            "amount_cad",
            "txn_date",
            "branch_transit",
        ],
    ),
}

AGGREGATES = {
    "mart.monthly_branch_activity": """
        INSERT INTO mart.monthly_branch_activity
        SELECT d.year, d.month, f.branch_key, count(*), sum(f.amount_cad), count(DISTINCT f.customer_key)
        FROM dw.fact_transaction f JOIN dw.dim_date d USING (date_key)
        GROUP BY d.year, d.month, f.branch_key""",
}

# Column-level lineage published to OpenMetadata: target -> {target_col: [source "schema.table.col", ...]}
LINEAGE = {
    "dw.dim_branch": {
        "branch_key": ["core.branch.branch_id"],
        "transit_number": ["core.branch.transit_number"],
        "branch_name": ["core.branch.branch_name"],
        "city": ["core.branch.city"],
        "province": ["core.branch.province"],
    },
    "dw.dim_customer": {
        "customer_key": ["core.customer.customer_id"],
        "customer_id": ["core.customer.customer_id"],
        "full_name": ["core.customer.first_name", "core.customer.last_name"],
        "email": ["core.customer.email"],
        "birth_year": ["core.customer.date_of_birth"],
        "age_band": ["core.customer.date_of_birth"],
        "province": ["core.customer.province"],
        "postal_fsa": ["core.customer.postal_code"],
        "income_band": ["core.customer.annual_income"],
        "customer_status": ["core.customer.customer_status"],
        "customer_since": ["core.customer.created_at"],
        "closed_on": ["core.customer.closed_at"],
    },
    "dw.dim_consent": {
        "customer_key": ["core.customer_consent.customer_id"],
        "purpose": ["core.customer_consent.purpose"],
        "granted": ["core.customer_consent.granted"],
        "consent_type": ["core.customer_consent.consent_type"],
        "captured_on": ["core.customer_consent.captured_at"],
        "withdrawn_on": ["core.customer_consent.withdrawn_at"],
    },
    "dw.dim_account": {
        "account_key": ["core.account.account_id"],
        "account_id": ["core.account.account_id"],
        "customer_key": ["core.account.customer_id"],
        "account_number": ["core.account.account_number"],
        "account_type": ["core.account.account_type"],
        "account_status": ["core.account.account_status"],
        "opened_on": ["core.account.opened_at"],
    },
    "dw.fact_transaction": {
        "transaction_key": ["core.transaction.transaction_id"],
        "date_key": ["core.transaction.txn_timestamp"],
        "account_key": ["core.transaction.account_id"],
        "customer_key": ["core.account.customer_id"],
        "branch_key": ["core.account.branch_id"],
        "amount_cad": ["core.transaction.amount"],
        "txn_type": ["core.transaction.txn_type"],
        "channel": ["core.transaction.channel"],
        "merchant_category": ["core.transaction.merchant_category"],
    },
    "mart.marketing_campaign_audience": {
        "customer_key": ["core.customer.customer_id"],
        "full_name": ["core.customer.first_name", "core.customer.last_name"],
        "email": ["core.customer.email"],
        "segment": ["core.customer.annual_income", "core.customer.date_of_birth"],
        "consent_marketing": ["core.customer_consent.granted"],
    },
    "mart.aml_large_cash_txn": {
        "transaction_key": ["core.transaction.transaction_id"],
        "customer_key": ["core.customer.customer_id"],
        "full_name": ["core.customer.first_name", "core.customer.last_name"],
        "date_of_birth": ["core.customer.date_of_birth"],
        "occupation": ["core.customer.occupation"],
        "amount_cad": ["core.transaction.amount"],
        "txn_date": ["core.transaction.txn_timestamp"],
        "branch_transit": ["core.branch.transit_number"],
    },
}
# Warehouse-internal lineage (same database)
DW_LINEAGE = {
    "mart.monthly_branch_activity": {
        "branch_key": ["dw.fact_transaction.branch_key"],
        "txn_count": ["dw.fact_transaction.transaction_key"],
        "total_amount_cad": ["dw.fact_transaction.amount_cad"],
        "active_customers": ["dw.fact_transaction.customer_key"],
        "year": ["dw.dim_date.year"],
        "month": ["dw.dim_date.month"],
    },
}


def main() -> None:
    with (
        psycopg.connect(config.dsn("core_banking")) as src,
        psycopg.connect(config.dsn("bank_dw")) as dst,
        dst.cursor() as w,
    ):
        w.execute("TRUNCATE " + ", ".join(list(EXTRACTS) + list(AGGREGATES)))
        for target, (sql, cols) in EXTRACTS.items():
            with src.cursor() as r, w.copy(f"COPY {target} ({', '.join(cols)}) FROM STDIN") as cp:
                r.execute(sql)
                n = 0
                for row in r:
                    cp.write_row(row)
                    n += 1
            print(f"  {target:<36} {n:>7} rows")
        for target, sql in AGGREGATES.items():
            w.execute(sql)
            print(f"  {target:<36} {w.rowcount:>7} rows")
        dst.commit()
        w.execute("ANALYZE")


if __name__ == "__main__":
    main()
