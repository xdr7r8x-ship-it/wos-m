"""
WOS-M Players Module
© MANSOUR — WOS-M. All rights reserved.
"""
import discord
from discord import ui
import csv
import io
import json
from typing import Dict, Any, List, Optional

from core.bot import WOSMBot
from core.i18n import i18n
from core.database import db
from core.permissions import PermissionLevel, PermissionGuard
from core.audit_log import audit_log, AuditCategory
from views.base import BaseView, PageInfo, PaginationView
from views.buttons import ActionButton
from views.modals import PlayerModal
from integrations.wos_api_client import wos_api_client


class PlayersView(BaseView):
    """Players management view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("players.title"),
                description="",
                icon="👥",
                color=0x3498db
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        """Add management buttons."""
        self.add_item(ActionButton(
            label=i18n.get("players.add_title"),
            custom_id="player_add",
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("players.search_player"),
            custom_id="player_search",
            style=discord.ButtonStyle.primary,
            emoji="🔍",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("buttons.view"),
            custom_id="player_list",
            style=discord.ButtonStyle.primary,
            emoji="📋",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("players.sync_data"),
            custom_id="player_sync",
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("players.move_player"),
            custom_id="player_move",
            style=discord.ButtonStyle.secondary,
            emoji="➡️",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("players.export_players"),
            custom_id="player_export",
            style=discord.ButtonStyle.secondary,
            emoji="📤",
            row=1
        ))


class PlayersListView(PaginationView):
    """Players list view."""
    
    def __init__(self, bot: WOSMBot, user_id: int, alliance_id: Optional[int] = None):
        self.bot = bot
        self.alliance_id = alliance_id
        
        super().__init__(
            user_id=user_id,
            items=[],
            items_per_page=10,
            page_info=PageInfo(
                title=i18n.get("players.title"),
                icon="👥",
                color=0x3498db
            )
        )
    
    async def load_players(self):
        """Load players from database."""
        query = "SELECT p.*, a.name as alliance_name FROM players p LEFT JOIN alliances a ON p.alliance_id = a.id"
        params = []
        
        if self.alliance_id:
            query += " WHERE p.alliance_id = ?"
            params.append(self.alliance_id)
        
        query += " ORDER BY p.name LIMIT 100"
        
        rows = await db.fetchall(query, tuple(params))
        self.items = [dict(row) for row in rows]
        self._total_pages = max(1, (len(self.items) + self.items_per_page - 1) // self.items_per_page)
        self._update_buttons()


async def players_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for players."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.MEMBER):
        await interaction.response.send_message(
            i18n.get("messages.no_permission"),
            ephemeral=True
        )
        return
    
    view = PlayersView(bot, interaction.user.id)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    await audit_log.log(
        user_id=str(interaction.user.id),
        user_name=str(interaction.user),
        action="view_players",
        category=AuditCategory.PLAYERS
    )


def validate_fid(fid: str) -> bool:
    """Validate FID format (8-11 digits)."""
    if not fid:
        return False
    fid_clean = fid.strip()
    return fid_clean.isdigit() and 8 <= len(fid_clean) <= 11


async def player_add_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle player_add button."""
    guard = PermissionGuard(bot)
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.ADMIN):
        await interaction.response.send_message("❌ ليس لديك صلاحية.", ephemeral=True)
        return
    modal = PlayerAddModal(bot)
    await interaction.response.send_modal(modal)

class PlayerAddModal(ui.Modal):
    """Modal for adding a player."""

    def __init__(self, bot):
        super().__init__(title="➕ إضافة لاعب")
        self.bot = bot
        self.fid_input = ui.TextInput(label="FID اللاعب", placeholder="12345678", required=True, min_length=8, max_length=11)
        self.name_input = ui.TextInput(label="اسم اللاعب", placeholder="Player Name", required=True, min_length=1, max_length=50)
        self.alliance_input = ui.TextInput(label="ID التحالف (اختياري)", placeholder="اتركه فارغاً", required=False)
        self.add_item(self.fid_input)
        self.add_item(self.name_input)
        self.add_item(self.alliance_input)

    async def on_submit(self, interaction):
        fid = self.fid_input.value.strip()
        name = self.name_input.value.strip()
        alliance_id = self.alliance_input.value.strip() or None
        if not validate_fid(fid):
            await interaction.response.send_message("❌ FID غير صالح.", ephemeral=True)
            return
        try:
            existing = await db.fetchone("SELECT id FROM players WHERE fid = ?", (fid,))
            if existing:
                await interaction.response.send_message(f"❌ اللاعب `{fid}` موجود.", ephemeral=True)
                return
            cursor = await db.execute("INSERT INTO players (fid, name, alliance_id) VALUES (?, ?, ?)", (fid, name, alliance_id))
            await db.commit()
            await interaction.response.send_message(f"✅ تم إضافة `{name}`.", ephemeral=True)
        except Exception:
            import logging
            logging.exception("PlayerAddModal failed")
            await interaction.response.send_message("❌ خطأ.", ephemeral=True)

    async def on_error(self, interaction, error):
        import logging
        logging.exception("PlayerAddModal error")
        if not interaction.response.is_done():
            await interaction.response.send_message("حدث خطأ.", ephemeral=True)

async def player_search_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle player_search button."""
    modal = PlayerSearchModal(bot)
    await interaction.response.send_modal(modal)

class PlayerSearchModal(ui.Modal):
    """Modal for searching players."""

    def __init__(self, bot):
        super().__init__(title="🔍 بحث عن لاعب")
        self.bot = bot
        self.fid_input = ui.TextInput(label="FID اللاعب", placeholder="اتركه فارغاً للبحث بالاسم", required=False, min_length=8, max_length=11)
        self.name_input = ui.TextInput(label="اسم اللاعب", placeholder="اكتب جزء من الاسم", required=False, min_length=1)
        self.add_item(self.fid_input)
        self.add_item(self.name_input)

    async def on_submit(self, interaction):
        query = "SELECT * FROM players WHERE 1=1"
        params = []
        if self.fid_input.value:
            if not validate_fid(self.fid_input.value):
                await interaction.response.send_message("❌ FID غير صالح.", ephemeral=True)
                return
            query += " AND fid = ?"
            params.append(self.fid_input.value.strip())
        if self.name_input.value:
            query += " AND name LIKE ?"
            params.append(f"%{self.name_input.value.strip()}%")
        if not self.fid_input.value and not self.name_input.value:
            await interaction.response.send_message("❌ أدخل FID أو اسم.", ephemeral=True)
            return
        try:
            rows = await db.fetchall(query, tuple(params))
            if not rows:
                await interaction.response.send_message("❌ لا نتائج.", ephemeral=True)
                return
            embed = discord.Embed(title=f"🔍 النتائج ({len(rows)})", color=0x3498db)
            for row in rows:
                embed.add_field(name=row['name'], value=f"FID: `{row['fid']}`", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception:
            import logging
            logging.exception("PlayerSearchModal failed")
            await interaction.response.send_message("❌ خطأ.", ephemeral=True)

    async def on_error(self, interaction, error):
        import logging
        logging.exception("PlayerSearchModal error")
        if not interaction.response.is_done():
            await interaction.response.send_message("حدث خطأ.", ephemeral=True)

async def player_list_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle player_list button - List all players."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.MEMBER):
        await interaction.response.send_message(
            "❌ ليس لديك صلاحية عرض اللاعبين.",
            ephemeral=True
        )
        return
    
    try:
        rows = await db.fetchall(
            """SELECT p.*, a.name as alliance_name 
               FROM players p 
               LEFT JOIN alliances a ON p.alliance_id = a.id 
               ORDER BY p.name LIMIT 100"""
        )
        
        if not rows:
            await interaction.response.send_message(
                "📋 لا يوجد لاعبون مسجلون.",
                ephemeral=True
            )
            return
        
        view = PlayersListView(bot, interaction.user.id)
        view.items = [dict(row) for row in rows]
        view._total_pages = max(1, (len(view.items) + view.items_per_page - 1) // view.items_per_page)
        view._update_buttons()
        
        embed = view.create_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(
            "❌ حدث خطأ أثناء تحميل اللاعبين. تم تسجيل التفاصيل.",
            ephemeral=True
        )


async def player_sync_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle player_sync button."""
    guard = PermissionGuard(bot)
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.ADMIN):
        await interaction.response.send_message("❌ ليس لديك صلاحية.", ephemeral=True)
        return
    modal = PlayerSyncModal(bot)
    await interaction.response.send_modal(modal)

class PlayerSyncModal(ui.Modal):
    """Modal for syncing player data."""

    def __init__(self, bot):
        super().__init__(title="🔄 مزامنة بيانات اللاعب")
        self.bot = bot
        self.fid_input = ui.TextInput(label="FID اللاعب", placeholder="12345678", required=True, min_length=8, max_length=11)
        self.add_item(self.fid_input)

    async def on_submit(self, interaction):
        fid = self.fid_input.value.strip()
        if not validate_fid(fid):
            await interaction.response.send_message("❌ FID غير صالح.", ephemeral=True)
            return
        try:
            success, player_info, msg = await wos_api_client.get_player(fid)
            if not success or not player_info:
                await interaction.response.send_message(f"❌ {msg or 'فشل'}", ephemeral=True)
                return
            await db.execute("UPDATE players SET level = ? WHERE fid = ?", (player_info.get("level", 1), fid))
            await db.commit()
            await interaction.response.send_message(f"✅ تم تحديث `{player_info.get('name', fid)}`.", ephemeral=True)
        except Exception:
            import logging
            logging.exception("PlayerSyncModal failed")
            await interaction.response.send_message("❌ خطأ.", ephemeral=True)

    async def on_error(self, interaction, error):
        import logging
        logging.exception("PlayerSyncModal error")
        if not interaction.response.is_done():
            await interaction.response.send_message("حدث خطأ.", ephemeral=True)

async def player_move_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle player_move button."""
    guard = PermissionGuard(bot)
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.ADMIN):
        await interaction.response.send_message("❌ ليس لديك صلاحية.", ephemeral=True)
        return
    modal = PlayerMoveModal(bot)
    await interaction.response.send_modal(modal)

class PlayerMoveModal(ui.Modal):
    """Modal for moving player."""

    def __init__(self, bot):
        super().__init__(title="➡️ نقل لاعب لتحالف")
        self.bot = bot
        self.fid_input = ui.TextInput(label="FID اللاعب", placeholder="12345678", required=True, min_length=8, max_length=11)
        self.alliance_input = ui.TextInput(label="ID التحالف الجديد", placeholder="اتركه فارغاً للإزالة", required=False)
        self.add_item(self.fid_input)
        self.add_item(self.alliance_input)

    async def on_submit(self, interaction):
        fid = self.fid_input.value.strip()
        alliance_id = self.alliance_input.value.strip() or None
        if not validate_fid(fid):
            await interaction.response.send_message("❌ FID غير صالح.", ephemeral=True)
            return
        try:
            player = await db.fetchone("SELECT * FROM players WHERE fid = ?", (fid,))
            if not player:
                await interaction.response.send_message(f"❌ اللاعب `{fid}` غير موجود.", ephemeral=True)
                return
            await db.execute("UPDATE players SET alliance_id = ? WHERE fid = ?", (alliance_id, fid))
            await db.commit()
            await interaction.response.send_message(f"✅ تم نقل `{player['name']}`.", ephemeral=True)
        except Exception:
            import logging
            logging.exception("PlayerMoveModal failed")
            await interaction.response.send_message("❌ خطأ.", ephemeral=True)

    async def on_error(self, interaction, error):
        import logging
        logging.exception("PlayerMoveModal error")
        if not interaction.response.is_done():
            await interaction.response.send_message("حدث خطأ.", ephemeral=True)

async def player_export_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle player_export button - Export players to CSV/JSON."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.ADMIN):
        await interaction.response.send_message(
            "❌ ليس لديك صلاحية تصدير اللاعبين.",
            ephemeral=True
        )
        return
    
    try:
        rows = await db.fetchall(
            """SELECT p.fid, p.name, p.level, a.name as alliance_name
               FROM players p 
               LEFT JOIN alliances a ON p.alliance_id = a.id 
               ORDER BY p.name"""
        )
        
        if not rows:
            await interaction.response.send_message(
                "❌ لا يوجد لاعبون للتصدير.",
                ephemeral=True
            )
            return
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["FID", "Name", "Level", "Alliance"])
        
        for row in rows:
            level = row["level"] if "level" in row.keys() else ""
            alliance = row["alliance_name"] if "alliance_name" in row.keys() else ""
            writer.writerow([row["fid"], row["name"], level, alliance])
        
        csv_content = output.getvalue()
        output.close()
        
        # Create JSON
        players = []
        for row in rows:
            players.append({
                "fid": row["fid"],
                "name": row["name"],
                "level": row["level"] if "level" in row.keys() else None,
                "alliance": row["alliance_name"] if "alliance_name" in row.keys() else None
            })
        
        json_content = json.dumps(players, indent=2, ensure_ascii=False)
        
        # Send files
        await interaction.response.send_message(
            "📤 تصدير اللاعبين:",
            ephemeral=True
        )
        
        await interaction.followup.send(
            file=discord.File(
                io.BytesIO(csv_content.encode()),
                filename="players.csv"
            ),
            ephemeral=True
        )
        
        await interaction.followup.send(
            file=discord.File(
                io.BytesIO(json_content.encode()),
                filename="players.json"
            ),
            ephemeral=True
        )
        
        await audit_log.log(
            user_id=str(interaction.user.id),
            user_name=str(interaction.user),
            action="export_players",
            category=AuditCategory.PLAYERS,
            details={"count": len(rows)}
        )
        
    except Exception as e:
        await interaction.followup.send(
            "❌ حدث خطأ أثناء التصدير. تم تسجيل التفاصيل.",
            ephemeral=True
        )


async def player_select_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle player_select from select menu."""
    if interaction.data.get("values"):
        selected_fid = interaction.data["values"][0]
        await interaction.response.send_message(
            f"✅ تم اختيار اللاعب: `{selected_fid}`",
            ephemeral=True
        )

