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













