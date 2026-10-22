"""Shared pytest setup for the POC test suites.

Puts poc/toolbox on sys.path so tests can ``import poc.<module>`` exactly as the
toolbox image does (PYTHONPATH=/app). The unit tests never open a database or
HTTP connection, so when the runtime-only dependencies (psycopg, requests,
PyYAML) are not installed they are replaced by empty stand-in modules; this
keeps the dev install down to pytest alone.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

TOOLBOX = Path(__file__).resolve().parents[1] / "toolbox"
RESULTS = Path(__file__).resolve().parents[1] / "results"

if str(TOOLBOX) not in sys.path:
    sys.path.insert(0, str(TOOLBOX))


def _stub(name: str, **attrs) -> None:
    try:
        __import__(name)
    except ImportError:
        mod = types.ModuleType(name)
        mod.__dict__.update(attrs)
        sys.modules[name] = mod


class _StubError(Exception):
    pass


_stub("psycopg", Error=_StubError, Cursor=object, connect=None)
_stub("requests", Session=object, RequestException=_StubError, get=None, post=None)
_stub("yaml", safe_load=None, safe_dump=None, dump=None)
