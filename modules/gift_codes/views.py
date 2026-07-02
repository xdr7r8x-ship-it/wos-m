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
            required=True
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            try:
                code = self.code_input.value.strip().upper()
                code_type = self.type_input.value.strip()
                value = self.value_input.value.strip()
                
                # Check if code already exists
                existing = await gift_code_service.get_code_by_code(code)
                if existing:
                    await interaction.response.send_message(
                        f"❌ الكود `{code}` موجود مسبقاً",
                        ephemeral=True
                    )
                    return
                
                # Add the code
                from modules.gift_codes.models import GiftCodeStatus
                await gift_code_service.create_code(
                    code=code,
                    code_type=code_type,
                    value=value,
                    created_by=str(interaction.user.id)
                )
                
                await interaction.response.send_message(
                    f"✅ تم إضافة الكود `{code}` بنجاح",
                    ephemeral=True
                )
                
                await audit_log.log(
                    user_id=str(interaction.user.id),
                    user_name=str(interaction.user),
                    action=f"add_gift_code:{code}",
                    category=AuditCategory.GIFT_CODES,
                    details={"code": code, "type": code_type, "value": value}
                )
                
            except Exception:
                import logging
                logging.exception("add_gift_code failed")
                await interaction.response.send_message(
                    "❌ حدث خطأ أثناء إضافة الكود",
                    ephemeral=True
                )
        
        async def on_error(self, interaction: discord.Interaction, error: Exception):
            import logging
            logging.exception("add_gift_code modal error")
            try:
                await interaction.response.send_message(
                    f"❌ خطأ: {str(error)[:100]}",
                    ephemeral=True
                )
            except:
                pass
    
    await interaction.response.send_modal(AddCodeModal())


async def redeem_single_code_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Redeem single code callback - Open modal for single redemption."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.MEMBER):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    class RedeemSingleModal(ui.Modal, title="استرداد كود فردي"):
        code_input = ui.TextInput(
            label="الكود",
            placeholder="أدخل كود الهدية",
            required=True,
            min_length=3,
            max_length=50
        )
        fid_input = ui.TextInput(
            label="FID اللاعب",
            placeholder="معرف اللاعب",
            required=True,
            min_length=8,
            max_length=20
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            try:
                code = self.code_input.value.strip().upper()
                player_fid = self.fid_input.value.strip()
                
                # Get player by FID
                player = await db.fetchone(
                    "SELECT id, fid, name FROM players WHERE fid = ?",
                    (player_fid,)
                )
                
                if not player:
                    await interaction.response.send_message(
                        f"❌ لم يتم العثور على لاعب بهذا FID: `{player_fid}`",
                        ephemeral=True
                    )
                    return
                
                # Redeem the code
                result = await redemption_engine.redeem_code(
                    code=code,
                    player_id=player['id'],
                    player_fid=player_fid
                )
                
                if result.get("success"):
                    await interaction.response.send_message(
                        f"✅ تم استرداد الكود `{code}` بنجاح للاعب {player.get('name', player_fid)}!",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f"❌ فشل استرداد الكود: {result.get('message', 'خطأ غير معروف')}",
                        ephemeral=True
                    )
                
                await audit_log.log(
                    user_id=str(interaction.user.id),
                    user_name=str(interaction.user),
                    action=f"redeem_single:{code}",
                    category=AuditCategory.GIFT_CODES,
                    details={"code": code, "player_fid": player_fid, "success": result.get("success")}
                )
                
            except Exception:
                import logging
                logging.exception("redeem_single failed")
                await interaction.response.send_message(
                    "❌ حدث خطأ أثناء استرداد الكود",
                    ephemeral=True
                )
        
        async def on_error(self, interaction: discord.Interaction, error: Exception):
            import logging
            logging.exception("redeem_single modal error")
            try:
                await interaction.response.send_message(
                    f"❌ خطأ: {str(error)[:100]}",
                    ephemeral=True
                )
            except:
                pass
    
    await interaction.response.send_modal(RedeemSingleModal())


async def batch_redeem_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Batch redeem callback - Show batch redeem view."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    view = BatchRedeemView(bot, interaction.user.id)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    await audit_log.log(
        user_id=str(interaction.user.id),
        user_name=str(interaction.user),
        action="view_batch_redeem",
        category=AuditCategory.GIFT_CODES
    )


async def redeem_alliance_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Redeem alliance callback - Open modal for alliance redemption."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.ALLIANCE_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    class AllianceRedeemModal(ui.Modal, title="استرداد كود للتحالف"):
        alliance_id_input = ui.TextInput(
            label="معرف التحالف",
            placeholder="أدخل معرف التحالف",
            required=True,
            min_length=1,
            max_length=50
        )
        code_input = ui.TextInput(
            label="الكود",
            placeholder="أدخل كود الهدية",
            required=True,
            min_length=3,
            max_length=50
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            try:
                alliance_id = self.alliance_id_input.value.strip()
                code = self.code_input.value.strip().upper()
                
                # Get alliance
                alliance = await db.fetchone(
                    "SELECT * FROM alliances WHERE id = ?",
                    (alliance_id,)
                )
                
                if not alliance:
                    await interaction.response.send_message(
                        f"❌ التحالف `{alliance_id}` غير موجود",
                        ephemeral=True
                    )
                    return
                
                # Redeem via logic layer
                from modules.gift_codes.logic import redeem_gift_code
                success, msg = await redeem_gift_code(code, alliance_id)
                
                if success:
                    await interaction.response.send_message(
                        f"✅ {msg}",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f"❌ {msg}",
                        ephemeral=True
                    )
                
                await audit_log.log(
                    user_id=str(interaction.user.id),
                    user_name=str(interaction.user),
                    action=f"redeem_alliance:{code}",
                    category=AuditCategory.GIFT_CODES,
                    details={"code": code, "alliance_id": alliance_id, "success": success}
                )
                
            except Exception:
                import logging
                logging.exception("redeem_alliance failed")
                await interaction.response.send_message(
                    "❌ حدث خطأ أثناء استرداد الكود",
                    ephemeral=True
                )
        
        async def on_error(self, interaction: discord.Interaction, error: Exception):
            import logging
            logging.exception("redeem_alliance modal error")
            try:
                await interaction.response.send_message(
                    f"❌ خطأ: {str(error)[:100]}",
                    ephemeral=True
                )
            except:
                pass
    
    await interaction.response.send_modal(AllianceRedeemModal())


async def auto_redeem_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Auto redeem settings callback - Configure auto-redeem settings."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    await interaction.response.send_message("⏳ جاري تحميل الإعدادات...", ephemeral=True)
    
    try:
        # Get current auto-redeem settings
        settings = await db.fetchall("""
            SELECT key, value FROM bot_settings WHERE key LIKE 'auto_redeem_%'
        """)
        
        embed = discord.Embed(
            title="⚙️ إعدادات الاسترداد التلقائي",
            description="إعدادات الاسترداد التلقائي الحالية:",
            color=0x2ecc71
        )
        
        default_settings = {
            "auto_redeem_enabled": "مفعّل",
            "auto_redeem_delay": "تأخير (ثواني)",
            "auto_redeem_max_daily": "الحد الأقصى يومياً",
        }
        
        settings_dict = {s['key']: s['value'] for s in settings}
        
        for key, desc in default_settings.items():
            value = settings_dict.get(key, 'غير مفعّل' if 'enabled' in key else '0')
            embed.add_field(name=desc, value=f"`{value}`", inline=True)
        
        embed.add_field(
            name="📝",
            value="للتعديل، استخدم أوامر الإدارة",
            inline=False
        )
        
        await interaction.edit_original_response(embed=embed)
        
        await audit_log.log(
            user_id=str(interaction.user.id),
            user_name=str(interaction.user),
            action="view_auto_redeem_settings",
            category=AuditCategory.GIFT_CODES
        )
        
    except Exception:
        import logging
        logging.exception("auto_redeem failed")
        await interaction.edit_original_response(
            content="❌ حدث خطأ أثناء تحميل الإعدادات"
        )


async def gift_report_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Gift codes report callback - Show redemption statistics."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.MEMBER):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    await interaction.response.send_message("⏳ جاري تحميل التقرير...", ephemeral=True)
    
    try:
        # Get statistics
        total_codes = await db.fetchone("SELECT COUNT(*) as count FROM gift_codes")
        used_codes = await db.fetchone("SELECT COUNT(*) as count FROM gift_codes WHERE status = GiftCodeStatus.REDEEMED.value")
        pending_codes = await db.fetchone("SELECT COUNT(*) as count FROM gift_codes WHERE status = 'pending'")
        total_redemptions = await db.fetchone("SELECT COUNT(*) as count FROM gift_redemptions")
        
        embed = discord.Embed(
            title="📊 تقرير أكواد الهدايا",
            color=0x2ecc71
        )
        
        embed.add_field(
            name="📦 إجمالي الأكواد",
            value=str(total_codes['count'] if total_codes else 0),
            inline=True
        )
        embed.add_field(
            name="✅ الأكواد المستخدمة",
            value=str(used_codes['count'] if used_codes else 0),
            inline=True
        )
        embed.add_field(
            name="⏳ الأكواد المعلقة",
            value=str(pending_codes['count'] if pending_codes else 0),
            inline=True
        )
        embed.add_field(
            name="🎁 إجمالي الاستردادات",
            value=str(total_redemptions['count'] if total_redemptions else 0),
            inline=True
        )
        
        # Get recent redemptions
        recent = await db.fetchall("""
            SELECT gr.*, gc.code 
            FROM gift_redemptions gr
            JOIN gift_codes gc ON gr.code_id = gc.id
            ORDER BY gr.redeemed_at DESC
            LIMIT 5
        """)
        
        if recent:
            recent_list = [dict(r) for r in recent]
            recent_text = "\n".join([
                f"• `{r['code'][:15]}` - {r.get('redeemed_at', '—')[:10]}"
                for r in recent_list
            ])
            embed.add_field(name="🔄 آخر الاستردادات", value=recent_text, inline=False)
        
        embed.set_footer(text="WOS-M • Gift Codes Report")
        
        await interaction.edit_original_response(embed=embed)
        
        await audit_log.log(
            user_id=str(interaction.user.id),
            user_name=str(interaction.user),
            action="view_gift_report",
            category=AuditCategory.GIFT_CODES
        )
        
    except Exception:
        import logging
        logging.exception("gift_report failed")
        await interaction.edit_original_response(
            content="❌ حدث خطأ أثناء تحميل التقرير"
        )


async def single_redeem_modal_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for single_redeem_modal - Handle modal submission."""
    # This is handled by the modal's on_submit directly
    await interaction.response.send_message(
        "⏳ جاري معالجة طلبك...",
        ephemeral=True
    )
