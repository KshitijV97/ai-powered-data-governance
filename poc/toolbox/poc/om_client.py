"""Minimal OpenMetadata REST client (requests-based) used by the POC scripts."""

from __future__ import annotations

import base64
import time
from typing import Any
from urllib.parse import quote

import requests

from poc import config


class OMError(RuntimeError):
    pass


class OpenMetadata:
    def __init__(self, api: str = config.OM_API, token: str | None = None):
        self.api = api.rstrip("/")
        self.s = requests.Session()
        self.s.headers["Content-Type"] = "application/json"
        if token:
            self.s.headers["Authorization"] = f"Bearer {token}"

    # ------------------------------------------------------------ auth
    @classmethod
    def login(
        cls, email: str = config.OM_ADMIN_EMAIL, password: str = config.OM_ADMIN_PASSWORD
    ) -> OpenMetadata:
        om = cls()
        r = om.s.post(
            f"{om.api}/v1/users/login",
            json={"email": email, "password": base64.b64encode(password.encode()).decode()},
        )
        if r.status_code != 200:
            raise OMError(f"login failed: {r.status_code} {r.text[:300]}")
        om.s.headers["Authorization"] = f"Bearer {r.json()['accessToken']}"
        return om

    def bot_token(self, bot: str = "ingestion-bot") -> str:
        bot_user = self.get(f"/v1/bots/name/{bot}")["botUser"]
        return self.get(f"/v1/users/auth-mechanism/{bot_user['id']}")["config"]["JWTToken"]

    @staticmethod
    def wait_until_ready(api: str = config.OM_API, timeout: int = 900) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if requests.get(f"{api}/v1/system/version", timeout=5).status_code == 200:
                    return
            except requests.RequestException:
                pass
            time.sleep(5)
        raise OMError("OpenMetadata server did not become ready")

    # ------------------------------------------------------------ verbs
    def _check(self, r: requests.Response, ok=(200, 201)) -> Any:
        if r.status_code not in ok:
            raise OMError(f"{r.request.method} {r.url} -> {r.status_code}: {r.text[:800]}")
        if not r.content:
            return None
        try:
            return r.json()
        except ValueError:
            return r.text

    def get(self, path: str, params: dict | None = None, ok=(200,)) -> Any:
        return self._check(self.s.get(self.api + path, params=params), ok)

    def get_or_none(self, path: str, params: dict | None = None) -> Any:
        r = self.s.get(self.api + path, params=params)
        return None if r.status_code == 404 else self._check(r, (200,))

    def put(self, path: str, body: Any) -> Any:
        return self._check(self.s.put(self.api + path, json=body))

    def post(self, path: str, body: Any, ok=(200, 201)) -> Any:
        return self._check(self.s.post(self.api + path, json=body), ok)

    def patch(self, path: str, ops: list[dict]) -> Any:
        return self._check(
            self.s.patch(
                self.api + path, json=ops, headers={"Content-Type": "application/json-patch+json"}
            )
        )

    def delete(self, path: str, params: dict | None = None) -> Any:
        return self._check(self.s.delete(self.api + path, params=params), (200, 204, 404))

    # ------------------------------------------------------------ helpers
    @staticmethod
    def q(fqn: str) -> str:
        return quote(fqn, safe="")

    def by_name(self, entity: str, fqn: str, fields: str = "") -> Any:
        return self.get_or_none(
            f"/v1/{entity}/name/{self.q(fqn)}", {"fields": fields} if fields else None
        )

    def list_all(self, entity: str, params: dict | None = None) -> list[dict]:
        params = dict(params or {}, limit=200)
        out, after = [], None
        while True:
            if after:
                params["after"] = after
            page = self.get(f"/v1/{entity}", params)
            out.extend(page.get("data", []))
            after = page.get("paging", {}).get("after")
            if not after:
                return out

    def table(self, fqn: str, fields: str = "columns,tags,owners,domains") -> dict | None:
        return self.by_name("tables", fqn, fields)
