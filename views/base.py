"""
WOS-M Base Views
© MANSOUR — WOS-M. All rights reserved.
"""
import discord
from discord import ui
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from core.i18n import i18n


@dataclass
class PageInfo:
    """Page information for navigation."""
    title: str
    description: str
    icon: str = ""
    color: int = 0x3498db


class BaseView(ui.View):
    """Base view with common functionality."""
    
    def __init__(
        self,
        user_id: int,
        page_info: Optional[PageInfo] = None,
        timeout: float = 300.0
    ):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.page_info = page_info
        self._current_page = 0
        self._total_pages = 1
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the user is allowed to interact."""
        return interaction.user.id == self.user_id
    
    def create_embed(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[int] = None,
        fields: Optional[List[Dict[str, Any]]] = None,
        footer: Optional[str] = None
    ) -> discord.Embed:
        """Create a standard embed."""
        if color is None:
            color = self.page_info.color if self.page_info else 0x3498db
        
        embed = discord.Embed(
            title=title or (self.page_info.title if self.page_info else ""),
            description=description or (self.page_info.description if self.page_info else ""),
            color=color
        )
        
        if self.page_info and self.page_info.icon:
            embed.title = f"{self.page_info.icon} {embed.title}"
        
        if fields:
            for field in fields:
                embed.add_field(**field)
        
        if footer is None:
            footer = i18n.get("bot.footer")
        
        embed.set_footer(text=footer)
        
        return embed
    
    def add_back_home_buttons(self):
        """Add back and home buttons."""
        self.add_item(
            ui.Button(
                label=i18n.get("buttons.back"),
                style=discord.ButtonStyle.secondary,
                custom_id="nav_back",
                emoji="🔙"
            )
        )
        self.add_item(
            ui.Button(
                label=i18n.get("buttons.home"),
                style=discord.ButtonStyle.primary,
                custom_id="nav_home",
                emoji="🏠"
            )
        )


class ConfirmView(BaseView):
    """Confirmation dialog view."""
    
    def __init__(self, user_id: int, action: str = ""):
        super().__init__(user_id)
        self.confirmed = False
        self.action = action
        
        self.add_item(
            ui.Button(
                label=i18n.get("buttons.confirm"),
                style=discord.ButtonStyle.success,
                custom_id="confirm_btn",
                emoji="✅"
            )
        )
        self.add_item(
            ui.Button(
                label=i18n.get("buttons.cancel"),
                style=discord.ButtonStyle.danger,
                custom_id="cancel_btn",
                emoji="❌"
            )
        )


class PaginationView(BaseView):
    """Pagination view for paginated content."""
    
    def __init__(
        self,
        user_id: int,
        items: List[Any],
        items_per_page: int = 10,
        page_info: Optional[PageInfo] = None
    ):
        super().__init__(user_id, page_info)
        self.items = items
        self.items_per_page = items_per_page
        self._total_pages = max(1, (len(items) + items_per_page - 1) // items_per_page)
        self._current_page = 0
        
        self._update_buttons()

    async def _prev_callback(self, interaction: discord.Interaction):
        """Handle previous page button."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "ليس لديك صلاحية استخدام هذه الأزرار.",
                ephemeral=True
            )
            return

        await self.prev_page()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def _next_callback(self, interaction: discord.Interaction):
        """Handle next page button."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "ليس لديك صلاحية استخدام هذه الأزرار.",
                ephemeral=True
            )
            return

        await self.next_page()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    def _update_buttons(self):
        """Update pagination buttons."""
        self.clear_items()
        
        # Previous button
        prev_button = ui.Button(
            label=i18n.get("buttons.previous"),
            style=discord.ButtonStyle.secondary,
            custom_id="nav_prev",
            emoji="◀️",
            disabled=self._current_page == 0
        )
        prev_button.callback = self._prev_callback

        # Next button
        next_button = ui.Button(
            label=i18n.get("buttons.next"),
            style=discord.ButtonStyle.secondary,
            custom_id="nav_next",
            emoji="▶️",
            disabled=self._current_page >= self._total_pages - 1
        )
        next_button.callback = self._next_callback
        
        # Page indicator
        page_label = f"{i18n.get('messages.page')} {self._current_page + 1} {i18n.get('messages.of')} {self._total_pages}"
        
        self.add_item(prev_button)
        self.add_item(
            ui.Button(
                label=page_label,
                style=discord.ButtonStyle.primary,
                custom_id="page_indicator",
                disabled=True
            )
        )
        self.add_item(next_button)
        
        self.add_back_home_buttons()
    
    def get_current_items(self) -> List[Any]:
        """Get items for current page."""
        start = self._current_page * self.items_per_page
        end = start + self.items_per_page
        return self.items[start:end]
    
    async def next_page(self):
        """Go to next page."""
        if self._current_page < self._total_pages - 1:
            self._current_page += 1
            self._update_buttons()
    
    async def prev_page(self):
        """Go to previous page."""
        if self._current_page > 0:
            self._current_page -= 1
            self._update_buttons()
