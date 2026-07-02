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

async def att_record_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for att_record."""
    from views.base import BaseView, PageInfo
    from views.selects import AttendanceStatusSelect
    
    guild_id = interaction.guild_id
    
    class RecordAttendanceView(BaseView):
        def __init__(self, bot, user_id):
            self.bot = bot
            super().__init__(user_id=user_id, page_info=PageInfo(
                title="✅ تسجيل الحضور",
                description="سجل حضور اللاعبين في الحدث",
                icon="✅",
                color=0x2ecc71
            ))
            self.add_item(AttendanceStatusSelect())
            self.add_back_home_buttons()
    
    view = RecordAttendanceView(bot, interaction.user.id)
    embed = view.create_embed()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def att_list_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for att_list."""
    from views.base import BaseView, PageInfo
    from core.database import db
    
    await interaction.response.send_message("⏳ جاري التحميل...", ephemeral=True, delete_after=1)
    
    records = await db.fetchall(
        "SELECT ar.*, e.name as event_name, p.name as player_name "
        "FROM attendance_records ar "
        "LEFT JOIN events e ON ar.event_id = e.id "
        "LEFT JOIN players p ON ar.player_id = p.id "
        "ORDER BY ar.recorded_at DESC LIMIT 20"
    )
    
    embed = discord.Embed(
        title="📋 قائمة الحضور",
        description=f"آخر {len(records)} سجلات حضور:",
        color=0x3498db
    )
    
    if not records:
        embed.description = "لا توجد سجلات حضور"
    else:
        for record in records:
            event_name = record["event_name"] if "event_name" in record.keys() else "—"
            player_name = record["player_name"] if "player_name" in record.keys() else "—"
            status = record["status"] if "status" in record.keys() else "—"
            recorded_at = record["recorded_at"] if "recorded_at" in record.keys() else "—"
            embed.add_field(
                name=f"🎭 {event_name}",
                value=f"👤 اللاعب: {player_name}\n📊 الحالة: {status}\n🕐 {recorded_at}",
                inline=False
            )
    
    await interaction.edit_original_response(embed=embed, view=None)


async def att_report_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for att_report."""
    from core.database import db
    
    await interaction.response.send_message("⏳ جاري إنشاء التقرير...", ephemeral=True, delete_after=2)
    
    # Get attendance statistics
    total_records = await db.fetchall(
        "SELECT COUNT(*) as total, status FROM attendance_records GROUP BY status"
    )
    
    embed = discord.Embed(
        title="📊 تقرير الحضور",
        description="إحصائيات الحضور:",
        color=0x9b59b6
    )
    
    if total_records:
        for stat in total_records:
            status = stat["status"] if "status" in stat.keys() else "—"
            count = stat["total"] if "total" in stat.keys() else 0
            embed.add_field(name=f"📌 {status}", value=f"**{count}** سجل", inline=True)
    else:
        embed.description = "لا توجد بيانات حضور"
    
    embed.set_footer(text="WOS-M © MANSOUR")
    await interaction.edit_original_response(embed=embed)


async def att_export_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for att_export."""
    from core.database import db
    import io
    import csv
    
    await interaction.response.send_message("⏳ جاري تصدير البيانات...", ephemeral=True, delete_after=2)
    
    records = await db.fetchall(
        "SELECT ar.*, e.name as event_name, p.name as player_name "
        "FROM attendance_records ar "
        "LEFT JOIN events e ON ar.event_id = e.id "
        "LEFT JOIN players p ON ar.player_id = p.id "
        "ORDER BY ar.recorded_at DESC"
    )
    
    if not records:
        await interaction.edit_original_response(content="❌ لا توجد بيانات للتصدير", embed=None, view=None)
        return
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["الحدث", "اللاعب", "الحالة", "تاريخ التسجيل"])
    
    for record in records:
        writer.writerow([
            record.get("event_name", "—") if hasattr(record, 'get') else record["event_name"] if "event_name" in record.keys() else "—",
            record.get("player_name", "—") if hasattr(record, 'get') else record["player_name"] if "player_name" in record.keys() else "—",
            record.get("status", "—") if hasattr(record, 'get') else record["status"] if "status" in record.keys() else "—",
            record.get("recorded_at", "—") if hasattr(record, 'get') else record["recorded_at"] if "recorded_at" in record.keys() else "—"
        ])
    
    output.seek(0)
    await interaction.edit_original_response(
        content="✅ تم تصدير البيانات بنجاح",
        embed=None,
        view=None
    )
    await interaction.followup.send(
        file=discord.File(fp=io.BytesIO(output.getvalue().encode()), filename="attendance_export.csv"),
        ephemeral=True
    )


async def att_history_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for att_history."""
    from views.base import BaseView, PageInfo
    from core.database import db
    
    await interaction.response.send_message("⏳ جاري تحميل السجل...", ephemeral=True, delete_after=1)
    
    history = await db.fetchall(
        "SELECT * FROM attendance_records ORDER BY recorded_at DESC LIMIT 50"
    )
    
    embed = discord.Embed(
        title="📜 سجل الحضور",
        description=f"آخر {len(history)} سجل:",
        color=0xe67e22
    )
    
    if not history:
        embed.description = "لا يوجد سجل حضور"
    else:
        for record in history:
            event_id = record["event_id"] if "event_id" in record.keys() else "—"
            status = record["status"] if "status" in record.keys() else "—"
            recorded_at = record["recorded_at"] if "recorded_at" in record.keys() else "—"
            embed.add_field(
                name=f"🎭 حدث #{event_id}",
                value=f"📊 الحالة: {status}\n🕐 {recorded_at}",
                inline=True
            )
    
    await interaction.edit_original_response(embed=embed)
