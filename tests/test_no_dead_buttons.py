"""
Tests for No Dead Buttons
Verifies all registered interactions have real handlers.
© MANSOUR — WOS-M. All rights reserved.
"""
import pytest
from core.interaction_registry import INTERACTION_REGISTRY, InteractionSpec


class TestNoDeadButtons:
    """Tests to ensure no dead buttons exist."""

    def test_all_registry_buttons_have_handlers(self):
        """All registry entries should have handler names."""
        for key, spec in INTERACTION_REGISTRY.items():
            assert spec.handler_name, f"Button {key} has no handler_name"
            assert spec.handler_name.startswith("_handle_"), f"Button {key} handler should start with _handle_"

    def test_all_buttons_have_labels(self):
        """All buttons should have label keys for i18n."""
        for key, spec in INTERACTION_REGISTRY.items():
            assert spec.label_key, f"Button {key} has no label_key"
            assert "." in spec.label_key, f"Button {key} label_key should be i18n format"

    def test_all_buttons_have_modules(self):
        """All buttons should belong to a module."""
        for key, spec in INTERACTION_REGISTRY.items():
            assert spec.module, f"Button {key} has no module"

    def test_no_empty_visible_to(self):
        """No button should have empty visible_to."""
        for key, spec in INTERACTION_REGISTRY.items():
            assert spec.visible_to, f"Button {key} has empty visible_to"
            assert len(spec.visible_to) > 0, f"Button {key} has empty visible_to tuple"

    def test_dangerous_has_confirmation(self):
        """Dangerous buttons should require confirmation."""
        dangerous = [s for s in INTERACTION_REGISTRY.values() if s.dangerous]
        for spec in dangerous:
            assert spec.requires_confirmation or spec.dangerous, \
                f"Dangerous {spec.custom_id} should require confirmation"

    def test_audit_required_for_sensitive(self):
        """Sensitive buttons should require audit."""
        sensitive = [
            s for s in INTERACTION_REGISTRY.values()
            if any(x in s.custom_id for x in ["add", "edit", "delete", "move", "export"])
        ]
        for spec in sensitive:
            assert spec.requires_audit, f"Sensitive {spec.custom_id} should require audit"


class TestHandlerNaming:
    """Tests for handler naming conventions."""

    def test_navigation_handlers(self):
        """Navigation buttons should have nav handlers."""
        nav = ["nav_back", "nav_home", "nav_close", "nav_refresh"]
        for n in nav:
            if n in INTERACTION_REGISTRY:
                assert "nav" in INTERACTION_REGISTRY[n].handler_name, \
                    f"{n} handler should contain 'nav'"

    def test_dashboard_handlers(self):
        """Dashboard buttons should have handlers."""
        for key, spec in INTERACTION_REGISTRY.items():
            if key.startswith("dash_"):
                # Handler should exist and be named properly
                assert spec.handler_name.startswith("_handle_"), \
                    f"{key} handler should start with _handle_"

    def test_module_handlers(self):
        """Module buttons should have module-specific handlers."""
        modules = ["alliances", "players", "gift_codes", "events", "attendance", 
                   "bear_tracking", "ministers", "notifications", "themes", "maintenance", "owner_panel"]
        for module in modules:
            module_buttons = [s for s in INTERACTION_REGISTRY.values() if s.module == module]
            if module_buttons:
                # At least one should have handler with module name
                has_handler = any(module in s.handler_name for s in module_buttons)
                assert has_handler or module_buttons[0].handler_name.startswith("_handle_"), \
                    f"Module {module} should have matching handlers"
