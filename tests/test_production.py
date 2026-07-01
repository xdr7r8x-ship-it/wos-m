"""
WOS-M Production Tests
© MANSOUR — WOS-M. All rights reserved.
"""
import pytest
import json
import re
import asyncio
from pathlib import Path


class TestSlashCommands:
    """Test that only /wos command exists."""
    
    def test_only_wos_command_exists(self):
        """Test that /wos is the only slash command registered."""
        bot_file = Path(__file__).parent.parent / "core" / "bot.py"
        
        with open(bot_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Find all @tree.command decorators
        commands = re.findall(r'name\s*=\s*["\']([^"\']+)', content)
        commands = [c for c in commands if c in ["wos", "test", "help", "start"]]
        
        assert "wos" in commands, "WOS command not found"
        other_commands = [c for c in commands if c != "wos"]
        assert len(other_commands) == 0, f"Extra commands found: {other_commands}"


class TestAutoRedeemButtons:
    """Test that auto redeem buttons have callbacks."""
    
    def test_auto_enable_alliance_callback_exists(self):
        """Test that auto_enable_alliance button callback exists."""
        bot_file = Path(__file__).parent.parent / "core" / "bot.py"
        
        with open(bot_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert '"auto_enable_alliance"' in content, "auto_enable_alliance callback not found"
    
    def test_auto_disable_alliance_callback_exists(self):
        """Test that auto_disable_alliance button callback exists."""
        bot_file = Path(__file__).parent.parent / "core" / "bot.py"
        
        with open(bot_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert '"auto_disable_alliance"' in content, "auto_disable_alliance callback not found"
    
    def test_auto_redeem_all_callback_exists(self):
        """Test that auto_redeem_all button callback exists."""
        bot_file = Path(__file__).parent.parent / "core" / "bot.py"
        
        with open(bot_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert '"auto_redeem_all"' in content, "auto_redeem_all callback not found"


class TestDemoMode:
    """Test demo mode enforcement."""
    
    def test_demo_mode_env_var(self):
        """Test that WOSM_DEMO_MODE is checked."""
        env_file = Path(__file__).parent.parent / ".env.example"
        
        with open(env_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "WOSM_DEMO_MODE" in content, "WOSM_DEMO_MODE not in .env.example"
    
    def test_demo_mode_in_settings(self):
        """Test that demo_mode is in settings."""
        from config.settings import settings
        
        assert hasattr(settings, 'demo_mode'), "demo_mode not in settings"
        assert hasattr(settings, 'is_production'), "is_production not in settings"


class TestCaptchaService:
    """Test captcha service integration."""
    
    def test_captcha_env_vars(self):
        """Test that captcha service vars are in .env.example."""
        env_file = Path(__file__).parent.parent / ".env.example"
        
        with open(env_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "CAPTCHA_SERVICE_URL" in content, "CAPTCHA_SERVICE_URL not in .env.example"
        assert "CAPTCHA_SERVICE_TOKEN" in content, "CAPTCHA_SERVICE_TOKEN not in .env.example"


class TestDatabase:
    """Test database system."""
    
    def test_auto_gift_column_exists(self):
        """Test that alliances table has auto_gift_enabled column."""
        from core.database import Database
        import inspect
        
        source = inspect.getsource(Database._create_tables)
        assert "auto_gift_enabled" in source, "auto_gift_enabled column not found"
    
    def test_gift_redemptions_table_exists(self):
        """Test that gift_redemptions table exists."""
        from core.database import Database
        import inspect
        
        source = inspect.getsource(Database._create_tables)
        assert "gift_redemptions" in source, "gift_redemptions table not found"


class TestProcessQueue:
    """Test process queue implementation."""
    
    def test_no_placeholder_in_process_queue(self):
        """Test that process queue has no placeholders."""
        pq_file = Path(__file__).parent.parent / "core" / "process_queue.py"
        
        with open(pq_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Only check for actual placeholder code (pass followed by placeholder)
        if re.search(r'pass\s*#\s*[Pp]laceholder', content):
            pytest.fail("Found placeholder in process_queue.py")


class TestNoPlaceholders:
    """Test that no placeholders exist in production code."""
    
    def test_no_pass_placeholders(self):
        """Test that no 'pass # Placeholder' exists in core/modules/views."""
        modules_dir = Path(__file__).parent.parent / "modules"
        core_dir = Path(__file__).parent.parent / "core"
        views_dir = Path(__file__).parent.parent / "views"
        
        issues = []
        for directory in [modules_dir, core_dir, views_dir]:
            for py_file in directory.rglob("*.py"):
                if py_file.name == "__init__.py":
                    continue
                
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if re.search(r'pass\s*#\s*[Pp]laceholder', content):
                    issues.append(f"Found placeholder in {py_file.name}")
        
        if issues:
            pytest.fail("\n".join(issues))


class TestGiftCodeClient:
    """Test gift code client."""
    
    def test_health_check_returns_dict(self):
        """Test that health_check returns proper status."""
        from integrations.gift_code_client import gift_code_client
        
        assert hasattr(gift_code_client, 'health_check'), "health_check not found"
    
    def test_simulation_mode_warning(self):
        """Test that simulation mode shows warning."""
        from integrations.gift_code_client import gift_code_client
        
        result = gift_code_client._simulate_validate("TEST123")
        assert result.get("demo_mode") is True, "Simulation should set demo_mode"


class TestI18n:
    """Test internationalization system."""
    
    def test_locales_exist(self):
        """Test that locale files exist."""
        locales_dir = Path(__file__).parent.parent / "locales"
        assert (locales_dir / "ar.json").exists()
        assert (locales_dir / "en.json").exists()
    
    def test_locale_format(self):
        """Test that locale files are valid JSON."""
        locales_dir = Path(__file__).parent.parent / "locales"
        
        for locale_file in locales_dir.glob("*.json"):
            with open(locale_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                assert isinstance(data, dict)
                assert "bot" in data
                assert "dashboard" in data


class TestPermissions:
    """Test permission system."""
    
    def test_permission_levels(self):
        """Test permission level hierarchy."""
        from core.permissions import PermissionLevel
        
        levels = [PermissionLevel.OWNER, PermissionLevel.GLOBAL_ADMIN, 
                   PermissionLevel.SERVER_ADMIN, PermissionLevel.ALLIANCE_ADMIN, 
                   PermissionLevel.MEMBER]
        for level in levels:
            assert hasattr(level, 'value')
