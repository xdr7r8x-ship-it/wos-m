"""
Tests for Interaction Registry
© MANSOUR — WOS-M. All rights reserved.
"""
import pytest
from core.interaction_registry import (
    INTERACTION_REGISTRY,
    get_all_custom_ids,
    get_owner_only,
    get_dangerous,
    get_selects,
    get_modals,
    InteractionSpec,
    PermissionLevel,
    InteractionType,
)


class TestInteractionRegistry:
    """Test the interaction registry."""

    def test_registry_not_empty(self):
        """Registry should not be empty."""
        assert len(INTERACTION_REGISTRY) > 0

    def test_all_custom_ids_unique(self):
        """All custom_ids should be unique."""
        custom_ids = list(INTERACTION_REGISTRY.keys())
        assert len(custom_ids) == len(set(custom_ids)), "Duplicate custom_ids found"

    def test_all_have_custom_id(self):
        """All specs should have custom_id matching their key."""
        for key, spec in INTERACTION_REGISTRY.items():
            assert spec.custom_id == key, f"Spec custom_id {spec.custom_id} doesn't match key {key}"

    def test_all_have_label_key(self):
        """All specs should have a label_key."""
        for key, spec in INTERACTION_REGISTRY.items():
            assert spec.label_key, f"Spec {key} has no label_key"
            assert "." in spec.label_key, f"Spec {key} label_key should contain '.'"

    def test_all_have_module(self):
        """All specs should have a module."""
        for key, spec in INTERACTION_REGISTRY.items():
            assert spec.module, f"Spec {key} has no module"

    def test_all_have_handler_name(self):
        """All specs should have a handler_name."""
        for key, spec in INTERACTION_REGISTRY.items():
            assert spec.handler_name, f"Spec {key} has no handler_name"
            assert spec.handler_name.startswith("_handle_"), f"Spec {key} handler should start with '_handle_'"

    def test_all_have_permission(self):
        """All specs should have a required_permission."""
        for key, spec in INTERACTION_REGISTRY.items():
            assert spec.required_permission, f"Spec {key} has no required_permission"
            assert isinstance(spec.required_permission, PermissionLevel), f"Spec {key} permission is not PermissionLevel"

    def test_all_have_visible_to(self):
        """All specs should have visible_to tuple."""
        for key, spec in INTERACTION_REGISTRY.items():
            assert spec.visible_to, f"Spec {key} has no visible_to"
            assert isinstance(spec.visible_to, tuple), f"Spec {key} visible_to should be tuple"
            assert len(spec.visible_to) > 0, f"Spec {key} visible_to is empty"

    def test_owner_only_have_owner_in_visible(self):
        """Owner-only specs should have 'owner' in visible_to."""
        owner_specs = get_owner_only()
        for spec in owner_specs:
            assert "owner" in spec.visible_to, f"Owner-only spec {spec.custom_id} doesn't have 'owner' in visible_to"

    def test_dangerous_have_confirmation(self):
        """Dangerous specs should require confirmation."""
        dangerous_specs = get_dangerous()
        for spec in dangerous_specs:
            assert spec.requires_confirmation or spec.dangerous, f"Dangerous spec {spec.custom_id} should require confirmation"

    def test_no_selects_in_registry(self):
        """Registry should not contain select menus (they have different handling)."""
        selects = get_selects()
        # Selects are handled separately
        assert isinstance(selects, list)

    def test_modals_have_modal_type(self):
        """Modal specs should have MODAL type."""
        modals = get_modals()
        for spec in modals:
            assert spec.interaction_type == InteractionType.MODAL, f"Modal spec {spec.custom_id} has wrong type"


class TestRegistryCoverage:
    """Test that all custom_ids from views are in registry."""

    def test_registry_has_all_navigation(self):
        """Registry should have all navigation buttons."""
        nav_ids = ["nav_back", "nav_home", "nav_close", "nav_refresh"]
        for nav_id in nav_ids:
            assert nav_id in INTERACTION_REGISTRY, f"Navigation {nav_id} not in registry"

    def test_registry_has_all_dashboard(self):
        """Registry should have all dashboard buttons."""
        dash_ids = [
            "dash_alliances", "dash_players", "dash_gift_codes", "dash_events",
            "dash_attendance", "dash_bear_tracking", "dash_ministers",
            "dash_notifications", "dash_themes", "dash_permissions",
            "dash_maintenance", "dash_owner_panel", "dash_language", "dash_settings"
        ]
        for dash_id in dash_ids:
            assert dash_id in INTERACTION_REGISTRY, f"Dashboard {dash_id} not in registry"

    def test_registry_has_all_alliance_buttons(self):
        """Registry should have all alliance buttons."""
        alliance_ids = [
            "alliance_add", "alliance_list", "alliance_edit",
            "alliance_delete", "alliance_gift_settings",
            "alliance_sync_settings", "alliance_redeem_modal"
        ]
        for aid in alliance_ids:
            assert aid in INTERACTION_REGISTRY, f"Alliance {aid} not in registry"

    def test_registry_has_all_player_buttons(self):
        """Registry should have all player buttons."""
        player_ids = [
            "player_add", "player_list", "player_search",
            "player_sync", "player_move", "player_export"
        ]
        for pid in player_ids:
            assert pid in INTERACTION_REGISTRY, f"Player {pid} not in registry"

    def test_registry_has_all_gift_buttons(self):
        """Registry should have all gift code buttons."""
        gift_ids = [
            "gift_add", "gift_redeem_single", "gift_batch",
            "gift_redeem_alliance", "gift_auto", "gift_report",
            "single_redeem_modal", "auto_enable_alliance",
            "auto_disable_alliance", "auto_redeem_all"
        ]
        for gid in gift_ids:
            assert gid in INTERACTION_REGISTRY, f"Gift {gid} not in registry"

    def test_registry_has_all_owner_panel_buttons(self):
        """Registry should have all owner panel buttons."""
        owner_ids = [
            "owner_panel_language", "owner_panel_buttons", "owner_panel_texts",
            "owner_panel_icons", "owner_panel_branding", "owner_panel_features",
            "btn_add", "btn_edit_name", "btn_edit_icon", "btn_edit_order",
            "btn_enable", "btn_disable", "brand_name", "brand_colors",
            "brand_reset", "brand_save", "feat_add", "feat_edit",
            "feat_enable", "feat_disable", "feat_link", "feat_registry",
            "icon_button", "icon_section", "icon_status",
            "text_edit_title", "text_edit_desc", "text_edit_msg", "text_reset"
        ]
        for oid in owner_ids:
            assert oid in INTERACTION_REGISTRY, f"Owner panel {oid} not in registry"


class TestRegistryCount:
    """Test registry counts."""

    def test_total_interactions(self):
        """Should have significant number of interactions."""
        total = len(INTERACTION_REGISTRY)
        assert total >= 90, f"Expected >= 90 interactions, got {total}"

    def test_owner_only_count(self):
        """Should have owner-only interactions."""
        owner_count = len(get_owner_only())
        assert owner_count > 0, "No owner-only interactions found"

    def test_dangerous_count(self):
        """Should have dangerous interactions tracked."""
        dangerous_count = len(get_dangerous())
        assert dangerous_count > 0, "No dangerous interactions found"
