"""
WOS-M Operations Control System - Alerts

This module handles sending alerts to the bot owner via Discord DM
or a dedicated channel.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import discord

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Represents an alert to be sent."""
    id: str
    title: str
    message: str
    severity: AlertSeverity
    source: str
    incident_id: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class AlertManager:
    """
    Manages alerts and notifications to the bot owner.
    """
    
    _instance: Optional['AlertManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._enabled = os.environ.get('OPS_ALERTS_ENABLED', 'true').lower() == 'true'
        self._cooldown_seconds = 300  # 5 minutes
        self._last_alert: dict[str, datetime] = {}
        self._alert_counter = 0
    
    @classmethod
    def get_instance(cls) -> 'AlertManager':
        """Get the singleton instance."""
        return cls()
    
    @property
    def owner_id(self) -> Optional[str]:
        """Get owner Discord ID."""
        try:
            from config.settings import settings
            return str(settings.bot.owner_id)
        except Exception:
            return os.environ.get('OWNER_DISCORD_ID')
    
    @property
    def alert_channel_id(self) -> Optional[str]:
        """Get dedicated alert channel ID."""
        return os.environ.get('OPS_ALERT_CHANNEL_ID')
    
    def is_enabled(self) -> bool:
        """Check if alerts are enabled."""
        return self._enabled
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable alerts."""
        self._enabled = enabled
        logger.info(f"Alerts {'enabled' if enabled else 'disabled'}")
    
    def set_cooldown(self, seconds: int) -> None:
        """Set alert cooldown in seconds."""
        self._cooldown_seconds = max(60, seconds)
    
    def _can_send_alert(self, alert_type: str) -> bool:
        """Check if an alert can be sent (cooldown check)."""
        if not self._enabled:
            return False
        
        now = datetime.now(timezone.utc)
        
        if alert_type not in self._last_alert:
            return True
        
        elapsed = (now - self._last_alert[alert_type]).total_seconds()
        return elapsed >= self._cooldown_seconds
    
    def _record_alert(self, alert_type: str) -> None:
        """Record that an alert was sent."""
        self._last_alert[alert_type] = datetime.now(timezone.utc)
        self._alert_counter += 1
    
    def _generate_alert_id(self) -> str:
        """Generate a unique alert ID."""
        return f"ALT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{self._alert_counter:04d}"
    
    def _get_severity_emoji(self, severity: AlertSeverity) -> str:
        """Get emoji for severity level."""
        return {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "🔴",
            AlertSeverity.CRITICAL: "🚨"
        }.get(severity, "📢")
    
    def _format_alert_message(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        incident_id: Optional[str] = None
    ) -> discord.Embed:
        """Format an alert as a Discord embed."""
        emoji = self._get_severity_emoji(severity)
        
        color_map = {
            AlertSeverity.INFO: 0x3498db,      # Blue
            AlertSeverity.WARNING: 0xf39c12,   # Orange
            AlertSeverity.ERROR: 0xe74c3c,    # Red
            AlertSeverity.CRITICAL: 0x9b59b6   # Purple
        }
        
        embed = discord.Embed(
            title=f"{emoji} {title}",
            description=message,
            color=color_map.get(severity, 0x3498db),
            timestamp=datetime.now(timezone.utc)
        )
        
        if incident_id:
            embed.add_field(
                name="🔖 Incident ID",
                value=incident_id,
                inline=True
            )
        
        embed.add_field(
            name="⏰ Timestamp",
            value=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            inline=True
        )
        
        embed.set_footer(text="WOS-M Operations Alert")
        
        return embed
    
    async def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        source: str = "system",
        incident_id: Optional[str] = None,
        alert_type: Optional[str] = None,
        bypass_cooldown: bool = False
    ) -> bool:
        """
        Send an alert to the owner.
        
        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity level
            source: Source of the alert
            incident_id: Related incident ID if any
            alert_type: Type for cooldown grouping
            bypass_cooldown: Skip cooldown check for critical alerts
        
        Returns:
            True if alert was sent successfully
        """
        if not self._enabled:
            logger.debug("Alerts disabled, skipping")
            return False
        
        # Check cooldown unless bypassed
        alert_key = alert_type or source
        if not bypass_cooldown and not self._can_send_alert(alert_key):
            logger.debug(f"Alert cooldown active for {alert_key}")
            return False
        
        # Generate alert
        alert_id = self._generate_alert_id()
        alert = Alert(
            id=alert_id,
            title=title,
            message=message,
            severity=severity,
            source=source,
            incident_id=incident_id
        )
        
        # Get bot instance
        try:
            from core.bot import WOSMBot
            if not hasattr(WOSMBot, '_instance') or WOSMBot._instance is None:
                logger.warning("Bot not initialized, cannot send alert")
                return False
            
            bot = WOSMBot._instance
            
            # Try to send DM to owner
            owner_id = self.owner_id
            if owner_id:
                try:
                    owner = await bot.fetch_user(int(owner_id))
                    if owner:
                        embed = self._format_alert_message(
                            title, message, severity, incident_id
                        )
                        await owner.send(embed=embed)
                        self._record_alert(alert_key)
                        logger.info(f"Alert sent to owner {owner_id}: {title}")
                        return True
                except discord.Forbidden:
                    logger.warning(f"Cannot DM owner {owner_id}")
                except Exception as e:
                    logger.error(f"Failed to send DM to owner: {e}")
            
            # Try to send to alert channel
            channel_id = self.alert_channel_id
            if channel_id:
                try:
                    channel = await bot.fetch_channel(int(channel_id))
                    if channel:
                        embed = self._format_alert_message(
                            title, message, severity, incident_id
                        )
                        await channel.send(embed=embed)
                        self._record_alert(alert_key)
                        logger.info(f"Alert sent to channel {channel_id}: {title}")
                        return True
                except Exception as e:
                    logger.error(f"Failed to send alert to channel: {e}")
            
            logger.warning("No valid destination for alert")
            return False
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return False
    
    async def test_alert(self) -> bool:
        """Send a test alert to verify configuration."""
        return await self.send_alert(
            title="🧪 اختبار التنبيهات",
            message="هذا اختبار ناجح لإعدادات التنبيهات.\nThis is a successful test of alert settings.",
            severity=AlertSeverity.INFO,
            source="test",
            alert_type="test",
            bypass_cooldown=True
        )


# Convenience functions

async def send_alert(
    title: str,
    message: str,
    severity: AlertSeverity = AlertSeverity.INFO,
    source: str = "system",
    incident_id: Optional[str] = None,
    alert_type: Optional[str] = None
) -> bool:
    """Send an alert to the owner."""
    manager = AlertManager.get_instance()
    return await manager.send_alert(
        title=title,
        message=message,
        severity=severity,
        source=source,
        incident_id=incident_id,
        alert_type=alert_type
    )


async def send_critical_alert(title: str, message: str, incident_id: Optional[str] = None) -> bool:
    """Send a critical alert (bypasses cooldown)."""
    manager = AlertManager.get_instance()
    return await manager.send_alert(
        title=title,
        message=message,
        severity=AlertSeverity.CRITICAL,
        source="critical",
        incident_id=incident_id,
        alert_type="critical",
        bypass_cooldown=True
    )


async def send_error_alert(title: str, message: str, incident_id: Optional[str] = None) -> bool:
    """Send an error alert."""
    manager = AlertManager.get_instance()
    return await manager.send_alert(
        title=title,
        message=message,
        severity=AlertSeverity.ERROR,
        source="error",
        incident_id=incident_id,
        alert_type="error"
    )


async def send_warning_alert(title: str, message: str, incident_id: Optional[str] = None) -> bool:
    """Send a warning alert."""
    manager = AlertManager.get_instance()
    return await manager.send_alert(
        title=title,
        message=message,
        severity=AlertSeverity.WARNING,
        source="warning",
        incident_id=incident_id,
        alert_type="warning"
    )
