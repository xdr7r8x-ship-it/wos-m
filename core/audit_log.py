"""
WOS-M Audit Log System
© MANSOUR — WOS-M. All rights reserved.
"""
import json
from typing import Optional, Any, Dict
import logging

from core.database import db

logger = logging.getLogger(__name__)


class AuditCategory:
    """Audit log categories."""
    PERMISSIONS = "permissions"
    ALLIANCES = "alliances"
    PLAYERS = "players"
    GIFT_CODES = "gift_codes"
    EVENTS = "events"
    ATTENDANCE = "attendance"
    BEAR_TRACKING = "bear_tracking"
    NOTIFICATIONS = "notifications"
    MINISTERS = "ministers"
    THEMES = "themes"
    MAINTENANCE = "maintenance"
    OWNER_PANEL = "owner_panel"
    BUTTON_MANAGEMENT = "owner_panel"
    SETTINGS = "settings"
    SYSTEM = "system"


class AuditLog:
    """Centralized audit logging system."""

    @staticmethod
    async def log(
        user_id: str,
        action: str,
        category: str,
        details: Optional[Dict[str, Any]] = None,
        user_name: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> int:
        """Log an audit event."""
        details_json = json.dumps(details, ensure_ascii=False) if details else None

        cursor = await db.execute(
            "INSERT INTO audit_logs (user_id, user_name, action, category, details, ip_address) VALUES (?, ?, ?, ?, ?, ?)",
            (str(user_id), user_name, action, category, details_json, ip_address)
        )
        await db.commit()

        log_id = cursor.lastrowid
        logger.info(f"Audit Log [{category}]: User {user_id} performed {action}")

        return log_id

    @staticmethod
    async def get_logs(
        category: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """Get audit logs with optional filters."""
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if user_id:
            query += " AND user_id = ?"
            params.append(str(user_id))

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        return await db.fetchall(query, tuple(params))

    @staticmethod
    async def get_user_activity(user_id: str, limit: int = 50) -> list:
        """Get all activity for a specific user."""
        return await db.fetchall(
            "SELECT * FROM audit_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (str(user_id), limit)
        )

    @staticmethod
    async def get_category_logs(category: str, limit: int = 50, offset: int = 0) -> list:
        """Get logs for a specific category."""
        return await db.fetchall(
            "SELECT * FROM audit_logs WHERE category = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (category, limit, offset)
        )

    @staticmethod
    async def get_logs_by_category(category: str, limit: int = 50, offset: int = 0) -> list:
        """Backward-compatible alias used by owner-panel callbacks."""
        return await AuditLog.get_category_logs(category, limit=limit, offset=offset)

    @staticmethod
    async def clear_old_logs(days: int = 90) -> int:
        """Clear logs older than specified days."""
        cursor = await db.execute(
            "DELETE FROM audit_logs WHERE timestamp < datetime('now', ?||' days')",
            (f"-{days}",)
        )
        await db.commit()
        deleted_count = cursor.rowcount
        logger.info(f"Cleared {deleted_count} old audit logs")
        return deleted_count


audit_log = AuditLog()
