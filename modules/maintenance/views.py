"""
WOS-M Maintenance Module
© MANSOUR — WOS-M. All rights reserved.
"""
import discord
from discord import ui
from typing import Dict, Any, List, Optional
import asyncio

from core.bot import WOSMBot
from core.i18n import i18n
from core.database import db
from core.permissions import PermissionLevel, PermissionGuard
from core.audit_log import audit_log, AuditCategory
from views.base import BaseView, PageInfo
from views.buttons import ActionButton
from integrations.wos_api_client import wos_api_client
from integrations.gift_code_client import gift_code_client
from integrations.captcha_service import captcha_service
from integrations.ocr_service import ocr_service

class MaintenanceView(BaseView):
    """Maintenance tools view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("maintenance.title"),
                description="",
                icon="🔧",
                color=0x34495e
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        self.add_item(ActionButton(
            label=i18n.get("maintenance.health_check"),
            custom_id="maint_health",
            style=discord.ButtonStyle.success,
            emoji="💚",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("maintenance.database_check"),
            custom_id="maint_database",
            style=discord.ButtonStyle.primary,
            emoji="💾",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("maintenance.queue_check"),
            custom_id="maint_queue",
            style=discord.ButtonStyle.primary,
            emoji="📬",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("maintenance.api_check"),
            custom_id="maint_api",
            style=discord.ButtonStyle.primary,
            emoji="🌐",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("maintenance.backup"),
            custom_id="maint_backup",
            style=discord.ButtonStyle.secondary,
            emoji="💾",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("maintenance.error_logs"),
            custom_id="maint_logs",
            style=discord.ButtonStyle.secondary,
            emoji="❌",
            row=1
        ))

class PermissionsView(BaseView):
    """Permissions management view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("permissions.title"),
                description="",
                icon="🔐",
                color=0xf39c12
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        self.add_item(ActionButton(
            label=i18n.get("permissions.assign_role"),
            custom_id="perm_assign",
            style=discord.ButtonStyle.success,
            emoji="👤",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("permissions.remove_role"),
            custom_id="perm_remove",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("permissions.role_list"),
            custom_id="perm_list",
            style=discord.ButtonStyle.primary,
            emoji="📋",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("permissions.audit_log"),
            custom_id="perm_audit",
            style=discord.ButtonStyle.secondary,
            emoji="📜",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("permissions.transfer_ownership"),
            custom_id="perm_transfer",
            style=discord.ButtonStyle.danger,
            emoji="👑",
            row=1
        ))

class SettingsView(BaseView):
    """Settings management view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("settings.title"),
                description="",
                icon="⚙️",
                color=0x3498db
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        self.add_item(ActionButton(
            label=i18n.get("settings.general"),
            custom_id="settings_general",
            style=discord.ButtonStyle.primary,
            emoji="⚙️",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("settings.api"),
            custom_id="settings_api",
            style=discord.ButtonStyle.primary,
            emoji="🌐",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("settings.save_settings"),
            custom_id="settings_save",
            style=discord.ButtonStyle.success,
            emoji="💾",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("settings.reset_settings"),
            custom_id="settings_reset",
            style=discord.ButtonStyle.danger,
            emoji="🔄",
            row=1
        ))

async def maintenance_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for maintenance."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    view = MaintenanceView(bot, interaction.user.id)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    await audit_log.log(
        user_id=str(interaction.user.id),
        user_name=str(interaction.user),
        action="view_maintenance",
        category=AuditCategory.MAINTENANCE
    )

async def health_check_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for health check."""
    await interaction.response.send_message("⏳ " + i18n.get("messages.loading"), ephemeral=True)
    
    results = {}
    
    # Database check
    try:
        await db.fetchone("SELECT 1")
        results["database"] = "✅ OK"
    except:
        results["database"] = "❌ Failed"
    
    # API check
    results["wos_api"] = "✅ OK" if await wos_api_client.health_check() else "⚠️ Not configured"
    results["gift_api"] = "✅ OK" if await gift_code_client.health_check() else "⚠️ Not configured"
    results["captcha"] = "✅ OK" if await captcha_service.health_check() else "⚠️ Not configured"
    results["ocr"] = "✅ OK" if await ocr_service.health_check() else "⚠️ Not configured"
    
    embed = discord.Embed(
        title=f"💚 {i18n.get('maintenance.health_check')}",
        color=0x2ecc71
    )
    
    for check, status in results.items():
        embed.add_field(name=check.upper(), value=status, inline=True)
    
    await interaction.edit_original_response(embed=embed)

async def permissions_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for permissions."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.ALLIANCE_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    view = PermissionsView(bot, interaction.user.id)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def settings_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for settings."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.MEMBER):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    view = SettingsView(bot, interaction.user.id)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def maint_health_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for maint_health - Run comprehensive health check."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    await interaction.response.send_message("💚 جاري فحص صحة النظام...", ephemeral=True)
    
    try:
        results = {}
        
        # Database check
        try:
            await db.fetchone("SELECT 1")
            results["database"] = "✅ متصل"
        except Exception as e:
            results["database"] = f"❌ خطأ: {str(e)[:50]}"
        
        # Bot status
        bot_uptime = getattr(bot, 'uptime', 'غير متاح')
        results["bot_status"] = f"✅ متصل | وقت التشغيل: {bot_uptime}"
        
        # API checks
        try:
            wos_status = await wos_api_client.health_check()
            results["wos_api"] = "✅ متصل" if wos_status else "⚠️ غير مكون"
        except:
            results["wos_api"] = "❌ غير متصل"
        
        try:
            gift_status = await gift_code_client.health_check()
            results["gift_api"] = "✅ متصل" if gift_status else "⚠️ غير مكون"
        except:
            results["gift_api"] = "❌ غير متصل"
        
        try:
            captcha_status = await captcha_service.health_check()
            results["captcha"] = "✅ متصل" if captcha_status else "⚠️ غير مكون"
        except:
            results["captcha"] = "❌ غير متصل"
        
        try:
            ocr_status = await ocr_service.health_check()
            results["ocr"] = "✅ متصل" if ocr_status else "⚠️ غير مكون"
        except:
            results["ocr"] = "❌ غير متصل"
        
        # Memory check
        import psutil
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        results["memory"] = f"✅ {memory_percent:.1f}% مستخدم" if memory_percent < 90 else f"⚠️ {memory_percent:.1f}% مستخدم"
        
        embed = discord.Embed(
            title="💚 نتيجة فحص الصحة",
            color=0x2ecc71 if all("✅" in v for v in results.values()) else 0xf39c12
        )
        
        for check, status in results.items():
            embed.add_field(name=check.upper(), value=status, inline=False)
        
        embed.set_footer(text="WOS-M • System Health")
        
        await interaction.edit_original_response(embed=embed)
        
        await audit_log.log(
            user_id=str(interaction.user.id),
            user_name=str(interaction.user),
            action="health_check",
            category=AuditCategory.MAINTENANCE,
            details={"results": results}
        )
        
    except ImportError:
        # psutil not available
        embed = discord.Embed(
            title="💚 نتيجة فحص الصحة",
            description="فحص ذاكرة النظام غير متاح (psutil غير موجود)",
            color=0x2ecc71
        )
        
        for check, status in results.items():
            embed.add_field(name=check.upper(), value=status, inline=False)
        
        await interaction.edit_original_response(embed=embed)
    except Exception:
        import logging
        logging.exception("maint_health failed")
        await interaction.edit_original_response(
            content="❌ حدث خطأ أثناء فحص صحة النظام"
        )


async def maint_database_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for maint_database - Run database checks."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    await interaction.response.send_message("💾 جاري فحص قاعدة البيانات...", ephemeral=True)
    
    try:
        results = {}
        
        # Connection test
        try:
            result = await db.fetchone("SELECT 1 as test")
            results["connection"] = "✅ الاتصال ناجح"
        except Exception as e:
            results["connection"] = f"❌ خطأ: {str(e)[:50]}"
        
        # Table counts
        tables = ["players", "alliances", "gift_codes", "gift_redemptions", "audit_logs"]
        for table in tables:
            try:
                result = await db.fetchone(f"SELECT COUNT(*) as count FROM {table}")
                count = result["count"] if result and "count" in result.keys() else 0
                results[f"table_{table}"] = f"✅ {count:,} سجل"
            except:
                results[f"table_{table}"] = f"⚠️ غير موجود"
        
        # Database size
        try:
            result = await db.fetchone("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            if result:
                size_bytes = result["size"] if result and "size" in result.keys() else 0
                size_mb = size_bytes / (1024 * 1024)
                results["database_size"] = f"📊 {size_mb:.2f} MB"
        except:
            pass
        
        embed = discord.Embed(
            title="💾 نتيجة فحص قاعدة البيانات",
            color=0x3498db
        )
        
        for check, status in results.items():
            name = check.replace("table_", "").replace("_", " ")
            embed.add_field(name=name.upper(), value=status, inline=False)
        
        embed.set_footer(text="WOS-M • Database Maintenance")
        
        await interaction.edit_original_response(embed=embed)
        
        await audit_log.log(
            user_id=str(interaction.user.id),
            user_name=str(interaction.user),
            action="database_check",
            category=AuditCategory.MAINTENANCE
        )
        
    except Exception:
        import logging
        logging.exception("maint_database failed")
        await interaction.edit_original_response(
            content="❌ حدث خطأ أثناء فحص قاعدة البيانات"
        )


async def maint_logs_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for maint_logs - View error logs."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    await interaction.response.send_message("📋 جاري تحميل السجلات...", ephemeral=True)
    
    try:
        # Get recent audit logs
        logs = await audit_log.get_logs(limit=15)
        
        embed = discord.Embed(
            title="❌ سجلات الأخطاء الأخيرة",
            description="آخر 15 إجراء في النظام:",
            color=0xe74c3c
        )
        
        if not logs:
            embed.description = "لا توجد سجلات حديثة"
        else:
            for log in logs:
                timestamp = log["created_at"] if "created_at" in log.keys() else "—"
                action = log["action"][:50] if "action" in log.keys() else "غير معروف"
                user = log["user_name"][:30] if "user_name" in log.keys() else "—"
                category = log["category"] if "category" in log.keys() else "—"
                embed.add_field(
                    name=f"⏰ {timestamp}",
                    value=f"**إجراء:** `{action}`\n**مستخدم:** {user}\n**فئة:** {category}",
                    inline=False
                )
        
        embed.set_footer(text="WOS-M • System Logs")
        
        await interaction.edit_original_response(embed=embed)
        
        await audit_log.log(
            user_id=str(interaction.user.id),
            user_name=str(interaction.user),
            action="view_logs",
            category=AuditCategory.MAINTENANCE
        )
        
    except Exception:
        import logging
        logging.exception("maint_logs failed")
        await interaction.edit_original_response(
            content="❌ حدث خطأ أثناء تحميل السجلات"
        )


async def maint_backup_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for maint_backup - Create backup."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.OWNER):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    class BackupConfirmModal(ui.Modal, title="تأكيد النسخ الاحتياطي"):
        confirm_input = ui.TextInput(
            label="اكتب 'نسخ' لإنشاء نسخة احتياطية",
            placeholder="نسخ",
            required=True,
            min_length=3,
            max_length=10
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            if self.confirm_input.value.strip() != "نسخ":
                await interaction.response.send_message(
                    "❌ يجب كتابة 'نسخ' لإنشاء نسخة احتياطية",
                    ephemeral=True
                )
                return
            
            await interaction.response.send_message("⏳ جاري إنشاء النسخة الاحتياطية...", ephemeral=True)
            
            try:
                # Get database path
                db_path = getattr(db, 'db_path', 'wos_m.db')
                
                import os
                import shutil
                from datetime import datetime
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"backups/wos_m_backup_{timestamp}.db"
                
                # Create backup directory if not exists
                os.makedirs("backups", exist_ok=True)
                
                # Create backup
                shutil.copy2(db_path, backup_path)
                
                await interaction.edit_original_response(
                    content=f"✅ تم إنشاء النسخة الاحتياطية بنجاح!\n📁 المسار: `{backup_path}`"
                )
                
                await audit_log.log(
                    user_id=str(interaction.user.id),
                    user_name=str(interaction.user),
                    action="create_backup",
                    category=AuditCategory.MAINTENANCE,
                    details={"backup_path": backup_path}
                )
                
            except FileNotFoundError:
                await interaction.edit_original_response(
                    content="❌ لم يتم العثور على قاعدة البيانات"
                )
            except PermissionError:
                await interaction.edit_original_response(
                    content="❌ لا يوجد صلاحية للكتابة في مجلد backups"
                )
            except Exception:
                import logging
                logging.exception("backup failed")
                await interaction.edit_original_response(
                    content="❌ حدث خطأ أثناء إنشاء النسخة الاحتياطية"
                )
        
        async def on_error(self, interaction: discord.Interaction, error: Exception):
            import logging
            logging.exception("backup modal error")
            try:
                await interaction.response.send_message(
                    f"❌ خطأ: {str(error)[:100]}",
                    ephemeral=True
                )
            except:
                pass
    
    await interaction.response.send_modal(BackupConfirmModal())


async def maint_api_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for maint_api - Check API status."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    await interaction.response.send_message("🌐 جاري فحص حالة APIs...", ephemeral=True)
    
    try:
        results = {}
        
        # WOS API
        try:
            status = await wos_api_client.health_check()
            if status:
                results["wos_api"] = "✅ متصل"
            else:
                results["wos_api"] = "⚠️ غير مكون أو غير مفعل"
        except Exception as e:
            results["wos_api"] = f"❌ خطأ: {str(e)[:40]}"
        
        # Gift API
        try:
            status = await gift_code_client.health_check()
            if status:
                results["gift_api"] = "✅ متصل"
            else:
                results["gift_api"] = "⚠️ غير مكون أو غير مفعل"
        except Exception as e:
            results["gift_api"] = f"❌ خطأ: {str(e)[:40]}"
        
        # Captcha Service
        try:
            status = await captcha_service.health_check()
            if status:
                results["captcha"] = "✅ متصل"
            else:
                results["captcha"] = "⚠️ غير مكون أو غير مفعل"
        except Exception as e:
            results["captcha"] = f"❌ خطأ: {str(e)[:40]}"
        
        # OCR Service
        try:
            status = await ocr_service.health_check()
            if status:
                results["ocr"] = "✅ متصل"
            else:
                results["ocr"] = "⚠️ غير مكون أو غير مفعل"
        except Exception as e:
            results["ocr"] = f"❌ خطأ: {str(e)[:40]}"
        
        embed = discord.Embed(
            title="🌐 حالة APIs",
            color=0x9b59b6
        )
        
        for api, status in results.items():
            embed.add_field(name=api.upper(), value=status, inline=True)
        
        embed.set_footer(text="WOS-M • API Status")
        
        await interaction.edit_original_response(embed=embed)
        
        await audit_log.log(
            user_id=str(interaction.user.id),
            user_name=str(interaction.user),
            action="api_check",
            category=AuditCategory.MAINTENANCE,
            details={"results": results}
        )
        
    except Exception:
        import logging
        logging.exception("maint_api failed")
        await interaction.edit_original_response(
            content="❌ حدث خطأ أثناء فحص APIs"
        )


async def maint_queue_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for maint_queue - View process queue status."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    await interaction.response.send_message("📬 جاري تحميل حالة الطابور...", ephemeral=True)
    
    try:
        process_queue = bot.process_queue
        
        # Get queue status
        queue_size = await process_queue.get_queue_size()
        pending = queue_size["pending"] if "pending" in queue_size else 0
        processing = queue_size["processing"] if "processing" in queue_size else 0
        completed = queue_size["completed"] if "completed" in queue_size else 0
        failed = queue_size["failed"] if "failed" in queue_size else 0
        
        embed = discord.Embed(
            title="📬 حالة طابور العمليات",
            color=0x3498db
        )
        
        embed.add_field(name="⏳ بانتظار", value=str(pending), inline=True)
        embed.add_field(name="🔄 قيد المعالجة", value=str(processing), inline=True)
        embed.add_field(name="✅ مكتمل", value=str(completed), inline=True)
        embed.add_field(name="❌ فاشل", value=str(failed), inline=True)
        
        # Get recent items
        recent = await process_queue.get_recent_items(limit=5)
        if recent:
            recent_text = "\n".join([
                f"• `{item['id'] if 'id' in item else '—'}` - {item['status'] if 'status' in item else '—'}"
                for item in recent
            ])
            embed.add_field(name="📋 العناصر الأخيرة", value=recent_text, inline=False)
        
        embed.set_footer(text="WOS-M • Process Queue")
        
        await interaction.edit_original_response(embed=embed)
        
        await audit_log.log(
            user_id=str(interaction.user.id),
            user_name=str(interaction.user),
            action="queue_check",
            category=AuditCategory.MAINTENANCE
        )
        
    except ImportError:
        await interaction.edit_original_response(
            content="⚠️ طابور العمليات غير متاح في هذا الإصدار"
        )
    except Exception:
        import logging
        logging.exception("maint_queue failed")
        await interaction.edit_original_response(
            content="❌ حدث خطأ أثناء تحميل حالة الطابور"
        )
