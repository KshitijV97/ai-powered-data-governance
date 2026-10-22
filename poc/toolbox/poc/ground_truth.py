"""Ground-truth sensitivity labels for every column in the synthetic bank.

Because the data is generated, we know exactly which columns hold personal
information (PI). This lets us measure the precision / recall of
OpenMetadata's AI auto-classification instead of judging it by eye.

Labels (Borealis Bank PIPEDA sensitivity scheme, see governance_model.py):
  H  high-risk identifier  - SIN, card PAN, CVV, government ID, account number
  D  direct identifier     - name, e-mail, phone, street address, full postal code,
                             date of birth, IP address, free text containing PI
  Q  quasi-identifier      - city, province, FSA, birth year, age band, occupation
  F  financial             - balances, income, amounts (PI when linked to a person)
  N  not personal          - keys, codes, timestamps, reference data

Positive class for detection metrics = H or D (what a PII scanner should flag).
"""

H, D, Q, F, N = "H", "D", "Q", "F", "N"

_OLTP = {
    "core.branch": dict(branch_id=N, transit_number=N, branch_name=N, city=N, province=N),
    "core.customer": dict(
        customer_id=N,
        first_name=D,
        last_name=D,
        date_of_birth=D,
        sin=H,
        email=D,
        phone_number=D,
        street_address=D,
        city=Q,
        province=Q,
        postal_code=D,
        occupation=Q,
        annual_income=F,
        preferred_language=Q,
        customer_status=N,
        created_at=N,
        closed_at=N,
    ),
    "core.customer_consent": dict(
        consent_id=N,
        customer_id=N,
        purpose=N,
        granted=N,
        consent_type=N,
        capture_channel=N,
        captured_at=N,
        withdrawn_at=N,
    ),
    "core.account": dict(
        account_id=N,
        customer_id=N,
        branch_id=N,
        account_number=H,
        account_type=N,
        currency=N,
        current_balance=F,
        account_status=N,
        opened_at=N,
        closed_at=N,
    ),
    "core.card": dict(
        card_id=N, account_id=N, card_number=H, expiry_month=N, expiry_year=N, cvv=H, card_status=N
    ),
    "core.transaction": dict(
        transaction_id=N,
        account_id=N,
        txn_timestamp=N,
        amount=F,
        txn_type=N,
        channel=N,
        merchant_name=N,
        merchant_category=N,
        counterparty_email=D,
        client_ip=D,
        memo=N,
    ),
    "kyc.identity_document": dict(
        document_id=N,
        customer_id=N,
        document_type=N,
        document_number=H,
        issuing_jurisdiction=N,
        expiry_date=N,
        verified_at=N,
        verified_by_employee=N,
    ),
    "ops.support_ticket": dict(ticket_id=N, customer_id=N, opened_at=N, category=N, agent_notes=D),
    "ops.legacy_member_import": dict(
        import_row_id=N, fld_01=D, fld_02=H, fld_03=D, fld_04=N, imported_at=N
    ),
    "ops.fx_rate": dict(rate_date=N, currency_pair=N, rate=N),
}

_OLAP = {
    "dw.dim_date": dict(date_key=N, full_date=N, year=N, quarter=N, month=N, day_of_week=N),
    "dw.dim_branch": dict(branch_key=N, transit_number=N, branch_name=N, city=N, province=N),
    "dw.dim_customer": dict(
        customer_key=N,
        customer_id=N,
        full_name=D,
        email=D,
        birth_year=Q,
        age_band=Q,
        province=Q,
        postal_fsa=Q,
        income_band=Q,
        customer_status=N,
        customer_since=N,
        closed_on=N,
    ),
    "dw.dim_consent": dict(
        customer_key=N, purpose=N, granted=N, consent_type=N, captured_on=N, withdrawn_on=N
    ),
    "dw.dim_account": dict(
        account_key=N,
        account_id=N,
        customer_key=N,
        account_number=H,
        account_type=N,
        account_status=N,
        opened_on=N,
    ),
    "dw.fact_transaction": dict(
        transaction_key=N,
        date_key=N,
        account_key=N,
        customer_key=N,
        branch_key=N,
        amount_cad=F,
        txn_type=N,
        channel=N,
        merchant_category=N,
    ),
    "mart.monthly_branch_activity": dict(
        year=N, month=N, branch_key=N, txn_count=N, total_amount_cad=N, active_customers=N
    ),
    "mart.marketing_campaign_audience": dict(
        customer_key=N, full_name=D, email=D, segment=N, consent_marketing=N, extracted_at=N
    ),
    "mart.aml_large_cash_txn": dict(
        transaction_key=N,
        customer_key=N,
        full_name=D,
        date_of_birth=D,
        occupation=Q,
        amount_cad=F,
        txn_date=N,
        branch_transit=N,
    ),
}

DATABASES = {"core_banking": _OLTP, "bank_dw": _OLAP}


def labels() -> dict[tuple[str, str, str, str], str]:
    """{(database, schema, table, column): label}"""
    out = {}
    for db, tables in DATABASES.items():
        for st, cols in tables.items():
            schema, table = st.split(".")
            for col, lab in cols.items():
                out[(db, schema, table, col)] = lab
    return out


def is_positive(label: str) -> bool:
    return label in (H, D)
