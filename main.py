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
    print("WOS-M System Check - STRICT MODE")
    print("=" * 70)
    
    issues = []
    warnings = []
    demo_mode = os.getenv("WOSM_DEMO_MODE", "false").lower() == "true"
    
    if not os.path.exists(".env"):
        issues.append(".env file not found")
    else:
        print("PASS: .env file found")
    
    if not os.getenv("DISCORD_BOT_TOKEN"):
        issues.append("DISCORD_BOT_TOKEN not set")
    else:
        print("PASS: DISCORD_BOT_TOKEN configured")
    
    if demo_mode:
        warnings.append("DEMO MODE ACTIVE")
        print("WARN: WOSM_DEMO_MODE=true")
    else:
        print("PASS: Production mode")
        if not os.getenv("GIFT_CODE_API_BASE_URL"):
            issues.append("GIFT_CODE_API_BASE_URL not set")
        else:
            print("PASS: Gift API configured")
        if not os.getenv("CAPTCHA_SERVICE_URL") or not os.getenv("CAPTCHA_SERVICE_TOKEN"):
            issues.append("CAPTCHA_SERVICE_URL/TOKEN not set")
        else:
            print("PASS: Captcha configured")
    
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
    
    # Check database columns
    db_file = Path(__file__).parent / "core" / "database.py"
    for col in ["auto_gift_enabled", "gift_channel_id", "member_count"]:
        if col not in open(db_file).read():
            issues.append(f"Missing column: {col}")
    
    # Check _run_migrations
    with open(db_file) as f:
        c = f.read()
        if "async def _run_migrations" in c and "pass" not in c.split("async def _run_migrations")[1].split("async def")[0]:
            print("PASS: _run_migrations implemented")
        else:
            issues.append("_run_migrations not implemented")
    
    print("=" * 70)
    if issues:
        print("FAIL: " + "; ".join(issues))
        return False
    print("PASS: All checks passed")
    if demo_mode:
        print("WARN: DEMO MODE - NOT FOR PRODUCTION")
    return True

def main():
    if "--check" in sys.argv:
        sys.exit(0 if check_system() else 1)
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
