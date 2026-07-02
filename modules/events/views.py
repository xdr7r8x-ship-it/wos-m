"""
WOS-M Events Module
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
from views.base import BaseView, PageInfo, PaginationView
from views.buttons import ActionButton
from views.modals import EventModal
from views.selects import EventTypeSelect

class EventsView(BaseView):
    """Events management view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("events.title"),
                description="",
                icon="📅",
                color=0x3498db
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        self.add_item(ActionButton(
            label=i18n.get("events.create_event"),
            custom_id="event_create",
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("buttons.view"),
            custom_id="event_list",
            style=discord.ButtonStyle.primary,
            emoji="📋",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("buttons.edit"),
            custom_id="event_edit",
            style=discord.ButtonStyle.primary,
            emoji="✏️",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("buttons.delete"),
            custom_id="event_delete",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            row=1
        ))

async def events_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for events."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.MEMBER):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    view = EventsView(bot, interaction.user.id)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    await audit_log.log(
        user_id=str(interaction.user.id),
        user_name=str(interaction.user),
        action="view_events",
        category=AuditCategory.EVENTS
    )

async def event_create_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for creating event."""
    modal = EventModal(mode="add")
    await interaction.response.send_modal(modal)
    
    # Modal submit handled by EventModal.on_submit

async def event_list_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for listing events."""
    rows = await db.fetchall("SELECT * FROM events ORDER BY event_date DESC LIMIT 50")
    
    if not rows:
        await interaction.response.send_message(i18n.get("messages.no_results"), ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"📅 {i18n.get('events.title')}",
        color=0x3498db
    )
    
    for row in rows[:10]:
        event_time = row["event_time"] if "event_time" in row.keys() else ""
        location = row["location"] if "location" in row.keys() else "N/A"
        embed.add_field(
            name=row["name"],
            value=f"📅 {row['event_date']} {event_time}\n📍 {location}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def event_edit_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for editing an event."""
    await interaction.response.send_message("تحرير الحدث.", ephemeral=True)

async def event_delete_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for deleting an event."""
    await interaction.response.send_message("حذف الحدث.", ephemeral=True)
