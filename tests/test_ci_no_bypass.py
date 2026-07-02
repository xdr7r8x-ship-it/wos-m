from pathlib import Path


def test_ci_has_no_failure_bypass():
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "|| true" not in ci
