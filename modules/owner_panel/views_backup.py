"""
WOS-M Owner Panel Module
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
from views.base import BaseView, PageInfo, PaginationView
from views.buttons import ActionButton, BackButton, HomeButton
from views.selects import LanguageSelect, OwnerPanelSectionSelect, FeatureSelect


class OwnerPanelView(BaseView):
    """Owner panel main view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("owner_panel.title"),
                description=i18n.get("owner_panel.welcome"),
                icon="👑",
                color=0xe74c3c
            )
        )
        
        self.add_item(OwnerPanelSectionSelect())
        self.add_back_home_buttons()


class LanguageManagementView(BaseView):
    """Language management view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("owner_panel.language_management"),
                description="",
                icon="🌐",
                color=0x1abc9c
            )
        )
        
        self.add_item(LanguageSelect(i18n.current_locale))
        self.add_back_home_buttons()


class ButtonManagementView(BaseView):
    """Button management view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("owner_panel.button_management"),
                description="",
                icon="🔘",
                color=0x3498db
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        """Add management buttons."""
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.add_button"),
            custom_id="btn_add",
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.edit_button_name"),
            custom_id="btn_edit_name",
            style=discord.ButtonStyle.primary,
            emoji="✏️",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.edit_button_icon"),
            custom_id="btn_edit_icon",
            style=discord.ButtonStyle.primary,
            emoji="🔣",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.edit_button_order"),
            custom_id="btn_edit_order",
            style=discord.ButtonStyle.primary,
            emoji="📊",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.enable_button"),
            custom_id="btn_enable",
            style=discord.ButtonStyle.success,
            emoji="✅",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.disable_button"),
            custom_id="btn_disable",
            style=discord.ButtonStyle.danger,
            emoji="❌",
            row=1
        ))


class TextManagementView(BaseView):
    """Text management view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("owner_panel.text_management"),
                description="",
                icon="📝",
                color=0xf39c12
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        """Add management buttons."""
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.edit_title"),
            custom_id="text_edit_title",
            style=discord.ButtonStyle.primary,
            emoji="📌",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.edit_description"),
            custom_id="text_edit_desc",
            style=discord.ButtonStyle.primary,
            emoji="📄",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.edit_messages"),
            custom_id="text_edit_msg",
            style=discord.ButtonStyle.primary,
            emoji="💬",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.reset_texts"),
            custom_id="text_reset",
            style=discord.ButtonStyle.danger,
            emoji="🔄",
            row=1
        ))


class IconManagementView(BaseView):
    """Icon management view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("owner_panel.icon_management"),
                description="",
                icon="🎨",
                color=0x9b59b6
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        """Add management buttons."""
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.edit_section_icon"),
            custom_id="icon_section",
            style=discord.ButtonStyle.primary,
            emoji="📁",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.edit_button_icon_manage"),
            custom_id="icon_button",
            style=discord.ButtonStyle.primary,
            emoji="🔘",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.edit_status_icon"),
            custom_id="icon_status",
            style=discord.ButtonStyle.primary,
            emoji="📊",
            row=0
        ))


class BrandingManagementView(BaseView):
    """Branding management view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("owner_panel.branding_management"),
                description="",
                icon="🎨",
                color=0xe91e63
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        """Add management buttons."""
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.change_bot_name"),
            custom_id="brand_name",
            style=discord.ButtonStyle.primary,
            emoji="🤖",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.change_colors"),
            custom_id="brand_colors",
            style=discord.ButtonStyle.primary,
            emoji="🎨",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.save_theme"),
            custom_id="brand_save",
            style=discord.ButtonStyle.success,
            emoji="💾",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.reset_theme"),
            custom_id="brand_reset",
            style=discord.ButtonStyle.danger,
            emoji="🔄",
            row=1
        ))


class FeatureManagementView(BaseView):
    """Feature management view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("owner_panel.feature_management"),
                description="",
                icon="⚙️",
                color=0x34495e
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        """Add management buttons."""
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.add_feature"),
            custom_id="feat_add",
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.edit_feature"),
            custom_id="feat_edit",
            style=discord.ButtonStyle.primary,
            emoji="✏️",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.enable_feature"),
            custom_id="feat_enable",
            style=discord.ButtonStyle.success,
            emoji="✅",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.disable_feature"),
            custom_id="feat_disable",
            style=discord.ButtonStyle.danger,
            emoji="❌",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.link_feature"),
            custom_id="feat_link",
            style=discord.ButtonStyle.primary,
            emoji="🔗",
            row=2
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("owner_panel.feature_registry"),
            custom_id="feat_registry",
            style=discord.ButtonStyle.secondary,
            emoji="📦",
            row=2
        ))


# Callbacks
async def owner_panel_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for owner panel."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.OWNER):
        await interaction.response.send_message(
            i18n.get("messages.no_permission"),
            ephemeral=True
        )
        return
    
    view = OwnerPanelView(bot, interaction.user.id)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    await audit_log.log(
        user_id=str(interaction.user.id),
        user_name=str(interaction.user),
        action="view_owner_panel",
        category=AuditCategory.OWNER_PANEL
    )


async def language_management_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for language management."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.OWNER):
        await interaction.response.send_message(
            i18n.get("messages.no_permission"),
            ephemeral=True
        )
        return
    
    view = LanguageManagementView(bot, interaction.user.id)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def button_management_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for button management."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.OWNER):
        await interaction.response.send_message(
            i18n.get("messages.no_permission"),
            ephemeral=True
        )
        return
    
    view = ButtonManagementView(bot, interaction.user.id)
    embed = view.create_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def text_management_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Text management callback."""
    from views.base import BaseView, PageInfo
    from views.buttons import ActionButton
    from views.selects import TextTypeSelect

    class TextManagementView(BaseView):
        def __init__(self, bot, user_id):
            self.bot = bot
            super().__init__(user_id=user_id, page_info=PageInfo(
                title="📝 إدارة النصوص",
                description="إدارة نصوص البوت",
                icon="📝",
                color=0x3498db
            ))
            self._add_items()
            self.add_back_home_buttons()

        def _add_items(self):
            self.add_item(TextTypeSelect())

    view = TextManagementView(bot, interaction.user.id)
    embed = view.create_embed()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def icon_management_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Icon management callback."""
    from views.base import BaseView, PageInfo
    from views.buttons import ActionButton
    from views.selects import IconTypeSelect

    class IconManagementView(BaseView):
        def __init__(self, bot, user_id):
            self.bot = bot
            super().__init__(user_id=user_id, page_info=PageInfo(
                title="🖼️ إدارة الأيقونات",
                description="إدارة أيقونات الأزرار",
                icon="🖼️",
                color=0x9b59b6
            ))
            self._add_items()
            self.add_back_home_buttons()

        def _add_items(self):
            self.add_item(IconTypeSelect())

    view = IconManagementView(bot, interaction.user.id)
    embed = view.create_embed()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def branding_management_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Branding management callback."""
    from views.base import BaseView, PageInfo
    from views.buttons import ActionButton
    from views.selects import BrandingTypeSelect

    class BrandingManagementView(BaseView):
        def __init__(self, bot, user_id):
            self.bot = bot
            super().__init__(user_id=user_id, page_info=PageInfo(
                title="🎨 إدارة الهوية",
                description="إدارة هوية البوت",
                icon="🎨",
                color=0xe74c3c
            ))
            self._add_items()
            self.add_back_home_buttons()

        def _add_items(self):
            self.add_item(BrandingTypeSelect())

    view = BrandingManagementView(bot, interaction.user.id)
    embed = view.create_embed()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def feature_management_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Feature management callback."""
    from views.base import BaseView, PageInfo
    from views.buttons import ActionButton
    from views.selects import FeatureSelect

    class FeatureManagementView(BaseView):
        def __init__(self, bot, user_id):
            self.bot = bot
            super().__init__(user_id=user_id, page_info=PageInfo(
                title="⚡ إدارة الميزات",
                description="تفعيل وإيقاف الميزات",
                icon="⚡",
                color=0xf39c12
            ))
            self._add_items()
            self.add_back_home_buttons()

        def _add_items(self):
            self.add_item(FeatureSelect())

    view = FeatureManagementView(bot, interaction.user.id)
    embed = view.create_embed()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def text_edit_desc_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle text_edit_desc button."""
    embed = discord.Embed(title="📝 تعديل الوصف", description="تم فتح نموذج تعديل الوصف.", color=0x3498db)
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def text_edit_msg_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle text_edit_msg button."""
    embed = discord.Embed(title="💬 تعديل الرسائل", description="تم فتح نموذج تعديل الرسائل.", color=0x3498db)
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def text_reset_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle text_reset button."""
    embed = discord.Embed(title="🔄 إعادة تعيين النصوص", description="تم إعادة تعيين النصوص.", color=0x3498db)
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def icon_button_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle icon_button button."""
    embed = discord.Embed(title="🔘 أيقونات الأزرار", description="تم فتح قائمة أيقونات الأزرار.", color=0x9b59b6)
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def icon_section_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle icon_section button."""
    embed = discord.Embed(title="📂 أيقونات الأقسام", description="تم فتح قائمة أيقونات الأقسام.", color=0x9b59b6)
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def icon_status_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle icon_status button."""
    embed = discord.Embed(title="📊 أيقونات الحالة", description="تم فتح قائمة أيقونات الحالة.", color=0x9b59b6)
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def brand_name_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle brand_name button."""
    embed = discord.Embed(title="🏷️ اسم العلامة", description="تم فتح نموذج اسم العلامة.", color=0xe74c3c)
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def brand_colors_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle brand_colors button."""
    embed = discord.Embed(title="🎨 الألوان", description="تم فتح نموذج الألوان.", color=0xe74c3c)
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def brand_save_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle brand_save button."""
    embed = discord.Embed(title="💾 حفظ", description="تم حفظ التغييرات.", color=0xe74c3c)
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def brand_reset_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle brand_reset button."""
    embed = discord.Embed(title="🔄 إعادة تعيين", description="تم إعادة تعيين الهوية.", color=0xe74c3c)
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def feat_add_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle feat_add button."""
    embed = discord.Embed(title="➕ إضافة ميزة", description="تم فتح نموذج إضافة ميزة.", color=0xf39c12)
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def feat_edit_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle feat_edit button."""
    embed = discord.Embed(title="✏️ تعديل ميزة", description="تم فتح نموذج تعديل ميزة.", color=0xf39c12)
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def feat_enable_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle feat_enable button."""
    embed = discord.Embed(title="✅ تفعيل", description="تم تفعيل الميزة.", color=0xf39c12)
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def feat_disable_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle feat_disable button."""
    embed = discord.Embed(title="❌ إيقاف", description="تم إيقاف الميزة.", color=0xf39c12)
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def feat_link_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle feat_link button."""
    embed = discord.Embed(title="🔗 ربط", description="تم فتح نموذج الربط.", color=0xf39c12)
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def feat_registry_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Handle feat_registry button."""
    embed = discord.Embed(title="📋 السجل", description="تم فتح سجل الميزات.", color=0xf39c12)
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def perm_list_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for perm_list - Display all permissions."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    await interaction.response.send_message("⏳ جاري تحميل قائمة الصلاحيات...", ephemeral=True)
    
    try:
        # Get all permission levels
        perm_levels = [
            (PermissionLevel.OWNER, "👑 المالك"),
            (PermissionLevel.GLOBAL_ADMIN, "🔧 مدير عام"),
            (PermissionLevel.ALLIANCE_ADMIN, "⚔️ مدير تحالف"),
            (PermissionLevel.MODERATOR, "🛡️ مشرف"),
            (PermissionLevel.MEMBER, "👤 عضو"),
        ]
        
        embed = discord.Embed(
            title="📋 قائمة الصلاحيات",
            description="مستويات الصلاحيات المتاحة في النظام",
            color=0xf39c12
        )
        
        for level, name in perm_levels:
            desc = _get_permission_description(level)
            embed.add_field(name=name, value=desc, inline=False)
        
        embed.set_footer(text="WOS-M • Owner Panel")
        
        await interaction.edit_original_response(embed=embed)
        
        await audit_log.log(
            user_id=str(interaction.user.id),
            user_name=str(interaction.user),
            action="view_permissions_list",
            category=AuditCategory.PERMISSIONS
        )
        
    except Exception:
        import logging
        logging.exception("perm_list failed")
        await interaction.edit_original_response(
            content="❌ حدث خطأ أثناء تحميل قائمة الصلاحيات"
        )


async def perm_assign_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for perm_assign - Assign a permission level to a user."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    class PermAssignModal(ui.Modal, title="تعيين صلاحية"):
        user_id_input = ui.TextInput(
            label="معرف المستخدم (Discord ID)",
            placeholder="مثال: 123456789012345678",
            required=True,
            min_length=17,
            max_length=20
        )
        level_input = ui.TextInput(
            label="مستوى الصلاحية",
            placeholder="owner, global_admin, alliance_admin, moderator, member",
            required=True
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            try:
                target_user_id = self.user_id_input.value.strip()
                level_name = self.level_input.value.strip().lower()
                
                # Validate level
                level_map = {
                    "owner": PermissionLevel.OWNER,
                    "global_admin": PermissionLevel.GLOBAL_ADMIN,
                    "alliance_admin": PermissionLevel.ALLIANCE_ADMIN,
                    "moderator": PermissionLevel.MODERATOR,
                    "member": PermissionLevel.MEMBER,
                }
                
                if level_name not in level_map:
                    await interaction.response.send_message(
                        f"❌ مستوى الصلاحية غير صالح: `{level_name}`",
                        ephemeral=True
                    )
                    return
                
                new_level = level_map[level_name]
                
                # Assign permission
                await guard.assign_permission(target_user_id, new_level)
                
                await interaction.response.send_message(
                    f"✅ تم تعيين الصلاحية `{new_level.name}` للمستخدم `{target_user_id}`",
                    ephemeral=True
                )
                
                await audit_log.log(
                    user_id=str(interaction.user.id),
                    user_name=str(interaction.user),
                    action=f"assign_permission:{target_user_id}:{new_level.name}",
                    category=AuditCategory.PERMISSIONS,
                    details={"target_user": target_user_id, "new_level": new_level.name}
                )
                
            except Exception:
                import logging
                logging.exception("perm_assign failed")
                await interaction.response.send_message(
                    "❌ حدث خطأ أثناء تعيين الصلاحية",
                    ephemeral=True
                )
        
        async def on_error(self, interaction: discord.Interaction, error: Exception):
            import logging
            logging.exception("perm_assign modal error")
            try:
                await interaction.response.send_message(
                    f"❌ خطأ: {str(error)[:100]}",
                    ephemeral=True
                )
            except:
                pass
    
    await interaction.response.send_modal(PermAssignModal())


async def perm_remove_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for perm_remove - Remove a user's permission."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    class PermRemoveModal(ui.Modal, title="إزالة صلاحية"):
        user_id_input = ui.TextInput(
            label="معرف المستخدم (Discord ID)",
            placeholder="مثال: 123456789012345678",
            required=True,
            min_length=17,
            max_length=20
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            try:
                target_user_id = self.user_id_input.value.strip()
                
                # Remove all permissions for this user
                await guard.revoke_permission(target_user_id, PermissionLevel.MEMBER)
                await guard.revoke_permission(target_user_id, PermissionLevel.MODERATOR)
                await guard.revoke_permission(target_user_id, PermissionLevel.ALLIANCE_ADMIN)
                await guard.revoke_permission(target_user_id, PermissionLevel.GLOBAL_ADMIN)
                await guard.revoke_permission(target_user_id, PermissionLevel.OWNER)
                
                await interaction.response.send_message(
                    f"✅ تم إزالة جميع الصلاحيات من المستخدم `{target_user_id}`",
                    ephemeral=True
                )
                
                await audit_log.log(
                    user_id=str(interaction.user.id),
                    user_name=str(interaction.user),
                    action=f"remove_permission:{target_user_id}",
                    category=AuditCategory.PERMISSIONS,
                    details={"target_user": target_user_id}
                )
                
            except Exception:
                import logging
                logging.exception("perm_remove failed")
                await interaction.response.send_message(
                    "❌ حدث خطأ أثناء إزالة الصلاحية",
                    ephemeral=True
                )
        
        async def on_error(self, interaction: discord.Interaction, error: Exception):
            import logging
            logging.exception("perm_remove modal error")
            try:
                await interaction.response.send_message(
                    f"❌ خطأ: {str(error)[:100]}",
                    ephemeral=True
                )
            except:
                pass
    
    await interaction.response.send_modal(PermRemoveModal())


async def perm_transfer_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for perm_transfer - Transfer ownership to another user."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.OWNER):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    class PermTransferModal(ui.Modal, title="نقل الملكية"):
        new_owner_input = ui.TextInput(
            label="معرف المستخدم الجديد (Discord ID)",
            placeholder="مثال: 123456789012345678",
            required=True,
            min_length=17,
            max_length=20
        )
        confirm_input = ui.TextInput(
            label="اكتب 'تأكيد' لنقل الملكية",
            placeholder="تأكيد",
            required=True,
            min_length=4,
            max_length=10
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            try:
                if self.confirm_input.value.strip() != "تأكيد":
                    await interaction.response.send_message(
                        "❌ يجب كتابة 'تأكيد' لنقل الملكية",
                        ephemeral=True
                    )
                    return
                
                new_owner_id = self.new_owner_input.value.strip()
                current_owner_id = str(interaction.user.id)
                
                # Remove owner from current user
                await guard.revoke_permission(current_owner_id, PermissionLevel.OWNER)
                
                # Assign owner to new user
                await guard.assign_permission(new_owner_id, PermissionLevel.OWNER)
                
                await interaction.response.send_message(
                    f"✅ تم نقل الملكية بنجاح إلى المستخدم `{new_owner_id}`",
                    ephemeral=True
                )
                
                await audit_log.log(
                    user_id=current_owner_id,
                    user_name=str(interaction.user),
                    action=f"transfer_ownership:{new_owner_id}",
                    category=AuditCategory.PERMISSIONS,
                    details={"old_owner": current_owner_id, "new_owner": new_owner_id}
                )
                
            except Exception:
                import logging
                logging.exception("perm_transfer failed")
                await interaction.response.send_message(
                    "❌ حدث خطأ أثناء نقل الملكية",
                    ephemeral=True
                )
        
        async def on_error(self, interaction: discord.Interaction, error: Exception):
            import logging
            logging.exception("perm_transfer modal error")
            try:
                await interaction.response.send_message(
                    f"❌ خطأ: {str(error)[:100]}",
                    ephemeral=True
                )
            except:
                pass
    
    await interaction.response.send_modal(PermTransferModal())


async def perm_audit_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for perm_audit - View permission audit log."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    await interaction.response.send_message("⏳ جاري تحميل سجل الصلاحيات...", ephemeral=True)
    
    try:
        # Get audit logs for permissions
        logs = await audit_log.get_logs_by_category(AuditCategory.PERMISSIONS, limit=20)
        
        embed = discord.Embed(
            title="📜 سجل الصلاحيات",
            description="آخر 20 إجراء في سجل الصلاحيات",
            color=0xf39c12
        )
        
        if not logs:
            embed.description = "لا توجد سجلات للصلاحيات"
        else:
            for log in logs:
                timestamp = log.get("created_at", "غير معروف")
                action = log.get("action", "غير معروف")
                user = log.get("user_name", "غير معروف")
                embed.add_field(
                    name=f"⏰ {timestamp}",
                    value=f"**إجراء:** {action}\n**مستخدم:** {user}",
                    inline=False
                )
        
        embed.set_footer(text="WOS-M • Owner Panel")
        
        await interaction.edit_original_response(embed=embed)
        
        await audit_log.log(
            user_id=str(interaction.user.id),
            user_name=str(interaction.user),
            action="view_permissions_audit",
            category=AuditCategory.PERMISSIONS
        )
        
    except Exception:
        import logging
        logging.exception("perm_audit failed")
        await interaction.edit_original_response(
            content="❌ حدث خطأ أثناء تحميل سجل الصلاحيات"
        )


async def btn_add_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for btn_add - Add a new button."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    class AddButtonModal(ui.Modal, title="إضافة زر جديد"):
        label_input = ui.TextInput(
            label="اسم الزر",
            placeholder="مثال: لوحة المراقبة",
            required=True,
            min_length=1,
            max_length=80
        )
        custom_id_input = ui.TextInput(
            label="معرف الزر (custom_id)",
            placeholder="مثال: dashboard_btn",
            required=True,
            min_length=1,
            max_length=50
        )
        emoji_input = ui.TextInput(
            label="الإيموجي (اختياري)",
            placeholder="مثال: 📊",
            required=False
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            try:
                label = self.label_input.value.strip()
                custom_id = self.custom_id_input.value.strip()
                emoji = self.emoji_input.value.strip() if self.emoji_input.value else None
                
                # Store button config in database
                await db.execute("""
                    INSERT OR REPLACE INTO button_configs 
                    (custom_id, label, emoji, enabled, created_by, created_at)
                    VALUES (?, ?, ?, 1, ?, datetime('now'))
                """, (custom_id, label, emoji, str(interaction.user.id)))
                
                await interaction.response.send_message(
                    f"✅ تم إضافة الزر `{label}` بالمعرف `{custom_id}`",
                    ephemeral=True
                )
                
                await audit_log.log(
                    user_id=str(interaction.user.id),
                    user_name=str(interaction.user),
                    action=f"add_button:{custom_id}",
                    category=AuditCategory.BUTTON_MANAGEMENT,
                    details={"label": label, "custom_id": custom_id}
                )
                
            except Exception:
                import logging
                logging.exception("btn_add failed")
                await interaction.response.send_message(
                    "❌ حدث خطأ أثناء إضافة الزر",
                    ephemeral=True
                )
        
        async def on_error(self, interaction: discord.Interaction, error: Exception):
            import logging
            logging.exception("btn_add modal error")
            try:
                await interaction.response.send_message(
                    f"❌ خطأ: {str(error)[:100]}",
                    ephemeral=True
                )
            except:
                pass
    
    await interaction.response.send_modal(AddButtonModal())


async def btn_edit_name_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for btn_edit_name - Edit button name."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    class EditButtonNameModal(ui.Modal, title="تعديل اسم الزر"):
        custom_id_input = ui.TextInput(
            label="معرف الزر الحالي",
            placeholder="مثال: dashboard_btn",
            required=True
        )
        new_label_input = ui.TextInput(
            label="الاسم الجديد",
            placeholder="مثال: لوحة التحكم",
            required=True,
            min_length=1,
            max_length=80
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            try:
                custom_id = self.custom_id_input.value.strip()
                new_label = self.new_label_input.value.strip()
                
                # Update button label
                result = await db.execute("""
                    UPDATE button_configs SET label = ? WHERE custom_id = ?
                """, (new_label, custom_id))
                
                if result:
                    await interaction.response.send_message(
                        f"✅ تم تغيير اسم الزر `{custom_id}` إلى `{new_label}`",
                        ephemeral=True
                    )
                    
                    await audit_log.log(
                        user_id=str(interaction.user.id),
                        user_name=str(interaction.user),
                        action=f"edit_button_name:{custom_id}",
                        category=AuditCategory.BUTTON_MANAGEMENT,
                        details={"new_label": new_label}
                    )
                else:
                    await interaction.response.send_message(
                        f"❌ لم يتم العثور على الزر `{custom_id}`",
                        ephemeral=True
                    )
                
            except Exception:
                import logging
                logging.exception("btn_edit_name failed")
                await interaction.response.send_message(
                    "❌ حدث خطأ أثناء تعديل اسم الزر",
                    ephemeral=True
                )
        
        async def on_error(self, interaction: discord.Interaction, error: Exception):
            import logging
            logging.exception("btn_edit_name modal error")
            try:
                await interaction.response.send_message(
                    f"❌ خطأ: {str(error)[:100]}",
                    ephemeral=True
                )
            except:
                pass
    
    await interaction.response.send_modal(EditButtonNameModal())


async def btn_edit_icon_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for btn_edit_icon - Edit button icon/emoji."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    class EditButtonIconModal(ui.Modal, title="تعديل أيقونة الزر"):
        custom_id_input = ui.TextInput(
            label="معرف الزر",
            placeholder="مثال: dashboard_btn",
            required=True
        )
        new_emoji_input = ui.TextInput(
            label="الإيموجي الجديد",
            placeholder="مثال: 🎯",
            required=True,
            min_length=1,
            max_length=32
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            try:
                custom_id = self.custom_id_input.value.strip()
                new_emoji = self.new_emoji_input.value.strip()
                
                # Update button emoji
                await db.execute("""
                    UPDATE button_configs SET emoji = ? WHERE custom_id = ?
                """, (new_emoji, custom_id))
                
                await interaction.response.send_message(
                    f"✅ تم تغيير أيقونة الزر `{custom_id}` إلى `{new_emoji}`",
                    ephemeral=True
                )
                
                await audit_log.log(
                    user_id=str(interaction.user.id),
                    user_name=str(interaction.user),
                    action=f"edit_button_icon:{custom_id}",
                    category=AuditCategory.BUTTON_MANAGEMENT,
                    details={"new_emoji": new_emoji}
                )
                
            except Exception:
                import logging
                logging.exception("btn_edit_icon failed")
                await interaction.response.send_message(
                    "❌ حدث خطأ أثناء تعديل أيقونة الزر",
                    ephemeral=True
                )
        
        async def on_error(self, interaction: discord.Interaction, error: Exception):
            import logging
            logging.exception("btn_edit_icon modal error")
            try:
                await interaction.response.send_message(
                    f"❌ خطأ: {str(error)[:100]}",
                    ephemeral=True
                )
            except:
                pass
    
    await interaction.response.send_modal(EditButtonIconModal())


async def btn_edit_order_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for btn_edit_order - Edit button display order."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    class EditButtonOrderModal(ui.Modal, title="تعديل ترتيب الزر"):
        custom_id_input = ui.TextInput(
            label="معرف الزر",
            placeholder="مثال: dashboard_btn",
            required=True
        )
        row_input = ui.TextInput(
            label="الصف (0-4)",
            placeholder="0",
            required=True
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            try:
                custom_id = self.custom_id_input.value.strip()
                row = int(self.row_input.value.strip())
                
                if row < 0 or row > 4:
                    await interaction.response.send_message(
                        "❌ الصف يجب أن يكون بين 0 و 4",
                        ephemeral=True
                    )
                    return
                
                # Update button row
                await db.execute("""
                    UPDATE button_configs SET row_position = ? WHERE custom_id = ?
                """, (row, custom_id))
                
                await interaction.response.send_message(
                    f"✅ تم نقل الزر `{custom_id}` إلى الصف {row}",
                    ephemeral=True
                )
                
                await audit_log.log(
                    user_id=str(interaction.user.id),
                    user_name=str(interaction.user),
                    action=f"edit_button_order:{custom_id}",
                    category=AuditCategory.BUTTON_MANAGEMENT,
                    details={"row": row}
                )
                
            except ValueError:
                await interaction.response.send_message(
                    "❌ الصف يجب أن يكون رقماً",
                    ephemeral=True
                )
            except Exception:
                import logging
                logging.exception("btn_edit_order failed")
                await interaction.response.send_message(
                    "❌ حدث خطأ أثناء تعديل ترتيب الزر",
                    ephemeral=True
                )
        
        async def on_error(self, interaction: discord.Interaction, error: Exception):
            import logging
            logging.exception("btn_edit_order modal error")
            try:
                await interaction.response.send_message(
                    f"❌ خطأ: {str(error)[:100]}",
                    ephemeral=True
                )
            except:
                pass
    
    await interaction.response.send_modal(EditButtonOrderModal())


async def btn_enable_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for btn_enable - Enable a button."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    await interaction.response.send_message("⏳ جاري تفعيل الزر...", ephemeral=True)
    
    try:
        # Get disabled buttons
        buttons = await db.fetchall("""
            SELECT custom_id, label FROM button_configs WHERE enabled = 0
        """)
        
        if not buttons:
            await interaction.edit_original_response(
                content="✅ لا توجد أزرار معطلة"
            )
            return
        
        embed = discord.Embed(
            title="🔘 تفعيل زر",
            description="الأزرار المعطلة حالياً:",
            color=0x2ecc71
        )
        
        for btn in buttons[:10]:
            embed.add_field(
                name=btn.get("label", "غير معروف"),
                value=f"`{btn.get('custom_id')}`",
                inline=True
            )
        
        embed.add_field(
            name="📝", 
            value="اكتب معرف الزر لتفعيله",
            inline=False
        )
        
        await interaction.edit_original_response(embed=embed)
        
        await audit_log.log(
            user_id=str(interaction.user.id),
            user_name=str(interaction.user),
            action="view_disabled_buttons",
            category=AuditCategory.BUTTON_MANAGEMENT
        )
        
    except Exception:
        import logging
        logging.exception("btn_enable failed")
        await interaction.edit_original_response(
            content="❌ حدث خطأ أثناء تفعيل الزر"
        )


async def btn_disable_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for btn_disable - Disable a button."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    await interaction.response.send_message("⏳ جاري تعطيل الزر...", ephemeral=True)
    
    try:
        # Get enabled buttons
        buttons = await db.fetchall("""
            SELECT custom_id, label FROM button_configs WHERE enabled = 1
        """)
        
        if not buttons:
            await interaction.edit_original_response(
                content="❌ لا توجد أزرار مفعلة لتعطيلها"
            )
            return
        
        embed = discord.Embed(
            title="🔘 تعطيل زر",
            description="الأزرار المفعلة حالياً:",
            color=0xe74c3c
        )
        
        for btn in buttons[:10]:
            embed.add_field(
                name=btn.get("label", "غير معروف"),
                value=f"`{btn.get('custom_id')}`",
                inline=True
            )
        
        embed.add_field(
            name="📝", 
            value="اكتب معرف الزر لتعطيله",
            inline=False
        )
        
        await interaction.edit_original_response(embed=embed)
        
        await audit_log.log(
            user_id=str(interaction.user.id),
            user_name=str(interaction.user),
            action="view_enabled_buttons",
            category=AuditCategory.BUTTON_MANAGEMENT
        )
        
    except Exception:
        import logging
        logging.exception("btn_disable failed")
        await interaction.edit_original_response(
            content="❌ حدث خطأ أثناء تعطيل الزر"
        )


async def text_edit_title_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Callback for text_edit_title - Edit panel title."""
    guard = PermissionGuard(bot)
    
    if not await guard.has_permission(str(interaction.user.id), PermissionLevel.GLOBAL_ADMIN):
        await interaction.response.send_message(i18n.get("messages.no_permission"), ephemeral=True)
        return
    
    class EditTitleModal(ui.Modal, title="تعديل العنوان"):
        new_title_input = ui.TextInput(
            label="العنوان الجديد",
            placeholder="مثال: لوحة تحكم WOS-M",
            required=True,
            min_length=1,
            max_length=100
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            try:
                new_title = self.new_title_input.value.strip()
                
                # Save to database
                await db.execute("""
                    INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('panel_title', ?)
                """, (new_title,))
                
                await interaction.response.send_message(
                    f"✅ تم تغيير العنوان إلى `{new_title}`",
                    ephemeral=True
                )
                
                await audit_log.log(
                    user_id=str(interaction.user.id),
                    user_name=str(interaction.user),
                    action="edit_panel_title",
                    category=AuditCategory.TEXT_MANAGEMENT,
                    details={"new_title": new_title}
                )
                
            except Exception:
                import logging
                logging.exception("text_edit_title failed")
                await interaction.response.send_message(
                    "❌ حدث خطأ أثناء تعديل العنوان",
                    ephemeral=True
                )
        
        async def on_error(self, interaction: discord.Interaction, error: Exception):
            import logging
            logging.exception("text_edit_title modal error")
            try:
                await interaction.response.send_message(
                    f"❌ خطأ: {str(error)[:100]}",
                    ephemeral=True
                )
            except:
                pass
    
    await interaction.response.send_modal(EditTitleModal())


def _get_permission_description(level: PermissionLevel) -> str:
    """Get description for a permission level."""
    descriptions = {
        PermissionLevel.OWNER: "التحكم الكامل بالنظام، بما في ذلك نقل الملكية",
        PermissionLevel.GLOBAL_ADMIN: "إدارة جميع المستخدمين والتحالفات والإعدادات العامة",
        PermissionLevel.ALLIANCE_ADMIN: "إدارة التحالف وإعداداته وأعضائه",
        PermissionLevel.MODERATOR: "إشراف على المحتوى وإدارة المحتوى المخالف",
        PermissionLevel.MEMBER: "الوصول الأساسي للنظام",
    }
    return descriptions.get(level, "غير معروف")
