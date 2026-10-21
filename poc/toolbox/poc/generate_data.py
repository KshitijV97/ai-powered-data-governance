"""Generate SYNTHETIC data for the fictional Borealis Bank of Canada OLTP database.

No real person is represented. Names are drawn from small generic lists,
e-mails use the reserved example.* domains (RFC 2606), phone numbers use the
fictional 555-01XX exchange, and SINs / card numbers are random Luhn-valid
digit strings that are not linked to any individual.

A handful of data-quality and privacy defects are planted on purpose so the
OpenMetadata controls have something to detect:
  * malformed postal codes            -> PIPEDA 4.6 Accuracy test fails
  * customers closed > 7 years ago    -> PIPEDA 4.5 Retention test fails
  * full card numbers and CVVs stored -> PIPEDA 4.7 Safeguards (classification)
  * PI hidden in ambiguous columns    -> tests content-based auto-classification
"""

from __future__ import annotations

import io
import random
from datetime import date, datetime, timedelta

import psycopg

from poc import config

rng = random.Random(config.SEED)

FIRST = ["Olivia", "Liam", "Emma", "Noah", "Charlotte", "William", "Amelia", "Benjamin",
         "Sophia", "Lucas", "Chloé", "Félix", "Léa", "Gabriel", "Zoé", "Samuel", "Aisha",
         "Arjun", "Mei", "Wei", "Priya", "Mohammed", "Fatima", "Hiroshi", "Ananya", "Mateo",
         "Isabella", "Ethan", "Ava", "Jacob", "Maya", "Owen", "Nora", "Elijah", "Hannah",
         "Raphaël", "Juliette", "Antoine", "Camille", "Thomas", "Kiana", "Tyler", "Siobhan",
         "Daniel", "Grace", "Marcus", "Leila", "Omar", "Sofia", "Nathan"]
LAST = ["Smith", "Brown", "Tremblay", "Martin", "Roy", "Wilson", "MacDonald", "Gagnon",
        "Johnson", "Taylor", "Côté", "Campbell", "Anderson", "Leblanc", "Lee", "Gauthier",
        "White", "Thompson", "Morin", "Singh", "Patel", "Nguyen", "Chen", "Wong", "Kim",
        "Bouchard", "Pelletier", "Fraser", "Bélanger", "Lévesque", "Ahmed", "Ali", "Khan",
        "Murphy", "O'Brien", "Stewart", "Fortin", "Lavoie", "Kaur", "Gill", "Robinson",
        "Clarke", "Hughes", "Bergeron", "Girard", "Ouellet", "Paquette", "Sharma", "Li", "Wu"]

# province -> (cities, postal FSA first letters, area codes)
PROVINCES = {
    "ON": (["Ottawa", "Toronto", "Mississauga", "Hamilton", "London", "Kingston"], "KLMNP", ["613", "416", "905", "519"]),
    "QC": (["Montréal", "Gatineau", "Québec", "Laval", "Sherbrooke"], "GHJ", ["514", "819", "418", "450"]),
    "BC": (["Vancouver", "Victoria", "Surrey", "Kelowna"], "V", ["604", "250", "778"]),
    "AB": (["Calgary", "Edmonton", "Red Deer"], "T", ["403", "780", "587"]),
    "MB": (["Winnipeg", "Brandon"], "R", ["204"]),
    "SK": (["Regina", "Saskatoon"], "S", ["306"]),
    "NS": (["Halifax", "Sydney"], "B", ["902"]),
    "NB": (["Moncton", "Fredericton", "Saint John"], "E", ["506"]),
    "NL": (["St. John's"], "A", ["709"]),
    "PE": (["Charlottetown"], "C", ["902"]),
}
PROVINCE_WEIGHTS = [38, 22, 14, 12, 3, 3, 3, 2, 2, 1]
STREETS = ["Main St", "King St W", "Rue Sainte-Catherine", "Bank St", "Elgin St", "Yonge St",
           "Granville St", "Jasper Ave", "Portage Ave", "Rue Saint-Denis", "Barrington St",
           "Water St", "Queen St E", "Rideau St", "Boulevard René-Lévesque", "Robson St"]
OCCUPATIONS = ["Software Developer", "Registered Nurse", "Teacher", "Electrician", "Accountant",
               "Retail Associate", "Civil Engineer", "Student", "Retired", "Truck Driver",
               "Physician", "Chef", "Graphic Designer", "Public Servant", "Small Business Owner"]
MERCHANTS = [("Maple Grocers", "GROCERY"), ("Northern Fuel", "FUEL"), ("Caribou Coffee House", "RESTAURANT"),
             ("TransCanada Air", "TRAVEL"), ("Pharma-Plus Demo", "PHARMACY"), ("Hydro Utility Demo", "UTILITIES"),
             ("Big Box Electronics", "ELECTRONICS"), ("Online Books Demo", "ONLINE_RETAIL"),
             ("Transit Authority Demo", "TRANSIT"), ("Casino Demo", "GAMBLING")]
POSTAL_LETTERS = "ABCEGHJKLMNPRSTVWXYZ"   # letters valid in positions 3 and 5
POSTAL_FIRST_INVALID = set("DFIOQUWZ")

START = datetime(2024, 1, 1)
END = datetime(2026, 9, 30)


def luhn_complete(prefix: str) -> str:
    """Append a Luhn check digit to a digit string."""
    total = 0
    for i, ch in enumerate(reversed(prefix)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return prefix + str((10 - total % 10) % 10)


def synthetic_sin() -> str:
    digits = luhn_complete(str(rng.choice([1, 2, 3, 4, 5, 6, 7])) + "".join(rng.choices("0123456789", k=7)))
    return f"{digits[0:3]}-{digits[3:6]}-{digits[6:9]}"


def synthetic_pan() -> str:
    digits = luhn_complete("4" + "".join(rng.choices("0123456789", k=14)))
    return " ".join(digits[i:i + 4] for i in range(0, 16, 4))


def postal_code(fsa_letters: str) -> str:
    a = rng.choice(fsa_letters)
    return f"{a}{rng.randint(0, 9)}{rng.choice(POSTAL_LETTERS)} {rng.randint(0, 9)}{rng.choice(POSTAL_LETTERS)}{rng.randint(0, 9)}"


def phone(area_codes: list[str]) -> str:
    return f"{rng.choice(area_codes)}-555-01{rng.randint(0, 99):02d}"


def email_for(first: str, last: str, n: int) -> str:
    clean = lambda s: "".join(c for c in s.lower() if c.isalpha())  # noqa: E731
    return f"{clean(first)}.{clean(last)}{n}@{rng.choice(['example.com', 'example.org', 'example.net'])}"


def rand_ts(start: datetime, end: datetime) -> datetime:
    return start + timedelta(seconds=rng.randint(0, int((end - start).total_seconds())))


def copy_rows(cur: psycopg.Cursor, table: str, cols: list[str], rows: list[tuple]) -> None:
    with cur.copy(f"COPY {table} ({', '.join(cols)}) FROM STDIN") as cp:
        for r in rows:
            cp.write_row(r)


def generate(n_customers: int = config.N_CUSTOMERS) -> dict:
    branches = []
    for i in range(1, 21):
        prov = rng.choices(list(PROVINCES), PROVINCE_WEIGHTS)[0]
        city = rng.choice(PROVINCES[prov][0])
        branches.append((i, f"{10000 + i * 37:05d}", f"{city} Branch {i}", city, prov))

    customers, consents, accounts, cards, docs, tickets = [], [], [], [], [], []
    consent_id = account_id = card_id = doc_id = ticket_id = 0
    for cid in range(1, n_customers + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        prov = rng.choices(list(PROVINCES), PROVINCE_WEIGHTS)[0]
        cities, fsa, areas = PROVINCES[prov]
        dob = date(1940, 1, 1) + timedelta(days=rng.randint(0, 365 * 66))
        created = rand_ts(datetime(2008, 1, 1), datetime(2026, 6, 30))
        status, closed = "ACTIVE", None
        roll = rng.random()
        if roll < 0.03:                                   # planted: closed long ago, never purged
            closed = rand_ts(datetime(2014, 1, 1), datetime(2018, 12, 31))
            created = min(created, closed - timedelta(days=400))
            status = "CLOSED"
        elif roll < 0.09:
            closed = rand_ts(max(created, datetime(2020, 1, 1)), datetime(2026, 9, 1))
            status = "CLOSED"
        pc = postal_code(fsa)
        if rng.random() < 0.01:                           # planted accuracy defect
            pc = rng.choice(["90210", "K1A0B1", "ZZZ 999", "k1p 5j9"])
        customers.append((cid, first, last, dob, synthetic_sin() if rng.random() > 0.02 else None,
                          email_for(first, last, cid), phone(areas),
                          f"{rng.randint(1, 9999)} {rng.choice(STREETS)}", rng.choice(cities), prov, pc,
                          rng.choice(OCCUPATIONS), round(rng.lognormvariate(11.0, 0.5), 2),
                          "fr" if prov == "QC" and rng.random() < 0.8 else "en", status, created, closed))

        for purpose, p_grant, ctype in [("ACCOUNT_SERVICING", 1.0, "IMPLIED"), ("MARKETING_EMAIL", 0.45, "EXPRESS"),
                                        ("ANALYTICS", 0.7, "IMPLIED"), ("THIRD_PARTY_SHARING", 0.15, "EXPRESS"),
                                        ("CREDIT_BUREAU", 0.9, "EXPRESS")]:
            consent_id += 1
            granted = rng.random() < p_grant
            captured = created + timedelta(minutes=rng.randint(0, 60))
            withdrawn = None
            if granted and purpose != "ACCOUNT_SERVICING" and rng.random() < 0.08:
                withdrawn = rand_ts(max(captured, datetime(2024, 1, 1)), datetime(2026, 9, 1))
            consents.append((consent_id, cid, purpose, granted, ctype,
                             rng.choice(["BRANCH", "ONLINE", "MOBILE", "PHONE"]), captured, withdrawn))

        for _ in range(rng.choices([1, 2, 3], [55, 35, 10])[0]):
            account_id += 1
            atype = rng.choices(["CHEQUING", "SAVINGS", "TFSA", "RRSP", "CREDIT_CARD", "MORTGAGE"],
                                [40, 20, 12, 8, 15, 5])[0]
            bal = round(rng.lognormvariate(8.5, 1.2), 2) * (-1 if atype in ("CREDIT_CARD", "MORTGAGE") else 1)
            opened = min(created + timedelta(days=rng.randint(0, 200)), datetime(2026, 9, 1))
            accounts.append((account_id, cid, rng.randint(1, 20), f"{rng.randint(1000000, 9999999)}", atype,
                             "CAD", bal, "CLOSED" if closed else "OPEN", opened, closed))
            if atype in ("CHEQUING", "CREDIT_CARD"):
                card_id += 1
                cards.append((card_id, account_id, synthetic_pan(), rng.randint(1, 12), rng.randint(2026, 2031),
                              f"{rng.randint(0, 999):03d}", "BLOCKED" if closed else "ACTIVE"))

        doc_id += 1
        if rng.random() < 0.5:
            docs.append((doc_id, cid, "PASSPORT", f"{rng.choice('ABGHJKLMNP')}{rng.choice('ABCDEFGHJK')}{rng.randint(100000, 999999)}",
                         "CANADA", date(2027, 1, 1) + timedelta(days=rng.randint(0, 3000)), created, "emp_" + str(rng.randint(100, 999))))
        else:
            dl = f"{last[0].upper()}{rng.randint(1000, 9999)}-{rng.randint(10000, 99999)}-{rng.randint(10000, 99999)}"
            docs.append((doc_id, cid, "DRIVERS_LICENCE", dl, prov, date(2027, 1, 1) + timedelta(days=rng.randint(0, 2000)),
                         created, "emp_" + str(rng.randint(100, 999))))

        if rng.random() < 0.35:
            ticket_id += 1
            templates = [
                f"Client {first} {last} called from {phone(areas)} disputing a charge at {rng.choice(MERCHANTS)[0]}.",
                f"{first} {last} requested a copy of all personal information we hold (PIPEDA access request).",
                f"Verified identity of {first} {last}; new mailing address {rng.randint(1, 999)} {rng.choice(STREETS)}, {rng.choice(cities)}.",
                "Card reported lost; replacement ordered.",
                "Customer asked about TFSA contribution room.",
                f"Customer wants marketing e-mails stopped at {email_for(first, last, cid)}.",
            ]
            tickets.append((ticket_id, cid, rand_ts(START, END),
                            rng.choice(["DISPUTE", "ACCESS_REQUEST", "ADDRESS_CHANGE", "CARD", "PRODUCT", "CONSENT"]),
                            rng.choice(templates)))

    # Transactions
    txns = []
    tid = 0
    open_accounts = [a for a in accounts if a[4] not in ("MORTGAGE",)]
    for a in open_accounts:
        for _ in range(rng.randint(5, 45)):
            tid += 1
            ttype = rng.choices(["DEBIT", "CREDIT", "CASH_DEPOSIT", "CASH_WITHDRAWAL", "E_TRANSFER", "BILL_PAYMENT"],
                                [45, 15, 6, 8, 16, 10])[0]
            channel = {"CASH_DEPOSIT": "BRANCH", "CASH_WITHDRAWAL": "ATM"}.get(ttype, rng.choice(["ONLINE", "MOBILE", "POS"]))
            amount = round(rng.lognormvariate(4.0, 1.1), 2)
            if ttype == "CASH_DEPOSIT" and rng.random() < 0.04:
                amount = round(rng.uniform(10000, 25000), 2)   # FINTRAC large cash transaction
            m = rng.choice(MERCHANTS) if ttype in ("DEBIT",) else (None, None)
            cp_email = email_for(rng.choice(FIRST), rng.choice(LAST), rng.randint(1, 9999)) if ttype == "E_TRANSFER" else None
            ip = f"198.51.100.{rng.randint(1, 254)}" if channel in ("ONLINE", "MOBILE") else None   # RFC 5737 range
            txns.append((tid, a[0], rand_ts(max(START, a[8]), END), amount, ttype, channel, m[0], m[1], cp_email, ip,
                         rng.choice([None, None, "rent", "groceries", "thanks!", "invoice 4471"])))

    legacy = []
    for i in range(1, 401):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        sin = synthetic_sin()
        legacy.append((i, f"{last.upper()}, {first}", sin.replace("-", " ") if i % 2 else sin.replace("-", ""),
                       postal_code(rng.choice(["KLMNP", "GHJ", "V"])), str(rng.randint(100, 9999)), datetime(2019, 5, 14)))

    fx = []
    d = date(2025, 1, 1)
    while d <= date(2026, 9, 30):
        for pair, base in [("USD/CAD", 1.37), ("EUR/CAD", 1.50), ("GBP/CAD", 1.78)]:
            fx.append((d, pair, round(base * rng.uniform(0.97, 1.03), 6)))
        d += timedelta(days=1)

    return dict(branches=branches, customers=customers, consents=consents, accounts=accounts, cards=cards,
                docs=docs, tickets=tickets, txns=txns, legacy=legacy, fx=fx)


def load(data: dict) -> None:
    with psycopg.connect(config.dsn("core_banking"), autocommit=False) as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE core.transaction, core.card, core.account, core.customer_consent, kyc.identity_document, "
                    "ops.support_ticket, core.customer, core.branch, ops.legacy_member_import, ops.fx_rate RESTART IDENTITY CASCADE")
        copy_rows(cur, "core.branch", ["branch_id", "transit_number", "branch_name", "city", "province"], data["branches"])
        copy_rows(cur, "core.customer", ["customer_id", "first_name", "last_name", "date_of_birth", "sin", "email",
                                         "phone_number", "street_address", "city", "province", "postal_code", "occupation",
                                         "annual_income", "preferred_language", "customer_status", "created_at", "closed_at"],
                  data["customers"])
        copy_rows(cur, "core.customer_consent", ["consent_id", "customer_id", "purpose", "granted", "consent_type",
                                                 "capture_channel", "captured_at", "withdrawn_at"], data["consents"])
        copy_rows(cur, "core.account", ["account_id", "customer_id", "branch_id", "account_number", "account_type",
                                        "currency", "current_balance", "account_status", "opened_at", "closed_at"],
                  data["accounts"])
        copy_rows(cur, "core.card", ["card_id", "account_id", "card_number", "expiry_month", "expiry_year", "cvv",
                                     "card_status"], data["cards"])
        copy_rows(cur, "kyc.identity_document", ["document_id", "customer_id", "document_type", "document_number",
                                                 "issuing_jurisdiction", "expiry_date", "verified_at",
                                                 "verified_by_employee"], data["docs"])
        copy_rows(cur, "ops.support_ticket", ["ticket_id", "customer_id", "opened_at", "category", "agent_notes"],
                  data["tickets"])
        copy_rows(cur, "core.transaction", ["transaction_id", "account_id", "txn_timestamp", "amount", "txn_type",
                                            "channel", "merchant_name", "merchant_category", "counterparty_email",
                                            "client_ip", "memo"], data["txns"])
        copy_rows(cur, "ops.legacy_member_import", ["import_row_id", "fld_01", "fld_02", "fld_03", "fld_04",
                                                    "imported_at"], data["legacy"])
        copy_rows(cur, "ops.fx_rate", ["rate_date", "currency_pair", "rate"], data["fx"])
        for seq_table, col in [("core.customer", "customer_id"), ("core.account", "account_id"),
                               ("core.transaction", "transaction_id"), ("core.customer_consent", "consent_id"),
                               ("core.card", "card_id"), ("kyc.identity_document", "document_id"),
                               ("ops.support_ticket", "ticket_id"), ("ops.legacy_member_import", "import_row_id"),
                               ("core.branch", "branch_id")]:
            cur.execute(f"SELECT setval(pg_get_serial_sequence('{seq_table}', '{col}'), (SELECT max({col}) FROM {seq_table}))")
        conn.commit()
        cur.execute("ANALYZE")


def main() -> None:
    data = generate()
    load(data)
    print("Loaded synthetic OLTP data: " + ", ".join(f"{k}={len(v)}" for k, v in data.items()))


if __name__ == "__main__":
    main()
