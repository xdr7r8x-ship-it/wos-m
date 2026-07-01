"""
Tests for Gift Code Redemption Provider Routing
© MANSOUR — WOS-M. All rights reserved.

Tests that redemption_engine uses the correct provider based on REAL_REDEMPTION_PROVIDER setting.
"""
import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch


class TestProviderRouting:
    """Test provider routing in redemption_engine."""
    
    def test_whiteout_project_provider_imported(self):
        """Test that whiteout_project_provider is imported in redemption_engine."""
        from modules.gift_codes.redemption_engine import whiteout_project_provider
        from integrations.whiteout_project_provider import RedemptionStatus as WPStatus
        assert whiteout_project_provider is not None
        assert WPStatus is not None
    
    def test_real_redemption_provider_setting_exists(self):
        """Test that REAL_REDEMPTION_PROVIDER setting exists."""
        from config.settings import settings
        provider = getattr(settings.api, "real_redemption_provider", None)
        assert provider is not None
        assert provider == "WhiteoutProject"
    
    def test_redemption_engine_has_whiteout_method(self):
        """Test that RedemptionEngine has _redeem_via_whiteout_project method."""
        from modules.gift_codes.redemption_engine import RedemptionEngine
        engine = RedemptionEngine()
        assert hasattr(engine, "_redeem_via_whiteout_project")
        assert callable(getattr(engine, "_redeem_via_whiteout_project"))
    
    def test_provider_routing_in_redeem_code(self):
        """Test that redeem_code has provider routing logic."""
        from modules.gift_codes import redemption_engine
        import inspect
        
        source = inspect.getsource(redemption_engine.RedemptionEngine.redeem_code)
        assert "real_redemption_provider" in source
        assert "whiteoutproject" in source.lower()
    
    def test_gift_code_client_not_used_for_whiteout(self):
        """Test that gift_code_client is not used when provider is WhiteoutProject."""
        from modules.gift_codes import redemption_engine
        import inspect
        
        # Get the source of _redeem_via_whiteout_project method
        source = inspect.getsource(redemption_engine.RedemptionEngine._redeem_via_whiteout_project)
        
        # Should NOT call gift_code_client.redeem_code
        assert "gift_code_client.redeem_code" not in source
        # Should call whiteout_project_provider.redeem
        assert "whiteout_project_provider.redeem" in source
    
    def test_status_mapping_complete(self):
        """Test that all API statuses are mapped to model statuses."""
        from modules.gift_codes.redemption_engine import RedemptionEngine
        from integrations.whiteout_project_provider import RedemptionStatus as WPStatus
        from modules.gift_codes.models import GiftCodeStatus as ModelStatus
        
        engine = RedemptionEngine()
        
        # Check that _redeem_via_whiteout_project has status mapping
        import inspect
        source = inspect.getsource(engine._redeem_via_whiteout_project)
        
        # All key statuses should be mapped
        expected_mappings = [
            "WPStatus.SUCCESS",
            "WPStatus.RECEIVED",
            "WPStatus.TIME_ERROR",
            "WPStatus.CDK_NOT_FOUND",
            "WPStatus.USAGE_LIMIT",
            "WPStatus.NOT_LOGIN",
            "WPStatus.UNAUTHORIZED",
            "WPStatus.CAPTCHA_INVALID",
        ]
        
        for status in expected_mappings:
            assert status in source, f"Missing mapping for {status}"


class TestWhiteoutProjectProvider:
    """Test WhiteoutProject provider implementation."""
    
    def test_provider_has_real_api_endpoints(self):
        """Test that provider has real CenturyGame API endpoints."""
        from integrations.whiteout_project_provider import WhiteoutProjectProvider
        
        provider = WhiteoutProjectProvider()
        
        assert hasattr(provider, "API_PLAYER")
        assert hasattr(provider, "API_CAPTCHA")
        assert hasattr(provider, "API_REDEEM")
        
        # Should be CenturyGame endpoints
        assert "centurygame.com" in provider.API_PLAYER
        assert "centurygame.com" in provider.API_CAPTCHA
        assert "centurygame.com" in provider.API_REDEEM
    
    def test_provider_has_redeem_method(self):
        """Test that provider has redeem method."""
        from integrations.whiteout_project_provider import WhiteoutProjectProvider
        
        provider = WhiteoutProjectProvider()
        assert hasattr(provider, "redeem")
        assert callable(provider.redeem)
    
    def test_provider_has_player_lookup(self):
        """Test that provider has player lookup method."""
        from integrations.whiteout_project_provider import WhiteoutProjectProvider
        
        provider = WhiteoutProjectProvider()
        assert hasattr(provider, "get_player")
        assert callable(provider.get_player)
    
    def test_provider_has_captcha_fetch(self):
        """Test that provider has captcha fetch method."""
        from integrations.whiteout_project_provider import WhiteoutProjectProvider
        
        provider = WhiteoutProjectProvider()
        assert hasattr(provider, "fetch_captcha")
        assert callable(provider.fetch_captcha)
    
    def test_redemption_status_enum_complete(self):
        """Test that RedemptionStatus enum has all expected values."""
        from integrations.whiteout_project_provider import RedemptionStatus
        
        expected_statuses = [
            "SUCCESS", "RECEIVED", "SAME_TYPE_EXCHANGE",
            "TIME_ERROR", "CDK_NOT_FOUND", "USAGE_LIMIT",
            "NOT_LOGIN", "UNAUTHORIZED", "LOGIN_FAILED",
            "CAPTCHA_ERROR", "CAPTCHA_INVALID", "CAPTCHA_TOO_FREQUENT",
            "SOLVER_ERROR", "OCR_DISABLED", "SIGN_ERROR",
            "TIMEOUT_RETRY", "CONNECTION_ERROR", "ERROR",
            "UNKNOWN_API_RESPONSE"
        ]
        
        for status_name in expected_statuses:
            assert hasattr(RedemptionStatus, status_name), f"Missing status: {status_name}"


class TestDistributionVsRedemptionSeparation:
    """Test separation between Distribution and Real Redemption."""
    
    def test_real_redemption_provider_setting_documented(self):
        """Test that REAL_REDEMPTION_PROVIDER is documented in .env.example."""
        import os
        env_example_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            ".env.example"
        )
        
        if os.path.exists(env_example_path):
            with open(env_example_path) as f:
                content = f.read()
            
            assert "REAL_REDEMPTION_PROVIDER" in content


class TestDatabaseSchema:
    """Test database schema for provider tracking."""
    
    def test_redemption_record_has_provider_field(self):
        """Test that gift_redemptions table has provider field."""
        from modules.gift_codes.service import GiftCodeService
        
        service = GiftCodeService()
        
        # Check add_redemption accepts provider parameter
        import inspect
        sig = inspect.signature(service.add_redemption)
        params = list(sig.parameters.keys())
        
        assert "provider" in params, "add_redemption should accept 'provider' parameter"
        assert "api_status" in params, "add_redemption should accept 'api_status' parameter"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
