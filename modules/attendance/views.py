"""
WOS-M Attendance Module
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
from views.selects import AttendanceStatusSelect


class AttendanceView(BaseView):
    """Attendance management view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("attendance.title"),
                description="",
                icon="✅",
                color=0x2ecc71
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        self.add_item(ActionButton(
            label=i18n.get("attendance.record_attendance"),
            custom_id="att_record",
            style=discord.ButtonStyle.success,
            emoji="📝",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("attendance.attendance_list"),
            custom_id="att_list",
            style=discord.ButtonStyle.primary,
            emoji="📋",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("attendance.attendance_report"),
            custom_id="att_report",
            style=discord.ButtonStyle.primary,
            emoji="📊",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("attendance.attendance_history"),
            custom_id="att_history",
            style=discord.ButtonStyle.secondary,
            emoji="📜",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("attendance.export_report"),
            custom_id="att_export",
            style=discord.ButtonStyle.secondary,
            emoji="📤",
            row=1
        ))


async def attendance_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for attendance."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.MEMBER):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    view = AttendanceView(bot, interaction.user.id)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    await audit_log.log(
        user_id=str(interaction.user.id),
        user_name=str(interaction.user),
        action="view_attendance",
        category=AuditCategory.ATTENDANCE
    )


async def record_attendance_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for recording attendance."""
    events = await db.fetchall("SELECT * FROM events ORDER BY event_date DESC LIMIT 10")
    
    if not events:
        await interaction.response.send_message(i18n.get("messages.no_results"), ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"📝 {i18n.get('attendance.record_attendance')}",
        color=0x2ecc71
    )
    
    for event in events[:5]:
        embed.add_field(
            name=event["name"],
            value=f"📅 {event['event_date']}",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def attendance_list_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for attendance list."""
    rows = await db.fetchall("""
        SELECT e.name, e.event_date, 
               COUNT(CASE WHEN ar.status = 'present' THEN 1 END) as present,
               COUNT(CASE WHEN ar.status = 'absent' THEN 1 END) as absent
        FROM events e
        LEFT JOIN attendance_records ar ON e.id = ar.event_id
        GROUP BY e.id
        ORDER BY e.event_date DESC
        LIMIT 20
    """)
    
    embed = discord.Embed(
        title=f"📋 {i18n.get('attendance.attendance_list')}",
        color=0x2ecc71
    )
    
    for row in rows:
        embed.add_field(
            name=row["name"],
            value=f"📅 {row['event_date']}\n✅ {row['present']} | ❌ {row['absent']}",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)





