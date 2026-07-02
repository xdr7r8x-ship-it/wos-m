"""
WOS-M Settings Manager
نظام الإعدادات الشامل
© MANSOUR — WOS-M. All rights reserved.
"""
import json
import asyncio
import discord
from discord import ui, ButtonStyle
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from core.database import db
from core.audit_log import audit_log, AuditCategory


class SettingCategory(Enum):
    """فئات الإعدادات"""
    GENERAL = "عام"
    APPEARANCE = "المظهر"
    SECURITY = "الأمان"
    FEATURES = "الميزات"
    NOTIFICATIONS = "الإشعارات"
    DATABASE = "قاعدة البيانات"
    API = "API"
    MAINTENANCE = "الصيانة"


@dataclass
class Setting:
    """تعريف إعداد"""
    key: str
    name_ar: str
    name_en: str
    description: str
    category: SettingCategory
    value_type: str  # str, int, bool, list, dict
    default: Any
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    options: Optional[List[str]] = None
    required: bool = False
    secret: bool = False
    on_change: Optional[Callable] = None


class SettingsManager:
    """
    مدير الإعدادات الشامل
    يوفر واجهة موحدة لإدارة جميع إعدادات البوت
    """
    
    # الإعدادات المسجلة
    SETTINGS: Dict[str, Setting] = {}
    
    # القيم الحالية
    _cache: Dict[str, Any] = {}
    _cache_loaded: bool = False
    
    @classmethod
    def register_setting(cls, setting: Setting):
        """تسجيل إعداد جديد"""
        cls.SETTINGS[setting.key] = setting
    
    @classmethod
    def register_settings(cls, settings: List[Setting]):
        """تسجيل عدة إعدادات"""
        for setting in settings:
            cls.register_setting(setting)
    
    @classmethod
    async def load_all(cls):
        """تحميل جميع الإعدادات من قاعدة البيانات"""
        if cls._cache_loaded:
            return
        
        try:
            rows = await db.fetchall("SELECT key, value FROM bot_settings")
            for row in rows:
                cls._cache[row['key']] = cls._parse_value(row['key'], row['value'])
            cls._cache_loaded = True
        except Exception as e:
            print(f"Error loading settings: {e}")
            cls._cache_loaded = True
    
    @classmethod
    def _parse_value(cls, key: str, value: str) -> Any:
        """تحليل قيمة من النص"""
        if key not in cls.SETTINGS:
            return value
        
        setting = cls.SETTINGS[key]
        
        try:
            if setting.value_type == "bool":
                return value.lower() in ("true", "1", "yes", "on")
            elif setting.value_type == "int":
                return int(value)
            elif setting.value_type == "float":
                return float(value)
            elif setting.value_type == "list":
                return json.loads(value) if value else []
            elif setting.value_type == "dict":
                return json.loads(value) if value else {}
            else:
                return value
        except:
            return value
    
    @classmethod
    def _serialize_value(cls, value: Any) -> str:
        """تحويل القيمة إلى نص للحفظ"""
        if isinstance(value, (list, dict)):
            return json.dumps(value)
        return str(value)
    
    @classmethod
    async def get(cls, key: str, default: Any = None) -> Any:
        """الحصول على قيمة إعداد"""
        await cls.load_all()
        
        if key in cls._cache:
            return cls._cache[key]
        
        if key in cls.SETTINGS:
            return cls.SETTINGS[key].default
        
        return default
    
    @classmethod
    async def set(cls, key: str, value: Any, user_id: str = None) -> bool:
        """تعيين قيمة إعداد"""
        await cls.load_all()
        
        # التحقق من وجود الإعداد
        if key not in cls.SETTINGS:
            print(f"Unknown setting: {key}")
            return False
        
        setting = cls.SETTINGS[key]
        
        # التحقق من النوع
        if setting.value_type == "int" and not isinstance(value, int):
            try:
                value = int(value)
            except:
                return False
        
        if setting.value_type == "bool" and not isinstance(value, bool):
            value = str(value).lower() in ("true", "1", "yes", "on")
        
        # التحقق من النطاق
        if setting.min_value is not None and value < setting.min_value:
            value = setting.min_value
        if setting.max_value is not None and value > setting.max_value:
            value = setting.max_value
        
        # حفظ في قاعدة البيانات
        try:
            serialized = cls._serialize_value(value)
            await db.execute(
                "INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)",
                (key, serialized)
            )
            await db.commit()
            
            # تحديث الكاش
            cls._cache[key] = value
            
            # استدعاء callback إذا كان موجوداً
            if setting.on_change:
                await setting.on_change(value)
            
            # تسجيل في السجل
            if user_id:
                await audit_log.log(
                    user_id=user_id,
                    action=f"setting_change",
                    category=AuditCategory.SETTINGS,
                    details={"key": key, "value": "***" if setting.secret else value}
                )
            
            return True
            
        except Exception as e:
            print(f"Error saving setting {key}: {e}")
            return False
    
    @classmethod
    async def reset(cls, key: str, user_id: str = None) -> bool:
        """إعادة تعيين إعداد للقيمة الافتراضية"""
        if key not in cls.SETTINGS:
            return False
        
        setting = cls.SETTINGS[key]
        return await cls.set(key, setting.default, user_id)
    
    @classmethod
    async def reset_all(cls, user_id: str = None) -> int:
        """إعادة تعيين جميع الإعدادات"""
        count = 0
        for key in cls.SETTINGS:
            if await cls.reset(key, user_id):
                count += 1
        return count
    
    @classmethod
    def get_by_category(cls, category: SettingCategory) -> Dict[str, Setting]:
        """الحصول على الإعدادات حسب الفئة"""
        return {
            key: setting 
            for key, setting in cls.SETTINGS.items() 
            if setting.category == category
        }
    
    @classmethod
    async def export_all(cls) -> Dict[str, Any]:
        """تصدير جميع الإعدادات"""
        await cls.load_all()
        return {
            key: setting.to_dict() if hasattr(setting, 'to_dict') else {
                "name": setting.name_ar,
                "value": cls._cache.get(key, setting.default),
                "category": setting.category.value
            }
            for key, setting in cls.SETTINGS.items()
        }
    
    @classmethod
    async def import_settings(cls, data: Dict[str, Any], user_id: str = None) -> int:
        """استيراد الإعدادات"""
        count = 0
        for key, value in data.items():
            if key in cls.SETTINGS:
                if await cls.set(key, value, user_id):
                    count += 1
        return count
    
    @classmethod
    def clear_cache(cls):
        """مسح الكاش"""
        cls._cache.clear()
        cls._cache_loaded = False


# ═══════════════════════════════════════════════════════════════════════════════════
# تسجيل الإعدادات الافتراضية
# ═══════════════════════════════════════════════════════════════════════════════════

def _setup_default_settings():
    """إعداد الإعدادات الافتراضية"""
    
    # الإعدادات العامة
    SettingsManager.register_settings([
        Setting(
            key="bot_name",
            name_ar="اسم البوت",
            name_en="Bot Name",
            description="اسم البوت المعروض في الواجهة",
            category=SettingCategory.GENERAL,
            value_type="str",
            default="WOS-M Bot"
        ),
        Setting(
            key="bot_prefix",
            name_ar="بادئة الأوامر",
            name_en="Command Prefix",
            description="البادئة المستخدمة للأوامر",
            category=SettingCategory.GENERAL,
            value_type="str",
            default="/"
        ),
        Setting(
            key="owner_id",
            name_ar="معرف المالك",
            name_en="Owner ID",
            description="Discord ID للمالك",
            category=SettingCategory.GENERAL,
            value_type="str",
            default=""
        ),
        Setting(
            key="owner_name",
            name_ar="اسم المالك",
            name_en="Owner Name",
            description="اسم المالك",
            category=SettingCategory.GENERAL,
            value_type="str",
            default="MANSOUR"
        ),
        Setting(
            key="main_language",
            name_ar="اللغة الرئيسية",
            name_en="Main Language",
            description="اللغة الافتراضية للنظام",
            category=SettingCategory.GENERAL,
            value_type="str",
            default="ar",
            options=["ar", "en", "tr", "zh"]
        ),
        Setting(
            key="timezone",
            name_ar="المنطقة الزمنية",
            name_en="Timezone",
            description="المنطقة الزمنية للسجلات",
            category=SettingCategory.GENERAL,
            value_type="str",
            default="Asia/Riyadh"
        ),
    ])
    
    # إعدادات المظهر
    SettingsManager.register_settings([
        Setting(
            key="theme_color_primary",
            name_ar="اللون الرئيسي",
            name_en="Primary Color",
            description="اللون الرئيسي للـ embeds",
            category=SettingCategory.APPEARANCE,
            value_type="int",
            default=0xe74c3c,
            min_value=0,
            max_value=0xFFFFFF
        ),
        Setting(
            key="theme_color_success",
            name_ar="لون النجاح",
            name_en="Success Color",
            description="لون رسائل النجاح",
            category=SettingCategory.APPEARANCE,
            value_type="int",
            default=0x2ecc71,
            min_value=0,
            max_value=0xFFFFFF
        ),
        Setting(
            key="theme_color_warning",
            name_ar="لون التحذير",
            name_en="Warning Color",
            description="لون رسائل التحذير",
            category=SettingCategory.APPEARANCE,
            value_type="int",
            default=0xf39c12,
            min_value=0,
            max_value=0xFFFFFF
        ),
        Setting(
            key="theme_color_error",
            name_ar="لون الخطأ",
            name_en="Error Color",
            description="لون رسائل الخطأ",
            category=SettingCategory.APPEARANCE,
            value_type="int",
            default=0xe74c3c,
            min_value=0,
            max_value=0xFFFFFF
        ),
        Setting(
            key="footer_text",
            name_ar="نص الفوتر",
            name_en="Footer Text",
            description="النص المعروض في أسفل الـ embeds",
            category=SettingCategory.APPEARANCE,
            value_type="str",
            default="WOS-M • Powered by AI"
        ),
        Setting(
            key="show_avatar",
            name_ar="إظهار الصورة",
            name_en="Show Avatar",
            description="إظهار صورة البوت في الفوتر",
            category=SettingCategory.APPEARANCE,
            value_type="bool",
            default=True
        ),
    ])
    
    # إعدادات الأمان
    SettingsManager.register_settings([
        Setting(
            key="require_verification",
            name_ar="طلب التحقق",
            name_en="Require Verification",
            description="طلب التحقق من المستخدم قبل منح الصلاحيات",
            category=SettingCategory.SECURITY,
            value_type="bool",
            default=True
        ),
        Setting(
            key="log_all_actions",
            name_ar="تسجيل كل الأفعال",
            name_en="Log All Actions",
            description="تسجيل جميع أفعال المستخدمين",
            category=SettingCategory.SECURITY,
            value_type="bool",
            default=True
        ),
        Setting(
            key="max_admins",
            name_ar="الحد الأقصى للمشرفين",
            name_en="Max Admins",
            description="الحد الأقصى لعدد المشرفين",
            category=SettingCategory.SECURITY,
            value_type="int",
            default=10,
            min_value=1,
            max_value=100
        ),
        Setting(
            key="session_timeout",
            name_ar="مهلة الجلسة",
            name_en="Session Timeout",
            description="مهلة الجلسة بالدقائق",
            category=SettingCategory.SECURITY,
            value_type="int",
            default=30,
            min_value=5,
            max_value=1440
        ),
        Setting(
            key="rate_limit_enabled",
            name_ar="تفعيل حد المعدل",
            name_en="Enable Rate Limit",
            description="تفعيل حد المعدل للطلبات",
            category=SettingCategory.SECURITY,
            value_type="bool",
            default=True
        ),
    ])
    
    # إعدادات الميزات
    SettingsManager.register_settings([
        Setting(
            key="feature_gift_codes",
            name_ar="أكواد الهدايا",
            name_en="Gift Codes",
            description="تفعيل نظام أكواد الهدايا",
            category=SettingCategory.FEATURES,
            value_type="bool",
            default=True
        ),
        Setting(
            key="feature_alliances",
            name_ar="التحالفات",
            name_en="Alliances",
            description="تفعيل نظام التحالفات",
            category=SettingCategory.FEATURES,
            value_type="bool",
            default=True
        ),
        Setting(
            key="feature_events",
            name_ar="الفعاليات",
            name_en="Events",
            description="تفعيل نظام الفعاليات",
            category=SettingCategory.FEATURES,
            value_type="bool",
            default=True
        ),
        Setting(
            key="feature_auto_redeem",
            name_ar="الاسترداد التلقائي",
            name_en="Auto Redeem",
            description="تفعيل الاسترداد التلقائي للأكواد",
            category=SettingCategory.FEATURES,
            value_type="bool",
            default=False
        ),
        Setting(
            key="feature_broadcast",
            name_ar="البث",
            name_en="Broadcast",
            description="تفعيل نظام البث",
            category=SettingCategory.FEATURES,
            value_type="bool",
            default=True
        ),
        Setting(
            key="feature_audit_log",
            name_ar="سجل التدقيق",
            name_en="Audit Log",
            description="تفعيل سجل التدقيق",
            category=SettingCategory.FEATURES,
            value_type="bool",
            default=True
        ),
    ])
    
    # إعدادات الإشعارات
    SettingsManager.register_settings([
        Setting(
            key="notify_new_code",
            name_ar="إشعار كود جديد",
            name_en="New Code Notification",
            description="إرسال إشعار عند اكتشاف كود جديد",
            category=SettingCategory.NOTIFICATIONS,
            value_type="bool",
            default=True
        ),
        Setting(
            key="notify_redeem_success",
            name_ar="إشعار نجاح الاسترداد",
            name_en="Redeem Success Notification",
            description="إرسال إشعار عند نجاح استرداد كود",
            category=SettingCategory.NOTIFICATIONS,
            value_type="bool",
            default=True
        ),
        Setting(
            key="notify_admin_action",
            name_ar="إشعار إجراء مشرف",
            name_en="Admin Action Notification",
            description="إرسال إشعار عند تنفيذ إجراء من مشرف",
            category=SettingCategory.NOTIFICATIONS,
            value_type="bool",
            default=True
        ),
        Setting(
            key="notify_channel_id",
            name_ar="قناة الإشعارات",
            name_en="Notification Channel",
            description="قناة Discord للإشعارات",
            category=SettingCategory.NOTIFICATIONS,
            value_type="str",
            default=""
        ),
    ])
    
    # إعدادات قاعدة البيانات
    SettingsManager.register_settings([
        Setting(
            key="db_backup_enabled",
            name_ar="تفعيل النسخ الاحتياطي",
            name_en="Enable Backup",
            description="تفعيل النسخ الاحتياطي التلقائي",
            category=SettingCategory.DATABASE,
            value_type="bool",
            default=True
        ),
        Setting(
            key="db_backup_interval",
            name_ar="فترة النسخ",
            name_en="Backup Interval",
            description="فترة النسخ الاحتياطي بالساعات",
            category=SettingCategory.DATABASE,
            value_type="int",
            default=24,
            min_value=1,
            max_value=168
        ),
        Setting(
            key="db_max_backups",
            name_ar="الحد الأقصى للنسخ",
            name_en="Max Backups",
            description="الحد الأقصى لعدد النسخ الاحتياطية",
            category=SettingCategory.DATABASE,
            value_type="int",
            default=7,
            min_value=1,
            max_value=30
        ),
        Setting(
            key="db_auto_vacuum",
            name_ar="تنظيف تلقائي",
            name_en="Auto Vacuum",
            description="تنظيف تلقائي لقاعدة البيانات",
            category=SettingCategory.DATABASE,
            value_type="bool",
            default=True
        ),
    ])
    
    # إعدادات API
    SettingsManager.register_settings([
        Setting(
            key="api_rate_limit",
            name_ar="حد معدل API",
            name_en="API Rate Limit",
            description="حد معدل الطلبات في الثانية",
            category=SettingCategory.API,
            value_type="int",
            default=10,
            min_value=1,
            max_value=100
        ),
        Setting(
            key="api_timeout",
            name_ar="مهلة API",
            name_en="API Timeout",
            description="مهلة طلبات API بالثواني",
            category=SettingCategory.API,
            value_type="int",
            default=30,
            min_value=5,
            max_value=300
        ),
        Setting(
            key="wos_api_url",
            name_ar="رابط WOS API",
            name_en="WOS API URL",
            description="رابط API للعبة WOS",
            category=SettingCategory.API,
            value_type="str",
            default="https://wos-giftcode-api.centurygame.com"
        ),
        Setting(
            key="distribution_api_url",
            name_ar="رابط API التوزيع",
            name_en="Distribution API URL",
            description="رابط API للتوزيع",
            category=SettingCategory.API,
            value_type="str",
            default="http://gift-code-api.whiteout-bot.com"
        ),
    ])
    
    # إعدادات الصيانة
    SettingsManager.register_settings([
        Setting(
            key="maintenance_mode",
            name_ar="وضع الصيانة",
            name_en="Maintenance Mode",
            description="تفعيل وضع الصيانة",
            category=SettingCategory.MAINTENANCE,
            value_type="bool",
            default=False
        ),
        Setting(
            key="maintenance_message",
            name_ar="رسالة الصيانة",
            name_en="Maintenance Message",
            description="الرسالة المعروضة أثناء الصيانة",
            category=SettingCategory.MAINTENANCE,
            value_type="str",
            default="النظام قيد الصيانة حالياً. يرجى المحاولة لاحقاً."
        ),
        Setting(
            key="allowed_users_maintenance",
            name_ar="المستخدمون المسموح لهم",
            name_en="Allowed Users",
            description="معرفات المستخدمين المسموح لهم خلال الصيانة",
            category=SettingCategory.MAINTENANCE,
            value_type="list",
            default=[]
        ),
        Setting(
            key="debug_mode",
            name_ar="وضع التصحيح",
            name_en="Debug Mode",
            description="تفعيل وضع التصحيح",
            category=SettingCategory.MAINTENANCE,
            value_type="bool",
            default=False
        ),
    ])


# تهيئة الإعدادات عند استيراد الوحدة
_setup_default_settings()
