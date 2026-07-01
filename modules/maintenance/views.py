"""
WOS-M Maintenance Module
© MANSOUR — WOS-M. All rights reserved.
"""
import discord
from typing import Dict, Any, List, Optional
import asyncio

from core.bot import WOSMBot
from core.i18n import i18n
from core.database import db
from core.permissions import PermissionLevel, PermissionGuard
from core.audit_log import audit_log, AuditCategory
from views.base import BaseView, PageInfo
from views.buttons import ActionButton
from integrations.wos_api_client import wos_api_client
from integrations.gift_code_client import gift_code_client
from integrations.captcha_service import captcha_service
from integrations.ocr_service import ocr_service


class MaintenanceView(BaseView):
    """Maintenance tools view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("maintenance.title"),
                description="",
                icon="🔧",
                color=0x34495e
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        self.add_item(ActionButton(
            label=i18n.get("maintenance.health_check"),
            custom_id="maint_health",
            style=discord.ButtonStyle.success,
            emoji="💚",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("maintenance.database_check"),
            custom_id="maint_database",
            style=discord.ButtonStyle.primary,
            emoji="💾",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("maintenance.queue_check"),
            custom_id="maint_queue",
            style=discord.ButtonStyle.primary,
            emoji="📬",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("maintenance.api_check"),
            custom_id="maint_api",
            style=discord.ButtonStyle.primary,
            emoji="🌐",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("maintenance.backup"),
            custom_id="maint_backup",
            style=discord.ButtonStyle.secondary,
            emoji="💾",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("maintenance.error_logs"),
            custom_id="maint_logs",
            style=discord.ButtonStyle.secondary,
            emoji="❌",
            row=1
        ))


class PermissionsView(BaseView):
    """Permissions management view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("permissions.title"),
                description="",
                icon="🔐",
                color=0xf39c12
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        self.add_item(ActionButton(
            label=i18n.get("permissions.assign_role"),
            custom_id="perm_assign",
            style=discord.ButtonStyle.success,
            emoji="👤",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("permissions.remove_role"),
            custom_id="perm_remove",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("permissions.role_list"),
            custom_id="perm_list",
            style=discord.ButtonStyle.primary,
            emoji="📋",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("permissions.audit_log"),
            custom_id="perm_audit",
            style=discord.ButtonStyle.secondary,
            emoji="📜",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("permissions.transfer_ownership"),
            custom_id="perm_transfer",
            style=discord.ButtonStyle.danger,
            emoji="👑",
            row=1
        ))


class SettingsView(BaseView):
    """Settings management view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("settings.title"),
                description="",
                icon="⚙️",
                color=0x3498db
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        self.add_item(ActionButton(
            label=i18n.get("settings.general"),
            custom_id="settings_general",
            style=discord.ButtonStyle.primary,
            emoji="⚙️",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("settings.api"),
            custom_id="settings_api",
            style=discord.ButtonStyle.primary,
            emoji="🌐",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("settings.save_settings"),
            custom_id="settings_save",
            style=discord.ButtonStyle.success,
            emoji="💾",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("settings.reset_settings"),
            custom_id="settings_reset",
            style=discord.ButtonStyle.danger,
            emoji="🔄",
            row=1
        ))


async def maintenance_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for maintenance."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    view = MaintenanceView(bot, interaction.user.id)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    await audit_log.log(
        user_id=str(interaction.user.id),
        user_name=str(interaction.user),
        action="view_maintenance",
        category=AuditCategory.MAINTENANCE
    )


async def health_check_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for health check."""
    await interaction.response.send_message("⏳ " + i18n.get("messages.loading"), ephemeral=True)
    
    results = {}
    
    # Database check
    try:
        await db.fetchone("SELECT 1")
        results["database"] = "✅ OK"
    except:
        results["database"] = "❌ Failed"
    
    # API check
    results["wos_api"] = "✅ OK" if await wos_api_client.health_check() else "⚠️ Not configured"
    results["gift_api"] = "✅ OK" if await gift_code_client.health_check() else "⚠️ Not configured"
    results["captcha"] = "✅ OK" if await captcha_service.health_check() else "⚠️ Not configured"
    results["ocr"] = "✅ OK" if await ocr_service.health_check() else "⚠️ Not configured"
    
    embed = discord.Embed(
        title=f"💚 {i18n.get('maintenance.health_check')}",
        color=0x2ecc71
    )
    
    for check, status in results.items():
        embed.add_field(name=check.upper(), value=status, inline=True)
    
    await interaction.edit_original_response(embed=embed)


async def permissions_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for permissions."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.ALLIANCE_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    view = PermissionsView(bot, interaction.user.id)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def settings_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for settings."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.MEMBER):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    view = SettingsView(bot, interaction.user.id)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)















