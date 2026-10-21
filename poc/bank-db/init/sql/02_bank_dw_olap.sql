-- =====================================================================
-- Borealis Bank of Canada (FICTIONAL) - analytical warehouse (OLAP)
-- Kimball-style star schema loaded from core_banking by etl_to_dw.py
-- =====================================================================

CREATE SCHEMA dw;        -- conformed dimensions and facts
CREATE SCHEMA mart;      -- purpose-specific data marts
CREATE SCHEMA governed;  -- masked views generated from OpenMetadata tags

CREATE TABLE dw.dim_date (
    date_key        INT PRIMARY KEY,           -- yyyymmdd
    full_date       DATE NOT NULL,
    year            SMALLINT NOT NULL,
    quarter         SMALLINT NOT NULL,
    month           SMALLINT NOT NULL,
    day_of_week     SMALLINT NOT NULL
);

CREATE TABLE dw.dim_branch (
    branch_key      INT PRIMARY KEY,
    transit_number  CHAR(5) NOT NULL,
    branch_name     VARCHAR(80) NOT NULL,
    city            VARCHAR(60) NOT NULL,
    province        CHAR(2) NOT NULL
);

-- Customer dimension. Note the deliberate mix: some PI is minimised
-- (birth_year, postal_fsa), some is copied verbatim (full_name, email)
-- to support the "Customer 360" use case.
CREATE TABLE dw.dim_customer (
    customer_key    BIGINT PRIMARY KEY,
    customer_id     BIGINT NOT NULL,
    full_name       VARCHAR(130),
    email           VARCHAR(120),
    birth_year      SMALLINT,
    age_band        VARCHAR(10),
    province        CHAR(2),
    postal_fsa      CHAR(3),                    -- forward sortation area only
    income_band     VARCHAR(20),
    customer_status VARCHAR(10),
    customer_since  DATE,
    closed_on       DATE
);

-- Replica of consent state, needed so marts can be checked against it.
CREATE TABLE dw.dim_consent (
    customer_key    BIGINT NOT NULL,
    purpose         VARCHAR(40) NOT NULL,
    granted         BOOLEAN NOT NULL,
    consent_type    VARCHAR(10) NOT NULL,
    captured_on     DATE NOT NULL,
    withdrawn_on    DATE,
    PRIMARY KEY (customer_key, purpose)
);

CREATE TABLE dw.dim_account (
    account_key     BIGINT PRIMARY KEY,
    account_id      BIGINT NOT NULL,
    customer_key    BIGINT NOT NULL,
    account_number  VARCHAR(12) NOT NULL,
    account_type    VARCHAR(20) NOT NULL,
    account_status  VARCHAR(10) NOT NULL,
    opened_on       DATE NOT NULL
);

CREATE TABLE dw.fact_transaction (
    transaction_key BIGINT PRIMARY KEY,
    date_key        INT NOT NULL,
    account_key     BIGINT NOT NULL,
    customer_key    BIGINT NOT NULL,
    branch_key      INT NOT NULL,
    amount_cad      NUMERIC(14,2) NOT NULL,
    txn_type        VARCHAR(20) NOT NULL,
    channel         VARCHAR(20) NOT NULL,
    merchant_category VARCHAR(40)
);

-- Monthly aggregate used by finance dashboards (should be non-personal).
CREATE TABLE mart.monthly_branch_activity (
    year            SMALLINT NOT NULL,
    month           SMALLINT NOT NULL,
    branch_key      INT NOT NULL,
    txn_count       INT NOT NULL,
    total_amount_cad NUMERIC(16,2) NOT NULL,
    active_customers INT NOT NULL,
    PRIMARY KEY (year, month, branch_key)
);

-- Marketing audience. PIPEDA 4.3: every row must have express consent
-- for MARKETING_EMAIL. A data-quality test in OpenMetadata checks this.
CREATE TABLE mart.marketing_campaign_audience (
    customer_key    BIGINT PRIMARY KEY,
    full_name       VARCHAR(130),
    email           VARCHAR(120),
    segment         VARCHAR(30) NOT NULL,
    consent_marketing BOOLEAN NOT NULL,
    extracted_at    TIMESTAMP NOT NULL
);

-- FINTRAC large cash transaction candidates (>= CAD 10,000 in cash).
CREATE TABLE mart.aml_large_cash_txn (
    transaction_key BIGINT PRIMARY KEY,
    customer_key    BIGINT NOT NULL,
    full_name       VARCHAR(130),
    date_of_birth   DATE,
    occupation      VARCHAR(80),
    amount_cad      NUMERIC(14,2) NOT NULL,
    txn_date        DATE NOT NULL,
    branch_transit  CHAR(5) NOT NULL
);
