"""Create the Borealis Bank PIPEDA governance model in OpenMetadata.

    python -m poc.bootstrap_governance org             # teams, users, policies, roles, domains, glossary, purposes
    python -m poc.bootstrap_governance classification  # PIPEDA classification + Canadian recognizers

All calls are idempotent PUT (create-or-update), so the step can be re-run.
"""

from __future__ import annotations

import sys

from poc import governance_model as gm
from poc.om_client import OpenMetadata

PERSONA_PASSWORD = "Borealis!Poc2026"  # local test accounts only (see README)


def ref(entity_type: str, entity: dict) -> dict:
    return {"id": entity["id"], "type": entity_type}


def put_roles(om: OpenMetadata, include_pipeda: bool) -> dict:
    roles = {}
    for name, display, policies in gm.ROLES:
        policies = [p for p in policies if include_pipeda or not p.startswith("PIPEDA")]
        roles[name] = om.put(
            "/v1/roles",
            {
                "name": name,
                "displayName": display,
                "policies": policies,
                "description": f"{display} (PIPEDA POC)",
            },
        )
    print(f"  roles: {', '.join(roles)}")
    return roles


def org(om: OpenMetadata) -> None:
    teams = {}
    for name, display, ttype, parent in gm.TEAMS:
        body = {
            "name": name,
            "displayName": display,
            "teamType": ttype,
            "parents": [teams[parent]["id"]]
            if parent
            else [om.by_name("teams", "Organization")["id"]],
        }
        teams[name] = om.put("/v1/teams", body)
    print(f"  teams: {', '.join(teams)}")

    # Policies that reference PIPEDA tags are added in the `classification` step, once the tags exist.
    for p in gm.POLICIES:
        if not p["name"].startswith("PIPEDA"):
            om.put("/v1/policies", p)
    roles = put_roles(om, include_pipeda=False)

    users = {}
    for name, display, team, role in gm.USERS:
        body = {
            "name": name,
            "displayName": display,
            "email": f"{name}@borealis.example",
            "teams": [teams[team]["id"]],
            "roles": [roles[role]["id"]],
            "isBot": False,
        }
        if om.by_name("users", name) is None:
            # POST (not PUT) is the only call that honours ADMIN_CREATE passwords under basic auth
            om.post(
                "/v1/users",
                {
                    **body,
                    "createPasswordType": "ADMIN_CREATE",
                    "password": PERSONA_PASSWORD,
                    "confirmPassword": PERSONA_PASSWORD,
                },
            )
        users[name] = om.put("/v1/users", body)
        # PUT on an existing user clears its basic-auth password, so (re)set it explicitly.
        om.put(
            "/v1/users/changePassword",
            {
                "username": name,
                "newPassword": PERSONA_PASSWORD,
                "confirmPassword": PERSONA_PASSWORD,
                "requestType": "USER",
            },
        )
    print(f"  users: {', '.join(users)}")

    cpo = ref("user", users["priya.cpo"])
    steward = ref("user", users["dan.steward"])

    for name, display, desc, owner_team in gm.DOMAINS:
        om.put(
            "/v1/domains",
            {
                "name": name,
                "displayName": display,
                "description": desc,
                "domainType": "Aggregate",
                "owners": [ref("team", teams[owner_team])],
                "experts": [users["dan.steward"]["name"]],
            },
        )
    print(f"  domains: {', '.join(d[0] for d in gm.DOMAINS)}")

    # Purpose classification (PIPEDA 4.2) - applied at table level, not auto-classified.
    om.put(
        "/v1/classifications",
        {
            "name": gm.PURPOSE_CLASSIFICATION,
            "displayName": "PIPEDA purpose of processing",
            "description": "Identified purposes for which personal information in an asset is "
            "collected and used (PIPEDA Principle 4.2).",
            "mutuallyExclusive": False,
            "owners": [cpo],
        },
    )
    for name, desc in gm.PURPOSE_TAGS:
        om.put(
            "/v1/tags",
            {"classification": gm.PURPOSE_CLASSIFICATION, "name": name, "description": desc},
        )
    print(f"  classification {gm.PURPOSE_CLASSIFICATION}: {len(gm.PURPOSE_TAGS)} tags")

    # Glossary with reviewers -> new terms go through the GlossaryTermApprovalWorkflow.
    om.put(
        "/v1/glossaries",
        {**gm.GLOSSARY, "owners": [cpo], "reviewers": [cpo], "mutuallyExclusive": False},
    )
    for name, display, desc in gm.GLOSSARY_TERMS:
        # Create only: editing a term that is In Review cancels its approval task and resets it to Draft.
        if om.by_name("glossaryTerms", f"{gm.GLOSSARY['name']}.{name}") is None:
            om.post(
                "/v1/glossaryTerms",
                {
                    "glossary": gm.GLOSSARY["name"],
                    "name": name,
                    "displayName": display,
                    "description": desc,
                    "owners": [steward],
                    "reviewers": [cpo],
                },
            )
    print(
        f"  glossary {gm.GLOSSARY['name']}: {len(gm.GLOSSARY_TERMS)} terms (pending CPO approval)"
    )

    if om.by_name(
        "classifications", gm.PIPEDA_CLASSIFICATION
    ):  # re-run: keep PIPEDA policies attached
        pipeda_policies(om)


def classification(om: OpenMetadata) -> None:
    cpo = om.by_name("users", "priya.cpo")
    owners = [ref("user", cpo)]
    om.put(
        "/v1/classifications",
        {
            "name": gm.PIPEDA_CLASSIFICATION,
            "displayName": "PIPEDA sensitivity (Borealis Bank)",
            "description": "Borealis Bank sensitivity scheme for personal information under PIPEDA. Tuned for Canadian "
            "identifiers (SIN, postal code, provincial licences, passports). Owned by the Chief Privacy "
            "Officer (Principle 4.1).",
            "mutuallyExclusive": True,
            "owners": owners,
            "autoClassificationConfig": {
                "enabled": True,
                "conflictResolution": "highest_priority",
                "minimumConfidence": 0.6,
                "requireExplicitMatch": True,
            },
        },
    )
    for t in gm.PIPEDA_TAGS:
        body = {
            "classification": gm.PIPEDA_CLASSIFICATION,
            **t,
            "owners": owners,
            "reviewers": owners,
        }
        om.put("/v1/tags", body)
        print(f"  tag PIPEDA.{t['name']}: {len(t.get('recognizers', []))} recognizers")

    pipeda_policies(om)


def pipeda_policies(om: OpenMetadata) -> None:
    """Tag-based PIPEDA policies (need the PIPEDA tags to exist)."""
    for p in gm.POLICIES:
        if p["name"].startswith("PIPEDA"):
            om.put("/v1/policies", p)
    print(f"  policies: {', '.join(p['name'] for p in gm.POLICIES)}")
    put_roles(om, include_pipeda=True)
    # Org-wide guard rail: PIPEDA tag integrity applies to everyone in the bank via the business unit.
    bu = om.by_name("teams", "BorealisBank")
    om.patch(
        f"/v1/teams/{bu['id']}",
        [
            {
                "op": "add",
                "path": "/policies",
                "value": [ref("policy", om.by_name("policies", "PIPEDAClassificationIntegrity"))],
            }
        ],
    )


def main() -> None:
    step = sys.argv[1] if len(sys.argv) > 1 else "org"
    om = OpenMetadata.login()
    {"org": org, "classification": classification}[step](om)


if __name__ == "__main__":
    main()
