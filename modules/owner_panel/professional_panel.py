"""
WOS-M Professional Owner Panel
لوحة تحكم المالك الاحترافية
© MANSOUR — WOS-M. All rights reserved.
"""
import os
import asyncio
import discord
from discord import ui
from views.buttons import RoutedButton
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
        self.add_item(RoutedButton(
            label="📊 الإحصائيات",
            custom_id="prof_stats",
            style=discord.ButtonStyle.primary,
            row=0
        ))
        self.add_item(RoutedButton(
            label="👥 المستخدمين",
            custom_id="prof_users",
            style=discord.ButtonStyle.primary,
            row=0
        ))
        self.add_item(RoutedButton(
            label="🏰 التحالفات",
            custom_id="prof_alliances",
            style=discord.ButtonStyle.primary,
            row=0
        ))
        
        # Row 1 - الإعدادات
        self.add_item(RoutedButton(
            label="🔐 الصلاحيات",
            custom_id="prof_permissions",
            style=discord.ButtonStyle.secondary,
            row=1
        ))
        self.add_item(RoutedButton(
            label="⚙️ الإعدادات",
            custom_id="prof_settings",
            style=discord.ButtonStyle.secondary,
            row=1
        ))
        self.add_item(RoutedButton(
            label="🎨 المظهر",
            custom_id="prof_appearance",
            style=discord.ButtonStyle.secondary,
            row=1
        ))
        
        # Row 2 - الأدوات
        self.add_item(RoutedButton(
            label="🎁 الهدايا",
            custom_id="prof_gifts",
            style=discord.ButtonStyle.success,
            row=2
        ))
        self.add_item(RoutedButton(
            label="🔧 الصيانة",
            custom_id="prof_maintenance",
            style=discord.ButtonStyle.success,
            row=2
        ))
        self.add_item(RoutedButton(
            label="📢 البث",
            custom_id="prof_broadcast",
            style=discord.ButtonStyle.success,
            row=2
        ))
        
        # Row 3 - قاعدة البيانات
        self.add_item(RoutedButton(
            label="🗄️ قاعدة البيانات",
            custom_id="prof_database",
            style=discord.ButtonStyle.danger,
            row=3
        ))
        self.add_item(RoutedButton(
            label="📜 السجلات",
            custom_id="prof_logs",
            style=discord.ButtonStyle.danger,
            row=3
        ))
        self.add_item(RoutedButton(
            label="🔄 تحديث",
            custom_id="prof_refresh",
            style=discord.ButtonStyle.danger,
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
        
        self.add_item(RoutedButton(
            label="➕ إضافة مشرف",
            custom_id="prof_add_admin",
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=0
        ))
        self.add_item(RoutedButton(
            label="➖ إزالة مشرف",
            custom_id="prof_remove_admin",
            style=discord.ButtonStyle.danger,
            emoji="➖",
            row=0
        ))
        self.add_item(RoutedButton(
            label="🔄 تحديث",
            custom_id="prof_users",
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            row=1
        ))
        self.add_back_home_buttons()
class OwnerPermissionsView(BaseView):
    """عرض إدارة الصلاحيات"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(RoutedButton(
            label="👑 نقل الملكية",
            custom_id="prof_transfer_owner",
            style=discord.ButtonStyle.danger,
            emoji="👑",
            row=0
        ))
        self.add_item(RoutedButton(
            label="🔰 ترقية",
            custom_id="prof_promote",
            style=discord.ButtonStyle.success,
            emoji="🔰",
            row=0
        ))
        self.add_item(RoutedButton(
            label="📉 تخفيض",
            custom_id="prof_demote",
            style=discord.ButtonStyle.secondary,
            emoji="📉",
            row=1
        ))
        self.add_item(RoutedButton(
            label="📜 سجل الصلاحيات",
            custom_id="prof_perm_log",
            style=discord.ButtonStyle.primary,
            emoji="📜",
            row=1
        ))
        self.add_back_home_buttons()
class OwnerSettingsView(BaseView):
    """عرض إدارة الإعدادات"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(RoutedButton(
            label="🔧 عام",
            custom_id="prof_set_general",
            style=discord.ButtonStyle.primary,
            emoji="🔧",
            row=0
        ))
        self.add_item(RoutedButton(
            label="✨ الميزات",
            custom_id="prof_set_features",
            style=discord.ButtonStyle.primary,
            emoji="✨",
            row=0
        ))
        self.add_item(RoutedButton(
            label="🔐 الأمان",
            custom_id="prof_set_security",
            style=discord.ButtonStyle.secondary,
            emoji="🔐",
            row=1
        ))
        self.add_item(RoutedButton(
            label="📢 الإشعارات",
            custom_id="prof_set_notifications",
            style=discord.ButtonStyle.secondary,
            emoji="📢",
            row=1
        ))
        self.add_item(RoutedButton(
            label="🌐 API",
            custom_id="prof_set_api",
            style=discord.ButtonStyle.secondary,
            emoji="🌐",
            row=2
        ))
        self.add_back_home_buttons()
class OwnerAppearanceView(BaseView):
    """عرض إدارة المظهر"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(RoutedButton(
            label="🎨 الألوان",
            custom_id="prof_color_theme",
            style=discord.ButtonStyle.primary,
            emoji="🎨",
            row=0
        ))
        self.add_item(RoutedButton(
            label="📝 النصوص",
            custom_id="prof_text_theme",
            style=discord.ButtonStyle.primary,
            emoji="📝",
            row=0
        ))
        self.add_item(RoutedButton(
            label="🖼️ الأيقونات",
            custom_id="prof_icons",
            style=discord.ButtonStyle.secondary,
            emoji="🖼️",
            row=1
        ))
        self.add_back_home_buttons()
class OwnerGiftsView(BaseView):
    """عرض إدارة الهدايا"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(RoutedButton(
            label="➕ إضافة كود",
            custom_id="prof_gift_add",
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=0
        ))
        self.add_item(RoutedButton(
            label="📋 القائمة",
            custom_id="prof_gift_list",
            style=discord.ButtonStyle.primary,
            emoji="📋",
            row=0
        ))
        self.add_item(RoutedButton(
            label="🎯 استرداد",
            custom_id="prof_gift_redeem",
            style=discord.ButtonStyle.secondary,
            emoji="🎯",
            row=1
        ))
        self.add_item(RoutedButton(
            label="📊 التقرير",
            custom_id="prof_gift_report",
            style=discord.ButtonStyle.secondary,
            emoji="📊",
            row=1
        ))
        self.add_back_home_buttons()
class OwnerMaintenanceView(BaseView):
    """عرض أدوات الصيانة"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(RoutedButton(
            label="تفعيل/إلغاء الصيانة",
            custom_id="prof_toggle_maintenance",
            style=discord.ButtonStyle.danger,
            emoji="🔒",
            row=0
        ))
        self.add_item(RoutedButton(
            label="💾 نسخ احتياطي",
            custom_id="prof_backup",
            style=discord.ButtonStyle.primary,
            emoji="💾",
            row=0
        ))
        self.add_item(RoutedButton(
            label="🧹 تنظيف",
            custom_id="prof_cleanup",
            style=discord.ButtonStyle.secondary,
            emoji="🧹",
            row=1
        ))
        self.add_item(RoutedButton(
            label="🔍 فحص",
            custom_id="prof_check",
            style=discord.ButtonStyle.secondary,
            emoji="🔍",
            row=1
        ))
        self.add_back_home_buttons()
class OwnerBroadcastView(BaseView):
    """عرض لوحة البث"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(RoutedButton(
            label="📝 بث نص",
            custom_id="prof_broadcast_text",
            style=discord.ButtonStyle.primary,
            emoji="📝",
            row=0
        ))
        self.add_item(RoutedButton(
            label="📌 تنبيه",
            custom_id="prof_broadcast_announce",
            style=discord.ButtonStyle.warning,
            emoji="📌",
            row=0
        ))
        self.add_item(RoutedButton(
            label="📊 سجل البث",
            custom_id="prof_broadcast_log",
            style=discord.ButtonStyle.secondary,
            emoji="📊",
            row=1
        ))
        self.add_back_home_buttons()
class OwnerDatabaseView(BaseView):
    """عرض إدارة قاعدة البيانات"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(RoutedButton(
            label="💾 تصدير",
            custom_id="prof_db_export",
            style=discord.ButtonStyle.primary,
            emoji="💾",
            row=0
        ))
        self.add_item(RoutedButton(
            label="📥 استيراد",
            custom_id="prof_db_import",
            style=discord.ButtonStyle.secondary,
            emoji="📥",
            row=0
        ))
        self.add_item(RoutedButton(
            label="🧹 تنظيف",
            custom_id="prof_db_vacuum",
            style=discord.ButtonStyle.warning,
            emoji="🧹",
            row=1
        ))
        self.add_item(RoutedButton(
            label="🔍 فحص",
            custom_id="prof_db_integrity",
            style=discord.ButtonStyle.secondary,
            emoji="🔍",
            row=1
        ))
        self.add_back_home_buttons()
class OwnerLogsView(BaseView):
    """عرض السجلات"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(RoutedButton(
            label="🔄 تحديث",
            custom_id="prof_logs",
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            row=0
        ))
        self.add_item(RoutedButton(
            label="🗑️ تنظيف",
            custom_id="prof_logs_clear",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            row=0
        ))
        self.add_back_home_buttons()
class OwnerAlliancesView(BaseView):
    """عرض إدارة التحالفات"""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(user_id=user_id, timeout=600)
        
        self.add_item(RoutedButton(
            label="📋 القائمة",
            custom_id="prof_alliance_list",
            style=discord.ButtonStyle.primary,
            emoji="📋",
            row=0
        ))
        self.add_item(RoutedButton(
            label="➕ إضافة",
            custom_id="prof_alliance_add",
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=0
        ))
        self.add_item(RoutedButton(
            label="🗑️ حذف",
            custom_id="prof_alliance_delete",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            row=1
        ))
        self.add_back_home_buttons()
