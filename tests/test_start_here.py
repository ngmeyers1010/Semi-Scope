"""docs/START_HERE.md: commands point at real files, quoted check.py output is still exact,
links resolve, and the README points to it."""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "START_HERE.md"
TEXT = DOC.read_text()
sys.path.insert(0, str(ROOT / "practice"))
import check  # noqa: E402


def blocks(lang=None):
    return [b for lg, b in re.findall(r"```(\w*)\n(.*?)```", TEXT, re.S) if lang is None or lg == lang]


def test_short_and_linked_from_readme():
    assert len(TEXT.splitlines()) <= 150
    assert "(docs/START_HERE.md)" in (ROOT / "README.md").read_text()


def test_every_command_refers_to_files_that_exist():
    cmds = [ln.strip() for b in blocks("bash") for ln in b.splitlines() if ln.strip()]
    assert cmds, "no commands found"
    for c in cmds:
        for tok in c.split():
            if re.search(r"\.(py|txt|md|html)$", tok) or tok in ("docs", "practice"):
                assert (ROOT / tok).exists(), (c, tok)
    inline = re.findall(r"`(python [^`]+)`", TEXT)
    for c in inline:
        for tok in c.split():
            if tok.endswith(".py"):
                assert (ROOT / tok).exists(), c
    for f in re.findall(r"`((?:practice|docs)/[\w./]+)`", TEXT):
        assert (ROOT / f.rstrip("/")).exists(), f


def test_relative_links_resolve():
    for target in re.findall(r"\]\(([^)]+)\)", TEXT):
        if target.startswith(("http://", "https://", "#")):
            continue
        assert (DOC.parent / target.split("#")[0]).resolve().exists(), target


def test_quoted_check_output_is_what_check_py_prints_today(tmp_path):
    src = (ROOT / "practice" / "ex01_last_price.py").read_text()
    answers = [line.strip() for b in blocks("python") for line in b.splitlines() if line.strip()]
    assert answers == ["return float(px[ticker].iloc[0])", "return float(px[ticker].dropna().iloc[-1])"]
    outputs = [b.strip("\n") for lg, b in re.findall(r"```(\w*)\n(.*?)```", TEXT, re.S) if lg == ""]
    assert len(outputs) == 3                     # not started, wrong, right
    got = []
    for body in ["raise NotImplementedError"] + answers:
        (tmp_path / "ex01_last_price.py").write_text(src.replace("raise NotImplementedError", body))
        got.append(check.report([1], tmp_path)[0])
    assert got == outputs
    assert check.report([1], ROOT / "practice")[0] == outputs[0]          # the starter file really is "not done"
    shutil.rmtree(tmp_path, ignore_errors=True)


def test_report_matches_cli(capsys):
    assert check.main(["1"]) == 1
    assert capsys.readouterr().out.strip() == check.report([1])[0].strip()
