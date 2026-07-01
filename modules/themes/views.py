"""
WOS-M Themes Module
© MANSOUR — WOS-M. All rights reserved.
"""
import discord
from typing import Dict, Any, List, Optional

from core.bot import WOSMBot
from core.i18n import i18n
from core.database import db
from core.permissions import PermissionLevel, PermissionGuard
from core.audit_log import audit_log, AuditCategory
from views.base import BaseView, PageInfo
from views.buttons import ActionButton


class ThemesView(BaseView):
    """Themes and branding management view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("themes.title"),
                description="",
                icon="🎨",
                color=0xe91e63
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        self.add_item(ActionButton(
            label=i18n.get("themes.bot_name"),
            custom_id="theme_bot_name",
            style=discord.ButtonStyle.primary,
            emoji="🤖",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("themes.primary_color"),
            custom_id="theme_primary_color",
            style=discord.ButtonStyle.primary,
            emoji="🎨",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("themes.preview"),
            custom_id="theme_preview",
            style=discord.ButtonStyle.secondary,
            emoji="👁️",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("themes.footer_text"),
            custom_id="theme_footer",
            style=discord.ButtonStyle.secondary,
            emoji="📝",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("themes.signature"),
            custom_id="theme_signature",
            style=discord.ButtonStyle.secondary,
            emoji="✍️",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("themes.reset_theme"),
            custom_id="theme_reset",
            style=discord.ButtonStyle.danger,
            emoji="🔄",
            row=1
        ))


async def themes_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for themes."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.MEMBER):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    view = ThemesView(bot, interaction.user.id)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    await audit_log.log(
        user_id=str(interaction.user.id),
        user_name=str(interaction.user),
        action="view_themes",
        category=AuditCategory.THEMES
    )






