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
        print("WARN: WOSM_DEMO_MODE=true (Demo mode - no real redemption)")
        print("INFO: Gift API not configured (demo mode)")
    else:
        print("PASS: Production mode")
        
        # Check Open Source Adapter
        has_adapter = Path(__file__).parent / "integrations" / "wos_open_source_adapter.py"
        
        # Check if we have OCR capability
        has_ocr = False
        try:
            import ddddocr
            has_ocr = True
            print("PASS: ddddocr installed (OCR available)")
        except ImportError:
            print("FAIL: ddddocr not installed")
            issues.append("ddddocr not installed")
        
        has_local_ocr = os.getenv("CAPTCHA_SERVICE_URL") == "local-ddddocr"
        has_external_captcha = bool(
            os.getenv("CAPTCHA_SERVICE_URL") and 
            os.getenv("CAPTCHA_SERVICE_TOKEN") and 
            not has_local_ocr
        )
        has_gift_api = bool(
            os.getenv("GIFT_CODE_API_BASE_URL") or 
            os.getenv("WOS_GIFT_PUBLIC_ENDPOINT")
        )
        
        if has_ocr or has_local_ocr:
            print("PASS: OCR solution available")
        elif has_external_captcha:
            print("PASS: External CAPTCHA service configured")
        else:
            issues.append("No OCR solution - install ddddocr or set CAPTCHA_SERVICE")
        
        if has_gift_api:
            print("PASS: Gift API configured")
        elif has_adapter.exists():
            print("PASS: Open source adapter available")
            
            # Check if external provider is configured
            has_external_provider = bool(os.getenv("EXTERNAL_PROVIDER_API_KEY"))
            has_login_token = bool(os.getenv("EXTERNAL_PROVIDER_LOGIN_TOKEN"))
            provider_name = os.getenv("EXTERNAL_PROVIDER_NAME", "Built-in")
            
            if has_external_provider:
                print(f"PASS: External provider configured ({provider_name})")
            elif has_login_token:
                print(f"PASS: Login token configured (Built-in adapter)")
            else:
                print("FAIL: Missing authorized provider credentials")
                print("INFO: Real redemption is LOCKED")
                print("INFO: Configure EXTERNAL_PROVIDER_API_KEY or EXTERNAL_PROVIDER_LOGIN_TOKEN")
                issues.append("External provider not configured")
        else:
            issues.append("No Gift API configured")
    
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
    
    # Check Open Source Adapter
    print("\n🔌 Checking Open Source Adapter...")
    adapter_file = Path(__file__).parent / "integrations" / "wos_open_source_adapter.py"
    if adapter_file.exists():
        print("PASS: Open source adapter exists")
        
        # Check for OCR
        try:
            import ddddocr
            print("PASS: ddddocr installed (OCR available)")
        except ImportError:
            print("WARN: ddddocr not installed - using external CAPTCHA or Demo Mode")
            if os.getenv("CAPTCHA_SERVICE_URL") and os.getenv("CAPTCHA_SERVICE_TOKEN"):
                print("PASS: External CAPTCHA service configured")
            else:
                print("WARN: No CAPTCHA solution available")
    else:
        warnings.append("Open source adapter not found")
    
    # Check WhiteoutProject Provider (Real Redemption)
    print("\n🎁 Checking WhiteoutProject Provider (Real Redemption)...")
    engine_file = Path(__file__).parent / "modules" / "gift_codes" / "redemption_engine.py"
    wp_provider_file = Path(__file__).parent / "integrations" / "whiteout_project_provider.py"
    
    if engine_file.exists():
        engine_content = open(engine_file).read()
        
        # Check imports
        if "whiteout_project_provider" in engine_content:
            print("PASS: redemption_engine imports whiteout_project_provider")
        else:
            issues.append("redemption_engine.py does not import whiteout_project_provider")
        
        # Check provider routing
        if "real_redemption_provider" in engine_content:
            print("PASS: Provider routing implemented in redemption_engine")
        else:
            issues.append("redemption_engine.py does not have provider routing")
        
        # Check redeem call
        if "whiteout_project_provider.redeem" in engine_content:
            print("PASS: redemption_engine calls whiteout_project_provider.redeem")
        else:
            issues.append("redemption_engine.py does not call whiteout_project_provider.redeem")
    
    if wp_provider_file.exists():
        print("PASS: whiteout_project_provider.py file exists")
        
        # Check for real API methods
        provider_content = open(wp_provider_file).read()
        if "/api/player" in provider_content and "/api/captcha" in provider_content and "/api/gift_code" in provider_content:
            print("PASS: Real API endpoints implemented in provider")
        else:
            issues.append("Provider missing real API endpoints")
    else:
        issues.append("whiteout_project_provider.py not found")
    
    # Check .env.example for REAL_REDEMPTION_PROVIDER
    env_example = Path(__file__).parent / ".env.example"
    if env_example.exists():
        env_content = open(env_example).read()
        if "REAL_REDEMPTION_PROVIDER" in env_content:
            print("PASS: REAL_REDEMPTION_PROVIDER documented in .env.example")
        else:
            issues.append("REAL_REDEMPTION_PROVIDER missing from .env.example")
    
    # Report distribution vs redemption separation
    print("\n📊 Provider Status:")
    print(f"   Real Redemption Provider: {getattr(settings.api, 'real_redemption_provider', 'Not Set')}")
    if engine_file.exists() and "whiteout_project_provider.redeem" in open(engine_file).read():
        print("   Real Redemption Route: Wired")
    else:
        print("   Real Redemption Route: NOT WIRED")
    
    # Check for proprietary secrets in code
    print("\n🔒 Checking for proprietary secrets...")
    forbidden_patterns = ["sk_live_", "pk_live_", "api_key_", "secret_key_", "ghp_", "gho_", "ghs_"]
    secrets_found = False
    for py_file in list(Path(__file__).parent.rglob("*.py")):
        if py_file.name.startswith("test_") or "test" in str(py_file):
            continue
        with open(py_file) as f:
            content = f.read()
            for pattern in forbidden_patterns:
                # Look for pattern followed by actual secret (not just variable name)
                import re
                matches = re.finditer(pattern + r'[A-Za-z0-9_-]{10,}', content)
                for m in matches:
                    # Check if this is in a comment or string assignment
                    pos = m.start()
                    line_start = content.rfind('\n', 0, pos) + 1
                    line = content[line_start:content.find('\n', pos)]
                    if 'os.getenv' not in line and '# ' + pattern not in line:
                        print(f"FAIL: Possible hardcoded secret in {py_file.name}: {line.strip()[:60]}")
                        secrets_found = True
    
    if not secrets_found:
        print("PASS: No hardcoded proprietary secrets found")
    
    print("=" * 70)
    if issues:
        print("FAIL: " + "; ".join(issues))
        return False
    
    if warnings:
        print("WARN: " + "; ".join(warnings))
    
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
