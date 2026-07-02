"""
WOS-M Bot Core
© MANSOUR — WOS-M. All rights reserved.
"""
import discord
from discord import app_commands
import asyncio
import logging
from typing import Optional, Dict, Callable

from config.settings import settings
from core.database import db
from core.i18n import i18n
from core.permissions import PermissionGuard, PermissionLevel
from core.process_queue import ProcessQueue
from core.audit_log import audit_log, AuditCategory
from core.feature_registry import FeatureRegistry, feature_registry

import importlib
import inspect

from core.interaction_registry import INTERACTION_REGISTRY

logger = logging.getLogger(__name__)

def _registry_permission_to_core(spec):
    """Convert registry permission to core PermissionLevel."""
    from core.permissions import PermissionLevel as CorePL
    if spec is None:
        return CorePL.MEMBER
    try:
        return CorePL.from_string(spec.required_permission.value)
    except Exception:
        return CorePL.MEMBER

def resolve_registered_handler(bot, spec):
    """Resolve handler from registry spec."""
    if spec is None:
        return None
    
    # Check if handler exists on bot (includes navigation handlers)
    if hasattr(bot, spec.handler_name):
        return getattr(bot, spec.handler_name)
    
    # Navigation handlers are on the bot as _handle_*
    if spec.module == "navigation":
        nav_handler = f"_handle_{spec.custom_id}"
        if hasattr(bot, nav_handler):
            return getattr(bot, nav_handler)
        return None
    
    if spec.module == "system":
        return None
    
    # Handle dash_* custom_ids - convert to _handle_* pattern
    dash_to_handle = spec.custom_id.replace("dash_", "_handle_")
    if hasattr(bot, dash_to_handle):
        return getattr(bot, dash_to_handle)
    
    # Try to import from module
    try:
        module = importlib.import_module(f"modules.{spec.module}.views")
    except Exception:
        return None
    
    # Try multiple handler name patterns based on custom_id
    # e.g., "event_list" -> try "event_list_callback", "list_events_callback"
    parts = spec.custom_id.split('_')
    candidates = [
        spec.handler_name,
        f"{spec.custom_id}_callback",
    ]
    
    # Generate all permutations
    for i in range(1, len(parts)):
        prefix = "_".join(parts[:i])
        suffix = "_".join(parts[i:])
        candidates.append(f"{prefix}_{suffix}_callback")
        candidates.append(f"{suffix}_{prefix}_callback")
    
    # Also try singular/plural variations
    singular_candidates = []
    for c in candidates[:]:
        if c.endswith('_callback'):
            singular = c[:-9]  # remove _callback
            if singular.endswith('s'):
                singular_candidates.append(singular[:-1] + '_callback')
            singular_candidates.append(singular + 's_callback')
    candidates.extend(singular_candidates)
    
    for name in candidates:
        handler = getattr(module, name, None)
        if callable(handler):
            return handler
    
    return None

# Custom IDs that are handled locally by views (PaginationView, etc)
# These should NOT be dispatched globally - they're handled by the View's own callbacks
LOCAL_VIEW_CALLBACKS = {"nav_prev", "nav_next"}

# Track dispatched interactions to prevent double execution
# Use a set instead of setting attributes on frozen Interaction objects
_DISPATCHED_INTERACTIONS = set()


async def dispatch_registered_interaction(bot, interaction):
    """Dispatch interaction through registry. No fallbacks."""
    # Idempotency check - prevent double execution
    interaction_id = id(interaction)
    if interaction_id in _DISPATCHED_INTERACTIONS:
        return
    _DISPATCHED_INTERACTIONS.add(interaction_id)
    
    # Cleanup old entries to prevent memory leak (keep set bounded)
    if len(_DISPATCHED_INTERACTIONS) > 10000:
        # Remove entries older than 100 (keep last 100)
        _DISPATCHED_INTERACTIONS.clear()

    custom_id = interaction.data.get("custom_id", "")

    # Skip local view callbacks - these are handled by View's own callbacks
    if custom_id in LOCAL_VIEW_CALLBACKS:
        return

    spec = INTERACTION_REGISTRY.get(custom_id)

    # Case 1: Unregistered custom_id
    if spec is None:
        # Log and reject unregistered IDs
        import logging
        logging.warning(f"UNREGISTERED_CUSTOM_ID: {custom_id}")
        try:
            await interaction.response.send_message(
                "هذا الزر غير مسجل في النظام.",
                ephemeral=True
            )
        except Exception:
            pass
        return

    guard = PermissionGuard(bot)
    user_id = str(interaction.user.id)
    required_level = _registry_permission_to_core(spec)

    # Check owner-only
    if spec.owner_only and not await guard.is_owner(user_id):
        try:
            await interaction.response.send_message(
                "ليس لديك صلاحية لتنفيذ هذا الإجراء.",
                ephemeral=True
            )
        except Exception:
            pass
        return

    # Check permission
    guild_id = str(interaction.guild_id) if interaction.guild_id else None
    if not await guard.has_permission(user_id, required_level, guild_id=guild_id):
        try:
            await interaction.response.send_message(
                "ليس لديك صلاحية لتنفيذ هذا الإجراء.",
                ephemeral=True
            )
        except Exception:
            pass
        return

    # Resolve and call handler
    handler = resolve_registered_handler(bot, spec)
    if handler is None:
        # Check if it's a local view callback
        if custom_id in LOCAL_VIEW_CALLBACKS:
            return
        # Log and reject missing handlers
        import logging
        logging.warning(f"MISSING_HANDLER: {custom_id} (spec.module={spec.module})")
        try:
            await interaction.response.send_message(
                "Handler غير موجود لهذا الزر.",
                ephemeral=True
            )
        except Exception:
            pass
        return

    result = handler(bot, interaction) if inspect.isfunction(handler) else handler(interaction)
    if inspect.isawaitable(result):
        await result


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
        
        self._button_callbacks: Dict[str, Callable] = {}
        self._select_callbacks: Dict[str, Callable] = {}
        self._dynamic_router: Dict[str, str] = {}
        
        self._setup_button_callbacks()
        self._setup_select_callbacks()
        self._setup_dynamic_router()
    
    def _setup_button_callbacks(self):
        """Setup button interaction callbacks."""
        self._button_callbacks.update({
            # Navigation
            "nav_back": self._handle_back,
            "nav_home": self._handle_home,
            "nav_close": self._handle_close,
            # Dashboard navigation
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
            # Gift codes dashboard
            "gift_dash_add": self._handle_gift_dash_add,
            "gift_dash_single": self._handle_gift_dash_single,
            "gift_dash_batch": self._handle_gift_dash_batch,
            "gift_dash_alliance": self._handle_gift_dash_alliance,
            "gift_dash_auto": self._handle_gift_dash_auto,
            "gift_dash_report": self._handle_gift_dash_report,
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
        })
    
    def _setup_select_callbacks(self):
        """Setup select menu interaction callbacks."""
        self._select_callbacks.update({
            "language_select": self._handle_language_select,
            "owner_panel_section_select": self._handle_owner_section_select,
            "alliance_select_enable": self._handle_alliance_select_enable,
            "alliance_select_disable": self._handle_alliance_select_disable,
            "alliance_select": self._handle_alliance_select,
            "player_select": self._handle_player_select,
            "event_select": self._handle_event_select,
            "notif_select": self._handle_notif_select,
        })
    
    def _setup_dynamic_router(self):
        """Setup dynamic routing to modules for uncategorized callbacks."""
        # Alliance module
        self._dynamic_router.update({
            "alliance_add": "alliances",
            "alliance_list": "alliances",
            "alliance_edit": "alliances",
            "alliance_delete": "alliances",
            "alliance_sync_settings": "alliances",
            "alliance_gift_settings": "alliances",
            "alliance_redeem_modal": "alliances",
        })
        
        # Player module
        self._dynamic_router.update({
            "player_add": "players",
            "player_search": "players",
            "player_list": "players",
            "player_sync": "players",
            "player_move": "players",
            "player_export": "players",
        })
        
        # Events module
        self._dynamic_router.update({
            "event_create": "events",
            "event_list": "events",
            "event_edit": "events",
            "event_delete": "events",
        })
        
        # Notifications module
        self._dynamic_router.update({
            "notif_add": "notifications",
            "notif_list": "notifications",
            "notif_edit": "notifications",
            "notif_delete": "notifications",
            "notif_enable": "notifications",
            "notif_disable": "notifications",
        })
        
        # Attendance module
        self._dynamic_router.update({
            "att_record": "attendance",
            "att_list": "attendance",
            "att_history": "attendance",
            "att_report": "attendance",
            "att_export": "attendance",
        })
        
        # Bear tracking module
        self._dynamic_router.update({
            "bear_add": "bear_tracking",
            "bear_damage": "bear_tracking",
            "bear_leaderboard": "bear_tracking",
            "bear_report": "bear_tracking",
            "bear_ocr": "bear_tracking",
            "bear_archive": "bear_tracking",
        })
        
        # Ministers module
        self._dynamic_router.update({
            "minister_add": "ministers",
            "minister_list": "ministers",
            "minister_assign": "ministers",
            "minister_schedule": "ministers",
            "minister_reminder": "ministers",
        })
        
        # Maintenance module
        self._dynamic_router.update({
            "maint_health": "maintenance",
            "maint_database": "maintenance",
            "maint_logs": "maintenance",
            "maint_queue": "maintenance",
            "maint_backup": "maintenance",
            "maint_api": "maintenance",
            "perm_list": "maintenance",
            "perm_assign": "maintenance",
            "perm_remove": "maintenance",
            "perm_transfer": "maintenance",
            "perm_audit": "maintenance",
            "settings_general": "maintenance",
            "settings_api": "maintenance",
            "settings_save": "maintenance",
            "settings_reset": "maintenance",
        })
        
        # Themes module
        self._dynamic_router.update({
            "theme_bot_name": "themes",
            "theme_primary_color": "themes",
            "theme_footer": "themes",
            "theme_signature": "themes",
            "theme_preview": "themes",
            "theme_reset": "themes",
        })
        
        # Owner panel module
        self._dynamic_router.update({
            "brand_name": "owner_panel",
            "brand_colors": "owner_panel",
            "brand_save": "owner_panel",
            "brand_reset": "owner_panel",
            "btn_add": "owner_panel",
            "btn_edit_name": "owner_panel",
            "btn_edit_icon": "owner_panel",
            "btn_edit_order": "owner_panel",
            "btn_enable": "owner_panel",
            "btn_disable": "owner_panel",
            "feat_add": "owner_panel",
            "feat_edit": "owner_panel",
            "feat_enable": "owner_panel",
            "feat_disable": "owner_panel",
            "feat_link": "owner_panel",
            "feat_registry": "owner_panel",
            "icon_button": "owner_panel",
            "icon_section": "owner_panel",
            "icon_status": "owner_panel",
            "text_edit_title": "owner_panel",
            "text_edit_desc": "owner_panel",
            "text_edit_msg": "owner_panel",
            "text_reset": "owner_panel",
            "single_redeem_modal": "gift_codes",
        })
    
    async def _route_to_module(self, interaction: discord.Interaction, module_name: str, action: str):
        """Route interaction to module handler."""
        try:
            module = __import__(f"modules.{module_name}.views", fromlist=[""])
            handler_name = f"{action}_callback"
            if hasattr(module, handler_name):
                handler = getattr(module, handler_name)
                await handler(self, interaction)
            else:
                logger.warning(f"No handler {handler_name} in {module_name}")
                await interaction.response.send_message(
                    "⚠️ تعذر تنفيذ هذا الإجراء. يرجى المحاولة مرة أخرى.",
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error routing to {module_name}.{action}: {e}", exc_info=True)
            await interaction.response.send_message(
                "❌ حدث خطأ أثناء تنفيذ العملية. تم تسجيل التفاصيل.",
                ephemeral=True
            )
    
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
        logger.info(f"Registered callbacks: {len(self._button_callbacks)} buttons, {len(self._select_callbacks)} selects")
        logger.info(f"Dynamic routes: {len(self._dynamic_router)}")
    
    async def _register_commands(self):
        """Register slash commands."""
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
        """Handle all interactions using registry as primary path."""
        if interaction.type == discord.InteractionType.component:
            await dispatch_registered_interaction(self, interaction)

    # Navigation handlers
    async def _handle_back(self, interaction: discord.Interaction):
        """Navigate back to previous page or module dashboard."""
        from modules.dashboard.views import dashboard_callback
        await dashboard_callback(self, interaction)
    
    async def _handle_home(self, interaction: discord.Interaction):
        from modules.dashboard.views import dashboard_callback
        await dashboard_callback(self, interaction)
    
    async def _handle_close(self, interaction: discord.Interaction):
        """Handle close button - delete message."""
        try:
            await interaction.message.delete()
        except Exception:
            if not interaction.response.is_done():
                await interaction.response.send_message("تم إغلاق النافذة.", ephemeral=True)

    async def _handle_nav_close(self, interaction: discord.Interaction):
        """Handle nav close button."""
        await self._handle_close(interaction)

    async def _handle_nav_back(self, interaction: discord.Interaction):
        """Navigate back to dashboard."""
        from modules.dashboard.views import dashboard_callback
        await dashboard_callback(self, interaction)

    async def _handle_nav_home(self, interaction: discord.Interaction):
        """Navigate home to dashboard."""
        from modules.dashboard.views import dashboard_callback
        await dashboard_callback(self, interaction)

    async def _handle_nav_refresh(self, interaction: discord.Interaction):
        """Refresh current dashboard."""
        from modules.dashboard.views import dashboard_callback
        await dashboard_callback(self, interaction)

    # Module navigation handlers
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
        from modules.dashboard.views import settings_callback
        await settings_callback(self, interaction)
    
    # Gift code handlers
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
        from modules.gift_codes.views import redeem_alliance_callback
        await redeem_alliance_callback(self, interaction)
    
    async def _handle_gift_auto(self, interaction: discord.Interaction):
        from modules.gift_codes.views import auto_redeem_callback
        await auto_redeem_callback(self, interaction)
    
    async def _handle_gift_report(self, interaction: discord.Interaction):
        from modules.gift_codes.views import gift_report_callback
        await gift_report_callback(self, interaction)

    async def _handle_gift_dash_add(self, interaction: discord.Interaction):
        from modules.gift_codes.views import add_gift_code_callback
        await add_gift_code_callback(self, interaction)

    async def _handle_gift_dash_single(self, interaction: discord.Interaction):
        from modules.gift_codes.views import redeem_single_code_callback
        await redeem_single_code_callback(self, interaction)

    async def _handle_gift_dash_batch(self, interaction: discord.Interaction):
        from modules.gift_codes.views import batch_redeem_callback
        await batch_redeem_callback(self, interaction)

    async def _handle_gift_dash_alliance(self, interaction: discord.Interaction):
        from modules.gift_codes.views import redeem_alliance_callback
        await redeem_alliance_callback(self, interaction)

    async def _handle_gift_dash_auto(self, interaction: discord.Interaction):
        from modules.gift_codes.views import auto_redeem_callback
        await auto_redeem_callback(self, interaction)

    async def _handle_gift_dash_report(self, interaction: discord.Interaction):
        from modules.gift_codes.views import gift_report_callback
        await gift_report_callback(self, interaction)
    
    # Auto redeem handlers
    async def _handle_auto_enable_alliance(self, interaction: discord.Interaction):
        from modules.gift_codes.views import enable_auto_redeem_callback
        await enable_auto_redeem_callback(self, interaction)
    
    async def _handle_auto_disable_alliance(self, interaction: discord.Interaction):
        from modules.gift_codes.views import disable_auto_redeem_callback
        await disable_auto_redeem_callback(self, interaction)
    
    async def _handle_auto_redeem_all(self, interaction: discord.Interaction):
        from modules.gift_codes.views import redeem_all_alliances_callback
        await redeem_all_alliances_callback(self, interaction)
    
    # Modal handlers for gift_codes
    async def _handle_add_gift_modal(self, interaction: discord.Interaction):
        from modules.gift_codes.views import add_gift_code_callback
        await add_gift_code_callback(self, interaction)
    
    async def _handle_batch_redeem_modal(self, interaction: discord.Interaction):
        from modules.gift_codes.views import batch_redeem_callback
        await batch_redeem_callback(self, interaction)
    
    async def _handle_redeem_gift_modal(self, interaction: discord.Interaction):
        from modules.gift_codes.views import redeem_single_code_callback
        await redeem_single_code_callback(self, interaction)
    
    async def _handle_single_redeem_modal(self, interaction: discord.Interaction):
        from modules.gift_codes.views import single_redeem_modal_callback
        await single_redeem_modal_callback(self, interaction)
    
    # Additional gift_codes handlers
    async def _handle_batch_manual(self, interaction: discord.Interaction):
        from modules.gift_codes.views import batch_redeem_callback
        await batch_redeem_callback(self, interaction)
    
    async def _handle_batch_redeem_all(self, interaction: discord.Interaction):
        from modules.gift_codes.views import redeem_all_alliances_callback
        await redeem_all_alliances_callback(self, interaction)
    
    async def _handle_gift_alliance(self, interaction: discord.Interaction):
        from modules.gift_codes.views import redeem_alliance_callback
        await redeem_alliance_callback(self, interaction)
    
    async def _handle_gift_redeem(self, interaction: discord.Interaction):
        from modules.gift_codes.views import redeem_single_code_callback
        await redeem_single_code_callback(self, interaction)
    
    async def _handle_gift_settings(self, interaction: discord.Interaction):
        from modules.gift_codes.views import gift_codes_callback
        await gift_codes_callback(self, interaction)
    
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
        await interaction.response.send_message(i18n.get("messages.action_completed"), ephemeral=True)
    
    async def _handle_cancel(self, interaction: discord.Interaction):
        await interaction.response.send_message(i18n.get("messages.action_cancelled"), ephemeral=True)
    
    # Select menu handlers
    async def _handle_language_select(self, interaction: discord.Interaction):
        if interaction.data.get("values"):
            new_locale = interaction.data["values"][0]
            await i18n.set_locale(new_locale)
            await interaction.response.send_message(
                i18n.get("messages.language_changed", locale=new_locale),
                ephemeral=True
            )
    
    async def _handle_owner_section_select(self, interaction: discord.Interaction):
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
        if interaction.data.get("values"):
            alliance_id = int(interaction.data["values"][0])
            await db.execute(
                "UPDATE alliances SET auto_gift_enabled = 1 WHERE id = ?",
                (alliance_id,)
            )
            await db.connection.commit()
            
            row = await db.fetchone("SELECT name FROM alliances WHERE id = ?", (alliance_id,))
            alliance_name = row["name"] if row else "Unknown"
            
            embed = discord.Embed(
                title=f"✅ {i18n.get('alliances.auto_enabled')}",
                description=f"**{alliance_name}**",
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
        if interaction.data.get("values"):
            alliance_id = int(interaction.data["values"][0])
            await db.execute(
                "UPDATE alliances SET auto_gift_enabled = 0 WHERE id = ?",
                (alliance_id,)
            )
            await db.connection.commit()
            
            row = await db.fetchone("SELECT name FROM alliances WHERE id = ?", (alliance_id,))
            alliance_name = row["name"] if row else "Unknown"
            
            embed = discord.Embed(
                title=f"❌ {i18n.get('alliances.auto_disabled')}",
                description=f"**{alliance_name}**",
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
    
    async def _handle_alliance_select(self, interaction: discord.Interaction):
        await self._route_to_module(interaction, "alliances", "alliance_select")
    
    async def _handle_player_select(self, interaction: discord.Interaction):
        await self._route_to_module(interaction, "players", "player_select")
    
    async def _handle_event_select(self, interaction: discord.Interaction):
        await self._route_to_module(interaction, "events", "event_select")
    
    async def _handle_notif_select(self, interaction: discord.Interaction):
        await self._route_to_module(interaction, "notifications", "notif_select")
    
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