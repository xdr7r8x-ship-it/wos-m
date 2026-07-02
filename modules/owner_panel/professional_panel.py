"""
WOS-M Professional Owner Panel
لوحة تحكم المالك الاحترافية
© MANSOUR — WOS-M. All rights reserved.
"""
import os
import asyncio
import discord
from discord import ui, ButtonStyle
from typing import Dict, Any, List, Optional

from core.bot import WOSMBot
from core.i18n import i18n
from core.database import db
from core.permissions import PermissionLevel, PermissionGuard
from core.audit_log import audit_log, AuditCategory
from core.settings_manager import SettingsManager, SettingCategory
from views.base import BaseView


# ═══════════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════════

def _check_owner(func):
    """Decorator للتحقق من صلاحية المالك"""
    async def wrapper(bot: WOSMBot, interaction: discord.Interaction, *args, **kwargs):
        guard = PermissionGuard(bot)
        if not await guard.is_owner(str(interaction.user.id)):
            await interaction.response.send_message(
                "❌ ليس لديك صلاحية الوصول لهذه اللوحة",
                ephemeral=True
            )
            return
        return await func(bot, interaction, *args, **kwargs)
    return wrapper


def _create_header(title: str, description: str, color: int = 0xe74c3c) -> discord.Embed:
    """إنشاء header احترافي"""
    embed = discord.Embed(
        title=f"👑 {title}",
        description=description,
        color=color
    )
    embed.set_author(
        name="WOS-M Owner Panel",
        icon_url="https://i.imgur.com/AfFp7pu.png"
    )
    embed.set_footer(text=f"WOS-M • {i18n.get('bot.footer', '© MANSOUR')}")
    return embed


def _create_stats_card(stats: Dict[str, Any], color: int = 0x3498db) -> discord.Embed:
    """إنشاء بطاقة إحصائيات"""
    embed = discord.Embed(color=color)
    
    for key, value in stats.items():
        embed.add_field(
            name=f"📊 {key}",
            value=f"```\n{value}\n```",
            inline=True
        )
    
    return embed


# ═══════════════════════════════════════════════════════════════════════════════════
# MAIN PANEL - لوحة التحكم الرئيسية
# ═══════════════════════════════════════════════════════════════════════════════════

@_check_owner
async def owner_main_callback(bot: WOSMBot, interaction: discord.Interaction):
    """اللوحة الرئيسية"""
    
    # Get system stats
    try:
        users = await db.fetchone("SELECT COUNT(*) as c FROM permissions")
        alliances = await db.fetchone("SELECT COUNT(*) as c FROM alliances")
        codes = await db.fetchone("SELECT COUNT(*) as c FROM gift_codes")
        admins = await db.fetchone("SELECT COUNT(*) as c FROM admins")
        
        stats = {
            "المستخدمين": f"{users['c'] if users else 0}",
            "التحالفات": f"{alliances['c'] if alliances else 0}",
            "الأكواد": f"{codes['c'] if codes else 0}",
            "المشرفين": f"{admins['c'] if admins else 0}",
        }
    except:
        stats = {"الحالة": "⚠️ غير متصل"}
    
    # System status
    import psutil, os
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / 1024 / 1024
    
    system_info = f"""
🖥️ الذاكرة: {mem:.1f} MB
⚡ CPU: {psutil.cpu_percent()}%
📦 البوت: {bot.user.name}
🔢 الأوامر: 0"""
    
    embed = _create_header(
        "لوحة تحكم المالك",
        "مرحباً بك في لوحة تحكم المالك الأعلى صلاحية"
    )
    
    embed.add_field(
        name="🖥️ حالة النظام",
        value=system_info,
        inline=True
    )
    
    embed.add_field(
        name="📊 الإحصائيات",
        value="```\n" + "\n".join([f"{k}: {v}" for k, v in stats.items()]) + "\n```",
        inline=True
    )
    
    embed.add_field(
        name="🎯 التنقل",
        value="استخدم الأزرار أدناه للتنقل بين الأقسام",
        inline=False
    )
    
    # Create main view
    view = OwnerMainView(bot, interaction.user.id)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class OwnerMainView(BaseView):
    """عرض اللوحة الرئيسية"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        self._build()
    
    def _build(self):
        # Row 0 - إدارة أساسية
        self.add_item(ui.Button(
            label="📊 الإحصائيات",
            custom_id="prof_stats",
            style=ButtonStyle.primary,
            row=0
        ))
        self.add_item(ui.Button(
            label="👥 المستخدمين",
            custom_id="prof_users",
            style=ButtonStyle.primary,
            row=0
        ))
        self.add_item(ui.Button(
            label="🏰 التحالفات",
            custom_id="prof_alliances",
            style=ButtonStyle.primary,
            row=0
        ))
        
        # Row 1 - الإعدادات
        self.add_item(ui.Button(
            label="🔐 الصلاحيات",
            custom_id="prof_permissions",
            style=ButtonStyle.secondary,
            row=1
        ))
        self.add_item(ui.Button(
            label="⚙️ الإعدادات",
            custom_id="prof_settings",
            style=ButtonStyle.secondary,
            row=1
        ))
        self.add_item(ui.Button(
            label="🎨 المظهر",
            custom_id="prof_appearance",
            style=ButtonStyle.secondary,
            row=1
        ))
        
        # Row 2 - الأدوات
        self.add_item(ui.Button(
            label="🎁 الهدايا",
            custom_id="prof_gifts",
            style=ButtonStyle.success,
            row=2
        ))
        self.add_item(ui.Button(
            label="🔧 الصيانة",
            custom_id="prof_maintenance",
            style=ButtonStyle.success,
            row=2
        ))
        self.add_item(ui.Button(
            label="📢 البث",
            custom_id="prof_broadcast",
            style=ButtonStyle.success,
            row=2
        ))
        
        # Row 3 - قاعدة البيانات
        self.add_item(ui.Button(
            label="🗄️ قاعدة البيانات",
            custom_id="prof_database",
            style=ButtonStyle.danger,
            row=3
        ))
        self.add_item(ui.Button(
            label="📜 السجلات",
            custom_id="prof_logs",
            style=ButtonStyle.danger,
            row=3
        ))
        self.add_item(ui.Button(
            label="🔄 تحديث",
            custom_id="prof_refresh",
            style=ButtonStyle.danger,
            row=3
        ))


# ═══════════════════════════════════════════════════════════════════════════════════
# STATISTICS - الإحصائيات
# ═══════════════════════════════════════════════════════════════════════════════════

@_check_owner
async def owner_stats_callback(bot: WOSMBot, interaction: discord.Interaction):
    """عرض الإحصائيات الشاملة"""
    
    import psutil, os
    
    # Database stats
    try:
        db_stats = {
            "المستخدمين": await db.fetchone("SELECT COUNT(*) as c FROM permissions"),
            "التحالفات": await db.fetchone("SELECT COUNT(*) as c FROM alliances"),
            "الأكواد": await db.fetchone("SELECT COUNT(*) as c FROM gift_codes"),
            "المستردات": await db.fetchone("SELECT COUNT(*) as c FROM gift_redemptions"),
            "المشرفين": await db.fetchone("SELECT COUNT(*) as c FROM admins"),
        }
        
        db_values = {}
        for key, val in db_stats.items():
            db_values[key] = str(val['c'] if val else 0)
    except Exception as e:
        db_values = {"خطأ": str(e)}
    
    # System stats
    process = psutil.Process(os.getpid())
    memory = process.memory_info()
    
    system_stats = f"""
🖥️ الذاكرة المستخدمة: {memory.rss / 1024 / 1024:.1f} MB
⚡ استخدام CPU: {psutil.cpu_percent()}%
💾 الذاكرة المتاحة: {psutil.virtual_memory().available / 1024 / 1024:.0f} MB
📂 مساحة القرص: {psutil.disk_usage('/').percent}%
🌡️ درجة الحرارة: {psutil.sensor_battery().percent if hasattr(psutil, 'sensor_battery') else 'N/A'}%"""
    
    embed = _create_header("📊 إحصائيات النظام الشاملة", "معلومات تفصيلية عن حالة النظام", 0x3498db)
    
    embed.add_field(
        name="🗄️ قاعدة البيانات",
        value="```\n" + "\n".join([f"{k}: {v}" for k, v in db_values.items()]) + "\n```",
        inline=True
    )
    
    embed.add_field(
        name="🖥️ النظام",
        value=system_stats,
        inline=True
    )
    
    embed.add_field(
        name="🤖 معلومات البوت",
        value=f"```\nالاسم: {bot.user.name}\nID: {bot.user.id}\nالأوامر: 0\nخوادم: {len(bot.guilds)}\n```",
        inline=False
    )
    
    view = OwnerMainView(bot, interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ═══════════════════════════════════════════════════════════════════════════════════
# USER MANAGEMENT - إدارة المستخدمين
# ═══════════════════════════════════════════════════════════════════════════════════

@_check_owner
async def owner_users_callback(bot: WOSMBot, interaction: discord.Interaction):
    """إدارة المستخدمين"""
    
    admins = await db.fetchall("""
        SELECT discord_id, discord_name, role, added_at 
        FROM admins 
        ORDER BY CASE role 
            WHEN 'owner' THEN 1 
            WHEN 'global_admin' THEN 2 
            WHEN 'server_admin' THEN 3 
            ELSE 4 
        END
    """)
    
    embed = _create_header(
        "👥 إدارة المستخدمين",
        f"إجمالي المشرفين: **{len(admins)}**",
        0x9b59b6
    )
    
    # Group by role
    owners = [a for a in admins if a.get('role') == 'owner']
    global_admins = [a for a in admins if a.get('role') == 'global_admin']
    server_admins = [a for a in admins if a.get('role') == 'server_admin']
    
    if owners:
        value = "\n".join([f"👑 <@{a.get('discord_id')}>" for a in owners])
        embed.add_field(name="👑 المالك", value=value, inline=False)
    
    if global_admins:
        value = "\n".join([f"🔰 <@{a.get('discord_id')}>" for a in global_admins[:10]])
        if len(global_admins) > 10:
            value += f"\n... و {len(global_admins) - 10} آخرين"
        embed.add_field(name="🔰 المشرفين العامين", value=value, inline=False)
    
    if server_admins:
        embed.add_field(
            name="⚔️ مشرفي السيرفر",
            value=f"عدد: {len(server_admins)}",
            inline=True
        )
    
    view = OwnerUsersView(bot, interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class OwnerUsersView(BaseView):
    """عرض إدارة المستخدمين"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(ui.Button(
            label="➕ إضافة مشرف",
            custom_id="prof_add_admin",
            style=ButtonStyle.success,
            emoji="➕",
            row=0
        ))
        self.add_item(ui.Button(
            label="➖ إزالة مشرف",
            custom_id="prof_remove_admin",
            style=ButtonStyle.danger,
            emoji="➖",
            row=0
        ))
        self.add_item(ui.Button(
            label="🔄 تحديث",
            custom_id="prof_users",
            style=ButtonStyle.secondary,
            emoji="🔄",
            row=1
        ))
        self.add_back_home_buttons()

    # ═══════════════════════════════════════════════════════════════════
    # CALLBACK METHODS - Required for button interactions
    # ═══════════════════════════════════════════════════════════════════
    
    @discord.ui.callback("prof_add_admin")
    async def prof_add_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_remove_admin")
    async def prof_remove_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_transfer_owner")
    async def prof_transfer_owner_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_promote")
    async def prof_promote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_demote")
    async def prof_demote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_perm_log")
    async def prof_perm_log_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_general")
    async def prof_set_general_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_features")
    async def prof_set_features_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_security")
    async def prof_set_security_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_notifications")
    async def prof_set_notifications_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_api")
    async def prof_set_api_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_color_theme")
    async def prof_color_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_text_theme")
    async def prof_text_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_icons")
    async def prof_icons_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_add")
    async def prof_gift_add_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_list")
    async def prof_gift_list_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_redeem")
    async def prof_gift_redeem_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_report")
    async def prof_gift_report_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_toggle_maintenance")
    async def prof_toggle_maintenance_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_backup")
    async def prof_backup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_cleanup")
    async def prof_cleanup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_check")
    async def prof_check_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_text")
    async def prof_broadcast_text_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_announce")
    async def prof_broadcast_announce_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_log")
    async def prof_broadcast_log_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_export")
    async def prof_db_export_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_import")
    async def prof_db_import_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_vacuum")
    async def prof_db_vacuum_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_integrity")
    async def prof_db_integrity_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_logs_clear")
    async def prof_logs_clear_callback(self, interaction: discord.Interaction):
        await owner_logs_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_list")
    async def prof_alliance_list_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_add")
    async def prof_alliance_add_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_delete")
    async def prof_alliance_delete_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)


# ═══════════════════════════════════════════════════════════════════════════════════
# PERMISSIONS - الصلاحيات
# ═══════════════════════════════════════════════════════════════════════════════════

@_check_owner
async def owner_permissions_callback(bot: WOSMBot, interaction: discord.Interaction):
    """إدارة الصلاحيات"""
    
    embed = _create_header(
        "🔐 إدارة الصلاحيات",
        "تحكم كامل في صلاحيات النظام",
        0xf39c12
    )
    
    embed.add_field(
        name="📋 مستويات الصلاحيات",
        value="""```
👑 OWNER - تحكم كامل
🔰 GLOBAL_ADMIN - إدارة عامة  
⚔️ SERVER_ADMIN - إدارة سيرفر
🏰 ALLIANCE_ADMIN - إدارة تحالف
👤 MEMBER - مستخدم عادي
```""",
        inline=False
    )
    
    embed.add_field(
        name="⚡ إجراءات سريعة",
        value="استخدم الأزرار أدناه",
        inline=False
    )
    
    view = OwnerPermissionsView(bot, interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class OwnerPermissionsView(BaseView):
    """عرض إدارة الصلاحيات"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(ui.Button(
            label="👑 نقل الملكية",
            custom_id="prof_transfer_owner",
            style=ButtonStyle.danger,
            emoji="👑",
            row=0
        ))
        self.add_item(ui.Button(
            label="🔰 ترقية",
            custom_id="prof_promote",
            style=ButtonStyle.success,
            emoji="🔰",
            row=0
        ))
        self.add_item(ui.Button(
            label="📉 تخفيض",
            custom_id="prof_demote",
            style=ButtonStyle.secondary,
            emoji="📉",
            row=1
        ))
        self.add_item(ui.Button(
            label="📜 سجل الصلاحيات",
            custom_id="prof_perm_log",
            style=ButtonStyle.primary,
            emoji="📜",
            row=1
        ))
        self.add_back_home_buttons()

    # ═══════════════════════════════════════════════════════════════════
    # CALLBACK METHODS - Required for button interactions
    # ═══════════════════════════════════════════════════════════════════
    
    @discord.ui.callback("prof_add_admin")
    async def prof_add_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_remove_admin")
    async def prof_remove_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_transfer_owner")
    async def prof_transfer_owner_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_promote")
    async def prof_promote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_demote")
    async def prof_demote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_perm_log")
    async def prof_perm_log_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_general")
    async def prof_set_general_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_features")
    async def prof_set_features_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_security")
    async def prof_set_security_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_notifications")
    async def prof_set_notifications_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_api")
    async def prof_set_api_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_color_theme")
    async def prof_color_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_text_theme")
    async def prof_text_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_icons")
    async def prof_icons_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_add")
    async def prof_gift_add_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_list")
    async def prof_gift_list_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_redeem")
    async def prof_gift_redeem_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_report")
    async def prof_gift_report_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_toggle_maintenance")
    async def prof_toggle_maintenance_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_backup")
    async def prof_backup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_cleanup")
    async def prof_cleanup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_check")
    async def prof_check_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_text")
    async def prof_broadcast_text_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_announce")
    async def prof_broadcast_announce_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_log")
    async def prof_broadcast_log_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_export")
    async def prof_db_export_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_import")
    async def prof_db_import_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_vacuum")
    async def prof_db_vacuum_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_integrity")
    async def prof_db_integrity_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_logs_clear")
    async def prof_logs_clear_callback(self, interaction: discord.Interaction):
        await owner_logs_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_list")
    async def prof_alliance_list_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_add")
    async def prof_alliance_add_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_delete")
    async def prof_alliance_delete_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)


# ═══════════════════════════════════════════════════════════════════════════════════
# SETTINGS - الإعدادات
# ═══════════════════════════════════════════════════════════════════════════════════

@_check_owner
async def owner_settings_callback(bot: WOSMBot, interaction: discord.Interaction):
    """إدارة الإعدادات"""
    
    from config.settings import settings
    
    # Load settings
    await SettingsManager.load_all()
    
    embed = _create_header(
        "⚙️ إدارة الإعدادات",
        "تكوين إعدادات النظام العامة",
        0x1abc9c
    )
    
    # Get current values
    general = SettingsManager.get_by_category(SettingCategory.GENERAL)
    features = SettingsManager.get_by_category(SettingCategory.FEATURES)
    security = SettingsManager.get_by_category(SettingCategory.SECURITY)
    
    general_text = "\n".join([
        f"• {s.name_ar}: {await SettingsManager.get(s.key, s.default)}"
        for k, s in list(general.items())[:5]
    ])
    
    embed.add_field(
        name="🔧 عام",
        value=f"```\n{general_text}\n```",
        inline=True
    )
    
    embed.add_field(
        name="✨ الميزات",
        value=f"```\nفعّل: {sum(1 for k, s in features.items() if SettingsManager._cache.get(k))}/{len(features)}\n```",
        inline=True
    )
    
    embed.add_field(
        name="🔐 الأمان",
        value=f"```\nتسجيل: {'تفعيل' if SettingsManager._cache.get('log_all_actions') else 'معطّل'}\n```",
        inline=True
    )
    
    view = OwnerSettingsView(bot, interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class OwnerSettingsView(BaseView):
    """عرض إدارة الإعدادات"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(ui.Button(
            label="🔧 عام",
            custom_id="prof_set_general",
            style=ButtonStyle.primary,
            emoji="🔧",
            row=0
        ))
        self.add_item(ui.Button(
            label="✨ الميزات",
            custom_id="prof_set_features",
            style=ButtonStyle.primary,
            emoji="✨",
            row=0
        ))
        self.add_item(ui.Button(
            label="🔐 الأمان",
            custom_id="prof_set_security",
            style=ButtonStyle.secondary,
            emoji="🔐",
            row=1
        ))
        self.add_item(ui.Button(
            label="📢 الإشعارات",
            custom_id="prof_set_notifications",
            style=ButtonStyle.secondary,
            emoji="📢",
            row=1
        ))
        self.add_item(ui.Button(
            label="🌐 API",
            custom_id="prof_set_api",
            style=ButtonStyle.secondary,
            emoji="🌐",
            row=2
        ))
        self.add_back_home_buttons()

    # ═══════════════════════════════════════════════════════════════════
    # CALLBACK METHODS - Required for button interactions
    # ═══════════════════════════════════════════════════════════════════
    
    @discord.ui.callback("prof_add_admin")
    async def prof_add_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_remove_admin")
    async def prof_remove_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_transfer_owner")
    async def prof_transfer_owner_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_promote")
    async def prof_promote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_demote")
    async def prof_demote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_perm_log")
    async def prof_perm_log_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_general")
    async def prof_set_general_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_features")
    async def prof_set_features_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_security")
    async def prof_set_security_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_notifications")
    async def prof_set_notifications_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_api")
    async def prof_set_api_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_color_theme")
    async def prof_color_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_text_theme")
    async def prof_text_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_icons")
    async def prof_icons_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_add")
    async def prof_gift_add_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_list")
    async def prof_gift_list_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_redeem")
    async def prof_gift_redeem_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_report")
    async def prof_gift_report_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_toggle_maintenance")
    async def prof_toggle_maintenance_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_backup")
    async def prof_backup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_cleanup")
    async def prof_cleanup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_check")
    async def prof_check_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_text")
    async def prof_broadcast_text_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_announce")
    async def prof_broadcast_announce_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_log")
    async def prof_broadcast_log_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_export")
    async def prof_db_export_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_import")
    async def prof_db_import_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_vacuum")
    async def prof_db_vacuum_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_integrity")
    async def prof_db_integrity_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_logs_clear")
    async def prof_logs_clear_callback(self, interaction: discord.Interaction):
        await owner_logs_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_list")
    async def prof_alliance_list_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_add")
    async def prof_alliance_add_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_delete")
    async def prof_alliance_delete_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)


# ═══════════════════════════════════════════════════════════════════════════════════
# APPEARANCE - المظهر
# ═══════════════════════════════════════════════════════════════════════════════════

@_check_owner
async def owner_appearance_callback(bot: WOSMBot, interaction: discord.Interaction):
    """إدارة المظهر"""
    
    from config.settings import settings
    
    embed = _create_header(
        "🎨 إدارة المظهر",
        "تكوين مظهر البوت",
        0xe91e63
    )
    
    embed.add_field(
        name="🎨 الألوان",
        value=f"""```
اللون الرئيسي: #{settings.theme_color_primary:06x}
لون النجاح: #{settings.theme_color_success:06x}
لون التحذير: #{settings.theme_color_warning:06x}
```""",
        inline=False
    )
    
    embed.add_field(
        name="📝 النصوص",
        value=f"""```
اسم البوت: {settings.bot_name}
```""",
        inline=False
    )
    
    view = OwnerAppearanceView(bot, interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class OwnerAppearanceView(BaseView):
    """عرض إدارة المظهر"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(ui.Button(
            label="🎨 الألوان",
            custom_id="prof_color_theme",
            style=ButtonStyle.primary,
            emoji="🎨",
            row=0
        ))
        self.add_item(ui.Button(
            label="📝 النصوص",
            custom_id="prof_text_theme",
            style=ButtonStyle.primary,
            emoji="📝",
            row=0
        ))
        self.add_item(ui.Button(
            label="🖼️ الأيقونات",
            custom_id="prof_icons",
            style=ButtonStyle.secondary,
            emoji="🖼️",
            row=1
        ))
        self.add_back_home_buttons()

    # ═══════════════════════════════════════════════════════════════════
    # CALLBACK METHODS - Required for button interactions
    # ═══════════════════════════════════════════════════════════════════
    
    @discord.ui.callback("prof_add_admin")
    async def prof_add_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_remove_admin")
    async def prof_remove_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_transfer_owner")
    async def prof_transfer_owner_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_promote")
    async def prof_promote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_demote")
    async def prof_demote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_perm_log")
    async def prof_perm_log_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_general")
    async def prof_set_general_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_features")
    async def prof_set_features_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_security")
    async def prof_set_security_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_notifications")
    async def prof_set_notifications_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_api")
    async def prof_set_api_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_color_theme")
    async def prof_color_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_text_theme")
    async def prof_text_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_icons")
    async def prof_icons_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_add")
    async def prof_gift_add_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_list")
    async def prof_gift_list_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_redeem")
    async def prof_gift_redeem_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_report")
    async def prof_gift_report_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_toggle_maintenance")
    async def prof_toggle_maintenance_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_backup")
    async def prof_backup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_cleanup")
    async def prof_cleanup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_check")
    async def prof_check_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_text")
    async def prof_broadcast_text_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_announce")
    async def prof_broadcast_announce_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_log")
    async def prof_broadcast_log_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_export")
    async def prof_db_export_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_import")
    async def prof_db_import_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_vacuum")
    async def prof_db_vacuum_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_integrity")
    async def prof_db_integrity_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_logs_clear")
    async def prof_logs_clear_callback(self, interaction: discord.Interaction):
        await owner_logs_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_list")
    async def prof_alliance_list_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_add")
    async def prof_alliance_add_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_delete")
    async def prof_alliance_delete_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)


# ═══════════════════════════════════════════════════════════════════════════════════
# GIFTS - الهدايا
# ═══════════════════════════════════════════════════════════════════════════════════

@_check_owner
async def owner_gifts_callback(bot: WOSMBot, interaction: discord.Interaction):
    """إدارة الهدايا"""
    
    try:
        total = await db.fetchone("SELECT COUNT(*) as c FROM gift_codes")
        active = await db.fetchone("SELECT COUNT(*) as c FROM gift_codes WHERE status = 'active'")
        redeemed = await db.fetchone("SELECT COUNT(*) as c FROM gift_codes WHERE status = 'redeemed'")
        invalid = await db.fetchone("SELECT COUNT(*) as c FROM gift_codes WHERE status = 'invalid'")
    except:
        total = active = redeemed = invalid = {"c": 0}
    
    embed = _create_header(
        "🎁 إدارة أكواد الهدايا",
        "إدارة نظام أكواد الهدايا",
        0x27ae60
    )
    
    embed.add_field(
        name="📊 الإحصائيات",
        value=f"""```
الإجمالي: {total['c']}
النشط: {active['c']}
المسترد: {redeemed['c']}
الملغي: {invalid['c']}
```""",
        inline=True
    )
    
    # Captcha status
    from integrations.gift_codes import GiftCaptchaSolver
    solver = GiftCaptchaSolver()
    
    embed.add_field(
        name="🤖 المحلل",
        value=f"""```
ONNX: {'جاهز' if solver.is_initialized else 'غير جاهز'}
```""",
        inline=True
    )
    
    view = OwnerGiftsView(bot, interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class OwnerGiftsView(BaseView):
    """عرض إدارة الهدايا"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(ui.Button(
            label="➕ إضافة كود",
            custom_id="prof_gift_add",
            style=ButtonStyle.success,
            emoji="➕",
            row=0
        ))
        self.add_item(ui.Button(
            label="📋 القائمة",
            custom_id="prof_gift_list",
            style=ButtonStyle.primary,
            emoji="📋",
            row=0
        ))
        self.add_item(ui.Button(
            label="🎯 استرداد",
            custom_id="prof_gift_redeem",
            style=ButtonStyle.secondary,
            emoji="🎯",
            row=1
        ))
        self.add_item(ui.Button(
            label="📊 التقرير",
            custom_id="prof_gift_report",
            style=ButtonStyle.secondary,
            emoji="📊",
            row=1
        ))
        self.add_back_home_buttons()

    # ═══════════════════════════════════════════════════════════════════
    # CALLBACK METHODS - Required for button interactions
    # ═══════════════════════════════════════════════════════════════════
    
    @discord.ui.callback("prof_add_admin")
    async def prof_add_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_remove_admin")
    async def prof_remove_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_transfer_owner")
    async def prof_transfer_owner_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_promote")
    async def prof_promote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_demote")
    async def prof_demote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_perm_log")
    async def prof_perm_log_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_general")
    async def prof_set_general_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_features")
    async def prof_set_features_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_security")
    async def prof_set_security_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_notifications")
    async def prof_set_notifications_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_api")
    async def prof_set_api_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_color_theme")
    async def prof_color_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_text_theme")
    async def prof_text_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_icons")
    async def prof_icons_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_add")
    async def prof_gift_add_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_list")
    async def prof_gift_list_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_redeem")
    async def prof_gift_redeem_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_report")
    async def prof_gift_report_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_toggle_maintenance")
    async def prof_toggle_maintenance_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_backup")
    async def prof_backup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_cleanup")
    async def prof_cleanup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_check")
    async def prof_check_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_text")
    async def prof_broadcast_text_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_announce")
    async def prof_broadcast_announce_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_log")
    async def prof_broadcast_log_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_export")
    async def prof_db_export_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_import")
    async def prof_db_import_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_vacuum")
    async def prof_db_vacuum_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_integrity")
    async def prof_db_integrity_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_logs_clear")
    async def prof_logs_clear_callback(self, interaction: discord.Interaction):
        await owner_logs_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_list")
    async def prof_alliance_list_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_add")
    async def prof_alliance_add_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_delete")
    async def prof_alliance_delete_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)


# ═══════════════════════════════════════════════════════════════════════════════════
# MAINTENANCE - الصيانة
# ═══════════════════════════════════════════════════════════════════════════════════

@_check_owner
async def owner_maintenance_callback(bot: WOSMBot, interaction: discord.Interaction):
    """أدوات الصيانة"""
    
    embed = _create_header(
        "🔧 أدوات الصيانة",
        "أدوات الصيانة والإصلاح",
        0xe67e22
    )
    
    # Maintenance status
    maintenance = await SettingsManager.get("maintenance_mode", False)
    
    embed.add_field(
        name="⚠️ وضع الصيانة",
        value=f"```\n{'🔒 مفعّل' if maintenance else '🔓 معطّل'}\n```",
        inline=True
    )
    
    embed.add_field(
        name="⚠️ تحذير",
        value="```\nاستخدم هذه الأدوات بحذر\n```",
        inline=True
    )
    
    view = OwnerMaintenanceView(bot, interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class OwnerMaintenanceView(BaseView):
    """عرض أدوات الصيانة"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(ui.Button(
            label="تفعيل/إلغاء الصيانة",
            custom_id="prof_toggle_maintenance",
            style=ButtonStyle.danger,
            emoji="🔒",
            row=0
        ))
        self.add_item(ui.Button(
            label="💾 نسخ احتياطي",
            custom_id="prof_backup",
            style=ButtonStyle.primary,
            emoji="💾",
            row=0
        ))
        self.add_item(ui.Button(
            label="🧹 تنظيف",
            custom_id="prof_cleanup",
            style=ButtonStyle.secondary,
            emoji="🧹",
            row=1
        ))
        self.add_item(ui.Button(
            label="🔍 فحص",
            custom_id="prof_check",
            style=ButtonStyle.secondary,
            emoji="🔍",
            row=1
        ))
        self.add_back_home_buttons()

    # ═══════════════════════════════════════════════════════════════════
    # CALLBACK METHODS - Required for button interactions
    # ═══════════════════════════════════════════════════════════════════
    
    @discord.ui.callback("prof_add_admin")
    async def prof_add_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_remove_admin")
    async def prof_remove_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_transfer_owner")
    async def prof_transfer_owner_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_promote")
    async def prof_promote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_demote")
    async def prof_demote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_perm_log")
    async def prof_perm_log_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_general")
    async def prof_set_general_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_features")
    async def prof_set_features_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_security")
    async def prof_set_security_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_notifications")
    async def prof_set_notifications_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_api")
    async def prof_set_api_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_color_theme")
    async def prof_color_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_text_theme")
    async def prof_text_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_icons")
    async def prof_icons_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_add")
    async def prof_gift_add_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_list")
    async def prof_gift_list_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_redeem")
    async def prof_gift_redeem_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_report")
    async def prof_gift_report_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_toggle_maintenance")
    async def prof_toggle_maintenance_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_backup")
    async def prof_backup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_cleanup")
    async def prof_cleanup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_check")
    async def prof_check_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_text")
    async def prof_broadcast_text_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_announce")
    async def prof_broadcast_announce_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_log")
    async def prof_broadcast_log_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_export")
    async def prof_db_export_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_import")
    async def prof_db_import_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_vacuum")
    async def prof_db_vacuum_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_integrity")
    async def prof_db_integrity_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_logs_clear")
    async def prof_logs_clear_callback(self, interaction: discord.Interaction):
        await owner_logs_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_list")
    async def prof_alliance_list_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_add")
    async def prof_alliance_add_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_delete")
    async def prof_alliance_delete_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)


# ═══════════════════════════════════════════════════════════════════════════════════
# BROADCAST - البث
# ═══════════════════════════════════════════════════════════════════════════════════

@_check_owner
async def owner_broadcast_callback(bot: WOSMBot, interaction: discord.Interaction):
    """لوحة البث"""
    
    embed = _create_header(
        "📢 لوحة البث",
        "إرسال رسائل جماعية للخوادم",
        0x2980b9
    )
    
    embed.add_field(
        name="📡 الخوادم",
        value=f"```\nعدد الخوادم: {len(bot.guilds)}\n```",
        inline=True
    )
    
    embed.add_field(
        name="⚠️ تحذير",
        value="```\nالبث يصل لجميع السيرفرات\n```",
        inline=True
    )
    
    view = OwnerBroadcastView(bot, interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class OwnerBroadcastView(BaseView):
    """عرض لوحة البث"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(ui.Button(
            label="📝 بث نص",
            custom_id="prof_broadcast_text",
            style=ButtonStyle.primary,
            emoji="📝",
            row=0
        ))
        self.add_item(ui.Button(
            label="📌 تنبيه",
            custom_id="prof_broadcast_announce",
            style=ButtonStyle.warning,
            emoji="📌",
            row=0
        ))
        self.add_item(ui.Button(
            label="📊 سجل البث",
            custom_id="prof_broadcast_log",
            style=ButtonStyle.secondary,
            emoji="📊",
            row=1
        ))
        self.add_back_home_buttons()

    # ═══════════════════════════════════════════════════════════════════
    # CALLBACK METHODS - Required for button interactions
    # ═══════════════════════════════════════════════════════════════════
    
    @discord.ui.callback("prof_add_admin")
    async def prof_add_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_remove_admin")
    async def prof_remove_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_transfer_owner")
    async def prof_transfer_owner_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_promote")
    async def prof_promote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_demote")
    async def prof_demote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_perm_log")
    async def prof_perm_log_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_general")
    async def prof_set_general_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_features")
    async def prof_set_features_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_security")
    async def prof_set_security_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_notifications")
    async def prof_set_notifications_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_api")
    async def prof_set_api_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_color_theme")
    async def prof_color_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_text_theme")
    async def prof_text_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_icons")
    async def prof_icons_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_add")
    async def prof_gift_add_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_list")
    async def prof_gift_list_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_redeem")
    async def prof_gift_redeem_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_report")
    async def prof_gift_report_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_toggle_maintenance")
    async def prof_toggle_maintenance_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_backup")
    async def prof_backup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_cleanup")
    async def prof_cleanup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_check")
    async def prof_check_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_text")
    async def prof_broadcast_text_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_announce")
    async def prof_broadcast_announce_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_log")
    async def prof_broadcast_log_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_export")
    async def prof_db_export_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_import")
    async def prof_db_import_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_vacuum")
    async def prof_db_vacuum_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_integrity")
    async def prof_db_integrity_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_logs_clear")
    async def prof_logs_clear_callback(self, interaction: discord.Interaction):
        await owner_logs_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_list")
    async def prof_alliance_list_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_add")
    async def prof_alliance_add_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_delete")
    async def prof_alliance_delete_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)


# ═══════════════════════════════════════════════════════════════════════════════════
# DATABASE - قاعدة البيانات
# ═══════════════════════════════════════════════════════════════════════════════════

@_check_owner
async def owner_database_callback(bot: WOSMBot, interaction: discord.Interaction):
    """إدارة قاعدة البيانات"""
    
    db_path = 'data/wosm.sqlite'
    db_size = os.path.getsize(db_path) / 1024 / 1024 if os.path.exists(db_path) else 0
    
    try:
        tables = await db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
        table_count = len(tables)
    except:
        table_count = 0
    
    embed = _create_header(
        "🗄️ إدارة قاعدة البيانات",
        "إدارة وصيانة قاعدة البيانات",
        0x8e44ad
    )
    
    embed.add_field(
        name="📊 المعلومات",
        value=f"""```
الحجم: {db_size:.2f} MB
الجداول: {table_count}
المسار: {db_path}
```""",
        inline=False
    )
    
    view = OwnerDatabaseView(bot, interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class OwnerDatabaseView(BaseView):
    """عرض إدارة قاعدة البيانات"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(ui.Button(
            label="💾 تصدير",
            custom_id="prof_db_export",
            style=ButtonStyle.primary,
            emoji="💾",
            row=0
        ))
        self.add_item(ui.Button(
            label="📥 استيراد",
            custom_id="prof_db_import",
            style=ButtonStyle.secondary,
            emoji="📥",
            row=0
        ))
        self.add_item(ui.Button(
            label="🧹 تنظيف",
            custom_id="prof_db_vacuum",
            style=ButtonStyle.warning,
            emoji="🧹",
            row=1
        ))
        self.add_item(ui.Button(
            label="🔍 فحص",
            custom_id="prof_db_integrity",
            style=ButtonStyle.secondary,
            emoji="🔍",
            row=1
        ))
        self.add_back_home_buttons()

    # ═══════════════════════════════════════════════════════════════════
    # CALLBACK METHODS - Required for button interactions
    # ═══════════════════════════════════════════════════════════════════
    
    @discord.ui.callback("prof_add_admin")
    async def prof_add_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_remove_admin")
    async def prof_remove_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_transfer_owner")
    async def prof_transfer_owner_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_promote")
    async def prof_promote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_demote")
    async def prof_demote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_perm_log")
    async def prof_perm_log_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_general")
    async def prof_set_general_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_features")
    async def prof_set_features_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_security")
    async def prof_set_security_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_notifications")
    async def prof_set_notifications_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_api")
    async def prof_set_api_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_color_theme")
    async def prof_color_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_text_theme")
    async def prof_text_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_icons")
    async def prof_icons_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_add")
    async def prof_gift_add_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_list")
    async def prof_gift_list_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_redeem")
    async def prof_gift_redeem_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_report")
    async def prof_gift_report_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_toggle_maintenance")
    async def prof_toggle_maintenance_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_backup")
    async def prof_backup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_cleanup")
    async def prof_cleanup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_check")
    async def prof_check_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_text")
    async def prof_broadcast_text_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_announce")
    async def prof_broadcast_announce_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_log")
    async def prof_broadcast_log_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_export")
    async def prof_db_export_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_import")
    async def prof_db_import_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_vacuum")
    async def prof_db_vacuum_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_integrity")
    async def prof_db_integrity_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_logs_clear")
    async def prof_logs_clear_callback(self, interaction: discord.Interaction):
        await owner_logs_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_list")
    async def prof_alliance_list_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_add")
    async def prof_alliance_add_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_delete")
    async def prof_alliance_delete_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)


# ═══════════════════════════════════════════════════════════════════════════════════
# LOGS - السجلات
# ═══════════════════════════════════════════════════════════════════════════════════

@_check_owner
async def owner_logs_callback(bot: WOSMBot, interaction: discord.Interaction):
    """عرض السجلات"""
    
    try:
        logs = await db.fetchall("""
            SELECT action, user_id, category, created_at 
            FROM audit_log 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
    except:
        logs = []
    
    embed = _create_header(
        "📜 سجلات النظام",
        f"آخر {len(logs)} أحداث",
        0x34495e
    )
    
    if logs:
        log_text = "\n".join([
            f"• [{log.get('created_at', 'N/A')[:19]}] {log.get('action', 'N/A')}"
            for log in logs[:10]
        ])
        embed.add_field(
            name="📝 آخر الأحداث",
            value=f"```\n{log_text}\n```",
            inline=False
        )
    else:
        embed.add_field(
            name="📝 السجلات",
            value="```\nلا توجد سجلات\n```",
            inline=False
        )
    
    view = OwnerLogsView(bot, interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class OwnerLogsView(BaseView):
    """عرض السجلات"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(ui.Button(
            label="🔄 تحديث",
            custom_id="prof_logs",
            style=ButtonStyle.secondary,
            emoji="🔄",
            row=0
        ))
        self.add_item(ui.Button(
            label="🗑️ تنظيف",
            custom_id="prof_logs_clear",
            style=ButtonStyle.danger,
            emoji="🗑️",
            row=0
        ))
        self.add_back_home_buttons()

    # ═══════════════════════════════════════════════════════════════════
    # CALLBACK METHODS - Required for button interactions
    # ═══════════════════════════════════════════════════════════════════
    
    @discord.ui.callback("prof_add_admin")
    async def prof_add_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_remove_admin")
    async def prof_remove_admin_callback(self, interaction: discord.Interaction):
        await owner_users_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_transfer_owner")
    async def prof_transfer_owner_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_promote")
    async def prof_promote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_demote")
    async def prof_demote_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_perm_log")
    async def prof_perm_log_callback(self, interaction: discord.Interaction):
        await owner_permissions_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_general")
    async def prof_set_general_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_features")
    async def prof_set_features_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_security")
    async def prof_set_security_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_notifications")
    async def prof_set_notifications_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_set_api")
    async def prof_set_api_callback(self, interaction: discord.Interaction):
        await owner_settings_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_color_theme")
    async def prof_color_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_text_theme")
    async def prof_text_theme_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_icons")
    async def prof_icons_callback(self, interaction: discord.Interaction):
        await owner_appearance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_add")
    async def prof_gift_add_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_list")
    async def prof_gift_list_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_redeem")
    async def prof_gift_redeem_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_gift_report")
    async def prof_gift_report_callback(self, interaction: discord.Interaction):
        await owner_gifts_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_toggle_maintenance")
    async def prof_toggle_maintenance_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_backup")
    async def prof_backup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_cleanup")
    async def prof_cleanup_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_check")
    async def prof_check_callback(self, interaction: discord.Interaction):
        await owner_maintenance_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_text")
    async def prof_broadcast_text_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_announce")
    async def prof_broadcast_announce_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_broadcast_log")
    async def prof_broadcast_log_callback(self, interaction: discord.Interaction):
        await owner_broadcast_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_export")
    async def prof_db_export_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_import")
    async def prof_db_import_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_vacuum")
    async def prof_db_vacuum_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_db_integrity")
    async def prof_db_integrity_callback(self, interaction: discord.Interaction):
        await owner_database_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_logs_clear")
    async def prof_logs_clear_callback(self, interaction: discord.Interaction):
        await owner_logs_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_list")
    async def prof_alliance_list_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_add")
    async def prof_alliance_add_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)
    
    @discord.ui.callback("prof_alliance_delete")
    async def prof_alliance_delete_callback(self, interaction: discord.Interaction):
        await owner_alliances_callback(self.bot, interaction)


# ═══════════════════════════════════════════════════════════════════════════════════
# ALLIANCES - التحالفات
# ═══════════════════════════════════════════════════════════════════════════════════

@_check_owner
async def owner_alliances_callback(bot: WOSMBot, interaction: discord.Interaction):
    """إدارة التحالفات"""
    
    try:
        alliances = await db.fetchall("""
            SELECT name, member_count, created_at 
            FROM alliances 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        total = await db.fetchone("SELECT COUNT(*) as c FROM alliances")
    except:
        alliances = []
        total = {"c": 0}
    
    embed = _create_header(
        "🏰 إدارة التحالفات",
        f"إجمالي التحالفات: **{total['c']}**",
        0xe74c3c
    )
    
    if alliances:
        text = "\n".join([
            f"• {a.get('name', 'N/A')} ({a.get('member_count', 0)} عضو)"
            for a in alliances[:5]
        ])
        embed.add_field(
            name="🏆 أحدث التحالفات",
            value=text,
            inline=False
        )
    
    view = OwnerAlliancesView(bot, interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class OwnerAlliancesView(BaseView):
    """عرض إدارة التحالفات"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(ui.Button(
            label="📋 القائمة",
            custom_id="prof_alliance_list",
            style=ButtonStyle.primary,
            emoji="📋",
            row=0
        ))
        self.add_item(ui.Button(
            label="➕ إضافة",
            custom_id="prof_alliance_add",
            style=ButtonStyle.success,
            emoji="➕",
            row=0
        ))
        self.add_item(ui.Button(
            label="🗑️ حذف",
            custom_id="prof_alliance_delete",
            style=ButtonStyle.danger,
            emoji="🗑️",
            row=1
        ))
        self.add_back_home_buttons()
