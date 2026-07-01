"""
Tests for Role Visibility Matrix
© MANSOUR — WOS-M. All rights reserved.
"""
import pytest
from core.interaction_registry import INTERACTION_REGISTRY, InteractionSpec


class TestOwnerVisibility:
    """Tests for Owner visibility."""

    def test_owner_sees_everything(self):
        """Owner should see all interactions where owner is in visible_to."""
        owner_visible = [
            spec for spec in INTERACTION_REGISTRY.values()
            if "owner" in spec.visible_to
        ]
        assert len(owner_visible) > 50, "Owner should see many interactions"

    def test_owner_sees_owner_panel(self):
        """Owner should see all owner panel buttons."""
        owner_panel = [
            spec for spec in INTERACTION_REGISTRY.values()
            if spec.module == "owner_panel" and "owner" in spec.visible_to
        ]
        assert len(owner_panel) > 20, "Owner should see owner panel buttons"

    def test_owner_sees_settings(self):
        """Owner should see settings buttons."""
        settings = [
            spec for spec in INTERACTION_REGISTRY.values()
            if "settings" in spec.custom_id and "owner" in spec.visible_to
        ]
        assert len(settings) >= 4, "Owner should see settings buttons"

    def test_owner_sees_maintenance(self):
        """Owner should see maintenance buttons."""
        maintenance = [
            spec for spec in INTERACTION_REGISTRY.values()
            if spec.module == "maintenance" and "owner" in spec.visible_to
        ]
        assert len(maintenance) > 0, "Owner should see maintenance buttons"


class TestAdminVisibility:
    """Tests for Admin visibility."""

    def test_admin_sees_dashboard(self):
        """Admin should see dashboard buttons."""
        dash_buttons = [
            spec for spec in INTERACTION_REGISTRY.values()
            if spec.custom_id.startswith("dash_") and "admin" in spec.visible_to
        ]
        assert len(dash_buttons) >= 8, "Admin should see dashboard buttons"

    def test_admin_sees_alliances(self):
        """Admin should see alliance management buttons."""
        alliance = [
            spec for spec in INTERACTION_REGISTRY.values()
            if spec.module == "alliances" and "admin" in spec.visible_to
        ]
        assert len(alliance) > 0, "Admin should see alliance buttons"

    def test_admin_sees_players(self):
        """Admin should see player management buttons."""
        players = [
            spec for spec in INTERACTION_REGISTRY.values()
            if spec.module == "players" and "admin" in spec.visible_to
        ]
        assert len(players) > 0, "Admin should see player buttons"

    def test_admin_sees_gift_codes(self):
        """Admin should see gift code buttons based on permission."""
        gift = [
            spec for spec in INTERACTION_REGISTRY.values()
            if spec.module == "gift_codes" and "admin" in spec.visible_to
        ]
        assert len(gift) > 0, "Admin should see gift code buttons"

    def test_admin_does_not_see_owner_panel(self):
        """Admin should NOT see owner panel buttons."""
        owner_panel = [
            spec for spec in INTERACTION_REGISTRY.values()
            if spec.module == "owner_panel"
        ]
        for spec in owner_panel:
            # Owner-only means visible ONLY to owner, not admin
            if spec.owner_only:
                assert "admin" not in spec.visible_to, \
                    f"Owner panel {spec.custom_id} should not be visible to admin"

    def test_admin_does_not_see_owner_only_settings(self):
        """Admin should NOT see owner-only settings."""
        owner_only = [
            spec for spec in INTERACTION_REGISTRY.values()
            if spec.owner_only and "admin" in spec.visible_to
        ]
        assert len(owner_only) == 0, "Admin should not see owner-only buttons"

    def test_admin_does_not_see_dangerous_settings(self):
        """Admin should NOT see dangerous settings like database."""
        dangerous = [
            spec for spec in INTERACTION_REGISTRY.values()
            if spec.dangerous and spec.owner_only
        ]
        for spec in dangerous:
            assert "admin" not in spec.visible_to, \
                f"Dangerous owner-only {spec.custom_id} should not be visible to admin"


class TestMemberVisibility:
    """Tests for Member visibility."""

    def test_member_sees_navigation(self):
        """Member should see navigation buttons."""
        nav = [
            spec for spec in INTERACTION_REGISTRY.values()
            if spec.module == "navigation" and "member" in spec.visible_to
        ]
        assert len(nav) > 0, "Member should see navigation"

    def test_member_sees_language(self):
        """Member should see language button."""
        language = [
            spec for spec in INTERACTION_REGISTRY.values()
            if "language" in spec.custom_id and "member" in spec.visible_to
        ]
        assert len(language) > 0, "Member should see language button"

    def test_member_does_not_see_owner_panel(self):
        """Member should NOT see owner panel."""
        owner_panel = [
            spec for spec in INTERACTION_REGISTRY.values()
            if spec.module == "owner_panel"
        ]
        for spec in owner_panel:
            assert "member" not in spec.visible_to, \
                f"Owner panel {spec.custom_id} should not be visible to member"

    def test_member_does_not_see_admin_buttons(self):
        """Member should NOT see admin-only buttons."""
        admin_only = [
            spec for spec in INTERACTION_REGISTRY.values()
            if spec.admin_only and "member" in spec.visible_to
        ]
        assert len(admin_only) == 0, "Member should not see admin-only buttons"

    def test_member_does_not_see_add_buttons(self):
        """Member should NOT see add/edit/delete buttons."""
        management = [
            spec for spec in INTERACTION_REGISTRY.values()
            if any(x in spec.custom_id for x in ["_add", "_edit", "_delete"]) and "member" in spec.visible_to
        ]
        for spec in management:
            # Allow attendance record for members
            if spec.custom_id == "att_record":
                continue
            assert False, f"Member should not see management button {spec.custom_id}"

    def test_member_does_not_see_settings(self):
        """Member should NOT see settings."""
        settings = [
            spec for spec in INTERACTION_REGISTRY.values()
            if "settings" in spec.custom_id and "member" in spec.visible_to
        ]
        assert len(settings) == 0, "Member should not see settings"

    def test_member_does_not_see_maintenance(self):
        """Member should NOT see maintenance."""
        maintenance = [
            spec for spec in INTERACTION_REGISTRY.values()
            if spec.module == "maintenance" and "member" in spec.visible_to
        ]
        for spec in maintenance:
            assert spec.admin_only or spec.owner_only, \
                f"Maintenance {spec.custom_id} should not be visible to member"


class TestDangerousOperations:
    """Tests for dangerous operations visibility."""

    def test_delete_buttons_are_owner_only(self):
        """Delete buttons should be owner-only or dangerous."""
        delete_buttons = [
            spec for spec in INTERACTION_REGISTRY.values()
            if "_delete" in spec.custom_id
        ]
        for spec in delete_buttons:
            assert spec.dangerous, f"Delete {spec.custom_id} should be marked dangerous"
            assert spec.requires_confirmation, f"Delete {spec.custom_id} should require confirmation"

    def test_database_buttons_are_owner_only(self):
        """Database buttons should be owner-only."""
        db_buttons = [
            spec for spec in INTERACTION_REGISTRY.values()
            if "database" in spec.custom_id
        ]
        for spec in db_buttons:
            assert spec.owner_only, f"Database {spec.custom_id} should be owner_only"

    def test_backup_buttons_are_owner_only(self):
        """Backup buttons should be owner-only."""
        backup_buttons = [
            spec for spec in INTERACTION_REGISTRY.values()
            if "backup" in spec.custom_id
        ]
        for spec in backup_buttons:
            assert spec.owner_only, f"Backup {spec.custom_id} should be owner_only"

    def test_transfer_buttons_are_owner_only(self):
        """Permission transfer buttons should be owner-only."""
        transfer_buttons = [
            spec for spec in INTERACTION_REGISTRY.values()
            if "transfer" in spec.custom_id
        ]
        for spec in transfer_buttons:
            assert spec.owner_only, f"Transfer {spec.custom_id} should be owner_only"


class TestPermissionMatrix:
    """Test the complete permission matrix."""

    def test_owner_has_maximum_visibility(self):
        """Owner should have visibility to most interactions."""
        owner_visible = [
            spec for spec in INTERACTION_REGISTRY.values()
            if "owner" in spec.visible_to
        ]
        total = len(INTERACTION_REGISTRY)
        # Owner should see at least 80% of interactions
        assert len(owner_visible) >= total * 0.8, \
            f"Owner should see at least 80% of interactions"

    def test_admin_has_moderate_visibility(self):
        """Admin should have visibility to management interactions."""
        admin_visible = [
            spec for spec in INTERACTION_REGISTRY.values()
            if "admin" in spec.visible_to
        ]
        assert len(admin_visible) > 20, "Admin should see management interactions"

    def test_member_has_minimal_visibility(self):
        """Member should have minimal visibility."""
        member_visible = [
            spec for spec in INTERACTION_REGISTRY.values()
            if "member" in spec.visible_to
        ]
        # Member should only see navigation and basic buttons
        assert len(member_visible) < 20, "Member should have minimal visibility"
