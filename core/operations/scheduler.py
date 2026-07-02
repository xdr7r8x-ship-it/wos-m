"""
WOS-M Operations Control System - Scheduler

This module runs periodic maintenance tasks safely.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a scheduled task."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


class ScheduledTask:
    """Represents a scheduled task."""
    
    def __init__(
        self,
        name: str,
        func: Callable,
        interval_seconds: int,
        description: str = ""
    ):
        self.name = name
        self.func = func
        self.interval_seconds = interval_seconds
        self.description = description
        self.status = TaskStatus.IDLE
        self.last_run: Optional[datetime] = None
        self.last_status: Optional[TaskStatus] = None
        self.last_error: Optional[str] = None
        self.run_count = 0
    
    async def execute(self) -> bool:
        """Execute the task."""
        if self.status == TaskStatus.RUNNING:
            logger.warning(f"Task {self.name} already running, skipping")
            return False
        
        self.status = TaskStatus.RUNNING
        start_time = datetime.now(timezone.utc)
        
        try:
            if asyncio.iscoroutinefunction(self.func):
                await self.func()
            else:
                self.func()
            
            self.last_run = start_time
            self.last_status = TaskStatus.COMPLETED
            self.status = TaskStatus.COMPLETED
            self.run_count += 1
            logger.info(f"Task {self.name} completed successfully")
            return True
            
        except Exception as e:
            self.last_error = str(e)
            self.last_status = TaskStatus.FAILED
            self.status = TaskStatus.FAILED
            logger.error(f"Task {self.name} failed: {e}")
            return False


class OperationsScheduler:
    """
    Runs periodic operations tasks.
    
    Tasks are run safely without blocking the bot.
    """
    
    _instance: Optional['OperationsScheduler'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._enabled = os.environ.get('OPS_SCHEDULER_ENABLED', 'true').lower() == 'true'
        self._tasks: dict[str, ScheduledTask] = {}
        self._running = False
        self._task_handles: dict[str, asyncio.Task] = {}
    
    def is_enabled(self) -> bool:
        """Check if scheduler is enabled."""
        return self._enabled
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable scheduler."""
        self._enabled = enabled
        logger.info(f"Scheduler {'enabled' if enabled else 'disabled'}")
    
    def register_task(
        self,
        name: str,
        func: Callable,
        interval_seconds: int,
        description: str = ""
    ) -> None:
        """Register a scheduled task."""
        task = ScheduledTask(name, func, interval_seconds, description)
        self._tasks[name] = task
        logger.info(f"Registered task: {name} (every {interval_seconds}s)")
    
    def unregister_task(self, name: str) -> bool:
        """Unregister a task."""
        if name in self._tasks:
            del self._tasks[name]
            logger.info(f"Unregistered task: {name}")
            return True
        return False
    
    def get_task_status(self, name: str) -> Optional[dict]:
        """Get status of a task."""
        if name not in self._tasks:
            return None
        
        task = self._tasks[name]
        return {
            "name": task.name,
            "description": task.description,
            "interval_seconds": task.interval_seconds,
            "status": task.status.value,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "last_status": task.last_status.value if task.last_status else None,
            "last_error": task.last_error,
            "run_count": task.run_count
        }
    
    def get_all_tasks_status(self) -> list[dict]:
        """Get status of all tasks."""
        return [self.get_task_status(name) for name in self._tasks]
    
    async def _task_runner(self, task: ScheduledTask) -> None:
        """Run a task continuously on its interval."""
        while self._running:
            try:
                await task.execute()
                await asyncio.sleep(task.interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Task runner error for {task.name}: {e}")
                await asyncio.sleep(task.interval_seconds)
    
    async def start(self) -> None:
        """Start the scheduler."""
        if not self._enabled:
            logger.info("Scheduler is disabled")
            return
        
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        
        # Register default tasks
        self._register_default_tasks()
        
        # Start all tasks
        for name, task in self._tasks.items():
            handle = asyncio.create_task(self._task_runner(task))
            self._task_handles[name] = handle
            logger.info(f"Started task: {name}")
        
        logger.info(f"Scheduler started with {len(self._tasks)} tasks")
    
    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        
        # Cancel all task handles
        for name, handle in self._task_handles.items():
            handle.cancel()
            try:
                await handle
            except asyncio.CancelledError:
                pass
        
        self._task_handles.clear()
        logger.info("Scheduler stopped")
    
    def _register_default_tasks(self) -> None:
        """Register default scheduled tasks."""
        
        # Health check every 5 minutes
        async def health_check_task():
            try:
                from core.operations.health import run_full_health_check
                report = await run_full_health_check()
                
                if report.overall_status.value == "unhealthy":
                    from core.operations.alerts import send_error_alert
                    await send_error_alert(
                        title="🏥 مشكلة في صحة النظام",
                        message=f"فشل {len([c for c in report.checks if c.status == 'fail'])} فحص"
                    )
            except Exception as e:
                logger.error(f"Scheduled health check failed: {e}")
        
        self.register_task(
            "health_check",
            health_check_task,
            300,  # 5 minutes
            "Periodic health check"
        )
        
        # Metrics snapshot every 10 minutes
        async def metrics_task():
            try:
                from core.operations.metrics import get_metrics_collector
                collector = get_metrics_collector()
                snapshot = collector.collect_snapshot()
                logger.debug(f"Metrics snapshot: {collector.get_uptime_formatted()}")
            except Exception as e:
                logger.error(f"Scheduled metrics collection failed: {e}")
        
        self.register_task(
            "metrics_snapshot",
            metrics_task,
            600,  # 10 minutes
            "Periodic metrics collection"
        )
        
        # Daily backup at midnight
        async def backup_task():
            try:
                from core.operations.backup import get_backup_manager
                manager = get_backup_manager()
                success, msg, _ = await manager.create_backup(
                    name=f"daily_backup_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
                    note="Scheduled daily backup"
                )
                if success:
                    logger.info("Daily backup completed")
                else:
                    logger.warning(f"Daily backup failed: {msg}")
            except Exception as e:
                logger.error(f"Scheduled backup failed: {e}")
        
        self.register_task(
            "daily_backup",
            backup_task,
            86400,  # 24 hours
            "Daily backup"
        )
        
        # Incident summary daily
        async def incident_summary_task():
            try:
                from core.operations.incident_reports import get_incident_manager
                manager = get_incident_manager()
                summary = await manager.summarize_incidents(since_hours=24)
                
                if summary.get('total_incidents', 0) > 10:
                    from core.operations.alerts import send_warning_alert
                    await send_warning_alert(
                        title="📊 تقرير حوادث",
                        message=f"تم تسجيل {summary['total_incidents']} حادث خلال 24 ساعة"
                    )
            except Exception as e:
                logger.error(f"Scheduled incident summary failed: {e}")
        
        self.register_task(
            "incident_summary",
            incident_summary_task,
            86400,  # 24 hours
            "Daily incident summary"
        )
        
        # Queue check every 5 minutes
        async def queue_check_task():
            try:
                from core.process_queue import ProcessQueue
                if hasattr(ProcessQueue, '_instance') and ProcessQueue._instance:
                    queue = ProcessQueue._instance
                    size = getattr(queue, 'queue_size', 0)
                    
                    if size > 100:
                        from core.operations.alerts import send_warning_alert
                        await send_warning_alert(
                            title="📬 تراكم في Queue",
                            message=f"Queue متراكم: {size} عنصر"
                        )
            except Exception:
                pass
        
        self.register_task(
            "queue_check",
            queue_check_task,
            300,  # 5 minutes
            "Queue backlog check"
        )


# Global instance
_scheduler: Optional[OperationsScheduler] = None


def get_scheduler() -> OperationsScheduler:
    """Get or create the global scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = OperationsScheduler()
    return _scheduler
