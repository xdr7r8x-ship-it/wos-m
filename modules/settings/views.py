"""
WOS-M Settings Module
© MANSOUR — WOS-M. All rights reserved.
"""
from __future__ import annotations

import logging

import discord

from core.audit_log import AuditCategory, audit_log
from core.bot import WOSMBot
from core.database import db
from core.permissions import PermissionGuard, PermissionLevel

logger = logging.getLogger(__name__)

async def _require_owner(bot: WOSMBot, interaction: discord.Interaction) -> bool:
    guard = PermissionGuard(bot)
    allowed = await guard.has_permission(str(interaction.user.id), PermissionLevel.OWNER)
    if not allowed:
        await interaction.response.send_message("❌ ليس لديك صلاحية.", ephemeral=True)
    return allowed

def _row_value(row, name: str, default="—"):
    if row and name in row.keys():
        value = row[name]
        return default if value is None else value
    return default

def _key_lines(rows, limit: int = 15) -> str:
    output = []
    for row in list(rows or [])[:limit]:
        name = _row_value(row, "key", "")
        if name:
            output.append(f"• `{name}`")
    return "\n".join(output) if output else "لا توجد إعدادات مسجلة"

async def settings_general_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Display general bot settings."""
    if not await _require_owner(bot, interaction):
        return

    await interaction.response.send_message("⏳ جاري تحميل الإعدادات...", ephemeral=True)

    try:
        rows = await db.fetchall("SELECT key, value, updated_at FROM bot_settings ORDER BY key")
        language_row = await db.fetchone(
            "SELECT value FROM bot_settings WHERE key IN ('language', 'default_language') ORDER BY key LIMIT 1"
        )
        demo_row = await db.fetchone("SELECT value FROM bot_settings WHERE key = 'demo_mode'")
        footer_row = await db.fetchone(
            "SELECT value FROM bot_settings WHERE key IN ('footer_text', 'theme_footer') ORDER BY key LIMIT 1"
        )

        embed = discord.Embed(title="⚙️ الإعدادات العامة", color=0x3498db)
        embed.add_field(
            name="الحالة",
            value=(
                f"• اللغة: `{_row_value(language_row, 'value', 'ar')}`\n"
                f"• وضع التجربة: `{_row_value(demo_row, 'value', 'false')}`\n"
                f"• عدد المفاتيح: `{len(rows) if rows else 0}`\n"
                f"• Footer: `{_row_value(footer_row, 'value', 'WOS-M')}`"
            ),
            inline=False,
        )
        embed.add_field(name="مفاتيح الإعدادات", value=_key_lines(rows), inline=False)
        embed.set_footer(text="WOS-M • Settings")
        await interaction.edit_original_response(embed=embed, view=None)
    except Exception:
        logger.exception("settings_general_callback failed")
        await interaction.edit_original_response(
            content="❌ حدث خطأ أثناء تحميل الإعدادات.",
            embed=None,
            view=None,
        )

async def settings_api_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Display API configuration status."""
    if not await _require_owner(bot, interaction):
        return

    await interaction.response.send_message("⏳ جاري فحص حالة API...", ephemeral=True)

    try:
        rows = await db.fetchall(
            "SELECT key FROM bot_settings WHERE key LIKE 'api_%' OR key LIKE '%_api_%' ORDER BY key"
        )
        embed = discord.Embed(
            title="🔌 حالة API",
            description="يتم عرض أسماء المفاتيح فقط.",
            color=0x3498db,
        )
        embed.add_field(name="مفاتيح API المسجلة", value=_key_lines(rows, 20), inline=False)
        embed.set_footer(text="WOS-M • API Settings")
        await interaction.edit_original_response(embed=embed, view=None)
    except Exception:
        logger.exception("settings_api_callback failed")
        await interaction.edit_original_response(
            content="❌ حدث خطأ أثناء فحص إعدادات API.",
            embed=None,
            view=None,
        )

async def settings_save_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Save a setting through a Discord modal."""
    if not await _require_owner(bot, interaction):
        return

    class SettingsSaveModal(discord.ui.Modal, title="💾 حفظ إعداد"):
        key_input = discord.ui.TextInput(
            label="مفتاح الإعداد",
            required=True,
            min_length=2,
            max_length=100,
        )
        value_input = discord.ui.TextInput(
            label="القيمة",
            required=True,
            max_length=500,
        )

        async def on_submit(self, modal_interaction: discord.Interaction):
            name = str(self.key_input.value).strip()
            value = str(self.value_input.value).strip()

            if not name or not value:
                await modal_interaction.response.send_message("❌ مفتاح وقيمة مطلوبان.", ephemeral=True)
                return

            try:
                await db.execute(
                    "INSERT OR REPLACE INTO bot_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                    (name, value),
                )
                await db.commit()

                await audit_log.log(
                    user_id=str(modal_interaction.user.id),
                    user_name=str(modal_interaction.user),
                    action=f"settings_save:{name}",
                    category=AuditCategory.SETTINGS,
                    details={"key": name, "value_length": len(value)},
                )

                await modal_interaction.response.send_message(
                    f"✅ تم حفظ `{name}` بنجاح.",
                    ephemeral=True,
                )
            except Exception:
                logger.exception("settings_save failed")
                await modal_interaction.response.send_message(
                    "❌ حدث خطأ أثناء حفظ الإعداد.",
                    ephemeral=True,
                )

        async def on_error(self, modal_interaction: discord.Interaction, error: Exception):
            logger.exception("settings_save modal error", exc_info=error)
            if not modal_interaction.response.is_done():
                await modal_interaction.response.send_message(
                    "❌ حدث خطأ أثناء نموذج الحفظ.",
                    ephemeral=True,
                )

    await interaction.response.send_modal(SettingsSaveModal())

async def settings_reset_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Reset non-essential settings after confirmation."""
    if not await _require_owner(bot, interaction):
        return

    class SettingsResetModal(discord.ui.Modal, title="⚠️ تأكيد إعادة التعيين"):
        confirm_input = discord.ui.TextInput(
            label="اكتب تأكيد",
            placeholder="تأكيد",
            required=True,
            max_length=10,
        )

        async def on_submit(self, modal_interaction: discord.Interaction):
            if str(self.confirm_input.value).strip() != "تأكيد":
                await modal_interaction.response.send_message("❌ لم يتم التأكيد.", ephemeral=True)
                return

            try:
                rows = await db.fetchall("SELECT key FROM bot_settings")
                kept = {"owner_id", "language", "default_language"}
                removed = 0

                for row in rows or []:
                    name = _row_value(row, "key", "")
                    if name and name not in kept:
                        await db.execute("DELETE FROM bot_settings WHERE key = ?", (name,))
                        removed += 1

                await db.commit()

                await audit_log.log(
                    user_id=str(modal_interaction.user.id),
                    user_name=str(modal_interaction.user),
                    action="settings_reset",
                    category=AuditCategory.SETTINGS,
                    details={"removed_count": removed},
                )

                await modal_interaction.response.send_message(
                    f"✅ تم إعادة تعيين الإعدادات. المحذوف: `{removed}`.",
                    ephemeral=True,
                )
            except Exception:
                logger.exception("settings_reset failed")
                await modal_interaction.response.send_message(
                    "❌ حدث خطأ أثناء إعادة التعيين.",
                    ephemeral=True,
                )

        async def on_error(self, modal_interaction: discord.Interaction, error: Exception):
            logger.exception("settings_reset modal error", exc_info=error)
            if not modal_interaction.response.is_done():
                await modal_interaction.response.send_message(
                    "❌ حدث خطأ أثناء نموذج إعادة التعيين.",
                    ephemeral=True,
                )

    await interaction.response.send_modal(SettingsResetModal())
