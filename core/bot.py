"""
WOS-M Bot Core
© MANSOUR — WOS-M. All rights reserved.
"""
import discord
from discord import app_commands
import asyncio
import logging
from typing import Optional

from config.settings import settings
from core.database import db
from core.i18n import i18n
from core.permissions import PermissionGuard, PermissionLevel
from core.process_queue import ProcessQueue
from core.audit_log import audit_log, AuditCategory
from core.feature_registry import FeatureRegistry, feature_registry

logger = logging.getLogger(__name__)


class WOSMBot(discord.Client):
    """Main WOS-M bot class."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(intents=intents)
        
        self.owner_id = settings.bot.owner_id
        self.owner_name = settings.bot.owner_name
        self.owner_discord = settings.bot.owner_discord
        self.tree = app_commands.CommandTree(self)
        
        self.process_queue: Optional[ProcessQueue] = None
        self.feature_registry: Optional[FeatureRegistry] = None
        
        self._button_callbacks = {}
        self._select_callbacks = {}
        
        self._setup_button_callbacks()
        self._setup_select_callbacks()
    
    def _setup_button_callbacks(self):
        """Setup button interaction callbacks."""
        self._button_callbacks = {
            "nav_back": self._handle_back,
            "nav_home": self._handle_home,
            "nav_close": self._handle_close,
            "dash_alliances": self._handle_alliances,
            "dash_players": self._handle_players,
            "dash_gift_codes": self._handle_gift_codes,
            "dash_events": self._handle_events,
            "dash_attendance": self._handle_attendance,
            "dash_bear_tracking": self._handle_bear_tracking,
            "dash_ministers": self._handle_ministers,
            "dash_notifications": self._handle_notifications,
            "dash_themes": self._handle_themes,
            "dash_permissions": self._handle_permissions,
            "dash_maintenance": self._handle_maintenance,
            "dash_owner_panel": self._handle_owner_panel,
            "dash_language": self._handle_language,
            "dash_settings": self._handle_settings,
            # Gift codes
            "gift_add": self._handle_gift_add,
            "gift_redeem_single": self._handle_gift_redeem_single,
            "gift_batch": self._handle_gift_batch,
            "gift_redeem_alliance": self._handle_gift_redeem_alliance,
            "gift_auto": self._handle_gift_auto,
            "gift_report": self._handle_gift_report,
            # Auto redeem
            "auto_enable_alliance": self._handle_auto_enable_alliance,
            "auto_disable_alliance": self._handle_auto_disable_alliance,
            "auto_redeem_all": self._handle_auto_redeem_all,
            # Owner panel
            "owner_panel_language": self._handle_owner_language,
            "owner_panel_buttons": self._handle_owner_buttons,
            "owner_panel_texts": self._handle_owner_texts,
            "owner_panel_icons": self._handle_owner_icons,
            "owner_panel_branding": self._handle_owner_branding,
            "owner_panel_features": self._handle_owner_features,
            # Confirmation
            "confirm_btn": self._handle_confirm,
            "cancel_btn": self._handle_cancel,
        }
    
    def _setup_select_callbacks(self):
        """Setup select menu interaction callbacks."""
        self._select_callbacks = {
            "language_select": self._handle_language_select,
            "owner_panel_section_select": self._handle_owner_section_select,
            "alliance_select_enable": self._handle_alliance_select_enable,
            "alliance_select_disable": self._handle_alliance_select_disable,
        }
    
    async def setup_hook(self):
        """Setup hook called when bot is ready."""
        logger.info("Setting up WOS-M...")
        
        # Initialize database
        await db.initialize()
        logger.info("Database initialized")
        
        # Initialize i18n
        await i18n.initialize(db.connection)
        logger.info(f"i18n initialized with locale: {i18n.current_locale}")
        
        # Initialize feature registry
        self.feature_registry = FeatureRegistry(self)
        await self.feature_registry.load_features()
        global feature_registry
        feature_registry = self.feature_registry
        logger.info("Feature registry loaded")
        
        # Initialize process queue
        self.process_queue = ProcessQueue(self)
        await self.process_queue.start()
        logger.info("Process queue started")
        
        # Register slash commands
        await self._register_commands()
        
        # Sync commands
        await self.tree.sync()
        logger.info("Commands synced")
        
        logger.info(f"WOS-M is ready! Owner: {self.owner_name} ({self.owner_discord})")
    
    async def _register_commands(self):
        """Register slash commands."""
        # Clear existing commands
        self.tree.clear_commands(guild=None)
        
        @self.tree.command(
            name="wos",
            description="WOS-M Main Dashboard"
        )
        async def wos_command(interaction: discord.Interaction):
            """Main WOS-M command."""
            from modules.dashboard.views import dashboard_callback
            await dashboard_callback(self, interaction)
    
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle all interactions."""
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            
            # Handle button callbacks
            if custom_id in self._button_callbacks:
                callback = self._button_callbacks[custom_id]
                await callback(interaction)
            
            # Handle select callbacks
            elif "select" in custom_id:
                for key, callback in self._select_callbacks.items():
                    if key in custom_id:
                        await callback(interaction)
                        break
    
    # Button handlers
    async def _handle_back(self, interaction: discord.Interaction):
        """Handle back button."""
        await interaction.response.defer()
    
    async def _handle_home(self, interaction: discord.Interaction):
        """Handle home button."""
        from modules.dashboard.views import dashboard_callback
        await dashboard_callback(self, interaction)
    
    async def _handle_close(self, interaction: discord.Interaction):
        """Handle close button."""
        await interaction.message.delete()
        await interaction.response.defer()
    
    async def _handle_alliances(self, interaction: discord.Interaction):
        from modules.alliances.views import alliances_callback
        await alliances_callback(self, interaction)
    
    async def _handle_players(self, interaction: discord.Interaction):
        from modules.players.views import players_callback
        await players_callback(self, interaction)
    
    async def _handle_gift_codes(self, interaction: discord.Interaction):
        from modules.gift_codes.views import gift_codes_callback
        await gift_codes_callback(self, interaction)
    
    async def _handle_events(self, interaction: discord.Interaction):
        from modules.events.views import events_callback
        await events_callback(self, interaction)
    
    async def _handle_attendance(self, interaction: discord.Interaction):
        from modules.attendance.views import attendance_callback
        await attendance_callback(self, interaction)
    
    async def _handle_bear_tracking(self, interaction: discord.Interaction):
        from modules.bear_tracking.views import bear_tracking_callback
        await bear_tracking_callback(self, interaction)
    
    async def _handle_ministers(self, interaction: discord.Interaction):
        from modules.ministers.views import ministers_callback
        await ministers_callback(self, interaction)
    
    async def _handle_notifications(self, interaction: discord.Interaction):
        from modules.notifications.views import notifications_callback
        await notifications_callback(self, interaction)
    
    async def _handle_themes(self, interaction: discord.Interaction):
        from modules.themes.views import themes_callback
        await themes_callback(self, interaction)
    
    async def _handle_permissions(self, interaction: discord.Interaction):
        from modules.maintenance.views import permissions_callback
        await permissions_callback(self, interaction)
    
    async def _handle_maintenance(self, interaction: discord.Interaction):
        from modules.maintenance.views import maintenance_callback
        await maintenance_callback(self, interaction)
    
    async def _handle_owner_panel(self, interaction: discord.Interaction):
        from modules.owner_panel.views import owner_panel_callback
        await owner_panel_callback(self, interaction)
    
    async def _handle_language(self, interaction: discord.Interaction):
        from modules.dashboard.views import language_callback
        await language_callback(self, interaction)
    
    async def _handle_settings(self, interaction: discord.Interaction):
        from modules.maintenance.views import settings_callback
        await settings_callback(self, interaction)
    
    # Gift codes handlers
    async def _handle_gift_add(self, interaction: discord.Interaction):
        from modules.gift_codes.views import add_gift_code_callback
        await add_gift_code_callback(self, interaction)
    
    async def _handle_gift_redeem_single(self, interaction: discord.Interaction):
        from modules.gift_codes.views import redeem_single_code_callback
        await redeem_single_code_callback(self, interaction)
    
    async def _handle_gift_batch(self, interaction: discord.Interaction):
        from modules.gift_codes.views import batch_redeem_callback
        await batch_redeem_callback(self, interaction)
    
    async def _handle_gift_redeem_alliance(self, interaction: discord.Interaction):
        from modules.gift_codes.views import redeem_alliance_code_callback
        await redeem_alliance_code_callback(self, interaction)
    
    async def _handle_gift_auto(self, interaction: discord.Interaction):
        from modules.gift_codes.views import auto_redeem_callback
        await auto_redeem_callback(self, interaction)
    
    async def _handle_gift_report(self, interaction: discord.Interaction):
        from modules.gift_codes.views import gift_report_callback
        await gift_report_callback(self, interaction)
    
    # Auto redeem handlers
    async def _handle_auto_enable_alliance(self, interaction: discord.Interaction):
        """Enable auto redeem for an alliance."""
        from modules.gift_codes.views import enable_auto_redeem_callback
        await enable_auto_redeem_callback(self, interaction)
    
    async def _handle_auto_disable_alliance(self, interaction: discord.Interaction):
        """Disable auto redeem for an alliance."""
        from modules.gift_codes.views import disable_auto_redeem_callback
        await disable_auto_redeem_callback(self, interaction)
    
    async def _handle_auto_redeem_all(self, interaction: discord.Interaction):
        """Redeem a code for all alliances with auto redeem enabled."""
        from modules.gift_codes.views import redeem_all_alliances_callback
        await redeem_all_alliances_callback(self, interaction)
    
    # Owner panel handlers
    async def _handle_owner_language(self, interaction: discord.Interaction):
        from modules.owner_panel.views import language_management_callback
        await language_management_callback(self, interaction)
    
    async def _handle_owner_buttons(self, interaction: discord.Interaction):
        from modules.owner_panel.views import button_management_callback
        await button_management_callback(self, interaction)
    
    async def _handle_owner_texts(self, interaction: discord.Interaction):
        from modules.owner_panel.views import text_management_callback
        await text_management_callback(self, interaction)
    
    async def _handle_owner_icons(self, interaction: discord.Interaction):
        from modules.owner_panel.views import icon_management_callback
        await icon_management_callback(self, interaction)
    
    async def _handle_owner_branding(self, interaction: discord.Interaction):
        from modules.owner_panel.views import branding_management_callback
        await branding_management_callback(self, interaction)
    
    async def _handle_owner_features(self, interaction: discord.Interaction):
        from modules.owner_panel.views import feature_management_callback
        await feature_management_callback(self, interaction)
    
    async def _handle_confirm(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Confirmed!", ephemeral=True)
    
    async def _handle_cancel(self, interaction: discord.Interaction):
        await interaction.response.send_message("❌ Cancelled", ephemeral=True)
    
    async def _handle_language_select(self, interaction: discord.Interaction):
        """Handle language selection."""
        if interaction.data.get("values"):
            new_locale = interaction.data["values"][0]
            await i18n.set_locale(new_locale)
            await interaction.response.send_message(
                f"✅ Language changed to {new_locale}",
                ephemeral=True
            )
    
    async def _handle_owner_section_select(self, interaction: discord.Interaction):
        """Handle owner panel section selection."""
        if interaction.data.get("values"):
            section = interaction.data["values"][0]
            
            handlers = {
                "language": self._handle_owner_language,
                "buttons": self._handle_owner_buttons,
                "texts": self._handle_owner_texts,
                "icons": self._handle_owner_icons,
                "branding": self._handle_owner_branding,
                "features": self._handle_owner_features,
            }
            
            handler = handlers.get(section)
            if handler:
                await handler(interaction)
    
    async def _handle_alliance_select_enable(self, interaction: discord.Interaction):
        """Handle alliance selection for enabling auto redeem."""
        if interaction.data.get("values"):
            alliance_id = int(interaction.data["values"][0])
            
            # Update database
            await db.execute(
                "UPDATE alliances SET auto_gift_enabled = 1 WHERE id = ?",
                (alliance_id,)
            )
            await db.connection.commit()
            
            row = await db.fetchone("SELECT name FROM alliances WHERE id = ?", (alliance_id,))
            alliance_name = row["name"] if row else "Unknown"
            
            embed = discord.Embed(
                title="✅ Auto Redeem Enabled",
                description=f"Auto redeem has been enabled for **{alliance_name}**",
                color=0x2ecc71
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            await audit_log.log(
                user_id=str(interaction.user.id),
                user_name=str(interaction.user),
                action="enable_auto_redeem",
                category=AuditCategory.GIFT_CODES,
                details={"alliance_id": alliance_id, "alliance_name": alliance_name}
            )
    
    async def _handle_alliance_select_disable(self, interaction: discord.Interaction):
        """Handle alliance selection for disabling auto redeem."""
        if interaction.data.get("values"):
            alliance_id = int(interaction.data["values"][0])
            
            # Update database
            await db.execute(
                "UPDATE alliances SET auto_gift_enabled = 0 WHERE id = ?",
                (alliance_id,)
            )
            await db.connection.commit()
            
            row = await db.fetchone("SELECT name FROM alliances WHERE id = ?", (alliance_id,))
            alliance_name = row["name"] if row else "Unknown"
            
            embed = discord.Embed(
                title="❌ Auto Redeem Disabled",
                description=f"Auto redeem has been disabled for **{alliance_name}**",
                color=0xe74c3c
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            await audit_log.log(
                user_id=str(interaction.user.id),
                user_name=str(interaction.user),
                action="disable_auto_redeem",
                category=AuditCategory.GIFT_CODES,
                details={"alliance_id": alliance_id, "alliance_name": alliance_name}
            )
    
    async def on_ready(self):
        """Called when bot is ready."""
        logger.info(f"Logged in as {self.user}")
        logger.info(f"Bot ID: {self.user.id}")
        
        if not hasattr(self, '_setup_complete'):
            await self.setup_hook()
            self._setup_complete = True
    
    async def close(self):
        """Close the bot."""
        logger.info("Shutting down WOS-M...")
        
        if self.process_queue:
            await self.process_queue.stop()
        
        await db.close()
        
        await super().close()
