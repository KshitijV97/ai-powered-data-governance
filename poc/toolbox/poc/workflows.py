"""Render OpenMetadata ingestion-framework workflow configs (YAML) for the POC.

The same configs are what the OpenMetadata UI "Agents" generate and schedule
through Airflow; here they are rendered to /work/workflows and executed with
the `metadata` CLI from the official ingestion image (scripts/run_poc.sh).

Data-quality tests are declared here "as code" and mapped to PIPEDA principles.
"""

from __future__ import annotations

import yaml

from poc import config
from poc.om_client import OpenMetadata

SERVICES = {
    config.OLTP_SERVICE: "core_banking",
    config.OLAP_SERVICE: "bank_dw",
}

PII_REGEX_CA_POSTAL = r"^[ABCEGHJ-NPRSTVXY][0-9][ABCEGHJ-NPRSTV-Z] [0-9][ABCEGHJ-NPRSTV-Z][0-9]$"
EMAIL_REGEX = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

# table FQN (without service) -> list of test cases. Each test name starts with the PIPEDA principle.
DATA_QUALITY = {
    "core_banking.core.customer": [
        dict(name="p4_6_accuracy_postal_code_format", columnName="postal_code",
             testDefinitionName="columnValuesToMatchRegex", parameterValues=[{"name": "regex", "value": PII_REGEX_CA_POSTAL}]),
        dict(name="p4_6_accuracy_email_format", columnName="email",
             testDefinitionName="columnValuesToMatchRegex", parameterValues=[{"name": "regex", "value": EMAIL_REGEX}]),
        dict(name="p4_6_accuracy_sin_unique", columnName="sin", testDefinitionName="columnValuesToBeUnique",
             parameterValues=[]),
        dict(name="p4_5_retention_closed_customers_purged", testDefinitionName="tableCustomSQLQuery",
             parameterValues=[{"name": "sqlExpression", "value":
                               "SELECT customer_id FROM core.customer WHERE customer_status = 'CLOSED' "
                               "AND closed_at < now() - interval '7 years'"},
                              {"name": "strategy", "value": "ROWS"}, {"name": "threshold", "value": "0"}]),
    ],
    "core_banking.core.card": [
        dict(name="p4_4_limiting_collection_no_cvv_stored", testDefinitionName="tableCustomSQLQuery",
             parameterValues=[{"name": "sqlExpression", "value": "SELECT card_id FROM core.card WHERE cvv IS NOT NULL"},
                              {"name": "strategy", "value": "ROWS"}, {"name": "threshold", "value": "0"}]),
    ],
    "core_banking.core.customer_consent": [
        dict(name="p4_3_consent_withdrawal_after_capture", testDefinitionName="tableCustomSQLQuery",
             parameterValues=[{"name": "sqlExpression", "value":
                               "SELECT consent_id FROM core.customer_consent WHERE withdrawn_at < captured_at"},
                              {"name": "strategy", "value": "ROWS"}, {"name": "threshold", "value": "0"}]),
        dict(name="p4_3_consent_purpose_not_null", columnName="purpose", testDefinitionName="columnValuesToBeNotNull",
             parameterValues=[]),
    ],
    "bank_dw.mart.marketing_campaign_audience": [
        dict(name="p4_3_consent_marketing_flag_true", columnName="consent_marketing",
             testDefinitionName="columnValuesToBeInSet", parameterValues=[{"name": "allowedValues", "value": "['True']"}]),
        dict(name="p4_3_consent_not_withdrawn", testDefinitionName="tableCustomSQLQuery",
             parameterValues=[{"name": "sqlExpression", "value":
                               "SELECT a.customer_key FROM mart.marketing_campaign_audience a "
                               "JOIN dw.dim_consent c ON c.customer_key = a.customer_key AND c.purpose = 'MARKETING_EMAIL' "
                               "WHERE NOT c.granted OR c.withdrawn_on IS NOT NULL"},
                              {"name": "strategy", "value": "ROWS"}, {"name": "threshold", "value": "0"}]),
    ],
    "bank_dw.dw.dim_customer": [
        dict(name="p4_4_minimisation_no_full_postal_code", columnName="postal_fsa",
             testDefinitionName="columnValueLengthsToBeBetween",
             parameterValues=[{"name": "minLength", "value": "3"}, {"name": "maxLength", "value": "3"}]),
        dict(name="p4_5_retention_closed_customers_purged", testDefinitionName="tableCustomSQLQuery",
             parameterValues=[{"name": "sqlExpression", "value":
                               "SELECT customer_key FROM dw.dim_customer WHERE closed_on < current_date - interval '7 years'"},
                              {"name": "strategy", "value": "ROWS"}, {"name": "threshold", "value": "0"}]),
    ],
    "bank_dw.mart.aml_large_cash_txn": [
        dict(name="fintrac_lctr_min_amount", testDefinitionName="tableCustomSQLQuery",
             parameterValues=[{"name": "sqlExpression", "value":
                               "SELECT transaction_key FROM mart.aml_large_cash_txn WHERE amount_cad < 10000"},
                              {"name": "strategy", "value": "ROWS"}, {"name": "threshold", "value": "0"}]),
    ],
}


def _server_config(token: str) -> dict:
    return {"openMetadataServerConfig": {"hostPort": config.OM_API, "authProvider": "openmetadata",
                                         "securityConfig": {"jwtToken": token}},
            "loggerLevel": "INFO"}


def _connection(database: str) -> dict:
    return {"config": {"type": "Postgres", "username": "om_reader",
                       "authType": {"password": config.OM_READER_PASSWORD},
                       "hostPort": f"{config.BANK_DB_HOST}:{config.BANK_DB_PORT}", "database": database,
                       "ingestAllDatabases": False}}


SCHEMA_FILTER = {"excludes": ["^information_schema$", "^pg_catalog$", "^public$", "^pg_toast$"]}


def render(token: str) -> list[str]:
    out_dir = config.WORK_DIR / "workflows"
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []

    def dump(name: str, cfg: dict):
        p = out_dir / f"{name}.yaml"
        p.write_text(yaml.safe_dump(cfg, sort_keys=False))
        written.append(str(p))

    for svc, db in SERVICES.items():
        base = {"type": "postgres", "serviceName": svc, "serviceConnection": _connection(db)}
        dump(f"{svc}__metadata", {
            "source": {**base, "sourceConfig": {"config": {
                "type": "DatabaseMetadata", "schemaFilterPattern": SCHEMA_FILTER, "includeViews": True,
                "markDeletedTables": True, "includeTags": True}}},
            "sink": {"type": "metadata-rest", "config": {}}, "workflowConfig": _server_config(token)})
        dump(f"{svc}__autoclassification", {
            "source": {**base, "sourceConfig": {"config": {
                "type": "AutoClassification", "schemaFilterPattern": SCHEMA_FILTER,
                "storeSampleData": True, "enableAutoClassification": True, "confidence": 60,
                "sampleDataCount": 50, "classificationLanguage": "en"}}},
            "processor": {"type": "tag-pii-processor", "config": {}},
            "sink": {"type": "metadata-rest", "config": {}}, "workflowConfig": _server_config(token)})
        dump(f"{svc}__profiler", {
            "source": {**base, "sourceConfig": {"config": {
                "type": "Profiler", "schemaFilterPattern": SCHEMA_FILTER,
                "computeTableMetrics": True, "computeColumnMetrics": True}}},
            "processor": {"type": "orm-profiler", "config": {}},
            "sink": {"type": "metadata-rest", "config": {}}, "workflowConfig": _server_config(token)})

    for table, tests in DATA_QUALITY.items():
        db = table.split(".")[0]
        svc = next(s for s, d in SERVICES.items() if d == db)
        dump(f"dq__{table.replace('.', '_')}", {
            "source": {"type": "postgres", "serviceName": svc, "serviceConnection": _connection(db),
                       "sourceConfig": {"config": {"type": "TestSuite",
                                                   "entityFullyQualifiedName": f"{svc}.{table}"}}},
            "processor": {"type": "orm-test-runner", "config": {"forceUpdate": True, "testCases": tests}},
            "sink": {"type": "metadata-rest", "config": {}}, "workflowConfig": _server_config(token)})
    return written


def main() -> None:
    OpenMetadata.wait_until_ready()
    token = OpenMetadata.login().bot_token("ingestion-bot")
    for p in render(token):
        print("  rendered", p)


if __name__ == "__main__":
    main()
