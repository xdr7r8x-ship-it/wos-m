"""
WOS-M Bear Tracking Module
© MANSOUR — WOS-M. All rights reserved.
"""
import discord
from typing import Dict, Any, List, Optional

from core.bot import WOSMBot
from core.i18n import i18n
from core.database import db
from core.permissions import PermissionLevel, PermissionGuard
from core.audit_log import audit_log, AuditCategory
from views.base import BaseView, PageInfo
from views.buttons import ActionButton


class BearTrackingView(BaseView):
    """Bear tracking management view."""
    
    def __init__(self, bot: WOSMBot, user_id: int):
        self.bot = bot
        super().__init__(
            user_id=user_id,
            page_info=PageInfo(
                title=i18n.get("bear_tracking.title"),
                description="",
                icon="🐻",
                color=0x8B4513
            )
        )
        
        self._add_buttons()
        self.add_back_home_buttons()
    
    def _add_buttons(self):
        self.add_item(ActionButton(
            label=i18n.get("bear_tracking.add_hunt"),
            custom_id="bear_add",
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("bear_tracking.damage_record"),
            custom_id="bear_damage",
            style=discord.ButtonStyle.primary,
            emoji="📝",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("bear_tracking.leaderboard"),
            custom_id="bear_leaderboard",
            style=discord.ButtonStyle.primary,
            emoji="🏆",
            row=0
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("bear_tracking.total_report"),
            custom_id="bear_report",
            style=discord.ButtonStyle.primary,
            emoji="📊",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("bear_tracking.ocr_import"),
            custom_id="bear_ocr",
            style=discord.ButtonStyle.secondary,
            emoji="📷",
            row=1
        ))
        
        self.add_item(ActionButton(
            label=i18n.get("bear_tracking.archive_results"),
            custom_id="bear_archive",
            style=discord.ButtonStyle.secondary,
            emoji="📦",
            row=1
        ))






