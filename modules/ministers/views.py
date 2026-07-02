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

async def minister_add_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for minister_add."""
    from views.base import BaseView, PageInfo
    
    guard = PermissionGuard(bot)
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.ALLIANCE_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    class AddMinisterView(BaseView):
        def __init__(self, bot, user_id):
            self.bot = bot
            super().__init__(user_id=user_id, page_info=PageInfo(
                title="👔 إضافة وزير جديد",
                description="أضف منصب وزير جديد في التحالف",
                icon="👔",
                color=0x9b59b6
            ))
            self.add_back_home_buttons()
    
    view = AddMinisterView(bot, interaction.user.id)
    embed = view.create_embed()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def minister_assign_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for minister_assign."""
    from core.database import db
    from views.selects import PlayerSelect
    
    guard = PermissionGuard(bot)
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.ALLIANCE_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    await interaction.response.send_message("⏳ جاري تحميل قائمة اللاعبين...", ephemeral=True, delete_after=2)
    
    # Get active ministers
    ministers = await db.fetchall(
        "SELECT m.*, p.name as player_name FROM ministers m "
        "LEFT JOIN players p ON m.player_id = p.id "
        "WHERE m.is_active = 1 ORDER BY m.created_at DESC"
    )
    
    embed = discord.Embed(
        title="👔 تعيين وزير",
        description="قائمة المناصب المتاحة:",
        color=0x9b59b6
    )
    
    if ministers:
        for m in ministers:
            player_name = m["player_name"] if "player_name" in m.keys() else "—"
            title = m["title"] if "title" in m.keys() else "—"
            embed.add_field(
                name=f"📌 {title}",
                value=f"👤 اللاعب: {player_name}",
                inline=True
            )
    else:
        embed.description = "لا توجد مناصب ministers"
    
    await interaction.edit_original_response(embed=embed, view=None)


async def minister_list_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for minister_list."""
    from core.database import db
    
    await interaction.response.send_message("⏳ جاري تحميل القائمة...", ephemeral=True, delete_after=1)
    
    ministers = await db.fetchall(
        "SELECT m.*, p.name as player_name FROM ministers m "
        "LEFT JOIN players p ON m.player_id = p.id "
        "ORDER BY m.created_at DESC LIMIT 30"
    )
    
    embed = discord.Embed(
        title="👔 قائمة الوزراء",
        description=f"إجمالي {len(ministers)} وزير:",
        color=0x3498db
    )
    
    if not ministers:
        embed.description = "لا توجد مناصب ministers"
    else:
        for m in ministers:
            player_name = m["player_name"] if "player_name" in m.keys() else "—"
            title = m["title"] if "title" in m.keys() else "—"
            is_active = "🟢 نشط" if m.get("is_active", 0) == 1 else "🔴 غير نشط"
            embed.add_field(
                name=f"📌 {title}",
                value=f"👤 {player_name} | {is_active}",
                inline=False
            )
    
    await interaction.edit_original_response(embed=embed)


async def minister_schedule_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for minister_schedule."""
    from views.base import BaseView, PageInfo
    
    guard = PermissionGuard(bot)
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.ALLIANCE_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    class ScheduleView(BaseView):
        def __init__(self, bot, user_id):
            self.bot = bot
            super().__init__(user_id=user_id, page_info=PageInfo(
                title="📅 جدول الوزراء",
                description="إدارة جدول عمل الوزراء",
                icon="📅",
                color=0xe67e22
            ))
            self.add_back_home_buttons()
    
    view = ScheduleView(bot, interaction.user.id)
    embed = view.create_embed()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def minister_reminder_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for minister_reminder."""
    from views.base import BaseView, PageInfo
    
    guard = PermissionGuard(bot)
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.ALLIANCE_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    class ReminderView(BaseView):
        def __init__(self, bot, user_id):
            self.bot = bot
            super().__init__(user_id=user_id, page_info=PageInfo(
                title="🔔 تذكيرات الوزراء",
                description="إدارة تذكيرات عمل الوزراء",
                icon="🔔",
                color=0xf39c12
            ))
            self.add_back_home_buttons()
    
    view = ReminderView(bot, interaction.user.id)
    embed = view.create_embed()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
