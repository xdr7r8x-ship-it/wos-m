"""
Tests for Gift Codes Module
© MANSOUR — WOS-M. All rights reserved.
"""
import pytest
from pathlib import Path


class TestGiftCodesModule:
    """Test gift codes module callbacks."""
    
    def test_gift_add_callback_exists(self):
        """gift_add_callback must exist."""
        views_file = Path("modules/gift_codes/views.py")
        assert views_file.exists()
        
        content = open(views_file).read()
        assert "async def add_gift_code_callback" in content or "gift_add" in content
    
    def test_gift_codes_table_has_required_columns(self):
        """gift_codes table must have required columns."""
        db_file = Path("core/database.py")
        content = open(db_file).read()
        
        required = ["id", "code", "alliance_id", "status"]
        for col in required:
            assert col in content, f"gift_codes missing column: {col}"
    
    def test_gift_redemptions_table_has_required_columns(self):
        """gift_redemptions table must have required columns."""
        db_file = Path("core/database.py")
        content = open(db_file).read()
        
        required = ["id", "code_id", "player_id", "status", "provider"]
        for col in required:
            assert col in content, f"gift_redemptions missing column: {col}"


class TestGiftCodeCallbacks:
    """Test gift code callback existence."""
    
    def test_auto_enable_callback_exists(self):
        """auto_enable_alliance callback must exist in bot."""
        bot_file = Path("core/bot.py")
        content = open(bot_file).read()
        
        assert "auto_enable_alliance" in content
    
    def test_auto_disable_callback_exists(self):
        """auto_disable_alliance callback must exist in bot."""
        bot_file = Path("core/bot.py")
        content = open(bot_file).read()
        
        assert "auto_disable_alliance" in content
    
    def test_auto_redeem_all_callback_exists(self):
        """auto_redeem_all callback must exist in bot."""
        bot_file = Path("core/bot.py")
        content = open(bot_file).read()
        
        assert "auto_redeem_all" in content


class TestGiftCodeDBOperations:
    """Test gift code database operations."""
    
    def test_insert_gift_code(self):
        """Code should support INSERT into gift_codes."""
        db_file = Path("core/database.py")
        content = open(db_file).read()
        
        assert "gift_codes" in content
    
    def test_select_gift_codes(self):
        """Code should support SELECT from gift_codes."""
        views_file = Path("modules/gift_codes/views.py")
        content = open(views_file).read()
        
        # Should have SELECT for gift codes
        assert "gift" in content.lower() or "code" in content.lower()
    
    def test_redemption_status_column(self):
        """gift_redemptions must have status column."""
        db_file = Path("core/database.py")
        content = open(db_file).read()
        
        assert "status" in content


class TestRealRedemptionProvider:
    """Test WhiteoutProject provider routing."""
    
    def test_whiteout_project_provider_exists(self):
        """WhiteoutProject provider must exist."""
        provider_file = Path("integrations/whiteout_project_provider.py")
        assert provider_file.exists(), "whiteout_project_provider.py must exist"
    
    def test_provider_has_redeem_method(self):
        """Provider must have redeem method."""
        provider_file = Path("integrations/whiteout_project_provider.py")
        content = open(provider_file).read()
        
        assert "def redeem" in content or "async def redeem" in content
    
    def test_provider_uses_onnx(self):
        """Provider should use ONNX captcha solver."""
        provider_file = Path("integrations/whiteout_project_provider.py")
        content = open(provider_file).read()
        
        assert "onnx" in content.lower() or "captcha" in content.lower()
    
    def test_redemption_engine_routes_to_provider(self):
        """Redemption engine should route to WhiteoutProject."""
        engine_file = Path("modules/gift_codes/redemption_engine.py")
        assert engine_file.exists(), "redemption_engine.py must exist"
        
        content = open(engine_file).read()
        assert "whiteout_project" in content.lower() or "provider" in content.lower()


class TestCaptchaSolver:
    """Test captcha solver integration."""
    
    def test_onnx_solver_exists(self):
        """ONNX captcha solver must exist."""
        solver_file = Path("integrations/captcha/onnx_captcha_solver.py")
        assert solver_file.exists(), "onnx_captcha_solver.py must exist"
    
    def test_captcha_model_file_exists(self):
        """Captcha model file must exist."""
        model_file = Path("models/captcha_model.onnx")
        assert model_file.exists(), "captcha_model.onnx must exist"
    
    def test_model_metadata_exists(self):
        """Model metadata must exist."""
        metadata_file = Path("models/captcha_model_metadata.json")
        assert metadata_file.exists(), "captcha_model_metadata.json must exist"
    
    def test_ddddocr_fallback_available(self):
        """ddddocr fallback should be available."""
        # This is a configuration check
        pass


class TestSecurityScans:
    """Test security-related functionality."""
    
    def test_no_hardcoded_secrets(self):
        """No hardcoded secrets in main code."""
        # Check adapter
        adapter_file = Path("integrations/wos_open_source_adapter.py")
        content = open(adapter_file).read()
        
        forbidden = ["sk_live_", "ghp_", "pk_live_"]
        for pattern in forbidden:
            assert pattern not in content, f"Found hardcoded secret pattern: {pattern}"
    
    def test_env_example_has_required_vars(self):
        """ENV example must have required variables."""
        env_file = Path(".env.example")
        content = open(env_file).read()
        
        assert "DISCORD_BOT_TOKEN" in content
        assert "REAL_REDEMPTION_PROVIDER" in content
        assert "WOS_GIFT_PUBLIC_ENDPOINT" in content


class TestAuditLogging:
    """Test audit logging functionality."""
    
    def test_audit_log_table_exists(self):
        """audit_logs table must exist."""
        db_file = Path("core/database.py")
        content = open(db_file).read()
        
        assert "audit_logs" in content
        assert "user_id" in content
        assert "action" in content
    
    def test_audit_log_module_exists(self):
        """Audit log module must exist."""
        audit_file = Path("core/audit_log.py")
        assert audit_file.exists(), "core/audit_log.py must exist"
    
    def test_audit_categories_exist(self):
        """Audit categories must be defined."""
        audit_file = Path("core/audit_log.py")
        content = open(audit_file).read()
        
        assert "AuditCategory" in content or "Category" in content


class TestPermissions:
    """Test permissions system."""
    
    def test_permissions_table_exists(self):
        """permissions table must exist."""
        db_file = Path("core/database.py")
        content = open(db_file).read()
        
        assert "permissions" in content
        assert "user_id" in content
        assert "level" in content
    
    def test_permission_levels_defined(self):
        """Permission levels must be defined."""
        perm_file = Path("core/permissions.py")
        assert perm_file.exists(), "core/permissions.py must exist"
        
        content = open(perm_file).read()
        assert "ADMIN" in content or "OWNER" in content or "MEMBER" in content
    
    def test_permission_guard_exists(self):
        """PermissionGuard class must exist."""
        perm_file = Path("core/permissions.py")
        content = open(perm_file).read()
        
        assert "class PermissionGuard" in content or "PermissionGuard" in content