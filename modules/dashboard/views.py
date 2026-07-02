"""
WOS-M Dashboard Module
© MANSOUR — WOS-M. All rights reserved.
"""
import discord
from discord import ui
from typing import Dict, Any, List, Optional

from core.bot import WOSMBot
from core.i18n import i18n
from core.database import db
from core.permissions import PermissionLevel, PermissionGuard
from core.audit_log import audit_log, AuditCategory
from core.interaction_registry import INTERACTION_REGISTRY
from views.base import BaseView, PageInfo
from views.buttons import DashboardButton
from views.selects import LanguageSelect

async def _get_user_role(bot: WOSMBot, interaction: discord.Interaction) -> str:
    """Get user role based on permissions."""
    guard = PermissionGuard(bot)
    user_id = str(interaction.user.id)
    
    if await guard.is_owner(user_id):
        return "owner"
    
    guild_id = str(interaction.guild_id) if interaction.guild_id else None
    level = await guard.get_user_level(user_id, guild_id=guild_id)
    
    if level and level <= PermissionLevel.SERVER_ADMIN:
        return "admin"
    
    return "member"

class DashboardView(BaseView):
    """Main dashboard view."""

    def __init__(self, bot: WOSMBot, user_id: int, role: str = "member"):
        self.bot = bot
        self.role = role
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("dashboard.title"),
                description=i18n.get("dashboard.description"),
                icon="🎮",
                color=0x3498db
            )
        )

        self._build_buttons()

    def _build_buttons(self):
        """Build dashboard buttons based on registry visibility."""
        from core.feature_registry import feature_registry
        
        ordered_ids = [
            "dash_alliances",
            "dash_players",
            "dash_gift_codes",
            "dash_events",
            "dash_attendance",
            "dash_bear_tracking",
            "dash_ministers",
            "dash_notifications",
            "dash_themes",
            "dash_permissions",
            "dash_maintenance",
            "dash_owner_panel",
            "dash_language",
            "dash_settings",
        ]
        
        row_map = {
            "dash_alliances": 0, "dash_players": 0, "dash_gift_codes": 0,
            "dash_events": 1, "dash_attendance": 1, "dash_bear_tracking": 1,
            "dash_ministers": 1, "dash_notifications": 2, "dash_themes": 2,
            "dash_permissions": 2, "dash_maintenance": 2, "dash_owner_panel": 3,
            "dash_language": 3, "dash_settings": 3,
        }

        for custom_id in ordered_ids:
            spec = INTERACTION_REGISTRY.get(custom_id)
            if not spec or not spec.production_visible:
                continue
            if self.role not in spec.visible_to:
                continue
            
            feature_name = custom_id.replace("dash_", "")
            if feature_registry and not feature_registry.is_feature_enabled(feature_name):
                continue

            row = row_map.get(custom_id, 0)
            
            self.add_item(DashboardButton(
                label=i18n.get(spec.label_key),
                custom_id=spec.custom_id,
                style=discord.ButtonStyle.primary,
                emoji=spec.emoji,
                row=row
            ))

        # ═══════════════════════════════════════════════════════
        # الأزرار الاحترافية للمالك
        # ═══════════════════════════════════════════════════════
        if self.role == "owner":
            # الصف 4 - أدوات احترافية
            self.add_item(DashboardButton(
                label="📊 الإحصائيات",
                custom_id="prof_stats",
                style=discord.ButtonStyle.secondary,
                emoji="📊",
                row=4
            ))
            self.add_item(DashboardButton(
                label="👥 المستخدمين",
                custom_id="prof_users",
                style=discord.ButtonStyle.secondary,
                emoji="👥",
                row=4
            ))
            self.add_item(DashboardButton(
                label="🔐 الصلاحيات",
                custom_id="prof_permissions",
                style=discord.ButtonStyle.secondary,
                emoji="🔐",
                row=4
            ))

            # الصف 5 - إعدادات متقدمة
            self.add_item(DashboardButton(
                label="⚙️ الإعدادات",
                custom_id="prof_settings",
                style=discord.ButtonStyle.secondary,
                emoji="⚙️",
                row=5
            ))
            self.add_item(DashboardButton(
                label="🎨 المظهر",
                custom_id="prof_appearance",
                style=discord.ButtonStyle.secondary,
                emoji="🎨",
                row=5
            ))
            self.add_item(DashboardButton(
                label="🔧 الصيانة",
                custom_id="prof_maintenance",
                style=discord.ButtonStyle.secondary,
                emoji="🔧",
                row=5
            ))

            # الصف 6 - إدارة متقدمة
            self.add_item(DashboardButton(
                label="🎁 الهدايا",
                custom_id="prof_gifts",
                style=discord.ButtonStyle.success,
                emoji="🎁",
                row=6
            ))
            self.add_item(DashboardButton(
                label="📢 البث",
                custom_id="prof_broadcast",
                style=discord.ButtonStyle.success,
                emoji="📢",
                row=6
            ))
            self.add_item(DashboardButton(
                label="🗄️ البيانات",
                custom_id="prof_database",
                style=discord.ButtonStyle.danger,
                emoji="🗄️",
                row=6
            ))

            # الصف 7 - سجلات وتحالفات
            self.add_item(DashboardButton(
                label="📜 السجلات",
                custom_id="prof_logs",
                style=discord.ButtonStyle.secondary,
                emoji="📜",
                row=7
            ))
            self.add_item(DashboardButton(
                label="🏰 التحالفات",
                custom_id="prof_alliances",
                style=discord.ButtonStyle.secondary,
                emoji="🏰",
                row=7
            ))
            self.add_item(DashboardButton(
                label="🔄 تحديث",
                custom_id="prof_refresh",
                style=discord.ButtonStyle.secondary,
                emoji="🔄",
                row=7
            ))


class LanguageView(BaseView):
    """Language selection view."""

    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("language.title"),
                description="",
                icon="🌐",
                color=0x1abc9c
            )
        )

        self.add_item(LanguageSelect(i18n.current_locale))
        self.add_back_home_buttons()

async def dashboard_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for dashboard command."""
    role = await _get_user_role(bot, interaction)
    view = DashboardView(bot, interaction.user.id, role)

    embed = view.create_embed()

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def language_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for language selection."""
    view = LanguageView(bot, interaction.user.id)

    embed = view.create_embed()

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# Navigation callbacks
async def nav_back_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Navigate back."""
    await dashboard_callback(bot, interaction)

async def nav_home_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Navigate home."""
    await dashboard_callback(bot, interaction)

async def nav_refresh_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Refresh dashboard."""
    await dashboard_callback(bot, interaction)

async def nav_close_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Close message."""
    try:
        await interaction.message.delete()
    except Exception:
        if not interaction.response.is_done():
            await interaction.response.send_message("تم إغلاق النافذة.", ephemeral=True)

async def settings_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Settings callback."""
    from views.base import BaseView, PageInfo
    from views.buttons import ActionButton
    
    class SettingsView(BaseView):
        def __init__(self, bot, user_id):
            self.bot = bot
            super().__init__(user_id=user_id, page_info=PageInfo(
                title="⚙️ الإعدادات",
                description="إعدادات البوت",
                icon="⚙️",
                color=0x3498db
            ))
            self.add_back_home_buttons()
    view = SettingsView(bot, interaction.user.id)
    embed = view.create_embed()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def settings_language_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Settings language callback."""
    from views.base import BaseView, PageInfo
    from views.selects import LanguageSelect
    
    class LanguageSettingsView(BaseView):
        def __init__(self, bot, user_id):
            self.bot = bot
            super().__init__(user_id=user_id, page_info=PageInfo(
                title="🌐 إعدادات اللغة",
                description="اختر لغة البوت",
                icon="🌐",
                color=0x3498db
            ))
            self.add_item(LanguageSelect(i18n.current_locale))
            self.add_back_home_buttons()
    
    view = LanguageSettingsView(bot, interaction.user.id)
    embed = view.create_embed()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def settings_timezone_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Settings timezone callback."""
    embed = discord.Embed(
        title="🕐 إعدادات المنطقة الزمنية",
        description="اختر منطقتك الزمنية.",
        color=0x3498db
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ═══════════════════════════════════════════════════════════════════════════════════
# Professional Panel Callbacks - Delegation
# ═══════════════════════════════════════════════════════════════════════════════════

async def prof_main_callback(bot: WOSMBot, interaction: discord.Interaction):
    from modules.owner_panel.professional_panel import owner_main_callback
    await owner_main_callback(bot, interaction)

async def prof_stats_callback(bot: WOSMBot, interaction: discord.Interaction):
    from modules.owner_panel.professional_panel import owner_stats_callback
    await owner_stats_callback(bot, interaction)

async def prof_users_callback(bot: WOSMBot, interaction: discord.Interaction):
    from modules.owner_panel.professional_panel import owner_users_callback
    await owner_users_callback(bot, interaction)

async def prof_permissions_callback(bot: WOSMBot, interaction: discord.Interaction):
    from modules.owner_panel.professional_panel import owner_permissions_callback
    await owner_permissions_callback(bot, interaction)

async def prof_settings_callback(bot: WOSMBot, interaction: discord.Interaction):
    from modules.owner_panel.professional_panel import owner_settings_callback
    await owner_settings_callback(bot, interaction)

async def prof_appearance_callback(bot: WOSMBot, interaction: discord.Interaction):
    from modules.owner_panel.professional_panel import owner_appearance_callback
    await owner_appearance_callback(bot, interaction)

async def prof_gifts_callback(bot: WOSMBot, interaction: discord.Interaction):
    from modules.owner_panel.professional_panel import owner_gifts_callback
    await owner_gifts_callback(bot, interaction)

async def prof_maintenance_callback(bot: WOSMBot, interaction: discord.Interaction):
    from modules.owner_panel.professional_panel import owner_maintenance_callback
    await owner_maintenance_callback(bot, interaction)

async def prof_broadcast_callback(bot: WOSMBot, interaction: discord.Interaction):
    from modules.owner_panel.professional_panel import owner_broadcast_callback
    await owner_broadcast_callback(bot, interaction)

async def prof_database_callback(bot: WOSMBot, interaction: discord.Interaction):
    from modules.owner_panel.professional_panel import owner_database_callback
    await owner_database_callback(bot, interaction)

async def prof_logs_callback(bot: WOSMBot, interaction: discord.Interaction):
    from modules.owner_panel.professional_panel import owner_logs_callback
    await owner_logs_callback(bot, interaction)

async def prof_alliances_callback(bot: WOSMBot, interaction: discord.Interaction):
    from modules.owner_panel.professional_panel import owner_alliances_callback
    await owner_alliances_callback(bot, interaction)

async def prof_refresh_callback(bot: WOSMBot, interaction: discord.Interaction):
    from modules.owner_panel.professional_panel import owner_main_callback
    await owner_main_callback(bot, interaction)
