"""
WOS-M Ministers Module
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


class MinistersView(BaseView):
    """Ministers management view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("ministers.title"),
                description="",
                icon="👔",
                color=0x9b59b6
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        self.add_item(ActionButton(
            label=i18n.get("ministers.add_minister"),
            custom_id="minister_add",
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("ministers.assign_minister"),
            custom_id="minister_assign",
            style=discord.ButtonStyle.primary,
            emoji="👤",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("ministers.minister_list"),
            custom_id="minister_list",
            style=discord.ButtonStyle.primary,
            emoji="📋",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("ministers.schedule_assignment"),
            custom_id="minister_schedule",
            style=discord.ButtonStyle.secondary,
            emoji="📅",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("ministers.reminder"),
            custom_id="minister_reminder",
            style=discord.ButtonStyle.secondary,
            emoji="🔔",
            row=1
        ))


async def ministers_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for ministers."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.MEMBER):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    view = MinistersView(bot, interaction.user.id)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    await audit_log.log(
        user_id=str(interaction.user.id),
        user_name=str(interaction.user),
        action="view_ministers",
        category=AuditCategory.MINISTERS
    )





