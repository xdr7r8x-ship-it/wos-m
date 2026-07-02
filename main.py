#!/usr/bin/env python3
"""
WOS-M Main Entry Point
© MANSOUR — WOS-M. All rights reserved.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

import dotenv

dotenv.load_dotenv()

from config.settings import settings
from core.bot import WOSMBot

def setup_logging():
    log_dir = Path(__file__).parent / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, settings.logging.level),
        format=settings.logging.format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(settings.logging.file),
        ]
    )
    logging.getLogger("discord").setLevel(logging.WARNING)

setup_logging()
logger = logging.getLogger(__name__)

async def run_bot():
    bot = WOSMBot()
    token = os.getenv("DISCORD_BOT_TOKEN") or settings.bot.token
    
    if not token:
        logger.error("No bot token found! Set DISCORD_BOT_TOKEN in .env file.")
        sys.exit(1)
    
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await bot.close()

def check_system():
    """Static check only - no .env or BOT_TOKEN required."""
    print("WOS-M System Check - STATIC MODE")
    print("=" * 70)

    issues = []

    # Runtime checks - skipped in static mode
    print("PASS: .env check skipped (static mode)")
    print("PASS: BOT_TOKEN check skipped (static mode)")
    print("INFO: Runtime checks (demo_mode, OCR, adapter) skipped")

    # Check schema columns
    db_file = Path(__file__).parent / "core" / "database.py"
    if db_file.exists():
        with open(db_file) as f:
            db_content = f.read()
        if "discord_role_id" in db_content:
            print("PASS: discord_role_id in schema")
        else:
            issues.append("discord_role_id not found in schema")
        if "state_kid" in db_content:
            print("PASS: state_kid in schema")
        else:
            issues.append("state_kid not found in schema")

    # Check migrations
    migrations_file = Path(__file__).parent / "database" / "migrations" / "__init__.py"
    if migrations_file.exists():
        with open(migrations_file) as f:
            mig_content = f.read()
        if "add_alliance_discord_role_id" in mig_content:
            print("PASS: add_alliance_discord_role_id migration exists")
        else:
            issues.append("add_alliance_discord_role_id migration missing")

    # Check locales
    locales_dir = Path(__file__).parent / "locales"
    if locales_dir.exists():
        import json
        for lf in locales_dir.glob("*.json"):
            with open(lf) as f:
                data = json.load(f)
                if all(k in data for k in ["bot", "dashboard", "messages"]):
                    print(f"PASS: {lf.name}")
                else:
                    issues.append(f"{lf.name} missing keys")

    # Check hardcoded strings
    hardcoded = ['"Confirmed"', '"Cancelled"', '"Language changed"']
    for pattern in hardcoded:
        for f in list(Path(__file__).parent.rglob("*.py")):
            if f.name == "__init__.py":
                continue
            with open(f) as fp:
                c = fp.read()
                if pattern in c and "i18n.get" not in c:
                    issues.append(f"Hardcoded: {pattern}")
                    print(f"FAIL: {pattern} in {f.name}")

    # Check placeholders
    core_dir = Path(__file__).parent / "core"
    for f in core_dir.rglob("*.py"):
        with open(f) as fp:
            c = fp.read()
            if "pass  # Placeholder" in c or "pass # Placeholder" in c:
                issues.append(f"Placeholder in {f.name}")

    # Check slash commands
    bot_file = Path(__file__).parent / "core" / "bot.py"
    if bot_file.exists():
        with open(bot_file) as f:
            c = f.read()
            if "name=" in c and '"wos"' in c:
                print("PASS: /wos command")
            else:
                issues.append("/wos command not found")

    # Check callbacks
    for cb in ["auto_enable_alliance", "auto_disable_alliance", "auto_redeem_all"]:
        if f'"{cb}"' not in open(bot_file).read():
            issues.append(f"Missing: {cb}")

    # Check for proprietary secrets
    print("\n🔒 Checking for proprietary secrets...")
    forbidden_patterns = ["sk_live_", "pk_live_", "api_key_", "secret_key_", "ghp_", "gho_", "ghs_"]
    secrets_found = False
    for py_file in list(Path(__file__).parent.rglob("*.py")):
        if py_file.name.startswith("test_") or "test" in str(py_file):
            continue
        if py_file.name in ["main.py"]:
            continue
        with open(py_file) as f:
            ci = f.read()
            for pattern in forbidden_patterns:
                import re
                matches = re.finditer(pattern + r'[A-Za-z0-9_-]{10,}', ci)
                for m in matches:
                    pos = m.start()
                    line_start = ci.rfind('\n', 0, pos) + 1
                    line = ci[line_start:ci.find('\n', pos)]
                    if 'os.getenv' not in line and '# ' + pattern not in line:
                        print(f"FAIL: Possible hardcoded secret in {py_file.name}: {line.strip()[:60]}")
                        secrets_found = True

    if not secrets_found:
        print("PASS: No hardcoded proprietary secrets found")

    print("=" * 70)
    if issues:
        print("FAIL: " + "; ".join(issues))
        return False

    print("PASS: All static checks passed")
    return True


def _run_runtime_checks():
    """Runtime checks - requires .env and BOT_TOKEN."""
    print("WOS-M System Check - RUNTIME MODE")
    print("=" * 70)

    issues = []
    demo_mode = os.getenv("WOSM_DEMO_MODE", "false").lower() == "true"

    if not os.getenv("DISCORD_BOT_TOKEN"):
        issues.append("DISCORD_BOT_TOKEN not set (required)")
    else:
        print("PASS: DISCORD_BOT_TOKEN configured")

    if demo_mode:
        print("WARN: DEMO MODE ACTIVE")
    else:
        has_adapter = Path(__file__).parent / "integrations" / "wos_open_source_adapter.py"
        has_ocr = False
        try:
            import ddddocr
            has_ocr = True
            print("PASS: ddddocr installed")
        except ImportError:
            issues.append("ddddocr not installed")
        has_gift_api = bool(os.getenv("GIFT_CODE_API_BASE_URL") or os.getenv("WOS_GIFT_PUBLIC_ENDPOINT"))
        if has_gift_api:
            print("PASS: Gift API configured")
        elif has_adapter.exists():
            print("PASS: Open source adapter available")
            if not (os.getenv("EXTERNAL_PROVIDER_API_KEY") or os.getenv("EXTERNAL_PROVIDER_LOGIN_TOKEN")):
                issues.append("External provider not configured")

    print("=" * 70)
    if issues:
        print("FAIL: " + "; ".join(issues))
        return False
    print("PASS: All runtime checks passed")
    return True


def main():
    if "--check-runtime" in sys.argv:
        sys.exit(0 if _run_runtime_checks() else 1)
    elif "--check" in sys.argv:
        sys.exit(0 if check_system() else 1)
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
