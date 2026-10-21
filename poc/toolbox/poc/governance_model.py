"""Borealis Bank PIPEDA governance model, expressed as OpenMetadata entities.

Mapping to the ten PIPEDA fair information principles (Schedule 1, CSA Q830):
  4.1 Accountability        -> Privacy Office team, Chief Privacy Officer owns classifications/glossary
  4.2 Identifying purposes  -> PIPEDAPurpose tags on tables, glossary terms
  4.3 Consent               -> consent data-quality tests on marketing mart
  4.4 Limiting collection   -> HighRisk/DirectIdentifier inventory exposes over-collection (e.g. CVV)
  4.5 Limiting use, retention -> table retentionPeriod + retention data-quality tests
  4.6 Accuracy              -> format / validity data-quality tests
  4.7 Safeguards            -> tag-based access policies, masked views generated from the catalogue
  4.8 Openness              -> business glossary published in the catalogue
  4.9 Individual access     -> column-level lineage + PI inventory to locate a person's data
  4.10 Challenging compliance -> recognizer feedback + approval workflow, audit trail
"""

PIPEDA_CLASSIFICATION = "PIPEDA"
PURPOSE_CLASSIFICATION = "PIPEDAPurpose"

# ---------------------------------------------------------------- recognizers
def _pattern(name, regex, score, context=(), target="content", threshold=0.6, desc=""):
    return {
        "name": name, "displayName": name.replace("_", " ").title(), "description": desc or name,
        "enabled": True, "target": target, "confidenceThreshold": threshold,
        "recognizerConfig": {
            "type": "pattern", "supportedLanguage": "en",
            "patterns": [{"name": f"{name}_p", "regex": regex, "score": score}],
            "regexFlags": {"dotAll": False, "multiline": False, "ignoreCase": target == "column_name"},
            "context": list(context),
        },
    }


def _predefined(name, cls, entities=None, context=()):
    cfg = {"type": "predefined", "name": cls, "supportedLanguage": "en", "context": list(context)}
    if entities:
        cfg["supportedEntities"] = entities
    return {"name": name, "displayName": name, "description": f"Presidio {cls}", "enabled": True,
            "target": "content", "confidenceThreshold": 0.6, "recognizerConfig": cfg}


# Canadian postal code: no D, F, I, O, Q, U anywhere; no W or Z in first position.
CA_POSTAL = r"\b[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z][ -]?\d[ABCEGHJ-NPRSTV-Z]\d\b"

PIPEDA_TAGS = [
    {
        "name": "HighRisk",
        "displayName": "High-risk identifier",
        "description": "Identifiers whose compromise creates a real risk of significant harm (identity theft, "
                       "financial fraud): Social Insurance Number, payment card number, CVV, government ID, "
                       "bank account number. Need-to-know access only; never copied to analytical marts.",
        "autoClassificationEnabled": True, "autoClassificationPriority": 100,
        "style": {"color": "#B42318"},
        "recognizers": [
            _pattern("ca_sin_formatted", r"\b[1-79]\d{2}[- ]\d{3}[- ]\d{3}\b", 0.7,
                     context=["sin", "social", "insurance", "nas"],
                     desc="Canadian Social Insurance Number written NNN-NNN-NNN or NNN NNN NNN"),
            _pattern("ca_sin_unformatted", r"\b[1-79]\d{8}\b", 0.3,
                     context=["sin", "social", "insurance", "nas"],
                     desc="9-digit SIN without separators; weak on its own, boosted by column-name context"),
            _pattern("ca_sin_column_name",
                     r"^(sin|sin_?(no|num|number)|social_?insurance(_?(no|num|number))?|nas)$", 0.9,
                     target="column_name", desc="Column named like a SIN"),
            _predefined("payment_card_pan", "CreditCardRecognizer"),
            _pattern("card_column_name", r"^(cvv2?|cvc|csc|card_?(number|no|num)|pan)$", 0.9,
                     target="column_name", desc="Payment-card columns"),
            _pattern("ca_account_number_column_name",
                     r"^(account_?(number|no|num)|acct_?(no|num|number))$", 0.8, target="column_name",
                     desc="Bank account number columns"),
            _pattern("ca_drivers_licence_on", r"\b[A-Z]\d{4}-\d{5}-\d{5}\b", 0.75,
                     desc="Ontario driver's licence number format"),
            _pattern("ca_passport", r"\b[A-Z]{2}\d{6}\b", 0.4, context=["passport", "document"],
                     desc="Canadian passport number format (2 letters + 6 digits)"),
            _pattern("gov_id_column_name", r"(passport|licen[cs]e_?(no|num|number)|document_?number|gov(ernment)?_?id)",
                     0.85, target="column_name", desc="Government ID columns"),
        ],
    },
    {
        "name": "DirectIdentifier",
        "displayName": "Direct identifier",
        "description": "Information that directly identifies or contacts an individual: name, e-mail, phone, "
                       "street address, full postal code, date of birth, IP address, free text containing these.",
        "autoClassificationEnabled": True, "autoClassificationPriority": 80,
        "style": {"color": "#DC6803"},
        "recognizers": [
            _predefined("email_address", "EmailRecognizer"),
            _predefined("phone_number", "PhoneRecognizer", context=["phone", "tel", "mobile"]),
            _predefined("ip_address", "IpRecognizer"),
            _predefined("person_name_ner", "SpacyRecognizer", entities=["PERSON"]),
            _pattern("ca_postal_code", CA_POSTAL, 0.75, context=["postal", "code", "address"],
                     desc="Full Canadian postal code (A1A 1A1)"),
            _pattern("direct_identifier_column_name",
                     r"(first_?name|last_?name|full_?name|surname|given_?name|e_?mail|phone|mobile|street|"
                     r"address|postal_?code|zip|date_of_birth|dob|birth_?date)", 0.85, target="column_name",
                     desc="Columns named like a direct identifier"),
        ],
    },
    {
        "name": "QuasiIdentifier",
        "displayName": "Quasi-identifier",
        "description": "Not identifying alone, but can re-identify a person when combined "
                       "(city, province, FSA, birth year, age band, occupation, language).",
        "autoClassificationEnabled": True, "autoClassificationPriority": 50,
        "style": {"color": "#CA8504"},
        "recognizers": [
            _pattern("quasi_identifier_column_name",
                     r"^(city|province|postal_fsa|fsa|birth_year|age_band|occupation|gender|preferred_language|"
                     r"income_band)$", 0.7, target="column_name"),
        ],
    },
    {
        "name": "Financial",
        "displayName": "Financial information",
        "description": "Balances, income and transaction amounts. Personal information when linked to an "
                       "identifiable customer; generally considered sensitive by the OPC.",
        "autoClassificationEnabled": True, "autoClassificationPriority": 40,
        "style": {"color": "#1570EF"},
        "recognizers": [
            _pattern("financial_column_name", r"(balance|income|salary|amount|credit_?score)", 0.7,
                     target="column_name"),
        ],
    },
    {
        "name": "NonPersonal",
        "displayName": "Not personal information",
        "description": "Reviewed and confirmed not to be personal information.",
        "autoClassificationEnabled": False, "style": {"color": "#079455"},
    },
]

PURPOSE_TAGS = [
    ("AccountServicing", "Providing and administering the banking products the customer requested."),
    ("RegulatoryReporting", "Mandatory reporting, e.g. FINTRAC large cash transaction reports (PCMLTFA)."),
    ("FraudPrevention", "Detecting and preventing fraud and money laundering."),
    ("Marketing", "Direct marketing. Requires express, withdrawable consent (PIPEDA 4.3)."),
    ("Analytics", "Internal aggregate analytics and reporting on de-identified or aggregated data."),
]

# ---------------------------------------------------------------- glossary
GLOSSARY = {
    "name": "PIPEDAGlossary",
    "displayName": "PIPEDA & Privacy Glossary",
    "description": "Business vocabulary for the Personal Information Protection and Electronic Documents Act "
                   "(S.C. 2000, c. 5) and its Schedule 1 fair information principles, as applied at Borealis Bank.",
}
GLOSSARY_TERMS = [
    ("PersonalInformation", "Personal information", "Information about an identifiable individual (PIPEDA s. 2(1))."),
    ("Accountability", "4.1 Accountability", "An organization is responsible for personal information under its "
     "control and must designate an individual accountable for compliance."),
    ("IdentifyingPurposes", "4.2 Identifying purposes", "Purposes for collection are identified at or before collection."),
    ("Consent", "4.3 Consent", "Knowledge and consent of the individual are required for collection, use or "
     "disclosure, except where inappropriate. Consent must be meaningful and may be withdrawn."),
    ("LimitingCollection", "4.4 Limiting collection", "Collection is limited to what is necessary for identified purposes."),
    ("LimitingUseDisclosureRetention", "4.5 Limiting use, disclosure and retention", "PI is used only for the "
     "purposes collected and retained only as long as necessary; then destroyed or anonymized."),
    ("Accuracy", "4.6 Accuracy", "PI is as accurate, complete and up to date as necessary for its purposes."),
    ("Safeguards", "4.7 Safeguards", "PI is protected by security safeguards appropriate to its sensitivity."),
    ("Openness", "4.8 Openness", "Policies and practices about PI management are readily available."),
    ("IndividualAccess", "4.9 Individual access", "On request, an individual is informed of the existence, use and "
     "disclosure of their PI and given access to it."),
    ("ChallengingCompliance", "4.10 Challenging compliance", "An individual can challenge compliance with the "
     "principles to the accountable individual."),
    ("RROSH", "Real risk of significant harm", "Threshold for mandatory breach reporting to the OPC and notification "
     "of affected individuals (PIPEDA s. 10.1); assessed using sensitivity and probability of misuse."),
    ("BreachOfSecuritySafeguards", "Breach of security safeguards", "Loss of, unauthorized access to or disclosure "
     "of PI resulting from a breach of safeguards; records of all breaches must be kept for 24 months."),
]

# ---------------------------------------------------------------- org
TEAMS = [
    # name, displayName, type, parent
    ("BorealisBank", "Borealis Bank of Canada (fictional)", "BusinessUnit", None),
    ("PrivacyOffice", "Privacy Office", "Group", "BorealisBank"),
    ("DataGovernanceOffice", "Data Governance Office", "Group", "BorealisBank"),
    ("RetailMarketing", "Retail Marketing", "Group", "BorealisBank"),
    ("FraudAML", "Fraud & AML", "Group", "BorealisBank"),
    ("DataEngineering", "Data Engineering", "Group", "BorealisBank"),
]
USERS = [
    # name, displayName, team, role
    ("priya.cpo", "Priya Sharma (Chief Privacy Officer)", "PrivacyOffice", "PrivacyOfficer"),
    ("dan.steward", "Dan Leblanc (Data Steward)", "DataGovernanceOffice", "PIPEDADataSteward"),
    ("maya.marketing", "Maya Chen (Marketing Analyst)", "RetailMarketing", "MarketingAnalyst"),
    ("femi.aml", "Femi Okafor (AML Analyst)", "FraudAML", "AMLAnalyst"),
    ("eli.engineer", "Eli Tremblay (Data Engineer)", "DataEngineering", "DataEngineer"),
]

POLICIES = [
    {
        "name": "PIPEDASafeguardsNeedToKnow",
        "displayName": "PIPEDA 4.7 - Need-to-know for high-risk and direct identifiers",
        "description": "Marketing users may discover that sensitive tables exist (openness) but may not view sample "
                       "data, queries or profiles of assets tagged PIPEDA.HighRisk or PIPEDA.DirectIdentifier.",
        "rules": [{
            "name": "DenySensitivePreview",
            "effect": "deny",
            "resources": ["table"],
            "operations": ["ViewSampleData", "ViewQueries", "ViewDataProfile"],
            "condition": "matchAnyTag('PIPEDA.HighRisk', 'PIPEDA.DirectIdentifier')",
        }],
    },
    {
        "name": "PIPEDAClassificationIntegrity",
        "displayName": "PIPEDA 4.1 - Only the Privacy Office may change PIPEDA tags",
        "description": "Prevents removal or downgrading of PIPEDA tags by anyone outside the Privacy Office or "
                       "Data Governance Office (tag tampering would silently disable safeguards).",
        "rules": [{
            "name": "DenyPIPEDATagEdits",
            "effect": "deny",
            "resources": ["table"],
            "operations": ["EditTags"],
            "condition": "matchAnyTag('PIPEDA.HighRisk', 'PIPEDA.DirectIdentifier', 'PIPEDA.QuasiIdentifier') "
                         "&& !inAnyTeam('PrivacyOffice', 'DataGovernanceOffice')",
        }],
    },
    {
        "name": "PrivacyOfficeStewardship",
        "displayName": "Privacy Office stewardship",
        "description": "Privacy Office and stewards curate classifications, glossary terms and tags.",
        "rules": [{
            "name": "AllowGovernanceCuration",
            "effect": "allow",
            "resources": ["classification", "tag", "glossary", "glossaryTerm", "table"],
            "operations": ["EditAll", "ViewAll", "EditTags", "EditGlossaryTerms", "EditDescription"],
        }],
    },
]
ROLES = [
    ("PrivacyOfficer", "Privacy Officer", ["PrivacyOfficeStewardship", "DataConsumerPolicy"]),
    ("PIPEDADataSteward", "PIPEDA Data Steward", ["PrivacyOfficeStewardship", "DataStewardPolicy"]),
    ("MarketingAnalyst", "Marketing Analyst", ["DataConsumerPolicy", "PIPEDASafeguardsNeedToKnow"]),
    ("AMLAnalyst", "AML Analyst", ["DataConsumerPolicy"]),
    ("DataEngineer", "Data Engineer", ["DataConsumerPolicy"]),
]

DOMAINS = [
    ("RetailBanking", "Retail Banking", "Customer, account and transaction data for personal banking.", "DataEngineering"),
    ("RiskCompliance", "Risk & Compliance", "AML, fraud and regulatory reporting data.", "FraudAML"),
    ("Marketing", "Marketing", "Campaign audiences and customer analytics.", "RetailMarketing"),
]
DATA_PRODUCTS = [
    ("Customer360", "Customer 360", "RetailBanking", ["bank_dw.dw.dim_customer", "bank_dw.dw.dim_account",
                                                     "bank_dw.dw.fact_transaction"]),
    ("FINTRACLargeCashReporting", "FINTRAC Large Cash Reporting", "RiskCompliance", ["bank_dw.mart.aml_large_cash_txn"]),
    ("EmailCampaignAudience", "E-mail Campaign Audience", "Marketing", ["bank_dw.mart.marketing_campaign_audience"]),
]

# Table-level metadata applied after ingestion:
#   key "<db>.<schema>.<table>" -> (domain, owner team, purposes, retention ISO-8601, tier)
# Retention values are Borealis internal policy ASSUMPTIONS for the POC
# (FINTRAC requires at least five years for most records; the bank adopts 7 years after relationship end).
TABLE_METADATA = {
    "core_banking.core.customer": ("RetailBanking", "DataEngineering", ["AccountServicing"], "P7Y", "Tier1"),
    "core_banking.core.customer_consent": ("RetailBanking", "PrivacyOffice", ["AccountServicing"], "P7Y", "Tier1"),
    "core_banking.core.account": ("RetailBanking", "DataEngineering", ["AccountServicing"], "P7Y", "Tier1"),
    "core_banking.core.card": ("RetailBanking", "DataEngineering", ["AccountServicing"], "P2Y", "Tier1"),
    "core_banking.core.transaction": ("RetailBanking", "DataEngineering", ["AccountServicing", "FraudPrevention"], "P7Y", "Tier1"),
    "core_banking.kyc.identity_document": ("RiskCompliance", "FraudAML", ["RegulatoryReporting"], "P5Y", "Tier1"),
    "core_banking.ops.support_ticket": ("RetailBanking", "DataEngineering", ["AccountServicing"], "P2Y", "Tier3"),
    "core_banking.ops.legacy_member_import": ("RetailBanking", "DataEngineering", [], "P0D", "Tier3"),
    "bank_dw.dw.dim_customer": ("RetailBanking", "DataEngineering", ["Analytics"], "P7Y", "Tier2"),
    "bank_dw.dw.dim_consent": ("RetailBanking", "PrivacyOffice", ["Marketing", "Analytics"], "P7Y", "Tier2"),
    "bank_dw.dw.fact_transaction": ("RetailBanking", "DataEngineering", ["Analytics", "FraudPrevention"], "P7Y", "Tier2"),
    "bank_dw.mart.marketing_campaign_audience": ("Marketing", "RetailMarketing", ["Marketing"], "P90D", "Tier2"),
    "bank_dw.mart.aml_large_cash_txn": ("RiskCompliance", "FraudAML", ["RegulatoryReporting"], "P5Y", "Tier1"),
    "bank_dw.mart.monthly_branch_activity": ("RetailBanking", "DataEngineering", ["Analytics"], "P10Y", "Tier3"),
}
