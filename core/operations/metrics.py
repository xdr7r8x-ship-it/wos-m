"""
WOS-M Operations Control System - Metrics

This module collects and manages system metrics and statistics.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MetricsSnapshot:
    """A snapshot of system metrics at a point in time."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    uptime_seconds: float = 0
    commands: int = 0
    interactions: int = 0
    failed_interactions: int = 0
    success_rate: float = 100.0
    avg_callback_duration_ms: float = 0
    api_calls: dict = field(default_factory=dict)
    db_errors: int = 0
    queue_size: int = 0
    backups_count: int = 0
    incidents_count: int = 0
    open_incidents: int = 0
    rate_limiter_throttles: int = 0


class MetricsCollector:
    """
    Collects and manages system metrics.
    """
    
    _instance: Optional['MetricsCollector'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._start_time = time.time()
        
        # Runtime metrics
        self._commands = 0
        self._interactions = 0
        self._failed_interactions = 0
        self._callback_durations: list[float] = []
        self._api_calls = {"success": 0, "failure": 0}
        self._api_latencies: list[float] = []
        self._db_errors = 0
        self._rate_limiter_throttles = 0
    
    def record_command(self) -> None:
        """Record a command execution."""
        self._commands += 1
    
    def record_interaction(self, success: bool = True) -> None:
        """Record an interaction."""
        self._interactions += 1
        if not success:
            self._failed_interactions += 1
    
    def record_callback_duration(self, duration_ms: float) -> None:
        """Record callback execution duration."""
        self._callback_durations.append(duration_ms)
        if len(self._callback_durations) > 1000:
            self._callback_durations.pop(0)
    
    def record_api_call(self, success: bool, latency_ms: float = 0) -> None:
        """Record an API call."""
        if success:
            self._api_calls["success"] += 1
        else:
            self._api_calls["failure"] += 1
        
        if latency_ms > 0:
            self._api_latencies.append(latency_ms)
            if len(self._api_latencies) > 1000:
                self._api_latencies.pop(0)
    
    def record_db_error(self) -> None:
        """Record a database error."""
        self._db_errors += 1
    
    def record_rate_limiter_throttle(self) -> None:
        """Record a rate limiter throttle."""
        self._rate_limiter_throttles += 1
    
    def get_uptime_seconds(self) -> float:
        """Get uptime in seconds."""
        return time.time() - self._start_time
    
    def get_uptime_formatted(self) -> str:
        """Get uptime as formatted string."""
        seconds = self.get_uptime_seconds()
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        return " ".join(parts) if parts else "<1m"
    
    def collect_snapshot(self) -> MetricsSnapshot:
        """Collect a snapshot of current metrics."""
        # Calculate derived metrics
        success_rate = 100.0
        if self._interactions > 0:
            success_rate = round((1 - self._failed_interactions / self._interactions) * 100, 2)
        
        avg_duration = 0.0
        if self._callback_durations:
            avg_duration = round(sum(self._callback_durations) / len(self._callback_durations), 2)
        
        avg_latency = 0.0
        if self._api_latencies:
            avg_latency = round(sum(self._api_latencies) / len(self._api_latencies), 2)
        
        # Get queue size
        queue_size = 0
        try:
            from core.process_queue import ProcessQueue
            if hasattr(ProcessQueue, '_instance') and ProcessQueue._instance:
                queue_size = getattr(ProcessQueue._instance, 'queue_size', 0)
        except Exception:
            pass
        
        # Get backup count
        backups_count = 0
        open_incidents = 0
        try:
            from core.operations.backup import get_backup_manager
            backup_mgr = get_backup_manager()
            import asyncio
            backups = asyncio.run(backup_mgr.list_backups(limit=100))
            backups_count = len(backups)
        except Exception:
            pass
        
        # Get incident count
        try:
            from core.operations.incident_reports import get_incident_manager
            incident_mgr = get_incident_manager()
            import asyncio
            incidents = asyncio.run(incident_mgr.list_open_incidents(limit=100))
            open_incidents = len(incidents)
        except Exception:
            pass
        
        return MetricsSnapshot(
            uptime_seconds=round(self.get_uptime_seconds(), 1),
            commands=self._commands,
            interactions=self._interactions,
            failed_interactions=self._failed_interactions,
            success_rate=success_rate,
            avg_callback_duration_ms=avg_duration,
            api_calls={
                "total": self._api_calls["success"] + self._api_calls["failure"],
                "success": self._api_calls["success"],
                "failure": self._api_calls["failure"],
                "avg_latency_ms": avg_latency
            },
            db_errors=self._db_errors,
            queue_size=queue_size,
            backups_count=backups_count,
            incidents_count=sum(self._api_calls.values()),
            open_incidents=open_incidents,
            rate_limiter_throttles=self._rate_limiter_throttles
        )
    
    def format_metrics(self, snapshot: Optional[MetricsSnapshot] = None) -> str:
        """Format metrics for display."""
        if snapshot is None:
            snapshot = self.collect_snapshot()
        
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📊 Metrics Dashboard",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "⏱️ **Uptime:** " + self.get_uptime_formatted(),
            "",
            "🎮 **Commands:** " + str(snapshot.commands),
            "🔄 **Interactions:** " + str(snapshot.interactions),
            "❌ **Failed:** " + str(snapshot.failed_interactions),
            "📈 **Success Rate:** " + str(snapshot.success_rate) + "%",
            "",
            "⚡ **Avg Callback:** " + str(snapshot.avg_callback_duration_ms) + "ms",
            "",
            "🌐 **API Calls:**",
            "   Total: " + str(snapshot.api_calls.get("total", 0)),
            "   Success: " + str(snapshot.api_calls.get("success", 0)),
            "   Failed: " + str(snapshot.api_calls.get("failure", 0)),
            "   Avg Latency: " + str(snapshot.api_calls.get("avg_latency_ms", 0)) + "ms",
            "",
            "🗄️ **DB Errors:** " + str(snapshot.db_errors),
            "🚦 **Rate Throttles:** " + str(snapshot.rate_limiter_throttles),
            "📬 **Queue Size:** " + str(snapshot.queue_size),
            "",
            "💾 **Backups:** " + str(snapshot.backups_count),
            "🚨 **Open Incidents:** " + str(snapshot.open_incidents),
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        
        return "\n".join(lines)
    
    def get_dict(self, snapshot: Optional[MetricsSnapshot] = None) -> dict:
        """Get metrics as dictionary."""
        if snapshot is None:
            snapshot = self.collect_snapshot()
        
        return {
            "uptime_formatted": self.get_uptime_formatted(),
            "uptime_seconds": snapshot.uptime_seconds,
            "commands": snapshot.commands,
            "interactions": snapshot.interactions,
            "failed_interactions": snapshot.failed_interactions,
            "success_rate": snapshot.success_rate,
            "avg_callback_duration_ms": snapshot.avg_callback_duration_ms,
            "api_calls": snapshot.api_calls,
            "db_errors": snapshot.db_errors,
            "queue_size": snapshot.queue_size,
            "backups_count": snapshot.backups_count,
            "open_incidents": snapshot.open_incidents,
            "rate_limiter_throttles": snapshot.rate_limiter_throttles
        }


# Global instance
_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector
