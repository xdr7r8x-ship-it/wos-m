"""
WOS-M Process Queue System
© MANSOUR — WOS-M. All rights reserved.
"""
import asyncio
import json
from datetime import datetime
from enum import IntEnum
from typing import Optional, Callable, Any, Dict, List
import logging

from core.database import db

logger = logging.getLogger(__name__)


class QueuePriority(IntEnum):
    """Queue priority levels (lower = higher priority)."""
    GIFT_VALIDATE = 100
    GIFT_REDEEM = 200
    PLAYER_ADD = 300
    ALLIANCE_UPDATE = 400
    ALLIANCE_SYNC = 500
    REPORT_GENERATION = 600
    DEFAULT = 500


class QueueStatus:
    """Queue task statuses."""
    QUEUED = "queued"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


class ProcessQueue:
    """Centralized process queue system."""
    
    def __init__(self, bot):
        self.bot = bot
        self._running = False
        self._queue_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the queue processor."""
        if self._running:
            return
        
        self._running = True
        self._queue_task = asyncio.create_task(self._process_loop())
        logger.info("Process queue started")
    
    async def stop(self):
        """Stop the queue processor."""
        self._running = False
        if self._queue_task:
            self._queue_task.cancel()
            try:
                await self._queue_task
            except asyncio.CancelledError:
                pass
        logger.info("Process queue stopped")
    
    async def add_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        priority: int = QueuePriority.DEFAULT
    ) -> int:
        """
        Add a task to the queue.
        
        Args:
            task_type: Type of task
            task_data: Task data dictionary
            priority: Task priority (lower = higher priority)
            
        Returns:
            Task ID
        """
        cursor = await db.execute(
            """INSERT INTO process_queue 
               (task_type, task_data, priority, status) 
               VALUES (?, ?, ?, ?)""",
            (task_type, json.dumps(task_data), priority, QueueStatus.QUEUED)
        )
        await db.commit()
        
        task_id = cursor.lastrowid
        logger.info(f"Added task {task_id} of type {task_type} with priority {priority}")
        
        return task_id
    
    async def get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get the next task from the queue."""
        row = await db.fetchone(
            """SELECT * FROM process_queue 
               WHERE status IN (?, ?) 
               ORDER BY priority ASC, created_at ASC 
               LIMIT 1""",
            (QueueStatus.QUEUED, QueueStatus.RETRY)
        )
        
        if not row:
            return None
        
        return {
            "id": row["id"],
            "task_type": row["task_type"],
            "task_data": json.loads(row["task_data"]),
            "priority": row["priority"],
            "status": row["status"],
            "retry_count": row["retry_count"],
            "max_retries": row["max_retries"]
        }
    
    async def update_task_status(
        self,
        task_id: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update task status."""
        query = "UPDATE process_queue SET status = ?, updated_at = CURRENT_TIMESTAMP"
        params = [status]
        
        if status == QueueStatus.ACTIVE:
            query += ", started_at = CURRENT_TIMESTAMP"
        elif status == QueueStatus.COMPLETED:
            query += ", completed_at = CURRENT_TIMESTAMP"
        elif status == QueueStatus.FAILED:
            query += ", error_message = ?"
            params.append(error_message)
        
        query += " WHERE id = ?"
        params.append(task_id)
        
        await db.execute(query, tuple(params))
        await db.commit()
    
    async def increment_retry(self, task_id: int) -> bool:
        """Increment retry count and check if max retries exceeded."""
        row = await db.fetchone(
            "SELECT retry_count, max_retries FROM process_queue WHERE id = ?",
            (task_id,)
        )
        
        if not row:
            return False
        
        new_retry_count = row["retry_count"] + 1
        
        if new_retry_count >= row["max_retries"]:
            await self.update_task_status(task_id, QueueStatus.FAILED, "Max retries exceeded")
            return False
        
        await db.execute(
            """UPDATE process_queue 
               SET retry_count = ?, status = ?, updated_at = CURRENT_TIMESTAMP 
               WHERE id = ?""",
            (new_retry_count, QueueStatus.RETRY, task_id)
        )
        await db.commit()
        
        return True
    
    async def cancel_task(self, task_id: int) -> bool:
        """Cancel a queued task."""
        row = await db.fetchone(
            "SELECT status FROM process_queue WHERE id = ?",
            (task_id,)
        )
        
        if not row or row["status"] not in (QueueStatus.QUEUED, QueueStatus.RETRY):
            return False
        
        await self.update_task_status(task_id, QueueStatus.FAILED, "Cancelled by user")
        return True
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        stats = {}
        
        for status in [QueueStatus.QUEUED, QueueStatus.ACTIVE, QueueStatus.COMPLETED, 
                       QueueStatus.FAILED, QueueStatus.RETRY]:
            row = await db.fetchone(
                "SELECT COUNT(*) as count FROM process_queue WHERE status = ?",
                (status,)
            )
            stats[status] = row["count"] if row else 0
        
        return stats
    
    async def get_queue_size(self) -> Dict[str, int]:
        """Get queue size summary."""
        stats = await self.get_queue_stats()
        return {
            "pending": stats.get(QueueStatus.QUEUED, 0),
            "processing": stats.get(QueueStatus.ACTIVE, 0),
            "completed": stats.get(QueueStatus.COMPLETED, 0),
            "failed": stats.get(QueueStatus.FAILED, 0) + stats.get(QueueStatus.RETRY, 0),
        }

    async def recover_crashed_tasks(self):
        """Recover tasks that were marked as active for too long."""
        await db.execute(
            """UPDATE process_queue 
               SET status = ?, retry_count = retry_count + 1, updated_at = CURRENT_TIMESTAMP 
               WHERE status = ? 
               AND datetime(started_at, '+1 hour') < datetime('now')""",
            (QueueStatus.RETRY, QueueStatus.ACTIVE)
        )
        await db.commit()
        
        rows = await db.fetchall(
            "SELECT COUNT(*) as count FROM process_queue WHERE status = ?",
            (QueueStatus.RETRY,)
        )
        
        if rows and rows[0]["count"] > 0:
            logger.info(f"Recovered {rows[0]['count']} crashed tasks")
    
    async def get_recent_items(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent queue items."""
        rows = await db.fetchall(
            """SELECT id, task_type, status, created_at, updated_at
               FROM process_queue ORDER BY created_at DESC LIMIT ?""",
            (limit,)
        )
        return [dict(row) for row in rows]
    
    async def _process_loop(self):
        """Main queue processing loop."""
        while self._running:
            try:
                # Recover any crashed tasks
                await self.recover_crashed_tasks()
                
                # Get next task
                task = await self.get_next_task()
                
                if task:
                    await self._execute_task(task)
                else:
                    # Wait before checking again
                    await asyncio.sleep(2)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(5)
    
    async def _execute_task(self, task: Dict[str, Any]):
        """Execute a single task."""
        task_id = task["id"]
        task_type = task["task_type"]
        task_data = task["task_data"]
        
        logger.info(f"Processing task {task_id} of type {task_type}")
        
        await self.update_task_status(task_id, QueueStatus.ACTIVE)
        
        try:
            # Get handler for task type
            handler = self._get_handler(task_type)
            
            if handler:
                await handler(task_data)
                await self.update_task_status(task_id, QueueStatus.COMPLETED)
                logger.info(f"Task {task_id} completed successfully")
            else:
                await self.update_task_status(task_id, QueueStatus.FAILED, f"No handler for {task_type}")
                
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            
            if await self.increment_retry(task_id):
                logger.info(f"Task {task_id} queued for retry")
            else:
                await self.update_task_status(task_id, QueueStatus.FAILED, str(e))
    
    def _get_handler(self, task_type: str) -> Optional[Callable]:
        """Get the handler function for a task type."""
        handlers = {
            "gift_validate": self._handle_gift_validate,
            "gift_redeem": self._handle_gift_redeem,
            "player_add": self._handle_player_add,
            "alliance_update": self._handle_alliance_update,
            "alliance_sync": self._handle_alliance_sync,
            "report_generation": self._handle_report_generation,
        }
        return handlers.get(task_type)
    
    async def _handle_gift_validate(self, data: Dict[str, Any]):
        """Handle gift code validation."""
        from integrations.gift_code_client import gift_code_client
        code = data.get("code")
        
        if code:
            result = await gift_code_client.validate_code(code)
            
            await db.execute(
                """UPDATE gift_codes 
                   SET status = ? 
                   WHERE code = ?""",
                (result.get("status", "invalid"), code)
            )
            await db.commit()
    
    async def _handle_gift_redeem(self, data: Dict[str, Any]):
        """Handle gift code redemption."""
        from modules.gift_codes.redemption_engine import redemption_engine
        code = data.get("code")
        player_id = data.get("player_id")
        
        if code and player_id:
            await redemption_engine.redeem_code(code, player_id)
    
    async def _handle_player_add(self, data: Dict[str, Any]):
        """Handle player addition."""
        from integrations.wos_api_client import wos_api_client
        fid = data.get("fid")
        
        if fid:
            player_data = await wos_api_client.get_player_data(fid)
            
            if player_data:
                await db.execute(
                    """INSERT OR REPLACE INTO players 
                       (fid, name, alliance_id, state_kid, level, last_synced) 
                       VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    (fid, player_data.get("name"), data.get("alliance_id"),
                     player_data.get("state_kid"), player_data.get("level"))
                )
                await db.commit()
    
    async def _handle_alliance_update(self, data: Dict[str, Any]):
        """Handle alliance update from WOS API."""
        alliance_id = data.get("alliance_id")
        
        if not alliance_id:
            return
        
        alliance = await db.fetchone(
            "SELECT * FROM alliances WHERE id = ?",
            (alliance_id,)
        )
        
        if alliance:
            # Update alliance info
            await db.execute(
                """UPDATE alliances SET 
                   name = ?, member_count = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (
                    data.get("name", alliance["name"]),
                    data.get("member_count", alliance["member_count"]),
                    alliance_id
                )
            )
            await db.connection.commit()
    
    async def _handle_alliance_sync(self, data: Dict[str, Any]):
        """Handle alliance sync."""
        from integrations.wos_api_client import wos_api_client
        alliance_id = data.get("alliance_id")
        
        if alliance_id:
            alliance = await db.fetchone(
                "SELECT * FROM alliances WHERE id = ?",
                (alliance_id,)
            )
            
            if alliance:
                await wos_api_client.sync_alliance(alliance["state_kid"])
    
    async def _handle_report_generation(self, data: Dict[str, Any]):
        """Handle report generation task."""
        from core.audit_log import audit_log
        
        report_type = data.get("type", "summary")
        
        if report_type == "gift_summary":
            from modules.gift_codes.service import gift_code_service
            stats = await gift_code_service.get_stats()
            return {"type": "gift_summary", "data": stats}
        
        elif report_type == "attendance":
            event_id = data.get("event_id")
            if event_id:
                records = await db.fetchall(
                    "SELECT * FROM attendance_records WHERE event_id = ?",
                    (event_id,)
                )
                return {"type": "attendance", "data": records}
        
        return {"type": report_type, "data": {}}
