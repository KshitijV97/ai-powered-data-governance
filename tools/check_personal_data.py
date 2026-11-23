"""Block commits that would publish personal information in this public repo.

The course forbids collecting or publishing personal information (course guidelines,
section 5) and asks teams not to share restricted information (section 20).
A past commit published student numbers inside a Word document,
so this check runs as a pre-commit hook and in CI.

What it flags:

* uOttawa student numbers (nine digits starting with ``300``),
* e-mail addresses, except the allow-listed placeholder and tool addresses.

It reads plain-text files directly and the XML parts of Office Open XML files
(.docx, .pptx, .xlsx), where Word keeps document text. Other binary files are
skipped. Usage::

    python tools/check_personal_data.py FILE [FILE ...]

Exit status is 1 when anything is found, 0 otherwise.
"""

from __future__ import annotations

import re
import sys
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path

STUDENT_ID = re.compile(r"(?<!\d)300\d{6}(?!\d)")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")

# Addresses that are not personal: the OpenMetadata quickstart login, the AI
# co-author trailer address and documentation placeholders.
ALLOWED_EMAILS = {"admin@open-metadata.org", "noreply@anthropic.com", "noreply@github.com"}
ALLOWED_EMAIL_DOMAINS = {"example.com", "example.org", "example.net"}

OOXML_SUFFIXES = {".docx", ".pptx", ".xlsx", ".dotx"}

# Decorators such as ``@pytest.fixture`` look like e-mail domains to the regex.
_CODE_SUFFIXES = {".py"}


def _email_allowed(address: str) -> bool:
    address = address.lower()
    return address in ALLOWED_EMAILS or address.rsplit("@", 1)[1] in ALLOWED_EMAIL_DOMAINS


def find_in_text(text: str, *, check_email: bool = True) -> list[str]:
    """Return a description of each personal-data match in ``text``."""
    hits = [f"student number {m.group()}" for m in STUDENT_ID.finditer(text)]
    if check_email:
        hits += [
            f"e-mail address {m.group()}"
            for m in EMAIL.finditer(text)
            if not _email_allowed(m.group())
        ]
    return hits


def _ooxml_text(path: Path) -> Iterator[tuple[str, str]]:
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if name.endswith((".xml", ".rels")):
                # Strip tags so text split across runs is still searched as a whole.
                xml = zf.read(name).decode("utf-8", errors="replace")
                yield name, re.sub(r"<[^>]+>", "", xml)


def scan_file(path: Path) -> list[str]:
    """Return ``"path: finding"`` strings for one file (empty when clean)."""
    if path.suffix.lower() in OOXML_SUFFIXES:
        try:
            parts = list(_ooxml_text(path))
        except zipfile.BadZipFile:
            return []
        return [f"{path} [{part}]: {hit}" for part, text in parts for hit in find_in_text(text)]

    data = path.read_bytes()
    if b"\0" in data[:8192]:  # binary file we cannot read as text
        return []
    text = data.decode("utf-8", errors="replace")
    check_email = path.suffix.lower() not in _CODE_SUFFIXES
    return [f"{path}: {hit}" for hit in find_in_text(text, check_email=check_email)]


def main(argv: Iterable[str]) -> int:
    findings = [f for arg in argv if Path(arg).is_file() for f in scan_file(Path(arg))]
    for finding in findings:
        print(finding)
    if findings:
        print(
            "\nPersonal information found. This repository is public: remove it "
            "(see docs/ai-use.md#personal-information) or add the address to the allow list."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
