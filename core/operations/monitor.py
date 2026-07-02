"""
WOS-M Operations Control System - Runtime Monitoring

This module monitors the bot during runtime, tracking exceptions,
failed interactions, and system metrics.
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import traceback

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


class ErrorType(Enum):
    """Types of errors that can be tracked."""
    EXCEPTION = "exception"
    FAILED_INTERACTION = "failed_interaction"
    UNKNOWN_INTERACTION = "unknown_interaction"
    ALREADY_RESPONDED = "already_responded"
    MISSING_PERMISSION = "missing_permission"
    DATABASE_LOCKED = "database_locked"
    API_TIMEOUT = "api_timeout"
    API_RATE_LIMIT = "api_rate_limit"
    QUEUE_BACKLOG = "queue_backlog"
    MEMORY_GROWTH = "memory_memory"
    HIGH_LATENCY = "high_latency"
    FAILED_CALLBACK = "failed_callback"
    SLOW_CALLBACK = "slow_callback"
    FAILED_MODAL = "failed_modal"
    FAILED_SELECT = "failed_select"
    FAILED_FILE_EXPORT = "failed_file_export"
    FAILED_BACKUP = "failed_backup"
    INCIDENT = "incident"


@dataclass
class Incident:
    """Represents a runtime incident or error."""
    id: str
    severity: IncidentSeverity
    source: str
    action: str
    error_type: ErrorType
    message: str
    traceback_hash: Optional[str] = None
    user_id: Optional[str] = None
    guild_id: Optional[str] = None
    channel_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    status: IncidentStatus = IncidentStatus.OPEN
    suggested_fix: Optional[str] = None
    occurrence_count: int = 1
    last_occurrence: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "severity": self.severity.value,
            "source": self.source,
            "action": self.action,
            "error_type": self.error_type.value,
            "message": self.message,
            "traceback_hash": self.traceback_hash,
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "status": self.status.value,
            "suggested_fix": self.suggested_fix,
            "occurrence_count": self.occurrence_count,
            "last_occurrence": self.last_occurrence.isoformat()
        }


class RuntimeMonitor:
    """
    Runtime monitor that tracks incidents and errors during bot operation.
    """
    
    _instance: Optional['RuntimeMonitor'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._incidents: dict[str, Incident] = {}
        self._incident_counter = 0
        self._alert_cooldown: dict[str, datetime] = {}
        self._alert_cooldown_seconds = 300  # 5 minutes default cooldown
        self._max_incidents = 1000
        
        # Metrics
        self._command_count = 0
        self._interaction_count = 0
        self._failed_interaction_count = 0
        self._callback_durations: list[float] = []
        self._api_calls = {"success": 0, "failure": 0}
        self._db_errors = 0
    
    @classmethod
    def get_instance(cls) -> 'RuntimeMonitor':
        """Get the singleton instance."""
        return cls()
    
    def _generate_incident_id(self) -> str:
        """Generate a unique incident ID."""
        self._incident_counter += 1
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"INC-{timestamp}-{self._incident_counter:04d}"
    
    def _hash_traceback(self, tb_str: str) -> str:
        """Create a hash of the traceback for grouping similar errors."""
        return hashlib.md5(tb_str.encode()).hexdigest()[:12]
    
    def can_send_alert(self, source: str) -> bool:
        """Check if an alert can be sent (cooldown check)."""
        now = datetime.now(timezone.utc)
        
        if source not in self._alert_cooldown:
            return True
        
        last_alert = self._alert_cooldown[source]
        elapsed = (now - last_alert).total_seconds()
        
        return elapsed >= self._alert_cooldown_seconds
    
    def set_alert_cooldown(self, source: str) -> None:
        """Set cooldown for alerts from a source."""
        self._alert_cooldown[source] = datetime.now(timezone.utc)
    
    def set_cooldown_seconds(self, seconds: int) -> None:
        """Set the alert cooldown duration."""
        self._alert_cooldown_seconds = max(60, seconds)  # Minimum 1 minute
    
    def track_exception(
        self,
        source: str,
        action: str,
        exception: Exception,
        user_id: Optional[str] = None,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None
    ) -> Incident:
        """Track an exception as an incident."""
        tb_str = traceback.format_exc()
        tb_hash = self._hash_traceback(tb_str)
        
        # Check if similar incident exists
        for inc in self._incidents.values():
            if inc.traceback_hash == tb_hash and inc.status == IncidentStatus.OPEN:
                inc.occurrence_count += 1
                inc.last_occurrence = datetime.now(timezone.utc)
                logger.info(f"Incident incremented: {inc.id} (count: {inc.occurrence_count})")
                return inc
        
        # Create new incident
        incident = Incident(
            id=self._generate_incident_id(),
            severity=self._determine_severity(exception),
            source=source,
            action=action,
            error_type=ErrorType.EXCEPTION,
            message=str(exception)[:500],
            traceback_hash=tb_hash,
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            suggested_fix=self._suggest_fix(exception)
        )
        
        self._add_incident(incident)
        return incident
    
    def track_error(
        self,
        source: str,
        action: str,
        error_type: ErrorType,
        message: str,
        severity: IncidentSeverity = IncidentSeverity.ERROR,
        user_id: Optional[str] = None,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        suggested_fix: Optional[str] = None
    ) -> Incident:
        """Track a generic error as an incident."""
        # Check for similar open incident
        for inc in self._incidents.values():
            if inc.source == source and inc.action == action and inc.status == IncidentStatus.OPEN:
                inc.occurrence_count += 1
                inc.last_occurrence = datetime.now(timezone.utc)
                return inc
        
        incident = Incident(
            id=self._generate_incident_id(),
            severity=severity,
            source=source,
            action=action,
            error_type=error_type,
            message=message[:500],
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            suggested_fix=suggested_fix
        )
        
        self._add_incident(incident)
        return incident
    
    def _add_incident(self, incident: Incident) -> None:
        """Add incident and manage collection size."""
        self._incidents[incident.id] = incident
        
        # Cleanup old closed incidents if over limit
        if len(self._incidents) > self._max_incidents:
            closed = [k for k, v in self._incidents.items() 
                     if v.status in (IncidentStatus.CLOSED, IncidentStatus.RESOLVED)]
            for key in closed[:100]:
                del self._incidents[key]
        
        logger.warning(f"Incident created: {incident.id} - {incident.error_type.value} - {incident.message[:100]}")
    
    def _determine_severity(self, exception: Exception) -> IncidentSeverity:
        """Determine severity based on exception type."""
        exception_type = type(exception).__name__.lower()
        
        if any(word in exception_type for word in ['crash', 'fatal', 'critical']):
            return IncidentSeverity.CRITICAL
        elif any(word in exception_type for word in ['timeout', 'connection', 'auth']):
            return IncidentSeverity.ERROR
        elif any(word in exception_type for word in ['warning', 'deprecat']):
            return IncidentSeverity.WARNING
        else:
            return IncidentSeverity.ERROR
    
    def _suggest_fix(self, exception: Exception) -> str:
        """Suggest a fix based on exception type."""
        exception_type = type(exception).__name__.lower()
        
        suggestions = {
            'timeout': "Check API availability and network connection",
            'connection': "Verify network and API endpoints",
            'database': "Check database file and permissions",
            'permission': "Verify bot permissions in Discord",
            'auth': "Check API keys and tokens",
            'rate_limit': "Implement exponential backoff",
            'disk': "Free up disk space",
            'memory': "Monitor for memory leaks"
        }
        
        for key, suggestion in suggestions.items():
            if key in exception_type:
                return suggestion
        
        return "Check logs for details and investigate"
    
    def get_open_incidents(self) -> list[Incident]:
        """Get all open incidents."""
        return [
            inc for inc in self._incidents.values()
            if inc.status in (IncidentStatus.OPEN, IncidentStatus.INVESTIGATING)
        ]
    
    def get_incidents_by_severity(self, severity: IncidentSeverity) -> list[Incident]:
        """Get incidents by severity."""
        return [inc for inc in self._incidents.values() if inc.severity == severity]
    
    def resolve_incident(self, incident_id: str) -> bool:
        """Mark an incident as resolved."""
        if incident_id in self._incidents:
            inc = self._incidents[incident_id]
            inc.status = IncidentStatus.RESOLVED
            inc.resolved_at = datetime.now(timezone.utc)
            logger.info(f"Incident resolved: {incident_id}")
            return True
        return False
    
    def close_incident(self, incident_id: str) -> bool:
        """Mark an incident as closed."""
        if incident_id in self._incidents:
            inc = self._incidents[incident_id]
            inc.status = IncidentStatus.CLOSED
            if inc.resolved_at is None:
                inc.resolved_at = datetime.now(timezone.utc)
            return True
        return False
    
    def get_incident_summary(self) -> dict:
        """Get a summary of all incidents."""
        open_incidents = self.get_open_incidents()
        
        return {
            "total_incidents": len(self._incidents),
            "open_incidents": len(open_incidents),
            "by_severity": {
                "critical": len(self.get_incidents_by_severity(IncidentSeverity.CRITICAL)),
                "error": len(self.get_incidents_by_severity(IncidentSeverity.ERROR)),
                "warning": len(self.get_incidents_by_severity(IncidentSeverity.WARNING)),
                "info": len(self.get_incidents_by_severity(IncidentSeverity.INFO))
            },
            "recent_open": [
                {
                    "id": inc.id,
                    "severity": inc.severity.value,
                    "message": inc.message[:100],
                    "created_at": inc.created_at.isoformat()
                }
                for inc in sorted(open_incidents, key=lambda x: x.created_at, reverse=True)[:10]
            ]
        }
    
    # Metrics tracking
    
    def record_command(self) -> None:
        """Record a command execution."""
        self._command_count += 1
    
    def record_interaction(self, success: bool = True) -> None:
        """Record an interaction."""
        self._interaction_count += 1
        if not success:
            self._failed_interaction_count += 1
    
    def record_callback_duration(self, duration_ms: float) -> None:
        """Record callback execution duration."""
        self._callback_durations.append(duration_ms)
        if len(self._callback_durations) > 100:
            self._callback_durations.pop(0)
    
    def record_api_call(self, success: bool) -> None:
        """Record an API call."""
        if success:
            self._api_calls["success"] += 1
        else:
            self._api_calls["failure"] += 1
    
    def record_db_error(self) -> None:
        """Record a database error."""
        self._db_errors += 1
    
    def get_metrics(self) -> dict:
        """Get current metrics."""
        avg_duration = sum(self._callback_durations) / len(self._callback_durations) if self._callback_durations else 0
        api_total = self._api_calls["success"] + self._api_calls["failure"]
        api_success_rate = (self._api_calls["success"] / api_total * 100) if api_total > 0 else 100
        
        return {
            "commands": self._command_count,
            "interactions": self._interaction_count,
            "failed_interactions": self._failed_interaction_count,
            "success_rate": round((1 - self._failed_interaction_count / max(1, self._interaction_count)) * 100, 2),
            "avg_callback_duration_ms": round(avg_duration, 2),
            "api_calls": {
                "total": api_total,
                "success": self._api_calls["success"],
                "failure": self._api_calls["failure"],
                "success_rate": round(api_success_rate, 2)
            },
            "db_errors": self._db_errors,
            "open_incidents": len(self.get_open_incidents())
        }


# Global monitor instance
_monitor: Optional[RuntimeMonitor] = None


def get_monitor() -> RuntimeMonitor:
    """Get or create the global monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = RuntimeMonitor()
    return _monitor
