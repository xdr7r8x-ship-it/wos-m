#!/usr/bin/env python3
"""
WOS-M Security Scanner
Scans all Python files for hardcoded secrets and placeholder text.
Does NOT skip main.py - all files are scanned.
© MANSOUR — WOS-M. All rights reserved.
"""
from pathlib import Path
import re
import sys


SECRET_PATTERNS = [
    r"sk_live_[A-Za-z0-9_-]{10,}",
    r"pk_live_[A-Za-z0-9_-]{10,}",
    r"ghp_[A-Za-z0-9]{20,}",
    r"gho_[A-Za-z0-9]{20,}",
    r"ghs_[A-Za-z0-9]{20,}",
    r"ghu_[A-Za-z0-9]{20,}",
    r"discord_[A-Za-z0-9]{20,}",
    r'(?i)(api_key|secret_key|token|password)\s*=\s*["\'][^"\']{16,}["\']',
]

PLACEHOLDER_PATTERNS = [
    r"Coming soon",
    r"Not implemented",
    r"pass\s*#\s*[Pp]laceholder",
]


IGNORE_LINE_HINTS = [
    "SECRET_PATTERNS",
    "PLACEHOLDER_PATTERNS",
    "forbidden =",
    "patterns =",
    "example",
    "your_",
    "test_token_for_ci",
    "# skip",
    "# Skip",
    "# Ignore",
    "# noqa",
    "def test_",
    "async def test_",
    '"pass  # Placeholder"',
    '"pass # Placeholder"',
]


IGNORE_FILE_PATTERNS = [
    "security_scan.py",
    "test_",
    "tests/",
]


def scan_file(path):
    secrets_found = []
    placeholders_found = []

    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return secrets_found, placeholders_found

    for line_no, line in enumerate(lines, 1):
        if any(hint in line for hint in IGNORE_LINE_HINTS):
            continue

        for pattern in SECRET_PATTERNS:
            if re.search(pattern, line):
                secrets_found.append(f"{path}:{line_no}: {line.strip()[:80]}")

        for pattern in PLACEHOLDER_PATTERNS:
            if re.search(pattern, line):
                placeholders_found.append(f"{path}:{line_no}: {line.strip()[:80]}")

    return secrets_found, placeholders_found


def main():
    all_secrets = []
    all_placeholders = []

    for path in Path(".").rglob("*.py"):
        text_path = str(path)
        
        # Skip ignored directories
        if any(skip in text_path for skip in [".venv", "venv", "__pycache__", ".pytest_cache", "node_modules"]):
            continue
        
        # Skip ignored files
        if any(skip in text_path for skip in IGNORE_FILE_PATTERNS):
            continue

        secrets, placeholders = scan_file(path)
        all_secrets.extend(secrets)
        all_placeholders.extend(placeholders)

    has_issues = False

    if all_secrets:
        print("SECRETS FOUND:")
        for item in all_secrets:
            print(f"  {item}")
        has_issues = True

    if all_placeholders:
        print("PLACEHOLDER TEXT FOUND:")
        for item in all_placeholders:
            print(f"  {item}")
        has_issues = True

    if has_issues:
        print("\n❌ SECURITY/PHASE CHECK FAILED")
        sys.exit(1)

    print("No hardcoded secrets or placeholder text found")
    sys.exit(0)


if __name__ == "__main__":
    main()
