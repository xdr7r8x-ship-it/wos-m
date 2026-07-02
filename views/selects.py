"""
WOS-M Select Menus
© MANSOUR — WOS-M. All rights reserved.
"""
import discord
from discord import ui
from typing import Optional, List, Dict, Any

from core.i18n import i18n


class BaseSelect(ui.Select):
    """Base select menu."""
    
    def __init__(
        self,
        custom_id: str,
        placeholder: str,
        options: List[discord.SelectOption],
        min_values: int = 1,
        max_values: int = 1
    ):
        super().__init__(
            custom_id=custom_id,
            placeholder=placeholder,
            options=options,
            min_values=min_values,
            max_values=max_values
        )


class LanguageSelect(ui.Select):
    """Language selection menu."""
    
    def __init__(self, current_locale: str = "ar"):
        options = [
            discord.SelectOption(
                label="العربية",
                value="ar",
                emoji="🇸🇦",
                default=current_locale == "ar"
            ),
            discord.SelectOption(
                label="English",
                value="en",
                emoji="🇬🇧",
                default=current_locale == "en"
            )
        ]
        
        super().__init__(
            custom_id="language_select",
            placeholder=i18n.get("language.select"),
            options=options
        )


class AllianceSelect(ui.Select):
    """Alliance selection menu."""
    
    def __init__(self, alliances: List[Dict[str, Any]], placeholder: str = ""):
        options = [
            discord.SelectOption(
                label=a.get("name", "Unknown"),
                value=str(a.get("id", "")),
                emoji="🏰"
            )
            for a in alliances
        ]
        
        super().__init__(
            custom_id="alliance_select",
            placeholder=placeholder or i18n.get("alliances.title"),
            options=options
        )


class PlayerSelect(ui.Select):
    """Player selection menu."""
    
    def __init__(self, players: List[Dict[str, Any]], placeholder: str = ""):
        options = [
            discord.SelectOption(
                label=f"{p.get('name', 'Unknown')} ({p.get('fid', '')})",
                value=str(p.get("id", "")),
                emoji="👥"
            )
            for p in players[:25]  # Discord limit
        ]
        
        super().__init__(
            custom_id="player_select",
            placeholder=placeholder or i18n.get("players.title"),
            options=options
        )


class EventTypeSelect(ui.Select):
    """Event type selection menu."""
    
    def __init__(self, current_type: Optional[str] = None):
        types = [
            ("foundry", i18n.get("events.types.foundry"), "🔥"),
            ("canyon", i18n.get("events.types.canyon"), "🏜️"),
            ("crazy_joe", i18n.get("events.types.crazy_joe"), "🃏"),
            ("bear", i18n.get("events.types.bear"), "🐻"),
            ("castle", i18n.get("events.types.castle"), "🏰"),
            ("frostdragon", i18n.get("events.types.frostdragon"), "🐉"),
            ("other", i18n.get("events.types.other"), "📌")
        ]
        
        options = [
            discord.SelectOption(
                label=name,
                value=type_key,
                emoji=emoji,
                default=current_type == type_key
            )
            for type_key, name, emoji in types
        ]
        
        super().__init__(
            custom_id="event_type_select",
            placeholder=i18n.get("events.event_type"),
            options=options
        )


class AttendanceStatusSelect(ui.Select):
    """Attendance status selection menu."""
    
    def __init__(self):
        options = [
            discord.SelectOption(
                label=i18n.get("attendance.present"),
                value="present",
                emoji="✅"
            ),
            discord.SelectOption(
                label=i18n.get("attendance.absent"),
                value="absent",
                emoji="❌"
            ),
            discord.SelectOption(
                label=i18n.get("attendance.late"),
                value="late",
                emoji="⏰"
            ),
            discord.SelectOption(
                label=i18n.get("attendance.excused"),
                value="excused",
                emoji="📋"
            )
        ]
        
        super().__init__(
            custom_id="attendance_status_select",
            placeholder=i18n.get("attendance.record_attendance"),
            options=options
        )


class PermissionRoleSelect(ui.Select):
    """Permission role selection menu."""
    
    def __init__(self, current_role: Optional[str] = None):
        roles = [
            ("owner", i18n.get("permissions.owner"), "👑"),
            ("global_admin", i18n.get("permissions.global_admin"), "⚙️"),
            ("server_admin", i18n.get("permissions.server_admin"), "🔧"),
            ("alliance_admin", i18n.get("permissions.alliance_admin"), "🏰"),
            ("member", i18n.get("permissions.member"), "👤")
        ]
        
        options = [
            discord.SelectOption(
                label=name,
                value=role_key,
                emoji=emoji,
                default=current_role == role_key
            )
            for role_key, name, emoji in roles
        ]
        
        super().__init__(
            custom_id="permission_role_select",
            placeholder=i18n.get("permissions.title"),
            options=options
        )


class NotificationTypeSelect(ui.Select):
    """Notification type selection menu."""
    
    def __init__(self):
        options = [
            discord.SelectOption(
                label=i18n.get("notifications.game_events"),
                value="game_events",
                emoji="🎮"
            ),
            discord.SelectOption(
                label=i18n.get("notifications.gift_codes"),
                value="gift_codes",
                emoji="🎁"
            ),
            discord.SelectOption(
                label=i18n.get("notifications.minister_schedule"),
                value="minister_schedule",
                emoji="👔"
            )
        ]
        
        super().__init__(
            custom_id="notification_type_select",
            placeholder=i18n.get("notifications.notification_type"),
            options=options
        )


class FeatureSelect(ui.Select):
    """Feature selection menu."""
    
    def __init__(self, features: List[Dict[str, Any]], placeholder: str = ""):
        options = [
            discord.SelectOption(
                label=f.get("name_ar") or f.get("name_en", "Unknown"),
                value=f.get("key", ""),
                emoji=f.get("icon", "⚙️"),
                description=f.get("description_ar") or f.get("description_en", "")
            )
            for f in features
        ]
        
        super().__init__(
            custom_id="feature_select",
            placeholder=placeholder or i18n.get("owner_panel.feature_management"),
            options=options
        )


class GiftCodeStatusSelect(ui.Select):
    """Gift code status selection menu."""
    
    def __init__(self):
        statuses = [
            ("pending", i18n.get("gift_codes.status_pending"), "⏳"),
            ("valid", i18n.get("gift_codes.status_valid"), "✅"),
            ("invalid", i18n.get("gift_codes.status_invalid"), "❌"),
            ("expired", i18n.get("gift_codes.status_expired"), "📅"),
            ("redeeming", i18n.get("gift_codes.status_redeeming"), "🔄"),
            ("redeemed", i18n.get("gift_codes.status_redeemed"), "🎉"),
            ("failed", i18n.get("gift_codes.status_failed"), "⚠️")
        ]
        
        options = [
            discord.SelectOption(
                label=name,
                value=status_key,
                emoji=emoji
            )
            for status_key, name, emoji in statuses
        ]
        
        super().__init__(
            custom_id="gift_code_status_select",
            placeholder=i18n.get("gift_codes.status"),
            options=options,
            max_values=len(options)
        )


class TimezoneSelect(ui.Select):
    """Timezone selection menu."""
    
    def __init__(self, current_timezone: str = "UTC"):
        timezones = [
            ("UTC", "UTC", "🌍"),
            ("Asia/Riyadh", "Riyadh (AST)", "🇸🇦"),
            ("Europe/London", "London (GMT/BST)", "🇬🇧"),
            ("America/New_York", "New York (EST/EDT)", "🇺🇸"),
            ("America/Los_Angeles", "Los Angeles (PST/PDT)", "🇺🇸"),
            ("Asia/Dubai", "Dubai (GST)", "🇦🇪"),
            ("Asia/Kolkata", "India (IST)", "🇮🇳"),
            ("Asia/Tokyo", "Tokyo (JST)", "🇯🇵"),
            ("Australia/Sydney", "Sydney (AEST/AEDT)", "🇦🇺")
        ]
        
        options = [
            discord.SelectOption(
                label=display,
                value=tz,
                emoji=emoji,
                default=current_timezone == tz
            )
            for tz, display, emoji in timezones
        ]
        
        super().__init__(
            custom_id="timezone_select",
            placeholder=i18n.get("notifications.timezone"),
            options=options
        )


class OwnerPanelSectionSelect(ui.Select):
    """Owner panel section selection menu."""
    
    def __init__(self):
        options = [
            discord.SelectOption(
                label=i18n.get("owner_panel.operations_center"),
                value="operations",
                emoji="🛠️",
                description="Operations monitoring and control"
            ),
            discord.SelectOption(
                label=i18n.get("owner_panel.language_management"),
                value="language",
                emoji="🌐",
                description="Change bot language"
            ),
            discord.SelectOption(
                label=i18n.get("owner_panel.button_management"),
                value="buttons",
                emoji="🔘",
                description="Manage dashboard buttons"
            ),
            discord.SelectOption(
                label=i18n.get("owner_panel.text_management"),
                value="texts",
                emoji="📝",
                description="Edit visible texts"
            ),
            discord.SelectOption(
                label=i18n.get("owner_panel.icon_management"),
                value="icons",
                emoji="🎨",
                description="Manage icons and emojis"
            ),
            discord.SelectOption(
                label=i18n.get("owner_panel.branding_management"),
                value="branding",
                emoji="🎨",
                description="Bot name and colors"
            ),
            discord.SelectOption(
                label=i18n.get("owner_panel.feature_management"),
                value="features",
                emoji="⚙️",
                description="Manage features"
            )
        ]
        
        super().__init__(
            custom_id="owner_panel_section_select",
            placeholder=i18n.get("owner_panel.title"),
            options=options,
            max_values=1
        )


class PaginationSelect(ui.Select):
    """Pagination select for pages."""
    
    def __init__(self, total_pages: int, current_page: int = 1):
        options = [
            discord.SelectOption(
                label=f"{i18n.get('messages.page')} {i}",
                value=str(i)
            )
            for i in range(1, min(total_pages + 1, 26))  # Discord limit
        ]
        
        super().__init__(
            custom_id="page_select",
            placeholder=i18n.get("messages.page"),
            options=options,
            default_values=[str(current_page)]
        )


class SettingsSelect(ui.Select):
    """Settings category selection menu."""
    
    def __init__(self):
        options = [
            discord.SelectOption(
                label=i18n.get("settings.general"),
                value="general",
                emoji="⚙️"
            ),
            discord.SelectOption(
                label=i18n.get("settings.database"),
                value="database",
                emoji="💾"
            ),
            discord.SelectOption(
                label=i18n.get("settings.api"),
                value="api",
                emoji="🌐"
            ),
            discord.SelectOption(
                label=i18n.get("settings.appearance"),
                value="appearance",
                emoji="🎨"
            ),
            discord.SelectOption(
                label=i18n.get("settings.advanced"),
                value="advanced",
                emoji="🔧"
            )
        ]
        
        super().__init__(
            custom_id="settings_select",
            placeholder=i18n.get("settings.title"),
            options=options
        )
