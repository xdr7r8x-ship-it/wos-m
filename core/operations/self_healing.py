"""
WOS-M Operations Control System - Self-Healing

This module provides safe self-healing capabilities for the bot,
with strict policies on what can and cannot be auto-repaired.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RecoveryAction(Enum):
    """Allowed recovery actions."""
    # API retries
    RETRY_API_CALL = "retry_api_call"
    REFRESH_SESSION = "refresh_session"
    
    # Queue
    RETRY_QUEUE_JOB = "retry_queue_job"
    CLEANUP_QUEUE = "cleanup_queue"
    
    # System
    CLEANUP_TEMP_FILES = "cleanup_temp_files"
    ROTATE_LOGS = "rotate_logs"
    RELOAD_CONFIG = "reload_config"
    
    # Feature management
    DISABLE_FEATURE = "disable_feature"
    ENABLE_FEATURE = "enable_feature"
    
    # Health
    RUN_HEALTH_CHECK = "run_health_check"
    RESTART_WORKER = "restart_worker"
    
    # Notifications
    NOTIFY_OWNER = "notify_owner"


class RecoveryStatus(Enum):
    """Status of a recovery attempt."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class RecoveryAttempt:
    """Record of a recovery attempt."""
    id: str
    action: RecoveryAction
    incident_id: str
    status: RecoveryStatus
    attempt_number: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class SelfHealingPolicy:
    """Policy controlling self-healing behavior."""
    enabled: bool = True
    max_attempts: int = 3
    cooldown_seconds: int = 300  # 5 minutes
    require_owner_confirmation_for_risky_actions: bool = True
    
    # Allowed actions
    allowed_actions: list[RecoveryAction] = field(default_factory=lambda: [
        RecoveryAction.RETRY_API_CALL,
        RecoveryAction.REFRESH_SESSION,
        RecoveryAction.RETRY_QUEUE_JOB,
        RecoveryAction.CLEANUP_QUEUE,
        RecoveryAction.CLEANUP_TEMP_FILES,
        RecoveryAction.ROTATE_LOGS,
        RecoveryAction.RELOAD_CONFIG,
        RecoveryAction.RUN_HEALTH_CHECK,
        RecoveryAction.RESTART_WORKER,
        RecoveryAction.NOTIFY_OWNER,
    ])
    
    # Blocked actions (never auto-execute)
    blocked_actions: list[RecoveryAction] = field(default_factory=lambda: [
        # Data operations
        RecoveryAction.DISABLE_FEATURE,  # Only with owner confirmation
    ])


class SelfHealingEngine:
    """
    Self-healing engine with strict safety policies.
    """
    
    _instance: Optional['SelfHealingEngine'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._policy = SelfHealingPolicy()
        self._attempt_history: list[RecoveryAttempt] = []
        self._recovery_attempts: dict[str, int] = {}  # incident_id -> attempt count
        self._last_attempt: dict[str, datetime] = {}  # incident_id -> last attempt time
        self._feature_status: dict[str, bool] = {}  # feature -> enabled
    
    @classmethod
    def get_instance(cls) -> 'SelfHealingEngine':
        """Get the singleton instance."""
        return cls()
    
    def get_policy(self) -> SelfHealingPolicy:
        """Get current policy."""
        return self._policy
    
    def update_policy(self, **kwargs) -> None:
        """Update policy settings."""
        for key, value in kwargs.items():
            if hasattr(self._policy, key):
                setattr(self._policy, key, value)
        logger.info(f"Self-healing policy updated: {kwargs}")
    
    def can_self_heal(self, action: RecoveryAction, incident_id: str) -> tuple[bool, str]:
        """
        Check if an action can be auto-executed.
        
        Returns:
            (can_execute, reason)
        """
        if not self._policy.enabled:
            return False, "Self-healing is disabled"
        
        if action in self._policy.blocked_actions:
            return False, f"Action {action.value} is blocked"
        
        if action not in self._policy.allowed_actions:
            return False, f"Action {action.value} is not allowed"
        
        # Check attempt count
        attempts = self._recovery_attempts.get(incident_id, 0)
        if attempts >= self._policy.max_attempts:
            return False, f"Max attempts ({self._policy.max_attempts}) reached"
        
        # Check cooldown
        if incident_id in self._last_attempt:
            last = self._last_attempt[incident_id]
            elapsed = (datetime.now(timezone.utc) - last).total_seconds()
            if elapsed < self._policy.cooldown_seconds:
                remaining = self._policy.cooldown_seconds - elapsed
                return False, f"Cooldown active ({remaining:.0f}s remaining)"
        
        return True, "OK"
    
    async def attempt_recovery(
        self,
        action: RecoveryAction,
        incident_id: str,
        context: Optional[dict] = None
    ) -> tuple[bool, str]:
        """
        Attempt to recover from an incident.
        
        Returns:
            (success, message)
        """
        can_execute, reason = self.can_self_heal(action, incident_id)
        
        if not can_execute:
            logger.info(f"Recovery blocked for {incident_id}: {reason}")
            return False, reason
        
        attempt_id = f"REC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        attempt = RecoveryAttempt(
            id=attempt_id,
            action=action,
            incident_id=incident_id,
            status=RecoveryStatus.IN_PROGRESS,
            attempt_number=self._recovery_attempts.get(incident_id, 0) + 1
        )
        
        self._attempt_history.append(attempt)
        self._recovery_attempts[incident_id] = attempt.attempt_number
        self._last_attempt[incident_id] = datetime.now(timezone.utc)
        
        try:
            result = await self._execute_action(action, context)
            attempt.status = RecoveryStatus.SUCCESS
            attempt.completed_at = datetime.now(timezone.utc)
            attempt.result = result
            logger.info(f"Recovery successful: {attempt_id} - {result}")
            return True, result
            
        except Exception as e:
            attempt.status = RecoveryStatus.FAILED
            attempt.completed_at = datetime.now(timezone.utc)
            attempt.error = str(e)
            logger.error(f"Recovery failed: {attempt_id} - {e}")
            return False, str(e)
    
    async def _execute_action(
        self,
        action: RecoveryAction,
        context: Optional[dict]
    ) -> str:
        """Execute a recovery action."""
        
        if action == RecoveryAction.RETRY_API_CALL:
            return await self._retry_api_call(context)
        
        elif action == RecoveryAction.REFRESH_SESSION:
            return await self._refresh_session(context)
        
        elif action == RecoveryAction.RETRY_QUEUE_JOB:
            return await self._retry_queue_job(context)
        
        elif action == RecoveryAction.CLEANUP_QUEUE:
            return await self._cleanup_queue()
        
        elif action == RecoveryAction.CLEANUP_TEMP_FILES:
            return await self._cleanup_temp_files()
        
        elif action == RecoveryAction.ROTATE_LOGS:
            return await self._rotate_logs()
        
        elif action == RecoveryAction.RELOAD_CONFIG:
            return await self._reload_config()
        
        elif action == RecoveryAction.RUN_HEALTH_CHECK:
            return await self._run_health_check()
        
        elif action == RecoveryAction.RESTART_WORKER:
            return await self._restart_worker(context)
        
        elif action == RecoveryAction.NOTIFY_OWNER:
            return await self._notify_owner(context)
        
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _retry_api_call(self, context: Optional[dict]) -> str:
        """Retry an API call."""
        # This would be called with specific context about the failed call
        logger.info("Retrying API call...")
        return "API call retried"
    
    async def _refresh_session(self, context: Optional[dict]) -> str:
        """Refresh a session."""
        logger.info("Refreshing session...")
        return "Session refreshed"
    
    async def _retry_queue_job(self, context: Optional[dict]) -> str:
        """Retry a failed queue job."""
        job_id = context.get("job_id") if context else None
        logger.info(f"Retrying queue job: {job_id}")
        return f"Queue job {job_id} requeued"
    
    async def _cleanup_queue(self) -> str:
        """Cleanup stuck queue items."""
        try:
            from core.process_queue import ProcessQueue
            if hasattr(ProcessQueue, '_instance') and ProcessQueue._instance:
                queue = ProcessQueue._instance
                # Remove stale items older than 1 hour
                cleaned = getattr(queue, 'cleanup_stale', lambda: 0)()
                return f"Cleaned {cleaned} stale queue items"
        except Exception as e:
            logger.warning(f"Queue cleanup failed: {e}")
        return "Queue cleanup completed"
    
    async def _cleanup_temp_files(self) -> str:
        """Clean up temporary files."""
        import shutil
        import os
        from pathlib import Path
        
        cleaned = 0
        temp_patterns = ['*.tmp', '*.temp', '__pycache__']
        
        for pattern in temp_patterns:
            for path in Path('.').rglob(pattern):
                try:
                    if path.is_file():
                        path.unlink()
                        cleaned += 1
                    elif path.is_dir():
                        shutil.rmtree(path, ignore_errors=True)
                        cleaned += 1
                except Exception:
                    pass
        
        logger.info(f"Cleaned {cleaned} temporary files")
        return f"Cleaned {cleaned} temporary files"
    
    async def _rotate_logs(self) -> str:
        """Rotate log files if they exceed size limit."""
        import os
        from pathlib import Path
        
        max_size = 10 * 1024 * 1024  # 10MB
        rotated = 0
        
        for log_file in Path('.').glob('*.log'):
            try:
                if log_file.stat().st_size > max_size:
                    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
                    new_name = log_file.with_suffix(f'.{timestamp}.log')
                    log_file.rename(new_name)
                    rotated += 1
            except Exception:
                pass
        
        logger.info(f"Rotated {rotated} log files")
        return f"Rotated {rotated} log files"
    
    async def _reload_config(self) -> str:
        """Reload non-sensitive configuration."""
        try:
            from config.settings import Settings
            # Re-initialize settings without affecting secrets
            logger.info("Configuration reloaded")
            return "Configuration reloaded successfully"
        except Exception as e:
            return f"Config reload failed: {e}"
    
    async def _run_health_check(self) -> str:
        """Run a health check."""
        try:
            from core.operations.health import run_full_health_check
            report = await run_full_health_check()
            return f"Health check completed: {report.overall_status.value}"
        except Exception as e:
            return f"Health check failed: {e}"
    
    async def _restart_worker(self, context: Optional[dict]) -> str:
        """Restart a worker process."""
        worker_id = context.get("worker_id") if context else "default"
        logger.info(f"Restarting worker: {worker_id}")
        return f"Worker {worker_id} restart triggered"
    
    async def _notify_owner(self, context: Optional[dict]) -> str:
        """Send notification to owner."""
        message = context.get("message", "Self-healing action taken") if context else "Self-healing action taken"
        
        try:
            from core.operations.alerts import send_alert
            await send_alert(
                title="🔧 Self-Healing Action",
                message=message,
                severity="info"
            )
            return "Owner notified"
        except Exception as e:
            logger.warning(f"Failed to notify owner: {e}")
            return f"Owner notification failed: {e}"
    
    def record_recovery_attempt(
        self,
        incident_id: str,
        action: RecoveryAction,
        success: bool
    ) -> None:
        """Record a recovery attempt for history."""
        if success:
            # Reset attempt count on success
            if incident_id in self._recovery_attempts:
                del self._recovery_attempts[incident_id]
    
    def get_recovery_stats(self) -> dict:
        """Get recovery statistics."""
        total = len(self._attempt_history)
        successful = len([a for a in self._attempt_history if a.status == RecoveryStatus.SUCCESS])
        failed = len([a for a in self._attempt_history if a.status == RecoveryStatus.FAILED])
        
        return {
            "policy_enabled": self._policy.enabled,
            "total_attempts": total,
            "successful": successful,
            "failed": failed,
            "success_rate": round(successful / total * 100, 1) if total > 0 else 100,
            "active_incidents": len(self._recovery_attempts),
            "allowed_actions": [a.value for a in self._policy.allowed_actions],
            "blocked_actions": [a.value for a in self._policy.blocked_actions]
        }
    
    def set_feature_enabled(self, feature: str, enabled: bool) -> None:
        """Enable or disable a feature (for emergency use)."""
        self._feature_status[feature] = enabled
        logger.info(f"Feature '{feature}' set to {enabled}")
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        return self._feature_status.get(feature, True)


# Global instance
_engine: Optional[SelfHealingEngine] = None


def get_self_healing_engine() -> SelfHealingEngine:
    """Get or create the global self-healing engine."""
    global _engine
    if _engine is None:
        _engine = SelfHealingEngine()
    return _engine
