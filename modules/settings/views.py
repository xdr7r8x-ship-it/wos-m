"""
WOS-M Settings Module
© MANSOUR — WOS-M. All rights reserved.
"""
import discord
from core.bot import WOSMBot
from core.database import db
from core.permissions import has_permission, AuditCategory, audit_log


async def settings_general_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Display general bot settings."""
    if not await has_permission(interaction.user.id, "owner"):
        await interaction.response.send_message("❌ ليس لديك صلاحية.", ephemeral=True)
        return

    await interaction.response.send_message("⏳ جاري تحميل الإعدادات...", ephemeral=True)

    try:
        # Get all bot settings
        settings = await db.fetchall(
            "SELECT key, value, updated_at FROM bot_settings ORDER BY key"
        )

        # Get language settings
        language = await db.fetchone(
            "SELECT value FROM bot_settings WHERE key = 'language'"
        )
        default_lang = language["value"] if language and "value" in language.keys() else "ar"

        # Check demo mode
        demo_setting = await db.fetchone(
            "SELECT value FROM bot_settings WHERE key = 'demo_mode'"
        )
        demo_mode = demo_setting["value"] if demo_setting and "value" in demo_setting.keys() else "false"

        # Build embed
        embed = discord.Embed(
            title="⚙️ الإعدادات العامة",
            color=0x3498db
        )

        # Bot info (no secrets)
        embed.add_field(
            name="🤖 معلومات البوت",
            value=f"• **اللغة:** `{default_lang}`\n• **وضع التجربة:** `{demo_mode}`\n• **عدد الإعدادات:** `{len(settings) if settings else 0}`",
            inline=False
        )

        # Theme settings if exists
        theme_setting = await db.fetchone(
            "SELECT value FROM bot_settings WHERE key = 'theme'"
        )
        if theme_setting and "value" in theme_setting.keys():
            embed.add_field(
                name="🎨 الثيم",
                value=f"• **الثيم الحالي:** `{theme_setting['value']}`",
                inline=True
            )

        # Footer settings if exists
        footer_setting = await db.fetchone(
            "SELECT value FROM bot_settings WHERE key = 'footer_text'"
        )
        if footer_setting and "value" in footer_setting.keys():
            embed.add_field(
                name="📝 Footer",
                value=f"• **النص:** `{footer_setting['value']}`",
                inline=True
            )

        # List all settings keys (no values for security)
        if settings:
            settings_list = "\n".join([
                f"• `{s['key'] if 'key' in s.keys() else '—'}`" 
                for s in settings[:15]
            ])
            embed.add_field(
                name="📋 مفاتيح الإعدادات",
                value=settings_list + ("\n• ... والمزيد" if len(settings) > 15 else ""),
                inline=False
            )

        # Add back button
        from modules.owner_panel.views import owner_back_callback
        from core.views import ButtonCallback, DynamicView
        
        view = DynamicView(timeout=180)
        view.add_item(ButtonCallback(label="🔙 رجوع", callback=owner_back_callback))
        
        await interaction.edit_original_response(embed=embed, view=view)

    except Exception as e:
        await interaction.edit_original_response(
            content=f"❌ خطأ: {str(e)[:100]}",
            embed=None, view=None
        )


async def settings_api_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Display API configuration status."""
    if not await has_permission(interaction.user.id, "owner"):
        await interaction.response.send_message("❌ ليس لديك صلاحية.", ephemeral=True)
        return

    await interaction.response.send_message("⏳ جاري فحص API...", ephemeral=True)

    try:
        # Check API-related settings (keys only, never values)
        api_keys = await db.fetchall(
            "SELECT key FROM bot_settings WHERE key LIKE 'api_%' OR key LIKE 'token_%' OR key LIKE 'key_%'"
        )

        embed = discord.Embed(
            title="🔌 حالة API",
            color=0x3498db
        )

        # API configured status
        if api_keys and len(api_keys) > 0:
            configured = "\n".join([
                f"• `{k['key'] if 'key' in k.keys() else '—'}`" 
                for k in api_keys
            ])
            embed.add_field(
                name="✅ APIs مهيأة",
                value=configured,
                inline=False
            )
        else:
            embed.add_field(
                name="⚠️ APIs غير مهيأة",
                value="• لا توجد مفاتيح API مسجلة",
                inline=False
            )

        # Security notice
        embed.set_footer(text="🔒 القيم السرية مخفية لأمانك")

        # Add back button
        from modules.owner_panel.views import owner_back_callback
        from core.views import ButtonCallback, DynamicView
        
        view = DynamicView(timeout=180)
        view.add_item(ButtonCallback(label="🔙 رجوع", callback=owner_back_callback))
        
        await interaction.edit_original_response(embed=embed, view=view)

    except Exception as e:
        await interaction.edit_original_response(
            content=f"❌ خطأ: {str(e)[:100]}",
            embed=None, view=None
        )


async def settings_save_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Save a specific setting via modal."""
    if not await has_permission(interaction.user.id, "owner"):
        await interaction.response.send_message("❌ ليس لديك صلاحية.", ephemeral=True)
        return

    # Show modal for setting key and value
    class SettingsModal(discord.ui.Modal):
        def __init__(self):
            super().__init__(title="💾 حفظ إعداد")
            self.add_item(discord.ui.TextInput(
                label="مفتاح الإعداد",
                placeholder="مثال: language, theme, footer_text",
                required=True,
                max_length=100
            ))
            self.add_item(discord.ui.TextInput(
                label="القيمة",
                placeholder="القيمة الجديدة",
                required=True,
                max_length=500
            ))

        async def callback(self, interaction: discord.Interaction):
            key = self.children[0].value.strip()
            value = self.children[1].value.strip()

            if not key or not value:
                await interaction.response.send_message("❌ مفتاح وقيمة مطلوبان.", ephemeral=True)
                return

            # Block sensitive keys
            sensitive = ["token", "password", "secret", "key", "cookie", "session"]
            if any(s in key.lower() for s in sensitive):
                await interaction.response.send_message("❌ لا يمكن تغيير إعدادات سرية.", ephemeral=True)
                return

            try:
                # Save to database
                await db.execute(
                    "INSERT OR REPLACE INTO bot_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                    (key, value)
                )

                # Audit log
                await audit_log.log(
                    user_id=str(interaction.user.id),
                    user_name=interaction.user.name,
                    action=f"settings_save:{key}",
                    category=AuditCategory.SETTINGS,
                    details={"key": key, "value_length": len(value)}
                )

                await interaction.response.send_message(
                    f"✅ تم حفظ `{key}` بنجاح",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ خطأ في الحفظ: {str(e)[:100]}",
                    ephemeral=True
                )

    await interaction.response.send_modal(SettingsModal())


async def settings_reset_callback(bot: WOSMBot, interaction: discord.Interaction):
    """Reset settings with confirmation."""
    if not await has_permission(interaction.user.id, "owner"):
        await interaction.response.send_message("❌ ليس لديك صلاحية.", ephemeral=True)
        return

    # Show confirmation modal
    class ResetModal(discord.ui.Modal):
        def __init__(self):
            super().__init__(title="⚠️ تأكيد إعادة التعيين")
            self.add_item(discord.ui.TextInput(
                label="اكتب 'تأكيد' لإعادة تعيين الإعدادات",
                placeholder="تأكيد",
                required=True,
                max_length=10
            ))

        async def callback(self, interaction: discord.Interaction):
            if self.children[0].value.strip() != "تأكيد":
                await interaction.response.send_message("❌ لم يتم التأكيد.", ephemeral=True)
                return

            try:
                # Keep essential settings, reset others
                essential_keys = ["owner_id", "language"]
                settings = await db.fetchall("SELECT key, value FROM bot_settings")
                
                kept = []
                for s in (settings or []):
                    key = s["key"] if "key" in s.keys() else None
                    if key not in essential_keys:
                        await db.execute("DELETE FROM bot_settings WHERE key = ?", (key,))
                    else:
                        kept.append(key)

                # Audit log
                await audit_log.log(
                    user_id=str(interaction.user.id),
                    user_name=interaction.user.name,
                    action="settings_reset",
                    category=AuditCategory.SETTINGS,
                    details={"kept_keys": kept}
                )

                await interaction.response.send_message(
                    f"✅ تم إعادة تعيين الإعدادات\n🔒 kept: {', '.join(kept)}",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ خطأ: {str(e)[:100]}",
                    ephemeral=True
                )

    await interaction.response.send_modal(ResetModal())
