"""
WOS-M Gift Codes Module Views
© MANSOUR — WOS-M. All rights reserved.
"""
import asyncio
import discord
from discord import ui, ButtonStyle
from typing import Optional, List

from core.bot import WOSMBot
from core.i18n import i18n
from core.database import db
from core.permissions import PermissionLevel, PermissionGuard
from core.audit_log import audit_log, AuditCategory
from core.interaction_registry import INTERACTION_REGISTRY
from views.base import BaseView, PageInfo
from views.buttons import DashboardButton, ActionButton


async def gift_codes_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Main gift codes callback - shows gift codes dashboard."""
    from config.settings import settings

    embed = discord.Embed(
        title="🎁 إدارة أكواد الهدايا",
        description="اختر الإجراء المطلوب:",
        color=settings.theme_color_primary
    )
    embed.add_field(name="➕ إضافة كود", value="إضافة كود هدية جديد", inline=False)
    embed.add_field(name="🎫 استرداد فردي", value="استرداد كود لعضو واحد", inline=False)
    embed.add_field(name="📦 استرداد جماعي", value="استرداد أكواد متعددة", inline=False)
    embed.add_field(name="🏰 استرداد للأونلاين", value="استرداد أكواد للأونلاين", inline=False)
    embed.add_field(name="⚙️ تلقائي", value="إدارة الاسترداد التلقائي", inline=False)
    embed.add_field(name="📊 التقرير", value="عرض تقرير الأكواد", inline=False)

    view = BaseView(user_id=interaction.user.id, timeout=300)
    
    view.add_item(DashboardButton(
        style=ButtonStyle.primary,
        label="➕ إضافة كود",
        custom_id="gift_dash_add",
        emoji="➕",
        row=0
    ))
    view.add_item(DashboardButton(
        style=ButtonStyle.primary,
        label="🎫 استرداد فردي",
        custom_id="gift_dash_single",
        emoji="🎫",
        row=0
    ))
    view.add_item(DashboardButton(
        style=ButtonStyle.primary,
        label="📦 استرداد جماعي",
        custom_id="gift_dash_batch",
        emoji="📦",
        row=0
    ))
    view.add_item(DashboardButton(
        style=ButtonStyle.secondary,
        label="🏰 للأونلاين",
        custom_id="gift_dash_alliance",
        emoji="🏰",
        row=1
    ))
    view.add_item(DashboardButton(
        style=ButtonStyle.secondary,
        label="⚙️ تلقائي",
        custom_id="gift_dash_auto",
        emoji="⚙️",
        row=1
    ))
    view.add_item(DashboardButton(
        style=ButtonStyle.secondary,
        label="📊 التقرير",
        custom_id="gift_dash_report",
        emoji="📊",
        row=1
    ))
    view.add_back_home_buttons()

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def add_gift_code_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Add gift code callback - Open modal to add a new gift code."""
    guard = PermissionGuard(bot)

    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return

    class AddCodeModal(ui.Modal, title="إضافة كود هدية"):
        code_input = ui.TextInput(
            label="الكود",
            placeholder="مثال: WOSM123456",
            required=True,
            min_length=3,
            max_length=50
        )
        type_input = ui.TextInput(
            label="النوع",
            placeholder="vip, resources, speedup, etc.",
            required=True
        )
        value_input = ui.TextInput(
            label="القيمة",
            placeholder="مثال: 100 أو premium_7d",
            required=False
        )

        async def callback(self, modal_interaction: discord.Interaction):
            code = self.code_input.value.strip().upper()
            code_type = self.type_input.value.strip()
            value = self.value_input.value.strip() if self.value_input.value else None

            if not code:
                await modal_interaction.response.send_message("❌ الكود مطلوب", ephemeral=True)
                return

            from datetime import datetime
            now = datetime.now().isoformat()
            
            await db.execute("""
                INSERT OR REPLACE INTO gift_codes 
                (code, code_type, value, status, created_at)
                VALUES (?, ?, ?, 'active', ?)
            """, (code, code_type, value, now))
            await db.commit()

            await audit_log.log(
                modal_interaction.user.id,
                AuditCategory.GIFT_CODE,
                f"Added gift code: {code}",
                modal_interaction.guild_id
            )

            await modal_interaction.response.send_message(
                f"✅ تم إضافة الكود: `{code}`",
                ephemeral=True
            )

    await interaction.response.send_modal(AddCodeModal())


async def single_redeem_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Single code redemption callback."""
    guard = PermissionGuard(bot)

    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return

    class RedeemModal(ui.Modal, title="استرداد كود فردي"):
        code_input = ui.TextInput(
            label="الكود",
            placeholder="أدخل كود الهدية",
            required=True,
            min_length=3,
            max_length=50
        )
        player_id_input = ui.TextInput(
            label="معرف اللاعب",
            placeholder="أدخل معرف اللاعب",
            required=True
        )

        async def callback(self, modal_interaction: discord.Interaction):
            code = self.code_input.value.strip().upper()
            player_id = self.player_id_input.value.strip()

            if not code or not player_id:
                await modal_interaction.response.send_message(
                    "❌ الكود ومعرف اللاعب مطلوبان",
                    ephemeral=True
                )
                return

            from integrations.gift_codes import GiftCodeService
            service = GiftCodeService(bot, db.conn)
            
            await modal_interaction.response.send_message(
                f"⏳ جاري استرداد الكود `{code}` للاعب `{player_id}`...",
                ephemeral=True
            )

            success, msg = await service.redeem_code(code, player_id)

            if success:
                embed = discord.Embed(
                    title="✅ تم الاسترداد بنجاح!",
                    description=f"**الكود:** `{code}`\n**اللاعب:** `{player_id}`",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="❌ فشل الاسترداد",
                    description=f"**الكود:** `{code}`\n**السبب:** {msg}",
                    color=0xff0000
                )

            await modal_interaction.edit_original_response(embed=embed)

    await interaction.response.send_modal(RedeemModal())


async def batch_redeem_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Batch code redemption callback."""
    guard = PermissionGuard(bot)

    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return

    class BatchModal(ui.Modal, title="استرداد جماعي"):
        codes_input = ui.TextInput(
            label="الأكواد",
            placeholder="أدخل الأكواد مفصولة بسطر جديد",
            style=discord.TextStyle.paragraph,
            required=True
        )
        player_ids_input = ui.TextInput(
            label="معرفات اللاعبين",
            placeholder="أدخل معرفات اللاعبين مفصولة بسطر جديد",
            style=discord.TextStyle.paragraph,
            required=True
        )

        async def callback(self, modal_interaction: discord.Interaction):
            codes = [c.strip().upper() for c in self.codes_input.value.split('\n') if c.strip()]
            player_ids = [p.strip() for p in self.player_ids_input.value.split('\n') if p.strip()]

            if not codes or not player_ids:
                await modal_interaction.response.send_message(
                    "❌ الأكواد ومعرفات اللاعبين مطلوبة",
                    ephemeral=True
                )
                return

            await modal_interaction.response.send_message(
                f"⏳ جاري استرداد {len(codes)} كود لـ {len(player_ids)} لاعب...",
                ephemeral=True
            )

            from integrations.gift_codes import GiftCodeService
            service = GiftCodeService(bot, db.conn)

            results = {"success": 0, "failed": 0, "skipped": 0}
            
            for code in codes:
                result = await service.batch_redeem(code, player_ids)
                results["success"] += result.get("success", 0)
                results["failed"] += result.get("failed", 0)
                results["skipped"] += result.get("skipped", 0)

            embed = discord.Embed(
                title="📊 تقرير الاسترداد الجماعي",
                description=f"**النجاح:** {results['success']}\n"
                           f"**الفشل:** {results['failed']}\n"
                           f"**المتروك:** {results['skipped']}",
                color=0x3498db
            )

            await modal_interaction.edit_original_response(embed=embed)

    await interaction.response.send_modal(BatchModal())


async def report_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Show gift codes report."""
    from integrations.gift_codes import GiftCodeService
    service = GiftCodeService(bot, db.conn)
    
    stats = service.get_stats()
    codes = service.get_codes(limit=10)
    
    embed = discord.Embed(
        title="📊 تقرير أكواد الهدايا",
        description="إحصائيات نظام أكواد الهدايا",
        color=0x3498db
    )
    
    embed.add_field(
        name="📈 الإحصائيات",
        value=f"**الإجمالي:** {stats['total_codes']}\n"
              f"**النشط:** {stats['active_codes']}\n"
              f"**المسترد:** {stats['redeemed_codes']}\n"
              f"**الصالح:** {stats['validated_codes']}\n"
              f"**الملغي:** {stats['invalid_codes']}",
        inline=True
    )
    
    embed.add_field(
        name="🔧 الحالة",
        value=f"**محلل الكابتشا:** {'✅ جاهز' if stats['captcha_solver_ready'] else '❌ غير جاهز'}\n"
              f"**الاسترداد التلقائي:** {'✅ مفعّل' if stats['auto_redeem_enabled'] else '❌ معطّل'}",
        inline=True
    )
    
    if codes:
        codes_text = "\n".join([f"`{c['code']}` - {c['status']}" for c in codes[:5]])
        embed.add_field(name="🔔 آخر الأكواد", value=codes_text, inline=False)
    
    view = BaseView(user_id=interaction.user.id)
    view.add_back_home_buttons()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def auto_redeem_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Auto redemption settings callback."""
    guard = PermissionGuard(bot)

    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return

    from integrations.gift_codes import GiftCodeService
    service = GiftCodeService(bot, db.conn)
    
    current = service.settings.get('auto_redeem_enabled', False)
    service.save_setting('auto_redeem_enabled', not current)
    
    new_state = not current
    status = "✅ مفعّل" if new_state else "❌ معطّل"
    
    embed = discord.Embed(
        title="⚙️ إعدادات الاسترداد التلقائي",
        description=f"الاسترداد التلقائي: {status}",
        color=0x00ff00 if new_state else 0xff0000
    )
    
    view = BaseView(user_id=interaction.user.id)
    view.add_back_home_buttons()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def alliance_redeem_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Alliance online players redemption callback."""
    guard = PermissionGuard(bot)

    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return

    from integrations.gift_codes import GiftCodeService
    service = GiftCodeService(bot, db.conn)
    
    online_players = await db.fetchall(
        "SELECT player_id, name FROM players WHERE status = 'online' LIMIT 50"
    )

    if not online_players:
        await interaction.response.send_message(
            "❌ لا يوجد لاعبون متصلون",
            ephemeral=True
        )
        return

    player_ids = [str(p['player_id']) for p in online_players]
    codes = service.get_codes(status='active', limit=5)
    
    if not codes:
        await interaction.response.send_message(
            "❌ لا توجد أكواد نشطة",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"⏳ جاري استرداد الأكواد لـ {len(online_players)} لاعب متصل...",
        ephemeral=True
    )
    
    results = {"success": 0, "failed": 0}
    for code_data in codes:
        code = code_data['code']
        result = await service.batch_redeem(code, player_ids)
        results["success"] += result.get("success", 0)
        results["failed"] += result.get("failed", 0)

    embed = discord.Embed(
        title="📊 تقرير الاسترداد للأونلاين",
        description=f"**النجاح:** {results['success']}\n"
                   f"**الفشل:** {results['failed']}",
        color=0x3498db
    )

    await interaction.edit_original_response(embed=embed)
