#!/usr/bin/env bash
# End-to-end Borealis Bank PIPEDA governance POC on OpenMetadata 2.0.5.
# Usage: ./scripts/run_poc.sh            (full run, ~15-20 min on a laptop)
#        ./scripts/run_poc.sh --from N   (resume at step N)
set -euo pipefail                  # abort on error, unset var, or failed pipe
cd "$(dirname "$0")/.."            # run from poc/ regardless of where the script is called
DC=scripts/dc.sh                   # docker compose wrapper
# Resume support: --from N skips steps below N (default: run everything)
FROM=${2:-1}; [[ "${1:-}" == "--from" ]] || FROM=1
[[ -f .env ]] || cp .env.example .env   # first run: create config from template
mkdir -p work results                   # work/ = logs + rendered workflows, results/ = outputs

# --- helpers ---
# step N "title": prints a header and succeeds only if N >= FROM (used as `step N ... && { body }`)

step() { local n=$1; shift; if (( n >= FROM )); then echo; echo "=== [$n] $*"; return 0; fi; return 1; }
# tool: run a Python module in the toolbox container (data gen, OM API calls, evaluation)
tool() { $DC run --rm toolbox "$@" 2>&1 | { grep -v "attribute \`version\` is obsolete" || true; }; }
# om: run the OpenMetadata CLI (ingest/classify/profile/test); logs to work/, exits on failure
om()   { $DC run --rm om-cli "$@" > "work/$(echo "$*" | tr ' /' '__' | cut -c1-80).log" 2>&1 \
           || { echo "  ! metadata $* failed - see work/*.log"; exit 1; }; echo "  ok: metadata $1 ${3##*/}"; }
# omx: like om classify, but via classify_with.py, a workaround because the OSS CLI hard-codes the PII classification
omx()  { $DC run --rm --entrypoint python om-cli /ext/classify_with.py "$@" > "work/classify_with_$(basename "$1").log" 2>&1 \
           || { echo "  ! classify_with $* failed"; exit 1; }; echo "  ok: classify_with ${1##*/} ${*:2}"; }
# The two ingested services: OLTP (core banking) and OLAP (data warehouse)
SVCS="borealis_core_banking_oltp borealis_enterprise_dw_olap"

# 1: bring up OpenMetadata + the bank DB containers and build the toolbox image
step 1 "Start OpenMetadata 2.0.5 + Borealis bank database" && {
  $DC up -d 2>&1 | grep -v obsolete | tail -3
  $DC --profile tools build toolbox 2>&1 | tail -1
  tool poc.workflows >/dev/null   # waits for the OpenMetadata server to be ready
}
# 2: create synthetic customers/accounts/transactions, then ETL them into the warehouse
step 2 "Generate synthetic OLTP data and load the warehouse" && { tool poc.generate_data; tool poc.etl_to_dw; }
# 3: set up teams, roles, domains, purposes and the PIPEDA glossary in OpenMetadata
step 3 "Org model: teams, personas, roles, domains, purposes, PIPEDA glossary" && tool poc.bootstrap_governance org
# 4: generate ingestion YAMLs and pull table/column metadata for both services
step 4 "Render ingestion workflows and ingest metadata" && {
  tool poc.workflows >/dev/null
  for s in $SVCS; do om ingest -c /work/workflows/${s}__metadata.yaml; done
}
# 5: run default PII auto-classification; score it vs. ground truth (precision/recall/F1)
step 5 "Baseline AI auto-classification (out-of-the-box PII recognizers)" && {
  for s in $SVCS; do om classify -c /work/workflows/${s}__autoclassification.yaml; done
  tool poc.evaluate_classification baseline_ootb
}
# 6: add custom PIPEDA classification + Canadian recognizers, re-classify, re-score
step 6 "Canada-tuned PIPEDA classification (SIN, postal code, licences, passports)" && {
  tool poc.bootstrap_governance classification
  for s in $SVCS; do omx /work/workflows/${s}__autoclassification.yaml PIPEDA; done
  tool poc.evaluate_classification canada_tuned
}
# 7: simulate approvals and steward feedback on false positives, re-classify, re-score
step 7 "Human-in-the-loop: CPO approves glossary; steward reports false positives" && {
  tool poc.human_in_the_loop glossary
  tool poc.human_in_the_loop feedback
  for s in $SVCS; do omx /work/workflows/${s}__autoclassification.yaml PIPEDA; done
  tool poc.evaluate_classification after_feedback
}
# 8: attach owners, domains, purposes, retention periods and lineage
step 8 "Ownership, domains, purposes, retention, lineage" && {
  tool poc.post_ingestion metadata
  tool poc.post_ingestion lineage
}
# 9: profile data, then run PIPEDA/FINTRAC data-quality tests (test failures are findings, not errors)
step 9 "Profiler + PIPEDA data-quality tests" && {
  for s in $SVCS; do om profile -c /work/workflows/${s}__profiler.yaml; done
  for f in work/workflows/dq__*.yaml; do   # failing *tests* are expected findings, not script errors
    $DC run --rm om-cli test -c "/work/workflows/$(basename "$f")" > "work/$(basename "$f" .yaml).log" 2>&1 \
      && echo "  ok: metadata test $(basename "$f")" || echo "  ! test workflow $(basename "$f") reported errors (see log)"
  done
}
# 10: define data products, link glossary terms, create a data contract
step 10 "Data products, glossary links, data contract" && tool poc.post_ingestion products
# 11: verify role-based access, and push catalogue tags into warehouse enforcement
step 11 "Access-control tests and catalogue-driven warehouse enforcement" && {
  tool poc.human_in_the_loop access
  tool poc.enforce_from_catalog
}
# 12: demo an AI assistant querying the catalogue over the MCP server
step 12 "AI assistant queries through the OpenMetadata MCP server" && tool poc.mcp_demo
# 13: aggregate results into summary.json, charts and pipeda_compliance_summary.md
step 13 "Compliance summary" && tool poc.compliance_report

echo; echo "Done. Open http://localhost:8585 (admin@open-metadata.org / admin) and results/pipeda_compliance_summary.md"
