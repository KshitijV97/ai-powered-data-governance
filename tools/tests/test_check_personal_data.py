"""Unit tests for tools/check_personal_data.py."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_personal_data as cpd  # noqa: E402


def test_flags_student_number():
    assert cpd.find_in_text("Khang Tran 300123456") == ["student number 300123456"]


def test_ignores_longer_or_other_numbers():
    assert cpd.find_in_text("id 1300123456 and 3001234567 and 400123456") == []


def test_flags_personal_email_but_not_allowed_ones():
    text = "a@uottawa.ca admin@open-metadata.org noreply@anthropic.com x@example.com"
    assert cpd.find_in_text(text) == ["e-mail address a@uottawa.ca"]


def test_python_decorators_are_not_emails(tmp_path):
    f = tmp_path / "t.py"
    f.write_text("@pytest.mark.parametrize\ndef f(): ...\n")
    assert cpd.scan_file(f) == []


def test_scans_docx_text_split_across_runs(tmp_path):
    f = tmp_path / "document.docx"
    with zipfile.ZipFile(f, "w") as zf:
        zf.writestr("word/document.xml", "<w:t>3001</w:t><w:t>23456</w:t>")
    hits = cpd.scan_file(f)
    assert hits == [f"{f} [word/document.xml]: student number 300123456"]


def test_skips_binary_files(tmp_path):
    f = tmp_path / "image.png"
    f.write_bytes(b"\x89PNG\0\0 300123456")
    assert cpd.scan_file(f) == []


def test_main_exit_status(tmp_path, capsys):
    clean = tmp_path / "clean.md"
    clean.write_text("All data is synthetic.\n")
    dirty = tmp_path / "dirty.md"
    dirty.write_text("Student ID: 300123456\n")
    assert cpd.main([str(clean)]) == 0
    assert cpd.main([str(clean), str(dirty)]) == 1
    assert "300123456" in capsys.readouterr().out
