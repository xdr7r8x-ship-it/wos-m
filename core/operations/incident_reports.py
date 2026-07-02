"""
WOS-M Operations Control System - Incident Reports

This module handles storing, querying, and reporting on incidents.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    """Severity levels for incidents."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IncidentStatus(Enum):
    """Status of an incident."""
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class Incident:
    """Represents an operational incident."""
    id: str
    severity: IncidentSeverity
    source: str
    action: str
    error_type: str
    message: str
    traceback_hash: Optional[str] = None
    user_id: Optional[str] = None
    guild_id: Optional[str] = None
    channel_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: IncidentStatus = IncidentStatus.OPEN
    suggested_fix: Optional[str] = None
    occurrence_count: int = 1
    last_occurrence: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "severity": self.severity.value,
            "source": self.source,
            "action": self.action,
            "error_type": self.error_type,
            "message": self.message,
            "traceback_hash": self.traceback_hash,
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value,
            "suggested_fix": self.suggested_fix,
            "occurrence_count": self.occurrence_count,
            "last_occurrence": self.last_occurrence.isoformat(),
            "metadata": self.metadata
        }


class IncidentReportManager:
    """
    Manages incident reports and persistence.
    """
    
    _instance: Optional['IncidentReportManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._db_initialized = False
        self._incidents_cache: dict[str, Incident] = {}
        self._incident_counter = 0
    
    async def _ensure_db(self) -> None:
        """Ensure database tables exist."""
        if self._db_initialized:
            return
        
        try:
            from core.database import Database
            db = Database()
            await db.initialize()
            
            # Create incidents table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS operations_incidents (
                    id TEXT PRIMARY KEY,
                    severity TEXT NOT NULL,
                    source TEXT NOT NULL,
                    action TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    traceback_hash TEXT,
                    user_id TEXT,
                    guild_id TEXT,
                    channel_id TEXT,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    suggested_fix TEXT,
                    occurrence_count INTEGER DEFAULT 1,
                    last_occurrence TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            
            # Create indexes
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_incidents_status 
                ON operations_incidents(status)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_incidents_severity 
                ON operations_incidents(severity)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_incidents_created 
                ON operations_incidents(created_at)
            """)
            
            await db.close()
            self._db_initialized = True
            logger.info("Incident database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize incident database: {e}")
    
    def _generate_incident_id(self) -> str:
        """Generate a unique incident ID."""
        self._incident_counter += 1
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"INC-{timestamp}-{self._incident_counter:04d}"
    
    async def create_incident(
        self,
        severity: IncidentSeverity,
        source: str,
        action: str,
        error_type: str,
        message: str,
        user_id: Optional[str] = None,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        suggested_fix: Optional[str] = None,
        metadata: Optional[dict] = None,
        traceback_hash: Optional[str] = None
    ) -> Incident:
        """Create a new incident."""
        await self._ensure_db()
        
        incident = Incident(
            id=self._generate_incident_id(),
            severity=severity,
            source=source,
            action=action,
            error_type=error_type,
            message=message[:500],
            traceback_hash=traceback_hash,
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            suggested_fix=suggested_fix,
            metadata=metadata or {}
        )
        
        # Save to database
        try:
            from core.database import Database
            db = Database()
            await db.initialize()
            
            await db.execute("""
                INSERT INTO operations_incidents 
                (id, severity, source, action, error_type, message, traceback_hash,
                 user_id, guild_id, channel_id, created_at, updated_at, status,
                 suggested_fix, occurrence_count, last_occurrence, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                incident.id,
                incident.severity.value,
                incident.source,
                incident.action,
                incident.error_type,
                incident.message,
                incident.traceback_hash,
                incident.user_id,
                incident.guild_id,
                incident.channel_id,
                incident.created_at.isoformat(),
                incident.updated_at.isoformat(),
                incident.status.value,
                incident.suggested_fix,
                incident.occurrence_count,
                incident.last_occurrence.isoformat(),
                json.dumps(incident.metadata)
            ))
            
            await db.close()
            logger.info(f"Incident created: {incident.id}")
            
        except Exception as e:
            logger.error(f"Failed to save incident: {e}")
        
        self._incidents_cache[incident.id] = incident
        return incident
    
    async def update_incident_status(
        self,
        incident_id: str,
        status: IncidentStatus,
        note: Optional[str] = None
    ) -> bool:
        """Update incident status."""
        await self._ensure_db()
        
        try:
            from core.database import Database
            db = Database()
            await db.initialize()
            
            update_fields = ["status = ?", "updated_at = ?"]
            params: list = [status.value, datetime.now(timezone.utc).isoformat()]
            
            if status == IncidentStatus.RESOLVED:
                update_fields.append("resolved_at = ?")
                params.append(datetime.now(timezone.utc).isoformat())
            
            if note and self._incidents_cache.get(incident_id):
                self._incidents_cache[incident_id].metadata['note'] = note
                update_fields.append("metadata = ?")
                params.append(json.dumps(self._incidents_cache[incident_id].metadata))
            
            params.append(incident_id)
            
            await db.execute(
                f"UPDATE operations_incidents SET {', '.join(update_fields)} WHERE id = ?",
                params
            )
            
            if incident_id in self._incidents_cache:
                self._incidents_cache[incident_id].status = status
                self._incidents_cache[incident_id].updated_at = datetime.now(timezone.utc)
                if status == IncidentStatus.RESOLVED:
                    self._incidents_cache[incident_id].resolved_at = datetime.now(timezone.utc)
            
            await db.close()
            logger.info(f"Incident {incident_id} status updated to {status.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update incident: {e}")
            return False
    
    async def resolve_incident(self, incident_id: str) -> bool:
        """Mark incident as resolved."""
        return await self.update_incident_status(incident_id, IncidentStatus.RESOLVED)
    
    async def close_incident(self, incident_id: str) -> bool:
        """Mark incident as closed."""
        return await self.update_incident_status(incident_id, IncidentStatus.CLOSED)
    
    async def list_open_incidents(
        self,
        limit: int = 50,
        severity: Optional[IncidentSeverity] = None
    ) -> list[Incident]:
        """List open incidents."""
        await self._ensure_db()
        
        try:
            from core.database import Database
            db = Database()
            await db.initialize()
            
            query = "SELECT * FROM operations_incidents WHERE status IN ('open', 'investigating')"
            params: list = []
            
            if severity:
                query += " AND severity = ?"
                params.append(severity.value)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            results = await db.fetchall(query, tuple(params))
            await db.close()
            
            incidents = []
            for row in results:
                incident = self._row_to_incident(row)
                incidents.append(incident)
                self._incidents_cache[incident.id] = incident
            
            return incidents
            
        except Exception as e:
            logger.error(f"Failed to list incidents: {e}")
            return []
    
    async def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Get a specific incident."""
        # Check cache first
        if incident_id in self._incidents_cache:
            return self._incidents_cache[incident_id]
        
        await self._ensure_db()
        
        try:
            from core.database import Database
            db = Database()
            await db.initialize()
            
            result = await db.fetchone(
                "SELECT * FROM operations_incidents WHERE id = ?",
                (incident_id,)
            )
            
            await db.close()
            
            if result:
                incident = self._row_to_incident(result)
                self._incidents_cache[incident.id] = incident
                return incident
            
        except Exception as e:
            logger.error(f"Failed to get incident: {e}")
        
        return None
    
    def _row_to_incident(self, row: dict) -> Incident:
        """Convert database row to Incident object."""
        return Incident(
            id=row['id'],
            severity=IncidentSeverity(row['severity']),
            source=row['source'],
            action=row['action'],
            error_type=row['error_type'],
            message=row['message'],
            traceback_hash=row.get('traceback_hash'),
            user_id=row.get('user_id'),
            guild_id=row.get('guild_id'),
            channel_id=row.get('channel_id'),
            created_at=datetime.fromisoformat(row['created_at']),
            resolved_at=datetime.fromisoformat(row['resolved_at']) if row.get('resolved_at') else None,
            updated_at=datetime.fromisoformat(row['updated_at']),
            status=IncidentStatus(row['status']),
            suggested_fix=row.get('suggested_fix'),
            occurrence_count=row.get('occurrence_count', 1),
            last_occurrence=datetime.fromisoformat(row['last_occurrence']),
            metadata=json.loads(row.get('metadata', '{}'))
        )
    
    async def summarize_incidents(
        self,
        since_hours: int = 24
    ) -> dict:
        """Get a summary of incidents."""
        await self._ensure_db()
        
        since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        
        try:
            from core.database import Database
            db = Database()
            await db.initialize()
            
            # Total incidents
            total = await db.fetchone(
                "SELECT COUNT(*) as cnt FROM operations_incidents WHERE created_at >= ?",
                (since.isoformat(),)
            )
            
            # By severity
            by_severity = {}
            for sev in IncidentSeverity:
                result = await db.fetchone(
                    "SELECT COUNT(*) as cnt FROM operations_incidents WHERE created_at >= ? AND severity = ?",
                    (since.isoformat(), sev.value)
                )
                by_severity[sev.value] = result['cnt'] if result else 0
            
            # By status
            by_status = {}
            for status in IncidentStatus:
                result = await db.fetchone(
                    "SELECT COUNT(*) as cnt FROM operations_incidents WHERE created_at >= ? AND status = ?",
                    (since.isoformat(), status.value)
                )
                by_status[status.value] = result['cnt'] if result else 0
            
            # Open critical
            open_critical = await db.fetchone(
                "SELECT COUNT(*) as cnt FROM operations_incidents WHERE status IN ('open', 'investigating') AND severity = 'critical'"
            )
            
            await db.close()
            
            return {
                "period_hours": since_hours,
                "period_start": since.isoformat(),
                "total_incidents": total['cnt'] if total else 0,
                "by_severity": by_severity,
                "by_status": by_status,
                "open_critical": open_critical['cnt'] if open_critical else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to summarize incidents: {e}")
            return {"error": str(e)}
    
    async def generate_daily_incident_report(self) -> str:
        """Generate a daily incident report."""
        summary = await self.summarize_incidents(since_hours=24)
        open_incidents = await self.list_open_incidents(limit=20)
        
        report = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📊 تقرير الحوادث اليومي",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📅 التاريخ: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            "",
            "📈 الملخص:",
            f"  • إجمالي الحوادث (24h): {summary.get('total_incidents', 0)}",
            f"  • حرجة: {summary.get('by_severity', {}).get('critical', 0)}",
            f"  • أخطاء: {summary.get('by_severity', {}).get('error', 0)}",
            f"  • تحذيرات: {summary.get('by_severity', {}).get('warning', 0)}",
            "",
            "🔓 الحوادث المفتوحة:",
        ]
        
        if open_incidents:
            for inc in open_incidents[:10]:
                emoji = {
                    "critical": "🔴",
                    "error": "🟠",
                    "warning": "🟡",
                    "info": "🔵"
                }.get(inc.severity.value, "⚪")
                report.append(
                    f"  {emoji} [{inc.id}] {inc.message[:50]}... ({inc.severity.value})"
                )
        else:
            report.append("  ✅ لا توجد حوادث مفتوحة")
        
        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        return "\n".join(report)
    
    async def generate_release_incident_report(self) -> str:
        """Generate a report for release."""
        summary = await self.summarize_incidents(since_hours=168)  # 7 days
        
        report = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📋 تقرير حوادث Release",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📅 الفترة: آخر 7 أيام",
            "",
            "📈 الملخص:",
            f"  • إجمالي الحوادث: {summary.get('total_incidents', 0)}",
            f"  • حرجة: {summary.get('by_severity', {}).get('critical', 0)}",
            f"  • أخطاء: {summary.get('by_severity', {}).get('error', 0)}",
            f"  • تحذيرات: {summary.get('by_severity', {}).get('warning', 0)}",
            "",
            "📊 حسب الحالة:",
            f"  • مفتوحة: {summary.get('by_status', {}).get('open', 0)}",
            f"  • قيد التحقيق: {summary.get('by_status', {}).get('investigating', 0)}",
            f"  • محلولة: {summary.get('by_status', {}).get('resolved', 0)}",
            f"  • مغلقة: {summary.get('by_status', {}).get('closed', 0)}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        
        return "\n".join(report)


# Global instance
_manager: Optional[IncidentReportManager] = None


def get_incident_manager() -> IncidentReportManager:
    """Get or create the global incident manager."""
    global _manager
    if _manager is None:
        _manager = IncidentReportManager()
    return _manager
