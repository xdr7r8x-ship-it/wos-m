"""
WOS-M Interaction Registry
Central registry for all buttons, selects, and modals.
© MANSOUR — WOS-M. All rights reserved.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, Any

# Import PermissionLevel from core.permissions to avoid duplication
# This is the SINGLE SOURCE OF TRUTH for permissions
from core.permissions import PermissionLevel


class InteractionType(str, Enum):
    BUTTON = "button"
    SELECT = "select"
    MODAL = "modal"


class Visibility(str, Enum):
    OWNER_ONLY = "owner_only"
    ADMIN_ABOVE = "admin_above"  # Owner + Global Admin
    SERVER_ADMIN_ABOVE = "server_admin_above"
    ALLIANCE_ADMIN_ABOVE = "alliance_admin_above"
    MEMBER = "member"  # All authenticated users


@dataclass(frozen=True)
class InteractionSpec:
    """Specification for an interaction (button/select/modal)."""
    custom_id: str
    label_key: str  # i18n key
    interaction_type: InteractionType
    module: str
    handler_name: str
    required_permission: PermissionLevel
    visible_to: tuple[str, ...]
    owner_only: bool = False
    admin_only: bool = False
    dangerous: bool = False  # Delete/modify operations
    production_visible: bool = True
    requires_audit: bool = True
    requires_confirmation: bool = False
    emoji: Optional[str] = None


# Central registry - ALL custom_ids must be registered here
INTERACTION_REGISTRY: dict[str, InteractionSpec] = {

    # ========== NAVIGATION ==========
    "nav_back": InteractionSpec(
        custom_id="nav_back",
        label_key="nav.back",
        interaction_type=InteractionType.BUTTON,
        module="navigation",
        handler_name="_handle_nav_back",
        required_permission=PermissionLevel.MEMBER,
        visible_to=("owner", "admin", "member"),
        emoji="⬅️"
    ),
    "nav_home": InteractionSpec(
        custom_id="nav_home",
        label_key="nav.home",
        interaction_type=InteractionType.BUTTON,
        module="navigation",
        handler_name="_handle_nav_home",
        required_permission=PermissionLevel.MEMBER,
        visible_to=("owner", "admin", "member"),
        emoji="🏠"
    ),
    "nav_close": InteractionSpec(
        custom_id="nav_close",
        label_key="nav.close",
        interaction_type=InteractionType.BUTTON,
        module="navigation",
        handler_name="_handle_nav_close",
        required_permission=PermissionLevel.MEMBER,
        visible_to=("owner", "admin", "member"),
        emoji="❌"
    ),
    "nav_refresh": InteractionSpec(
        custom_id="nav_refresh",
        label_key="nav.refresh",
        interaction_type=InteractionType.BUTTON,
        module="navigation",
        handler_name="_handle_nav_refresh",
        required_permission=PermissionLevel.MEMBER,
        visible_to=("owner", "admin", "member"),
        emoji="🔄"
    ),
    "nav_prev": InteractionSpec(
        custom_id="nav_prev",
        label_key="nav.previous",
        interaction_type=InteractionType.BUTTON,
        module="navigation",
        handler_name="_handle_nav_prev",
        required_permission=PermissionLevel.MEMBER,
        visible_to=("owner", "admin", "member"),
        emoji="◀️"
    ),
    "nav_next": InteractionSpec(
        custom_id="nav_next",
        label_key="nav.next",
        interaction_type=InteractionType.BUTTON,
        module="navigation",
        handler_name="_handle_nav_next",
        required_permission=PermissionLevel.MEMBER,
        visible_to=("owner", "admin", "member"),
        emoji="▶️"
    ),

    # ========== DASHBOARD ==========
    "dash_alliances": InteractionSpec(
        custom_id="dash_alliances",
        label_key="dashboard.alliances",
        interaction_type=InteractionType.BUTTON,
        module="alliances",
        handler_name="_handle_alliances",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="🏰"
    ),
    "dash_players": InteractionSpec(
        custom_id="dash_players",
        label_key="dashboard.players",
        interaction_type=InteractionType.BUTTON,
        module="players",
        handler_name="_handle_players",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="👥"
    ),
    "dash_gift_codes": InteractionSpec(
        custom_id="dash_gift_codes",
        label_key="dashboard.gift_codes",
        interaction_type=InteractionType.BUTTON,
        module="gift_codes",
        handler_name="_handle_gift_codes",
        required_permission=PermissionLevel.SERVER_ADMIN,
        visible_to=("owner", "admin"),
        emoji="🎁"
    ),
    "dash_events": InteractionSpec(
        custom_id="dash_events",
        label_key="dashboard.events",
        interaction_type=InteractionType.BUTTON,
        module="events",
        handler_name="_handle_events",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="📅"
    ),
    "dash_attendance": InteractionSpec(
        custom_id="dash_attendance",
        label_key="dashboard.attendance",
        interaction_type=InteractionType.BUTTON,
        module="attendance",
        handler_name="_handle_attendance",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="✅"
    ),
    "dash_bear_tracking": InteractionSpec(
        custom_id="dash_bear_tracking",
        label_key="dashboard.bear_tracking",
        interaction_type=InteractionType.BUTTON,
        module="bear_tracking",
        handler_name="_handle_bear_tracking",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="🐻"
    ),
    "dash_ministers": InteractionSpec(
        custom_id="dash_ministers",
        label_key="dashboard.ministers",
        interaction_type=InteractionType.BUTTON,
        module="ministers",
        handler_name="_handle_ministers",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="👔"
    ),
    "dash_notifications": InteractionSpec(
        custom_id="dash_notifications",
        label_key="dashboard.notifications",
        interaction_type=InteractionType.BUTTON,
        module="notifications",
        handler_name="_handle_notifications",
        required_permission=PermissionLevel.SERVER_ADMIN,
        visible_to=("owner", "admin"),
        emoji="🔔"
    ),
    "dash_themes": InteractionSpec(
        custom_id="dash_themes",
        label_key="dashboard.themes",
        interaction_type=InteractionType.BUTTON,
        module="themes",
        handler_name="_handle_themes",
        required_permission=PermissionLevel.SERVER_ADMIN,
        visible_to=("owner", "admin"),
        emoji="🎨"
    ),
    "dash_permissions": InteractionSpec(
        custom_id="dash_permissions",
        label_key="dashboard.permissions",
        interaction_type=InteractionType.BUTTON,
        module="maintenance",
        handler_name="_handle_permissions",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        emoji="🔐"
    ),
    "dash_maintenance": InteractionSpec(
        custom_id="dash_maintenance",
        label_key="dashboard.maintenance",
        interaction_type=InteractionType.BUTTON,
        module="maintenance",
        handler_name="_handle_maintenance",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        emoji="🔧"
    ),
    "dash_owner_panel": InteractionSpec(
        custom_id="dash_owner_panel",
        label_key="dashboard.owner_panel",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_owner_panel",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="👑"
    ),
    "dash_language": InteractionSpec(
        custom_id="dash_language",
        label_key="dashboard.language",
        interaction_type=InteractionType.BUTTON,
        module="dashboard",
        handler_name="_handle_language",
        required_permission=PermissionLevel.MEMBER,
        visible_to=("owner", "admin", "member"),
        emoji="🌐"
    ),
    "dash_settings": InteractionSpec(
        custom_id="dash_settings",
        label_key="dashboard.settings",
        interaction_type=InteractionType.BUTTON,
        module="maintenance",
        handler_name="_handle_settings",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        admin_only=True,
        emoji="⚙️"
    ),

    # ========== ALLIANCES ==========
    "alliance_add": InteractionSpec(
        custom_id="alliance_add",
        label_key="alliances.add",
        interaction_type=InteractionType.BUTTON,
        module="alliances",
        handler_name="_handle_alliance_add",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        dangerous=True,
        requires_audit=True,
        emoji="➕"
    ),
    "alliance_list": InteractionSpec(
        custom_id="alliance_list",
        label_key="alliances.list",
        interaction_type=InteractionType.BUTTON,
        module="alliances",
        handler_name="_handle_alliance_list",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="📋"
    ),
    "alliance_edit": InteractionSpec(
        custom_id="alliance_edit",
        label_key="alliances.edit",
        interaction_type=InteractionType.BUTTON,
        module="alliances",
        handler_name="_handle_alliance_edit",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        dangerous=True,
        requires_audit=True,
        emoji="✏️"
    ),
    "alliance_delete": InteractionSpec(
        custom_id="alliance_delete",
        label_key="alliances.delete",
        interaction_type=InteractionType.BUTTON,
        module="alliances",
        handler_name="_handle_alliance_delete",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        dangerous=True,
        requires_audit=True,
        requires_confirmation=True,
        emoji="🗑️"
    ),
    "alliance_gift_settings": InteractionSpec(
        custom_id="alliance_gift_settings",
        label_key="alliances.gift_settings",
        interaction_type=InteractionType.BUTTON,
        module="alliances",
        handler_name="_handle_alliance_gift_settings",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        requires_audit=True,
        emoji="🎁"
    ),
    "alliance_sync_settings": InteractionSpec(
        custom_id="alliance_sync_settings",
        label_key="alliances.sync_settings",
        interaction_type=InteractionType.BUTTON,
        module="alliances",
        handler_name="_handle_alliance_sync_settings",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        requires_audit=True,
        emoji="🔄"
    ),
    "alliance_redeem_modal": InteractionSpec(
        custom_id="alliance_redeem_modal",
        label_key="alliances.redeem",
        interaction_type=InteractionType.MODAL,
        module="alliances",
        handler_name="_handle_alliance_redeem_modal",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        requires_audit=True,
        emoji="🎁"
    ),

    # ========== PLAYERS ==========
    "player_add": InteractionSpec(
        custom_id="player_add",
        label_key="players.add",
        interaction_type=InteractionType.BUTTON,
        module="players",
        handler_name="_handle_player_add",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        requires_audit=True,
        emoji="➕"
    ),
    "player_list": InteractionSpec(
        custom_id="player_list",
        label_key="players.list",
        interaction_type=InteractionType.BUTTON,
        module="players",
        handler_name="_handle_player_list",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="📋"
    ),
    "player_search": InteractionSpec(
        custom_id="player_search",
        label_key="players.search",
        interaction_type=InteractionType.BUTTON,
        module="players",
        handler_name="_handle_player_search",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="🔍"
    ),
    "player_sync": InteractionSpec(
        custom_id="player_sync",
        label_key="players.sync",
        interaction_type=InteractionType.BUTTON,
        module="players",
        handler_name="_handle_player_sync",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        requires_audit=True,
        emoji="🔄"
    ),
    "player_move": InteractionSpec(
        custom_id="player_move",
        label_key="players.move",
        interaction_type=InteractionType.BUTTON,
        module="players",
        handler_name="_handle_player_move",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        dangerous=True,
        requires_audit=True,
        emoji="➡️"
    ),
    "player_export": InteractionSpec(
        custom_id="player_export",
        label_key="players.export",
        interaction_type=InteractionType.BUTTON,
        module="players",
        handler_name="_handle_player_export",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        requires_audit=True,
        emoji="📤"
    ),

    # ========== GIFT CODES ==========
    "gift_add": InteractionSpec(
        custom_id="gift_add",
        label_key="gift_codes.add",
        interaction_type=InteractionType.BUTTON,
        module="gift_codes",
        handler_name="_handle_gift_add",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        requires_audit=True,
        emoji="➕"
    ),
    "gift_redeem_single": InteractionSpec(
        custom_id="gift_redeem_single",
        label_key="gift_codes.redeem_single",
        interaction_type=InteractionType.BUTTON,
        module="gift_codes",
        handler_name="_handle_gift_redeem_single",
        required_permission=PermissionLevel.SERVER_ADMIN,
        visible_to=("owner", "admin"),
        requires_audit=True,
        emoji="🎁"
    ),
    "gift_batch": InteractionSpec(
        custom_id="gift_batch",
        label_key="gift_codes.batch",
        interaction_type=InteractionType.BUTTON,
        module="gift_codes",
        handler_name="_handle_gift_batch",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        requires_audit=True,
        emoji="📦"
    ),
    "gift_redeem_alliance": InteractionSpec(
        custom_id="gift_redeem_alliance",
        label_key="gift_codes.redeem_alliance",
        interaction_type=InteractionType.BUTTON,
        module="gift_codes",
        handler_name="_handle_gift_redeem_alliance",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        requires_audit=True,
        emoji="🏰"
    ),
    "gift_auto": InteractionSpec(
        custom_id="gift_auto",
        label_key="gift_codes.auto",
        interaction_type=InteractionType.BUTTON,
        module="gift_codes",
        handler_name="_handle_gift_auto",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        requires_audit=True,
        emoji="⚙️"
    ),
    "gift_report": InteractionSpec(
        custom_id="gift_report",
        label_key="gift_codes.report",
        interaction_type=InteractionType.BUTTON,
        module="gift_codes",
        handler_name="_handle_gift_report",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        emoji="📊"
    ),
    "auto_enable_alliance": InteractionSpec(
        custom_id="auto_enable_alliance",
        label_key="gift_codes.auto_enable",
        interaction_type=InteractionType.BUTTON,
        module="gift_codes",
        handler_name="_handle_auto_enable_alliance",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        dangerous=True,
        requires_audit=True,
        emoji="✅"
    ),
    "auto_disable_alliance": InteractionSpec(
        custom_id="auto_disable_alliance",
        label_key="gift_codes.auto_disable",
        interaction_type=InteractionType.BUTTON,
        module="gift_codes",
        handler_name="_handle_auto_disable_alliance",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        dangerous=True,
        requires_audit=True,
        emoji="❌"
    ),
    "auto_redeem_all": InteractionSpec(
        custom_id="auto_redeem_all",
        label_key="gift_codes.auto_redeem_all",
        interaction_type=InteractionType.BUTTON,
        module="gift_codes",
        handler_name="_handle_auto_redeem_all",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        dangerous=True,
        requires_audit=True,
        emoji="🚀"
    ),
    "single_redeem_modal": InteractionSpec(
        custom_id="single_redeem_modal",
        label_key="gift_codes.redeem_modal",
        interaction_type=InteractionType.MODAL,
        module="gift_codes",
        handler_name="_handle_single_redeem_modal",
        required_permission=PermissionLevel.SERVER_ADMIN,
        visible_to=("owner", "admin"),
    ),
    
    # ========== GIFT CODES - Additional buttons ==========
    "add_gift_code_modal": InteractionSpec(
        custom_id="add_gift_code_modal",
        label_key="gift_codes.add_modal",
        interaction_type=InteractionType.MODAL,
        module="gift_codes",
        handler_name="_handle_add_gift_modal",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner", "admin"),
    ),
    "batch_redeem_modal": InteractionSpec(
        custom_id="batch_redeem_modal",
        label_key="gift_codes.batch_modal",
        interaction_type=InteractionType.MODAL,
        module="gift_codes",
        handler_name="_handle_batch_redeem_modal",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner", "admin"),
    ),
    "redeem_gift_code_modal": InteractionSpec(
        custom_id="redeem_gift_code_modal",
        label_key="gift_codes.redeem_modal",
        interaction_type=InteractionType.MODAL,
        module="gift_codes",
        handler_name="_handle_redeem_gift_modal",
        required_permission=PermissionLevel.SERVER_ADMIN,
        visible_to=("owner", "admin"),
    ),
    "batch_manual": InteractionSpec(
        custom_id="batch_manual",
        label_key="gift_codes.batch_manual",
        interaction_type=InteractionType.BUTTON,
        module="gift_codes",
        handler_name="_handle_batch_manual",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner", "admin"),
    ),
    "batch_redeem_all": InteractionSpec(
        custom_id="batch_redeem_all",
        label_key="gift_codes.batch_redeem_all",
        interaction_type=InteractionType.BUTTON,
        module="gift_codes",
        handler_name="_handle_batch_redeem_all",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
    ),
    "gift_alliance": InteractionSpec(
        custom_id="gift_alliance",
        label_key="gift_codes.gift_alliance",
        interaction_type=InteractionType.BUTTON,
        module="gift_codes",
        handler_name="_handle_gift_alliance",
        required_permission=PermissionLevel.SERVER_ADMIN,
        visible_to=("owner", "admin"),
    ),
    "gift_redeem": InteractionSpec(
        custom_id="gift_redeem",
        label_key="gift_codes.gift_redeem",
        interaction_type=InteractionType.BUTTON,
        module="gift_codes",
        handler_name="_handle_gift_redeem",
        required_permission=PermissionLevel.SERVER_ADMIN,
        visible_to=("owner", "admin"),
    ),
    "gift_settings": InteractionSpec(
        custom_id="gift_settings",
        label_key="gift_codes.settings",
        interaction_type=InteractionType.BUTTON,
        module="gift_codes",
        handler_name="_handle_gift_settings",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner", "admin"),
    ),

    # ========== EVENTS ==========
    "event_create": InteractionSpec(
        custom_id="event_create",
        label_key="events.create",
        interaction_type=InteractionType.BUTTON,
        module="events",
        handler_name="_handle_event_create",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        requires_audit=True,
        emoji="➕"
    ),
    "event_list": InteractionSpec(
        custom_id="event_list",
        label_key="events.list",
        interaction_type=InteractionType.BUTTON,
        module="events",
        handler_name="_handle_event_list",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="📋"
    ),
    "event_edit": InteractionSpec(
        custom_id="event_edit",
        label_key="events.edit",
        interaction_type=InteractionType.BUTTON,
        module="events",
        handler_name="_handle_event_edit",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        requires_audit=True,
        emoji="✏️"
    ),
    "event_delete": InteractionSpec(
        custom_id="event_delete",
        label_key="events.delete",
        interaction_type=InteractionType.BUTTON,
        module="events",
        handler_name="_handle_event_delete",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        dangerous=True,
        requires_audit=True,
        requires_confirmation=True,
        emoji="🗑️"
    ),

    # ========== ATTENDANCE ==========
    "att_record": InteractionSpec(
        custom_id="att_record",
        label_key="attendance.record",
        interaction_type=InteractionType.BUTTON,
        module="attendance",
        handler_name="_handle_att_record",
        required_permission=PermissionLevel.MEMBER,
        visible_to=("owner", "admin", "member"),
        emoji="📝"
    ),
    "att_list": InteractionSpec(
        custom_id="att_list",
        label_key="attendance.list",
        interaction_type=InteractionType.BUTTON,
        module="attendance",
        handler_name="_handle_att_list",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="📋"
    ),
    "att_report": InteractionSpec(
        custom_id="att_report",
        label_key="attendance.report",
        interaction_type=InteractionType.BUTTON,
        module="attendance",
        handler_name="_handle_att_report",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="📊"
    ),
    "att_export": InteractionSpec(
        custom_id="att_export",
        label_key="attendance.export",
        interaction_type=InteractionType.BUTTON,
        module="attendance",
        handler_name="_handle_att_export",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        requires_audit=True,
        emoji="📤"
    ),
    "att_history": InteractionSpec(
        custom_id="att_history",
        label_key="attendance.history",
        interaction_type=InteractionType.BUTTON,
        module="attendance",
        handler_name="_handle_att_history",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="📜"
    ),

    # ========== BEAR TRACKING ==========
    "bear_add": InteractionSpec(
        custom_id="bear_add",
        label_key="bear_tracking.add",
        interaction_type=InteractionType.BUTTON,
        module="bear_tracking",
        handler_name="_handle_bear_add",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        requires_audit=True,
        emoji="➕"
    ),
    "bear_damage": InteractionSpec(
        custom_id="bear_damage",
        label_key="bear_tracking.damage",
        interaction_type=InteractionType.BUTTON,
        module="bear_tracking",
        handler_name="_handle_bear_damage",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        requires_audit=True,
        emoji="📝"
    ),
    "bear_report": InteractionSpec(
        custom_id="bear_report",
        label_key="bear_tracking.report",
        interaction_type=InteractionType.BUTTON,
        module="bear_tracking",
        handler_name="_handle_bear_report",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="📊"
    ),
    "bear_leaderboard": InteractionSpec(
        custom_id="bear_leaderboard",
        label_key="bear_tracking.leaderboard",
        interaction_type=InteractionType.BUTTON,
        module="bear_tracking",
        handler_name="_handle_bear_leaderboard",
        required_permission=PermissionLevel.MEMBER,
        visible_to=("owner", "admin", "member"),
        emoji="🏆"
    ),
    "bear_ocr": InteractionSpec(
        custom_id="bear_ocr",
        label_key="bear_tracking.ocr",
        interaction_type=InteractionType.BUTTON,
        module="bear_tracking",
        handler_name="_handle_bear_ocr",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        requires_audit=True,
        emoji="🔮"
    ),
    "bear_archive": InteractionSpec(
        custom_id="bear_archive",
        label_key="bear_tracking.archive",
        interaction_type=InteractionType.BUTTON,
        module="bear_tracking",
        handler_name="_handle_bear_archive",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        requires_audit=True,
        emoji="📦"
    ),

    # ========== MINISTERS ==========
    "minister_add": InteractionSpec(
        custom_id="minister_add",
        label_key="ministers.add",
        interaction_type=InteractionType.BUTTON,
        module="ministers",
        handler_name="_handle_minister_add",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        requires_audit=True,
        emoji="➕"
    ),
    "minister_assign": InteractionSpec(
        custom_id="minister_assign",
        label_key="ministers.assign",
        interaction_type=InteractionType.BUTTON,
        module="ministers",
        handler_name="_handle_minister_assign",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        requires_audit=True,
        emoji="👤"
    ),
    "minister_list": InteractionSpec(
        custom_id="minister_list",
        label_key="ministers.list",
        interaction_type=InteractionType.BUTTON,
        module="ministers",
        handler_name="_handle_minister_list",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="📋"
    ),
    "minister_schedule": InteractionSpec(
        custom_id="minister_schedule",
        label_key="ministers.schedule",
        interaction_type=InteractionType.BUTTON,
        module="ministers",
        handler_name="_handle_minister_schedule",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="📅"
    ),
    "minister_reminder": InteractionSpec(
        custom_id="minister_reminder",
        label_key="ministers.reminder",
        interaction_type=InteractionType.BUTTON,
        module="ministers",
        handler_name="_handle_minister_reminder",
        required_permission=PermissionLevel.ALLIANCE_ADMIN,
        visible_to=("owner", "admin"),
        emoji="⏰"
    ),

    # ========== NOTIFICATIONS ==========
    "notif_add": InteractionSpec(
        custom_id="notif_add",
        label_key="notifications.add",
        interaction_type=InteractionType.BUTTON,
        module="notifications",
        handler_name="_handle_notif_add",
        required_permission=PermissionLevel.SERVER_ADMIN,
        visible_to=("owner", "admin"),
        requires_audit=True,
        emoji="➕"
    ),
    "notif_list": InteractionSpec(
        custom_id="notif_list",
        label_key="notifications.list",
        interaction_type=InteractionType.BUTTON,
        module="notifications",
        handler_name="_handle_notif_list",
        required_permission=PermissionLevel.SERVER_ADMIN,
        visible_to=("owner", "admin"),
        emoji="📋"
    ),
    "notif_edit": InteractionSpec(
        custom_id="notif_edit",
        label_key="notifications.edit",
        interaction_type=InteractionType.BUTTON,
        module="notifications",
        handler_name="_handle_notif_edit",
        required_permission=PermissionLevel.SERVER_ADMIN,
        visible_to=("owner", "admin"),
        requires_audit=True,
        emoji="✏️"
    ),
    "notif_delete": InteractionSpec(
        custom_id="notif_delete",
        label_key="notifications.delete",
        interaction_type=InteractionType.BUTTON,
        module="notifications",
        handler_name="_handle_notif_delete",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        dangerous=True,
        requires_audit=True,
        requires_confirmation=True,
        emoji="🗑️"
    ),
    "notif_enable": InteractionSpec(
        custom_id="notif_enable",
        label_key="notifications.enable",
        interaction_type=InteractionType.BUTTON,
        module="notifications",
        handler_name="_handle_notif_enable",
        required_permission=PermissionLevel.SERVER_ADMIN,
        visible_to=("owner", "admin"),
        requires_audit=True,
        emoji="✅"
    ),
    "notif_disable": InteractionSpec(
        custom_id="notif_disable",
        label_key="notifications.disable",
        interaction_type=InteractionType.BUTTON,
        module="notifications",
        handler_name="_handle_notif_disable",
        required_permission=PermissionLevel.SERVER_ADMIN,
        visible_to=("owner", "admin"),
        requires_audit=True,
        emoji="❌"
    ),

    # ========== THEMES ==========
    "theme_bot_name": InteractionSpec(
        custom_id="theme_bot_name",
        label_key="themes.bot_name",
        interaction_type=InteractionType.BUTTON,
        module="themes",
        handler_name="_handle_theme_bot_name",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        requires_audit=True,
        emoji="🤖"
    ),
    "theme_primary_color": InteractionSpec(
        custom_id="theme_primary_color",
        label_key="themes.primary_color",
        interaction_type=InteractionType.BUTTON,
        module="themes",
        handler_name="_handle_theme_primary_color",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        requires_audit=True,
        emoji="🎨"
    ),
    "theme_footer": InteractionSpec(
        custom_id="theme_footer",
        label_key="themes.footer",
        interaction_type=InteractionType.BUTTON,
        module="themes",
        handler_name="_handle_theme_footer",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        requires_audit=True,
        emoji="📝"
    ),
    "theme_signature": InteractionSpec(
        custom_id="theme_signature",
        label_key="themes.signature",
        interaction_type=InteractionType.BUTTON,
        module="themes",
        handler_name="_handle_theme_signature",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        requires_audit=True,
        emoji="✍️"
    ),
    "theme_preview": InteractionSpec(
        custom_id="theme_preview",
        label_key="themes.preview",
        interaction_type=InteractionType.BUTTON,
        module="themes",
        handler_name="_handle_theme_preview",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        emoji="👁️"
    ),
    "theme_reset": InteractionSpec(
        custom_id="theme_reset",
        label_key="themes.reset",
        interaction_type=InteractionType.BUTTON,
        module="themes",
        handler_name="_handle_theme_reset",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        dangerous=True,
        requires_audit=True,
        emoji="🔄"
    ),

    # ========== MAINTENANCE ==========
    "maint_health": InteractionSpec(
        custom_id="maint_health",
        label_key="maintenance.health",
        interaction_type=InteractionType.BUTTON,
        module="maintenance",
        handler_name="_handle_maint_health",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        emoji="💚"
    ),
    "maint_database": InteractionSpec(
        custom_id="maint_database",
        label_key="maintenance.database",
        interaction_type=InteractionType.BUTTON,
        module="maintenance",
        handler_name="_handle_maint_database",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        dangerous=True,
        requires_audit=True,
        emoji="🗄️"
    ),
    "maint_logs": InteractionSpec(
        custom_id="maint_logs",
        label_key="maintenance.logs",
        interaction_type=InteractionType.BUTTON,
        module="maintenance",
        handler_name="_handle_maint_logs",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        emoji="📜"
    ),
    "maint_backup": InteractionSpec(
        custom_id="maint_backup",
        label_key="maintenance.backup",
        interaction_type=InteractionType.BUTTON,
        module="maintenance",
        handler_name="_handle_maint_backup",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        dangerous=True,
        requires_audit=True,
        emoji="💾"
    ),
    "maint_api": InteractionSpec(
        custom_id="maint_api",
        label_key="maintenance.api",
        interaction_type=InteractionType.BUTTON,
        module="maintenance",
        handler_name="_handle_maint_api",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🔌"
    ),
    "maint_queue": InteractionSpec(
        custom_id="maint_queue",
        label_key="maintenance.queue",
        interaction_type=InteractionType.BUTTON,
        module="maintenance",
        handler_name="_handle_maint_queue",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        emoji="📬"
    ),
    "perm_list": InteractionSpec(
        custom_id="perm_list",
        label_key="permissions.list",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_perm_list",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        emoji="📋"
    ),
    "perm_assign": InteractionSpec(
        custom_id="perm_assign",
        label_key="permissions.assign",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_perm_assign",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        dangerous=True,
        requires_audit=True,
        emoji="➕"
    ),
    "perm_remove": InteractionSpec(
        custom_id="perm_remove",
        label_key="permissions.remove",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_perm_remove",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        dangerous=True,
        requires_audit=True,
        emoji="➖"
    ),
    "perm_transfer": InteractionSpec(
        custom_id="perm_transfer",
        label_key="permissions.transfer",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_perm_transfer",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        dangerous=True,
        requires_audit=True,
        emoji="🔄"
    ),
    "perm_audit": InteractionSpec(
        custom_id="perm_audit",
        label_key="permissions.audit",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_perm_audit",
        required_permission=PermissionLevel.GLOBAL_ADMIN,
        visible_to=("owner",),
        emoji="🔍"
    ),
    "settings_general": InteractionSpec(
        custom_id="settings_general",
        label_key="settings.general",
        interaction_type=InteractionType.BUTTON,
        module="settings",
        handler_name="_handle_settings_general",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="⚙️"
    ),
    "settings_api": InteractionSpec(
        custom_id="settings_api",
        label_key="settings.api",
        interaction_type=InteractionType.BUTTON,
        module="settings",
        handler_name="_handle_settings_api",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🔌"
    ),
    "settings_save": InteractionSpec(
        custom_id="settings_save",
        label_key="settings.save",
        interaction_type=InteractionType.BUTTON,
        module="settings",
        handler_name="_handle_settings_save",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        requires_audit=True,
        emoji="💾"
    ),
    "settings_reset": InteractionSpec(
        custom_id="settings_reset",
        label_key="settings.reset",
        interaction_type=InteractionType.BUTTON,
        module="settings",
        handler_name="_handle_settings_reset",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        dangerous=True,
        requires_audit=True,
        emoji="🔄"
    ),

    # ========== OWNER PANEL ==========
    "owner_panel_language": InteractionSpec(
        custom_id="owner_panel_language",
        label_key="owner_panel.language",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_owner_language",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🌐"
    ),
    "owner_panel_buttons": InteractionSpec(
        custom_id="owner_panel_buttons",
        label_key="owner_panel.buttons",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_owner_buttons",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🔘"
    ),
    "owner_panel_texts": InteractionSpec(
        custom_id="owner_panel_texts",
        label_key="owner_panel.texts",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_owner_texts",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="📝"
    ),
    "owner_panel_icons": InteractionSpec(
        custom_id="owner_panel_icons",
        label_key="owner_panel.icons",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_owner_icons",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🖼️"
    ),
    "owner_panel_branding": InteractionSpec(
        custom_id="owner_panel_branding",
        label_key="owner_panel.branding",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_owner_branding",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🎨"
    ),
    "owner_panel_features": InteractionSpec(
        custom_id="owner_panel_features",
        label_key="owner_panel.features",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_owner_features",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="⚡"
    ),
    "btn_add": InteractionSpec(
        custom_id="btn_add",
        label_key="owner_panel.btn_add",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_btn_add",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        requires_audit=True,
        emoji="➕"
    ),
    "btn_edit_name": InteractionSpec(
        custom_id="btn_edit_name",
        label_key="owner_panel.btn_edit_name",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_btn_edit_name",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        requires_audit=True,
        emoji="✏️"
    ),
    "btn_edit_icon": InteractionSpec(
        custom_id="btn_edit_icon",
        label_key="owner_panel.btn_edit_icon",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_btn_edit_icon",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        requires_audit=True,
        emoji="🖼️"
    ),
    "btn_edit_order": InteractionSpec(
        custom_id="btn_edit_order",
        label_key="owner_panel.btn_edit_order",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_btn_edit_order",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        requires_audit=True,
        emoji="📊"
    ),
    "btn_enable": InteractionSpec(
        custom_id="btn_enable",
        label_key="owner_panel.btn_enable",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_btn_enable",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        requires_audit=True,
        emoji="✅"
    ),
    "btn_disable": InteractionSpec(
        custom_id="btn_disable",
        label_key="owner_panel.btn_disable",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_btn_disable",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        dangerous=True,
        requires_audit=True,
        emoji="❌"
    ),
    "brand_name": InteractionSpec(
        custom_id="brand_name",
        label_key="owner_panel.brand_name",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_brand_name",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        requires_audit=True,
        emoji="🏷️"
    ),
    "brand_colors": InteractionSpec(
        custom_id="brand_colors",
        label_key="owner_panel.brand_colors",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_brand_colors",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        requires_audit=True,
        emoji="🎨"
    ),
    "brand_reset": InteractionSpec(
        custom_id="brand_reset",
        label_key="owner_panel.brand_reset",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_brand_reset",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        dangerous=True,
        requires_audit=True,
        emoji="🔄"
    ),
    "brand_save": InteractionSpec(
        custom_id="brand_save",
        label_key="owner_panel.brand_save",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_brand_save",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        requires_audit=True,
        emoji="💾"
    ),
    "feat_add": InteractionSpec(
        custom_id="feat_add",
        label_key="owner_panel.feat_add",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_feat_add",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        requires_audit=True,
        emoji="➕"
    ),
    "feat_edit": InteractionSpec(
        custom_id="feat_edit",
        label_key="owner_panel.feat_edit",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_feat_edit",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        requires_audit=True,
        emoji="✏️"
    ),
    "feat_enable": InteractionSpec(
        custom_id="feat_enable",
        label_key="owner_panel.feat_enable",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_feat_enable",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        requires_audit=True,
        emoji="✅"
    ),
    "feat_disable": InteractionSpec(
        custom_id="feat_disable",
        label_key="owner_panel.feat_disable",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_feat_disable",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        dangerous=True,
        requires_audit=True,
        emoji="❌"
    ),
    "feat_link": InteractionSpec(
        custom_id="feat_link",
        label_key="owner_panel.feat_link",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_feat_link",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🔗"
    ),
    "feat_registry": InteractionSpec(
        custom_id="feat_registry",
        label_key="owner_panel.feat_registry",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_feat_registry",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="📋"
    ),
    "icon_button": InteractionSpec(
        custom_id="icon_button",
        label_key="owner_panel.icon_button",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_icon_button",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🔘"
    ),
    "icon_section": InteractionSpec(
        custom_id="icon_section",
        label_key="owner_panel.icon_section",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_icon_section",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="📂"
    ),
    "icon_status": InteractionSpec(
        custom_id="icon_status",
        label_key="owner_panel.icon_status",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_icon_status",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="📊"
    ),
    "text_edit_title": InteractionSpec(
        custom_id="text_edit_title",
        label_key="owner_panel.text_edit_title",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_text_edit_title",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        requires_audit=True,
        emoji="✏️"
    ),
    "text_edit_desc": InteractionSpec(
        custom_id="text_edit_desc",
        label_key="owner_panel.text_edit_desc",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_text_edit_desc",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        requires_audit=True,
        emoji="📝"
    ),
    "text_edit_msg": InteractionSpec(
        custom_id="text_edit_msg",
        label_key="owner_panel.text_edit_msg",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_text_edit_msg",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        requires_audit=True,
        emoji="💬"
    ),
    "text_reset": InteractionSpec(
        custom_id="text_reset",
        label_key="owner_panel.text_reset",
        interaction_type=InteractionType.BUTTON,
        module="owner_panel",
        handler_name="_handle_text_reset",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        dangerous=True,
        requires_audit=True,
        emoji="🔄"
    ),

    # ========== CONFIRMATION ==========
    "confirm_btn": InteractionSpec(
        custom_id="confirm_btn",
        label_key="confirm.yes",
        interaction_type=InteractionType.BUTTON,
        module="system",
        handler_name="_handle_confirm",
        required_permission=PermissionLevel.MEMBER,
        visible_to=("owner", "admin", "member"),
        emoji="✅"
    ),
    "cancel_btn": InteractionSpec(
        custom_id="cancel_btn",
        label_key="confirm.no",
        interaction_type=InteractionType.BUTTON,
        module="system",
        handler_name="_handle_cancel",
        required_permission=PermissionLevel.MEMBER,
        visible_to=("owner", "admin", "member"),
        emoji="❌"
    ),

    # ========== OPERATIONS PANEL ==========
    "ops_health_check": InteractionSpec(
        custom_id="ops_health_check",
        label_key="operations.health_check",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_health_check",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="💚"
    ),
    "ops_metrics": InteractionSpec(
        custom_id="ops_metrics",
        label_key="operations.metrics",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_metrics",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="📊"
    ),
    "ops_incidents": InteractionSpec(
        custom_id="ops_incidents",
        label_key="operations.incidents",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_incidents",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🚨"
    ),
    "ops_alerts": InteractionSpec(
        custom_id="ops_alerts",
        label_key="operations.alerts",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_alerts",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🔔"
    ),
    "ops_alert_test": InteractionSpec(
        custom_id="ops_alert_test",
        label_key="operations.alert_test",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_alert_test",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🧪"
    ),
    "ops_alert_toggle": InteractionSpec(
        custom_id="ops_alert_toggle",
        label_key="operations.alert_toggle",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_alert_toggle",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🔇"
    ),
    "ops_backup": InteractionSpec(
        custom_id="ops_backup",
        label_key="operations.backup",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_backup",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="💾"
    ),
    "ops_backup_create": InteractionSpec(
        custom_id="ops_backup_create",
        label_key="operations.backup_create",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_backup_create",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        requires_audit=True,
        emoji="➕"
    ),
    "ops_backup_list": InteractionSpec(
        custom_id="ops_backup_list",
        label_key="operations.backup_list",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_backup_list",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="📋"
    ),
    "ops_backup_verify": InteractionSpec(
        custom_id="ops_backup_verify",
        label_key="operations.backup_verify",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_backup_verify",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="✅"
    ),
    "ops_rollback": InteractionSpec(
        custom_id="ops_rollback",
        label_key="operations.rollback",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_rollback",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        dangerous=True,
        requires_audit=True,
        requires_confirmation=True,
        emoji="↩️"
    ),
    "ops_rollback_cancel": InteractionSpec(
        custom_id="ops_rollback_cancel",
        label_key="operations.rollback_cancel",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_rollback_cancel",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="❌"
    ),
    "ops_upgrade": InteractionSpec(
        custom_id="ops_upgrade",
        label_key="operations.upgrade",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_upgrade",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        dangerous=True,
        requires_audit=True,
        emoji="🚀"
    ),
    "ops_upgrade_check": InteractionSpec(
        custom_id="ops_upgrade_check",
        label_key="operations.upgrade_check",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_upgrade_check",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🔍"
    ),
    "ops_upgrade_apply": InteractionSpec(
        custom_id="ops_upgrade_apply",
        label_key="operations.upgrade_apply",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_upgrade_apply",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        dangerous=True,
        requires_audit=True,
        requires_confirmation=True,
        emoji="🚀"
    ),
    "ops_self_heal": InteractionSpec(
        custom_id="ops_self_heal",
        label_key="operations.self_heal",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_self_heal",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🧰"
    ),
    "ops_self_heal_toggle": InteractionSpec(
        custom_id="ops_self_heal_toggle",
        label_key="operations.self_heal_toggle",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_self_heal_toggle",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🔄"
    ),
    "ops_self_heal_run": InteractionSpec(
        custom_id="ops_self_heal_run",
        label_key="operations.self_heal_run",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_self_heal_run",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🧰"
    ),
    "ops_reports": InteractionSpec(
        custom_id="ops_reports",
        label_key="operations.reports",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_reports",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="📄"
    ),
    "ops_report_health": InteractionSpec(
        custom_id="ops_report_health",
        label_key="operations.report_health",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_report_health",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🏥"
    ),
    "ops_report_incidents": InteractionSpec(
        custom_id="ops_report_incidents",
        label_key="operations.report_incidents",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_report_incidents",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🚨"
    ),
    "ops_report_release": InteractionSpec(
        custom_id="ops_report_release",
        label_key="operations.report_release",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_report_release",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="🚀"
    ),
    "ops_settings": InteractionSpec(
        custom_id="ops_settings",
        label_key="operations.settings",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_settings",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="⚙️"
    ),
    "ops_settings_scheduler": InteractionSpec(
        custom_id="ops_settings_scheduler",
        label_key="operations.settings_scheduler",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_settings_scheduler",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="📅"
    ),
    "ops_settings_backup_retention": InteractionSpec(
        custom_id="ops_settings_backup_retention",
        label_key="operations.settings_backup_retention",
        interaction_type=InteractionType.BUTTON,
        module="operations",
        handler_name="_handle_settings_backup_retention",
        required_permission=PermissionLevel.OWNER,
        visible_to=("owner",),
        owner_only=True,
        emoji="💾"
    ),
}


def get_registry() -> dict[str, InteractionSpec]:
    """Get a copy of the interaction registry."""
    return INTERACTION_REGISTRY.copy()


def get_all_custom_ids() -> list[str]:
    """Get all registered custom_ids."""
    return list(INTERACTION_REGISTRY.keys())


def get_by_module(module: str) -> list[InteractionSpec]:
    """Get all interactions for a module."""
    return [spec for spec in INTERACTION_REGISTRY.values() if spec.module == module]


def get_by_permission(level: PermissionLevel) -> list[InteractionSpec]:
    """Get all interactions requiring a permission level."""
    return [spec for spec in INTERACTION_REGISTRY.values() if spec.required_permission == level]


def get_owner_only() -> list[InteractionSpec]:
    """Get all owner-only interactions."""
    return [spec for spec in INTERACTION_REGISTRY.values() if spec.owner_only]


def get_admin_only() -> list[InteractionSpec]:
    """Get all admin-only interactions."""
    return [spec for spec in INTERACTION_REGISTRY.values() if spec.admin_only]


def get_dangerous() -> list[InteractionSpec]:
    """Get all dangerous interactions (delete/modify)."""
    return [spec for spec in INTERACTION_REGISTRY.values() if spec.dangerous]


def get_selects() -> list[InteractionSpec]:
    """Get all select menu interactions."""
    return [spec for spec in INTERACTION_REGISTRY.values() if spec.interaction_type == InteractionType.SELECT]


def get_modals() -> list[InteractionSpec]:
    """Get all modal interactions."""
    return [spec for spec in INTERACTION_REGISTRY.values() if spec.interaction_type == InteractionType.MODAL]
