"""
WOS-M Gift Codes Views
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
from views.base import BaseView, PageInfo
from views.buttons import ActionButton
from modules.gift_codes.panel import GiftCodesPanelView, BatchRedeemView
from modules.gift_codes.service import gift_code_service
from modules.gift_codes.redemption_engine import redemption_engine
from modules.gift_codes.batch_runner import batch_runner


class GiftCodesView(BaseView):
    """Gift codes main view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("gift_codes.title"),
                description="",
                icon="🎁",
                color=0x2ecc71
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        """Add management buttons."""
        self.add_item(ActionButton(
            label=i18n.get("gift_codes.add_code"),
            custom_id="gift_add",
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("gift_codes.redeem_title"),
            custom_id="gift_redeem_single",
            style=discord.ButtonStyle.primary,
            emoji="🎁",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("gift_codes.batch_redeem"),
            custom_id="gift_batch",
            style=discord.ButtonStyle.primary,
            emoji="📦",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("gift_codes.redeem_alliance"),
            custom_id="gift_redeem_alliance",
            style=discord.ButtonStyle.success,
            emoji="🏰",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("gift_codes.auto_redeem"),
            custom_id="gift_auto",
            style=discord.ButtonStyle.success,
            emoji="🤖",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("gift_codes.report"),
            custom_id="gift_report",
            style=discord.ButtonStyle.secondary,
            emoji="📋",
            row=2
        ))


class SingleRedeemModal(ui.Modal):
    """Modal for single code redemption with FID."""
    
    def __init__(self):
        super().__init__(
            title=i18n.get("gift_codes.manual_redeem"),
            custom_id="single_redeem_modal"
        )
        
        self.code_input = ui.TextInput(
            label=i18n.get("gift_codes.code"),
            placeholder="WOSM123456",
            required=True,
            max_length=50
        )
        
        self.fid_input = ui.TextInput(
            label=i18n.get("players.fid"),
            placeholder="12345678",
            required=True,
            max_length=50
        )
        
        self.add_item(self.code_input)
        self.add_item(self.fid_input)


class AllianceRedeemModal(ui.Modal):
    """Modal for alliance code redemption."""
    
    def __init__(self):
        super().__init__(
            title=i18n.get("gift_codes.redeem_alliance"),
            custom_id="alliance_redeem_modal"
        )
        
        self.code_input = ui.TextInput(
            label=i18n.get("gift_codes.code"),
            placeholder="WOSM123456",
            required=True,
            max_length=50
        )
        
        self.add_item(self.code_input)


async def gift_codes_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for gift codes."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.MEMBER):
        await interaction.response.send_message(
            i18n.get("messages.no_permission"),
            ephemeral=True
        )
        return
    
    view = GiftCodesView(bot, interaction.user.id)
    
    # Add stats to description
    stats = await gift_code_service.get_stats()
    description = f"**{i18n.get('gift_codes.status')}:**\n"
    description += f"- {i18n.get('gift_codes.status_pending')}: {stats.get('pending', 0)}\n"
    description += f"- {i18n.get('gift_codes.status_valid')}: {stats.get('valid', 0)}\n"
    description += f"- {i18n.get('gift_codes.status_redeemed')}: {stats.get('redeemed', 0)}\n"
    description += f"- {i18n.get('gift_codes.status_failed')}: {stats.get('failed', 0)}"
    
    embed = view.create_embed(description=description)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    await audit_log.log(
        user_id=str(interaction.user.id),
        user_name=str(interaction.user),
        action="view_gift_codes",
        category=AuditCategory.GIFT_CODES
    )


async def add_gift_code_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for adding a gift code."""
    modal = ui.Modal(title=i18n.get("gift_codes.add_code"))
    
    code_input = ui.TextInput(
        label=i18n.get("gift_codes.code"),
        placeholder="WOSM123456",
        required=True,
        max_length=50
    )
    modal.add_item(code_input)
    
    await interaction.response.send_modal(modal)
    await modal.wait()
    
    code = code_input.value.strip().upper()
    
    if not code:
        await interaction.followup.send(
            i18n.get("messages.required_field"),
            ephemeral=True
        )
        return
    
    try:
        code_id = await gift_code_service.add_code(
            code=code,
            added_by=str(interaction.user.id)
        )
        
        await interaction.followup.send(
            f"✅ {i18n.get('messages.success')}\n{i18n.get('gift_codes.code')}: `{code}`",
            ephemeral=True
        )
        
        await audit_log.log(
            user_id=str(interaction.user.id),
            user_name=str(interaction.user),
            action="add_gift_code",
            category=AuditCategory.GIFT_CODES,
            details={"code": code, "code_id": code_id}
        )
        
    except Exception as e:
        await interaction.followup.send(
            f"❌ {i18n.get('messages.error')}: {str(e)}",
            ephemeral=True
        )


async def redeem_single_code_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for single code redemption with FID."""
    modal = SingleRedeemModal()
    await interaction.response.send_modal(modal)
    await modal.wait()
    
    code = modal.code_input.value.strip().upper()
    fid = modal.fid_input.value.strip()
    
    if not code or not fid:
        await interaction.followup.send(
            i18n.get("messages.required_field"),
            ephemeral=True
        )
        return
    
    # Show processing message
    await interaction.followup.send(
        f"⏳ {i18n.get('messages.processing')}\n{i18n.get('gift_codes.code')}: `{code}`\n{i18n.get('players.fid')}: `{fid}`",
        ephemeral=True
    )
    
    # Find or get player
    player_row = await db.fetchone("SELECT id FROM players WHERE fid = ?", (fid,))
    
    if not player_row:
        await interaction.followup.send(
            f"❌ Player with FID `{fid}` not found in database",
            ephemeral=True
        )
        return
    
    player_id = player_row["id"]
    
    # Redeem the code
    result = await redemption_engine.redeem_code(code, player_id, fid)
    
    if result.get("success"):
        rewards = result.get("rewards", [])
        reward_text = "\n".join([f"🎁 {r}" for r in rewards]) if rewards else "🎉"
        
        embed = discord.Embed(
            title=f"✅ {i18n.get('gift_codes.status_redeemed')}",
            description=f"{i18n.get('gift_codes.code')}: `{code}`\n{i18n.get('players.fid')}: `{fid}`",
            color=0x2ecc71
        )
        embed.add_field(name=i18n.get("gift_codes.redeem_title"), value=reward_text)
        embed.set_footer(text=i18n.get("bot.footer"))
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        await audit_log.log(
            user_id=str(interaction.user.id),
            user_name=str(interaction.user),
            action="redeem_code_single",
            category=AuditCategory.GIFT_CODES,
            details={"code": code, "fid": fid, "success": True}
        )
    else:
        error = result.get("error", "unknown")
        message = result.get("message", i18n.get("messages.error"))
        
        embed = discord.Embed(
            title=f"❌ {i18n.get('messages.error')}",
            description=f"**{i18n.get('gift_codes.code')}:** `{code}`\n**{i18n.get('players.fid')}:** `{fid}`\n**Error:** {error}",
            color=0xe74c3c
        )
        embed.set_footer(text=i18n.get("bot.footer"))
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        await audit_log.log(
            user_id=str(interaction.user.id),
            user_name=str(interaction.user),
            action="redeem_code_failed",
            category=AuditCategory.GIFT_CODES,
            details={"code": code, "fid": fid, "error": error}
        )


async def redeem_alliance_code_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for alliance batch redemption."""
    # Get alliances
    rows = await db.fetchall("SELECT id, name FROM alliances WHERE is_active = 1")
    
    if not rows:
        await interaction.response.send_message(
            i18n.get("messages.no_results"),
            ephemeral=True
        )
        return
    
    # Show selection view
    view = discord.ui.View()
    
    for alliance in rows:
        button = discord.ui.Button(
            label=alliance["name"],
            custom_id=f"alliance_redeem_{alliance['id']}",
            style=discord.ButtonStyle.primary,
            emoji="🏰"
        )
        view.add_item(button)
    
    embed = discord.Embed(
        title=f"🏰 {i18n.get('gift_codes.redeem_alliance')}",
        description=i18n.get("messages.select_option"),
        color=0x3498db
    )
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def batch_redeem_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for batch redemption."""
    view = BatchRedeemView(bot, interaction.user.id)
    embed = view.create_embed(
        description="📦 " + i18n.get("gift_codes.batch_redeem")
    )
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def auto_redeem_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for auto redeem settings."""
    # Show auto redeem settings
    enabled_alliances = []
    for alliance_id, enabled in redemption_engine._auto_redeem_enabled.items():
        if enabled:
            row = await db.fetchone("SELECT name FROM alliances WHERE id = ?", (alliance_id,))
            if row:
                enabled_alliances.append(row["name"])
    
    embed = discord.Embed(
        title=f"🤖 {i18n.get('gift_codes.auto_redeem')}",
        description=i18n.get("messages.select_option"),
        color=0x2ecc71
    )
    
    if enabled_alliances:
        embed.add_field(
            name=i18n.get("buttons.enable"),
            value="\n".join([f"✅ {a}" for a in enabled_alliances]),
            inline=False
        )
    else:
        embed.add_field(
            name=i18n.get("maintenance.title"),
            value=i18n.get("messages.no_results"),
            inline=False
        )
    
    # Add toggle buttons
    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label=i18n.get("buttons.enable"),
        custom_id="auto_enable_alliance",
        style=discord.ButtonStyle.success,
        emoji="✅"
    ))
    view.add_item(discord.ui.Button(
        label=i18n.get("buttons.disable"),
        custom_id="auto_disable_alliance",
        style=discord.ButtonStyle.danger,
        emoji="❌"
    ))
    view.add_item(discord.ui.Button(
        label=i18n.get("gift_codes.redeem_all"),
        custom_id="auto_redeem_all",
        style=discord.ButtonStyle.primary,
        emoji="🌐"
    ))
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def gift_report_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for gift codes report."""
    stats = await gift_code_service.get_stats()
    
    embed = discord.Embed(
        title=f"📋 {i18n.get('gift_codes.report')}",
        color=0x3498db
    )
    
    embed.add_field(
        name=i18n.get("gift_codes.title"),
        value=f"**{i18n.get('gift_codes.status_pending')}:** {stats.get('pending', 0)}\n"
              f"**{i18n.get('gift_codes.status_valid')}:** {stats.get('valid', 0)}\n"
              f"**{i18n.get('gift_codes.status_redeemed')}:** {stats.get('redeemed', 0)}\n"
              f"**{i18n.get('gift_codes.status_failed')}:** {stats.get('failed', 0)}",
        inline=True
    )
    
    embed.set_footer(text=i18n.get("bot.footer"))
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def enable_auto_redeem_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Enable auto redeem for an alliance - shows alliance selection."""
    rows = await db.fetchall("SELECT id, name FROM alliances WHERE is_active = 1")
    
    if not rows:
        await interaction.response.send_message(
            i18n.get("messages.no_results"),
            ephemeral=True
        )
        return
    
    # Create alliance selection
    view = discord.ui.View()
    select = discord.ui.Select(
        placeholder=i18n.get("messages.select_option"),
        custom_id="alliance_select_enable"
    )
    
    for alliance in rows:
        select.add_option(
            label=alliance["name"],
            value=str(alliance["id"])
        )
    
    view.add_item(select)
    
    embed = discord.Embed(
        title=f"✅ {i18n.get('gift_codes.auto_redeem')}",
        description=i18n.get("messages.select_option"),
        color=0x2ecc71
    )
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def disable_auto_redeem_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Disable auto redeem for an alliance - shows alliance selection."""
    rows = await db.fetchall("SELECT id, name FROM alliances WHERE is_active = 1")
    
    if not rows:
        await interaction.response.send_message(
            i18n.get("messages.no_results"),
            ephemeral=True
        )
        return
    
    view = discord.ui.View()
    select = discord.ui.Select(
        placeholder=i18n.get("messages.select_option"),
        custom_id="alliance_select_disable"
    )
    
    for alliance in rows:
        select.add_option(
            label=alliance["name"],
            value=str(alliance["id"])
        )
    
    view.add_item(select)
    
    embed = discord.Embed(
        title=f"❌ {i18n.get('gift_codes.auto_redeem')}",
        description=i18n.get("messages.select_option"),
        color=0xe74c3c
    )
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def redeem_all_alliances_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Redeem a code for all alliances with auto redeem enabled."""
    modal = discord.ui.Modal(title=i18n.get("gift_codes.redeem_all"))
    
    code_input = discord.ui.TextInput(
        label=i18n.get("gift_codes.code"),
        placeholder="WOSM123456",
        required=True,
        max_length=50
    )
    modal.add_item(code_input)
    
    await interaction.response.send_modal(modal)
    await modal.wait()
    
    code = code_input.value.strip().upper()
    
    if not code:
        await interaction.followup.send(
            i18n.get("messages.required_field"),
            ephemeral=True
        )
        return
    
    # Get alliances with auto redeem enabled
    rows = await db.fetchall(
        "SELECT id, name FROM alliances WHERE is_active = 1 AND auto_gift_enabled = 1"
    )
    
    if not rows:
        await interaction.followup.send(
            i18n.get("messages.no_results"),
            ephemeral=True
        )
        return
    
    await interaction.followup.send(
        f"⏳ {i18n.get('messages.processing')}\n{i18n.get('gift_codes.code')}: `{code}`\n{i18n.get('gift_codes.redeem_all')}: {len(rows)}",
        ephemeral=True
    )
    
    total_success = 0
    total_failed = 0
    
    for alliance in rows:
        result = await redemption_engine.batch_redeem(code, alliance["id"])
        total_success += result.get("success", 0)
        total_failed += result.get("failure", 0)
    
    embed = discord.Embed(
        title=f"🌐 {i18n.get('gift_codes.redeem_all')}",
        description=f"**{i18n.get('gift_codes.code')}:** `{code}`",
        color=0x3498db
    )
    embed.add_field(
        name=i18n.get("gift_codes.report"),
        value=f"**{i18n.get('gift_codes.status_redeemed')}:** {total_success}\n**{i18n.get('gift_codes.status_failed')}:** {total_failed}",
        inline=True
    )
    embed.set_footer(text=i18n.get("bot.footer"))
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    
    await audit_log.log(
        user_id=str(interaction.user.id),
        user_name=str(interaction.user),
        action="redeem_all_alliances",
        category=AuditCategory.GIFT_CODES,
        details={"code": code, "success": total_success, "failed": total_failed}
    )
