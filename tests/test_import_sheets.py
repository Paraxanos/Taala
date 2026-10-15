"""The importer, not Excel, is what enforces the spelling rules."""

import csv
import importlib.util
from pathlib import Path

import pytest
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]

# word_id, spelling, spelling_alt, dont_know
FILLED = [
    ("w001", "priyaa", "", ""),            # kept
    ("w002", "raahul", "rahool", ""),      # kept, two spellings
    ("w006", "", "", "1"),                 # don't know
    ("w007", "", "", ""),                  # blank
    ("w009", "Ajay", "", ""),              # kept, lowercased on the way in
    ("w010", "kaajal kajol", "", ""),      # rejected: space
    ("w012", "r1tu", "", ""),              # rejected: digit
    ("w013", "a", "", ""),                 # rejected: too short
    ("w014", "jyothi", "", "1"),           # rejected: spelled and marked unknown
    ("w015", "ameet", "", "x"),            # rejected: bad flag
    ("w018", "gourav", "gourav", ""),      # one kept, duplicate collapsed
]


@pytest.fixture
def mod(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("imp", ROOT / "tools" / "import_sheets.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    sheets = tmp_path / "sheets"
    sheets.mkdir()
    wb = Workbook()
    ws = wb.active
    ws.title = "Spellings"
    ws.append(["word_id", "word", "spelling", "spelling_alt", "dont_know"])
    for word_id, spelling, alt, flag in FILLED:
        ws.append([word_id, "x", spelling, alt, flag])
    wb.save(sheets / "author_A.xlsx")

    monkeypatch.setattr(m, "SHEETS", sheets)
    monkeypatch.setattr(m, "OUT", tmp_path / "observed_authors.tsv")
    monkeypatch.setattr(m, "AUTHORS", ("A",))
    return m


def read_out(mod):
    with mod.OUT.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def test_only_valid_spellings_survive(mod, capsys):
    mod.main()
    rows = read_out(mod)
    assert sorted((r["word_id"], r["spelling"]) for r in rows) == [
        ("w001", "priyaa"), ("w002", "raahul"), ("w002", "rahool"),
        ("w009", "ajay"), ("w018", "gourav"),
    ]


def test_every_rejection_is_reported(mod, capsys):
    mod.main()
    err = capsys.readouterr().err
    for bad in ("kaajal kajol", "r1tu", "'a'", "jyothi", "'x'"):
        assert bad in err, bad
    assert err.count("REJECTED") == 5


def test_author_and_kind_are_recorded(mod):
    mod.main()
    rows = read_out(mod)
    assert {r["author"] for r in rows} == {"A"}
    assert {r["kind"] for r in rows} == {"natural", "alt"}
    assert [r["kind"] for r in rows if r["word_id"] == "w002"] == ["natural", "alt"]


def test_empty_sheets_produce_an_empty_table(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("imp2", ROOT / "tools" / "import_sheets.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    sheets = tmp_path / "sheets"
    sheets.mkdir()
    monkeypatch.setattr(m, "SHEETS", sheets)
    monkeypatch.setattr(m, "OUT", tmp_path / "observed_authors.tsv")
    m.main()
    assert read_out(m) == []
