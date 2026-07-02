"""
Test: Operations Panel
Tests for the Operations Control Panel buttons and callbacks.
© MANSOUR — WOS-M. All rights reserved.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


class TestOperationsPanelButtons:
    """Test that all operations panel buttons exist and have proper structure."""

    def test_operations_panel_imports(self):
        """Test that OperationsPanelView can be imported."""
        from modules.operations.views import OperationsPanelView
        assert OperationsPanelView is not None

    def test_operations_panel_creates(self):
        """Test that OperationsPanelView can be created."""
        from modules.operations.views import OperationsPanelView
        view = OperationsPanelView(owner_id=12345)
        assert view is not None
        assert view.owner_id == 12345
        assert len(view.children) > 0

    def test_all_buttons_have_custom_ids(self):
        """Test that all buttons have custom_id set."""
        from modules.operations.views import OperationsPanelView
        
        view = OperationsPanelView(owner_id=12345)
        buttons = [c for c in view.children if hasattr(c, 'custom_id') and hasattr(c, 'callback')]
        
        assert len(buttons) >= 10, f"Expected at least 10 buttons, found {len(buttons)}"
        
        expected_ids = [
            'ops_health_check',
            'ops_metrics',
            'ops_incidents',
            'ops_alerts',
            'ops_backup',
            'ops_rollback',
            'ops_upgrade',
            'ops_self_heal',
            'ops_reports',
            'ops_settings'
        ]
        
        actual_ids = [b.custom_id for b in buttons]
        for expected_id in expected_ids:
            assert expected_id in actual_ids, f"Button '{expected_id}' not found"

    def test_all_buttons_have_callbacks(self):
        """Test that all buttons have callbacks."""
        from modules.operations.views import OperationsPanelView
        
        view = OperationsPanelView(owner_id=12345)
        buttons = [c for c in view.children if hasattr(c, 'custom_id') and hasattr(c, 'callback')]
        
        for button in buttons:
            assert button.callback is not None, f"Button '{button.custom_id}' has no callback"
            assert callable(button.callback), f"Button '{button.custom_id}' callback is not callable"

    def test_no_placeholder_callbacks(self):
        """Test that no buttons have placeholder/empty callbacks."""
        from modules.operations.views import OperationsPanelView
        
        view = OperationsPanelView(owner_id=12345)
        buttons = [c for c in view.children if hasattr(c, 'custom_id')]
        
        for button in buttons:
            # Verify the callback is not just a pass/empty
            if hasattr(button, '_callback') and button._callback:
                import inspect
                source = inspect.getsource(button._callback)
                # Should not contain placeholder patterns
                assert 'placeholder' not in source.lower(), f"Button '{button.custom_id}' has placeholder"
                assert 'pass  # TODO' not in source, f"Button '{button.custom_id}' has TODO"


class TestOperationsCallbacks:
    """Test that operations callbacks function correctly."""

    @pytest.mark.asyncio
    async def test_health_check_callback_returns_embed(self):
        """Test that health check callback returns proper embed."""
        from modules.operations.views import HealthCheckButton
        
        button = HealthCheckButton(label="Test", custom_id="ops_health_check")
        interaction = MagicMock()
        interaction.response = MagicMock()
        interaction.response.send_message = AsyncMock()
        
        # Mock health check at the correct location
        with patch('core.operations.health.run_full_health_check') as mock_health:
            mock_report = MagicMock()
            mock_report.overall_status.value = "healthy"
            mock_report.version = "1.0.0"
            mock_report.uptime_seconds = 3600
            mock_report.checks = []
            mock_report.checks_count = 10
            mock_report.suggested_action = None
            mock_report.timestamp.isoformat = lambda: "2024-01-01T00:00:00"
            mock_health.return_value = mock_report
            
            await button.callback(interaction)
            
            # Verify send_message was called
            assert interaction.response.send_message.called

    @pytest.mark.asyncio
    async def test_metrics_callback_returns_embed(self):
        """Test that metrics callback returns proper embed."""
        from modules.operations.views import MetricsButton
        
        button = MetricsButton(label="Test", custom_id="ops_metrics")
        interaction = MagicMock()
        interaction.response = MagicMock()
        interaction.response.send_message = AsyncMock()
        
        with patch('core.operations.metrics.get_metrics_collector') as mock_collector:
            collector = MagicMock()
            collector.collect_snapshot.return_value = MagicMock()
            collector.get_uptime_formatted.return_value = "1h"
            mock_collector.return_value = collector
            
            await button.callback(interaction)
            
            assert interaction.response.send_message.called


class TestOperationsRegistry:
    """Test that operations buttons are registered in interaction registry."""

    def test_ops_buttons_in_registry(self):
        """Test that ops_ buttons are registered in INTERACTION_REGISTRY."""
        from core.interaction_registry import INTERACTION_REGISTRY
        
        ops_buttons = [k for k in INTERACTION_REGISTRY.keys() if k.startswith('ops_')]
        assert len(ops_buttons) >= 10, f"Expected at least 10 ops_ buttons in registry, found {len(ops_buttons)}"

    def test_ops_buttons_have_proper_permissions(self):
        """Test that ops_ buttons have OWNER permission."""
        from core.interaction_registry import INTERACTION_REGISTRY
        from core.permissions import PermissionLevel
        
        ops_buttons = [k for k in INTERACTION_REGISTRY.keys() if k.startswith('ops_')]
        
        for btn_id in ops_buttons:
            spec = INTERACTION_REGISTRY[btn_id]
            assert spec.required_permission == PermissionLevel.OWNER, \
                f"Button '{btn_id}' should require OWNER permission"

    def test_ops_buttons_have_module_set(self):
        """Test that ops_ buttons have module set to 'operations'."""
        from core.interaction_registry import INTERACTION_REGISTRY
        
        ops_buttons = [k for k in INTERACTION_REGISTRY.keys() if k.startswith('ops_')]
        
        for btn_id in ops_buttons:
            spec = INTERACTION_REGISTRY[btn_id]
            assert spec.module == "operations", \
                f"Button '{btn_id}' should have module='operations'"

    def test_ops_buttons_owner_only(self):
        """Test that ops_ buttons are owner_only."""
        from core.interaction_registry import INTERACTION_REGISTRY
        
        ops_buttons = [k for k in INTERACTION_REGISTRY.keys() if k.startswith('ops_')]
        
        for btn_id in ops_buttons:
            spec = INTERACTION_REGISTRY[btn_id]
            assert spec.owner_only is True, \
                f"Button '{btn_id}' should be owner_only=True"


class TestOperationsSecurity:
    """Test that operations system is secure."""

    def test_backup_excludes_sensitive_files(self):
        """Test that backup excludes sensitive files."""
        from core.operations.backup import EXCLUDED_PATTERNS
        
        sensitive_patterns = ['.env', '*.pyc', '__pycache__', '*.log', 'node_modules']
        for pattern in sensitive_patterns:
            assert pattern in EXCLUDED_PATTERNS, f"Pattern '{pattern}' should be excluded from backup"

    def test_self_healing_policy_blocks_dangerous_actions(self):
        """Test that self-healing policy blocks dangerous actions."""
        from core.operations.self_healing import RecoveryAction, SelfHealingPolicy
        
        policy = SelfHealingPolicy()
        
        # Should have blocked actions
        assert RecoveryAction.DISABLE_FEATURE in policy.blocked_actions

    def test_rollback_requires_confirmation(self):
        """Test that rollback requires explicit confirmation."""
        from core.operations.rollback import RollbackManager
        
        # Verify the method signature requires confirmation
        import inspect
        sig = inspect.signature(RollbackManager.rollback_to_backup)
        params = list(sig.parameters.keys())
        assert 'confirmation' in params


class TestOperationsComponents:
    """Test individual operations components."""

    def test_health_module_imports(self):
        """Test that health module imports correctly."""
        from core.operations.health import run_full_health_check, HealthStatus
        
        assert run_full_health_check is not None
        assert HealthStatus is not None

    def test_backup_module_imports(self):
        """Test that backup module imports correctly."""
        from core.operations.backup import get_backup_manager, BackupStatus
        
        assert get_backup_manager is not None
        assert BackupStatus is not None

    def test_alerts_module_imports(self):
        """Test that alerts module imports correctly."""
        from core.operations.alerts import AlertManager, AlertSeverity
        
        assert AlertManager is not None
        assert AlertSeverity is not None

    def test_self_healing_module_imports(self):
        """Test that self-healing module imports correctly."""
        from core.operations.self_healing import get_self_healing_engine, RecoveryAction
        
        assert get_self_healing_engine is not None
        assert RecoveryAction is not None

    def test_upgrades_module_imports(self):
        """Test that upgrades module imports correctly."""
        from core.operations.upgrades import get_upgrade_manager, UpgradeStatus
        
        assert get_upgrade_manager is not None
        assert UpgradeStatus is not None

    def test_rollback_module_imports(self):
        """Test that rollback module imports correctly."""
        from core.operations.rollback import get_rollback_manager
        
        assert get_rollback_manager is not None

    def test_metrics_module_imports(self):
        """Test that metrics module imports correctly."""
        from core.operations.metrics import get_metrics_collector
        
        assert get_metrics_collector is not None

    def test_audit_module_imports(self):
        """Test that audit module imports correctly."""
        from core.operations.audit import AuditLogger, AuditAction
        
        assert AuditLogger is not None
        assert AuditAction is not None


def test_operations_panel_in_bot_handler():
    """Test that bot has handler for operations panel."""
    from core.bot import WOSMBot
    
    bot = WOSMBot()
    assert hasattr(bot, '_handle_operations_panel'), "Bot should have _handle_operations_panel method"
    assert callable(bot._handle_operations_panel)
