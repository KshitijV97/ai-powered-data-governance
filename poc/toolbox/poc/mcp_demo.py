"""Query the catalogue the way an AI assistant would: via OpenMetadata's built-in MCP server.

The same tools are what Claude Desktop / Claude Code / Cursor call when they are
connected to http://localhost:8585/mcp (see README). This script calls them
directly over JSON-RPC so the answers are reproducible and saved as evidence.
"""

from __future__ import annotations

import json

import requests

from poc import config
from poc.om_client import OpenMetadata


class MCP:
    def __init__(self, token: str):
        self.url = config.OM_HOST + "/mcp"
        self.h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                  "Accept": "application/json, text/event-stream"}
        self.n = 0
        r = self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "borealis-poc", "version": "1.0"}}, raw=True)
        if sid := r.headers.get("Mcp-Session-Id"):
            self.h["Mcp-Session-Id"] = sid
        requests.post(self.url, headers=self.h, json={"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _rpc(self, method: str, params: dict, raw: bool = False):
        self.n += 1
        r = requests.post(self.url, headers=self.h, json={"jsonrpc": "2.0", "id": self.n, "method": method,
                                                          "params": params}, timeout=120)
        r.raise_for_status()
        return r if raw else self._parse(r)

    @staticmethod
    def _parse(r: requests.Response) -> dict:
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            data = [line[5:].strip() for line in r.text.splitlines() if line.startswith("data:")]
            return json.loads(data[-1])
        return r.json()

    def tools(self) -> list[str]:
        return [t["name"] for t in self._rpc("tools/list", {})["result"]["tools"]]

    def call(self, name: str, arguments: dict) -> str:
        res = self._rpc("tools/call", {"name": name, "arguments": arguments})
        if "error" in res:
            return f"ERROR {res['error']}"
        return "\n".join(c.get("text", "") for c in res["result"].get("content", []))


QUESTIONS = [
    ("PIPEDA 4.7 - Which tables hold high-risk identifiers (SIN, card numbers, account numbers)?",
     "search_metadata", {"query": "*", "entityType": "table", "size": 20,
                         "queryFilter": json.dumps({"bool": {"must": [{"term": {"tags.tagFQN": "PIPEDA.HighRisk"}}]}})}),
    ("PIPEDA 4.9 - A customer asks where their e-mail address goes. What is downstream of core.customer?",
     "get_entity_lineage", {"entityType": "table", "fqn": f"{config.OLTP_SERVICE}.core_banking.core.customer",
                            "upstreamDepth": 0, "downstreamDepth": 2}),
    ("PIPEDA 4.3 - Is the marketing audience compliant with consent? Show its quality status and context.",
     "get_entity_details", {"entityType": "table",
                            "fqn": f"{config.OLAP_SERVICE}.bank_dw.mart.marketing_campaign_audience",
                            "include": ["quality", "context"]}),
    ("PIPEDA 4.8 - What does 'real risk of significant harm' mean at Borealis?",
     "search_metadata", {"query": "real risk of significant harm", "entityType": "glossaryTerm", "size": 3}),
]


def main() -> None:
    admin = OpenMetadata.login()
    token = admin.s.headers["Authorization"].split(" ", 1)[1]
    mcp = MCP(token)
    tools = mcp.tools()
    print(f"  MCP server exposes {len(tools)} tools: {', '.join(tools)}")
    transcript = {"tools": tools, "qa": []}
    for q, tool, args in QUESTIONS:
        ans = mcp.call(tool, args)
        transcript["qa"].append({"question": q, "tool": tool, "arguments": args, "answer": ans})
        print(f"\n  Q: {q}\n  -> {tool}: {ans[:600].strip()}{' ...' if len(ans) > 600 else ''}")
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (config.RESULTS_DIR / "mcp_transcript.json").write_text(json.dumps(transcript, indent=2))


if __name__ == "__main__":
    main()
