"""
WOS-M Operations Control System - Audit Logging

This module handles comprehensive audit logging for all administrative operations.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AuditAction(Enum):
    """Types of auditable actions."""
    # Settings
    SETTINGS_CHANGE = "settings_change"
    SETTINGS_RESET = "settings_reset"
    
    # Backup/Restore
    BACKUP_CREATE = "backup_create"
    BACKUP_VERIFY = "backup_verify"
    BACKUP_RESTORE = "backup_restore"
    BACKUP_DELETE = "backup_delete"
    
    # Upgrade/Rollback
    UPGRADE_PLAN = "upgrade_plan"
    UPGRADE_APPLY = "upgrade_apply"
    UPGRADE_COMPLETE = "upgrade_complete"
    ROLLBACK_PLAN = "rollback_plan"
    ROLLBACK_APPLY = "rollback_apply"
    
    # Permissions
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke"
    PERMISSION_CHANGE = "permission_change"
    
    # Feature management
    FEATURE_DISABLE = "feature_disable"
    FEATURE_ENABLE = "feature_enable"
    
    # Security
    AUTH_FAILURE = "auth_failure"
    PERMISSION_DENIED = "permission_denied"
    SENSITIVE_OPERATION = "sensitive_operation"
    
    # Operations
    SELF_HEALING = "self_healing"
    INCIDENT_CREATE = "incident_create"
    INCIDENT_RESOLVE = "incident_resolve"
    HEALTH_CHECK = "health_check"
    
    # Data
    DATA_EXPORT = "data_export"
    DATA_DELETE = "data_delete"


class RiskLevel(Enum):
    """Risk level of an operation."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Sensitive fields that should never be logged
SENSITIVE_FIELDS = {
    'token', 'password', 'secret', 'api_key', 'authorization',
    'auth', 'credential', 'private_key', 'access_token', 'refresh_token',
    'DISCORD_BOT_TOKEN', 'BOT_TOKEN', 'API_TOKEN', 'SECRET'
}


@dataclass
class AuditEntry:
    """Represents an audit log entry."""
    id: str
    user_id: Optional[str]
    action: AuditAction
    module: str
    target: Optional[str]
    before: Optional[dict] = None
    after: Optional[dict] = None
    status: str = "success"  # success, failure, denied
    ip_address: Optional[str] = None
    guild_id: Optional[str] = None
    channel_id: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.LOW
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action.value,
            "module": self.module,
            "target": self.target,
            "before": self.before,
            "after": self.after,
            "status": self.status,
            "ip_address": self.ip_address,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "risk_level": self.risk_level.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


def _sanitize_data(data: Optional[dict]) -> Optional[dict]:
    """Remove sensitive fields from data."""
    if data is None:
        return None
    
    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(s in key_lower for s in SENSITIVE_FIELDS):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_data(value)
        else:
            sanitized[key] = value
    
    return sanitized


class AuditLogger:
    """
    Manages audit logging for all administrative operations.
    """
    
    _instance: Optional['AuditLogger'] = None
    _db_initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._entry_counter = 0
    
    @classmethod
    def get_instance(cls) -> 'AuditLogger':
        """Get the singleton instance."""
        return cls()
    
    def _generate_id(self) -> str:
        """Generate unique audit entry ID."""
        self._entry_counter += 1
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"AUD-{timestamp}-{self._entry_counter:06d}"
    
    async def _ensure_db(self) -> None:
        """Ensure audit log table exists."""
        if AuditLogger._db_initialized:
            return
        
        try:
            from core.database import Database
            db = Database()
            await db.initialize()
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS operations_audit (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    action TEXT NOT NULL,
                    module TEXT NOT NULL,
                    target TEXT,
                    before TEXT,
                    after TEXT,
                    status TEXT NOT NULL DEFAULT 'success',
                    ip_address TEXT,
                    guild_id TEXT,
                    channel_id TEXT,
                    risk_level TEXT DEFAULT 'low',
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
            """)
            
            # Create indexes
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_user 
                ON operations_audit(user_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_action 
                ON operations_audit(action)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_created 
                ON operations_audit(created_at)
            """)
            
            await db.close()
            AuditLogger._db_initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize audit table: {e}")
    
    async def log(
        self,
        user_id: Optional[str],
        action: AuditAction,
        module: str,
        target: Optional[str] = None,
        before: Optional[dict] = None,
        after: Optional[dict] = None,
        status: str = "success",
        ip_address: Optional[str] = None,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        risk_level: RiskLevel = RiskLevel.LOW,
        metadata: Optional[dict] = None
    ) -> AuditEntry:
        """
        Log an administrative action.
        
        Args:
            user_id: ID of the user performing the action
            action: Type of action
            module: Module/component where action occurred
            target: Target of the action
            before: State before the action
            after: State after the action
            status: Success/failure/denied
            ip_address: IP address if available
            guild_id: Discord guild ID
            channel_id: Discord channel ID
            risk_level: Risk level of the operation
            metadata: Additional metadata
        
        Returns:
            Created audit entry
        """
        await self._ensure_db()
        
        # Sanitize sensitive data
        before_sanitized = _sanitize_data(before)
        after_sanitized = _sanitize_data(after)
        metadata_sanitized = _sanitize_data(metadata) if metadata else {}
        
        entry = AuditEntry(
            id=self._generate_id(),
            user_id=user_id,
            action=action,
            module=module,
            target=target,
            before=before_sanitized,
            after=after_sanitized,
            status=status,
            ip_address=ip_address,
            guild_id=guild_id,
            channel_id=channel_id,
            risk_level=risk_level,
            metadata=metadata_sanitized
        )
        
        try:
            from core.database import Database
            db = Database()
            await db.initialize()
            
            await db.execute("""
                INSERT INTO operations_audit 
                (id, user_id, action, module, target, before, after, status,
                 ip_address, guild_id, channel_id, risk_level, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.id,
                entry.user_id,
                entry.action.value,
                entry.module,
                entry.target,
                json.dumps(entry.before) if entry.before else None,
                json.dumps(entry.after) if entry.after else None,
                entry.status,
                entry.ip_address,
                entry.guild_id,
                entry.channel_id,
                entry.risk_level.value,
                json.dumps(entry.metadata),
                entry.created_at.isoformat()
            ))
            
            await db.close()
            logger.info(f"Audit logged: {entry.action.value} by {entry.user_id} - {entry.status}")
            
        except Exception as e:
            logger.error(f"Failed to save audit entry: {e}")
        
        return entry
    
    async def get_entries(
        self,
        limit: int = 100,
        action: Optional[AuditAction] = None,
        user_id: Optional[str] = None,
        module: Optional[str] = None,
        risk_level: Optional[RiskLevel] = None
    ) -> list[AuditEntry]:
        """Get audit entries with filters."""
        await self._ensure_db()
        
        try:
            from core.database import Database
            db = Database()
            await db.initialize()
            
            query = "SELECT * FROM operations_audit WHERE 1=1"
            params: list = []
            
            if action:
                query += " AND action = ?"
                params.append(action.value)
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if module:
                query += " AND module = ?"
                params.append(module)
            
            if risk_level:
                query += " AND risk_level = ?"
                params.append(risk_level.value)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            results = await db.fetchall(query, tuple(params))
            await db.close()
            
            entries = []
            for row in results:
                entries.append(AuditEntry(
                    id=row['id'],
                    user_id=row.get('user_id'),
                    action=AuditAction(row['action']),
                    module=row['module'],
                    target=row.get('target'),
                    before=json.loads(row['before']) if row.get('before') else None,
                    after=json.loads(row['after']) if row.get('after') else None,
                    status=row['status'],
                    ip_address=row.get('ip_address'),
                    guild_id=row.get('guild_id'),
                    channel_id=row.get('channel_id'),
                    risk_level=RiskLevel(row.get('risk_level', 'low')),
                    metadata=json.loads(row.get('metadata', '{}')),
                    created_at=datetime.fromisoformat(row['created_at'])
                ))
            
            return entries
            
        except Exception as e:
            logger.error(f"Failed to get audit entries: {e}")
            return []
    
    async def get_recent_high_risk(self, limit: int = 50) -> list[AuditEntry]:
        """Get recent high-risk audit entries."""
        return await self.get_entries(
            limit=limit,
            risk_level=RiskLevel.HIGH
        ) + await self.get_entries(
            limit=limit,
            risk_level=RiskLevel.CRITICAL
        )


# Convenience function
async def audit_log(
    user_id: Optional[str],
    action: AuditAction,
    module: str,
    target: Optional[str] = None,
    before: Optional[dict] = None,
    after: Optional[dict] = None,
    status: str = "success",
    guild_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    risk_level: RiskLevel = RiskLevel.LOW,
    metadata: Optional[dict] = None
) -> AuditEntry:
    """Log an administrative action."""
    logger = AuditLogger.get_instance()
    return await logger.log(
        user_id=user_id,
        action=action,
        module=module,
        target=target,
        before=before,
        after=after,
        status=status,
        guild_id=guild_id,
        channel_id=channel_id,
        risk_level=risk_level,
        metadata=metadata
    )
