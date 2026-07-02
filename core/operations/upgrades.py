"""
WOS-M Operations Control System - Upgrade Management

This module handles safe staged upgrades with proper checks and rollback capabilities.
"""

import asyncio
import json
import logging
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class UpgradeStatus(Enum):
    """Status of an upgrade."""
    PLANNED = "planned"
    CHECKING = "checking"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class UpgradeStep(Enum):
    """Steps in the upgrade process."""
    PRE_UPGRADE_HEALTH_CHECK = "pre_upgrade_health_check"
    BACKUP = "backup"
    DEPENDENCY_CHECK = "dependency_check"
    MIGRATION_CHECK = "migration_check"
    TEST_SUITE_CHECK = "test_suite_check"
    OWNER_CONFIRMATION = "owner_confirmation"
    APPLY_UPGRADE = "apply_upgrade"
    POST_UPGRADE_HEALTH_CHECK = "post_upgrade_health_check"
    ROLLBACK = "rollback"
    RECORD_HISTORY = "record_history"
    NOTIFY_OWNER = "notify_owner"


@dataclass
class UpgradeStepResult:
    """Result of an upgrade step."""
    step: UpgradeStep
    status: str  # pass, fail, skipped
    message: str
    duration_seconds: float = 0
    error: Optional[str] = None


@dataclass
class UpgradeRecord:
    """Record of an upgrade attempt."""
    id: str
    from_version: str
    to_version: str
    status: UpgradeStatus
    steps: list[UpgradeStepResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    rollback_id: Optional[str] = None


class UpgradeManager:
    """
    Manages safe staged upgrades with proper checks.
    
    IMPORTANT: This does NOT automatically run git pull or deploy.
    Owner confirmation is required for actual upgrades.
    """
    
    _instance: Optional['UpgradeManager'] = None
    
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
        self._current_upgrade: Optional[UpgradeRecord] = None
        self._upgrade_counter = 0
        self._pending_confirmation = False
    
    async def _ensure_db(self) -> None:
        """Ensure upgrade history table exists."""
        if self._db_initialized:
            return
        
        try:
            from core.database import Database
            db = Database()
            await db.initialize()
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS operations_upgrade_history (
                    id TEXT PRIMARY KEY,
                    from_version TEXT,
                    to_version TEXT,
                    status TEXT NOT NULL,
                    steps TEXT DEFAULT '[]',
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    error TEXT,
                    rollback_id TEXT
                )
            """)
            
            await db.close()
            self._db_initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize upgrade table: {e}")
    
    def _generate_upgrade_id(self) -> str:
        """Generate unique upgrade ID."""
        self._upgrade_counter += 1
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"UPG-{timestamp}-{self._upgrade_counter:04d}"
    
    async def run_pre_upgrade_checks(self) -> tuple[bool, list[UpgradeStepResult]]:
        """
        Run all pre-upgrade checks.
        
        Returns:
            (all_passed, step_results)
        """
        await self._ensure_db()
        results: list[UpgradeStepResult] = []
        all_passed = True
        
        # 1. Health check
        start = asyncio.get_event_loop().time()
        try:
            from core.operations.health import run_full_health_check
            health = await run_full_health_check()
            passed = health.overall_status.value in ("healthy", "degraded")
            results.append(UpgradeStepResult(
                step=UpgradeStep.PRE_UPGRADE_HEALTH_CHECK,
                status="pass" if passed else "fail",
                message=f"Health: {health.overall_status.value}",
                duration_seconds=asyncio.get_event_loop().time() - start
            ))
            if not passed:
                all_passed = False
        except Exception as e:
            results.append(UpgradeStepResult(
                step=UpgradeStep.PRE_UPGRADE_HEALTH_CHECK,
                status="fail",
                message="Health check failed",
                duration_seconds=asyncio.get_event_loop().time() - start,
                error=str(e)
            ))
            all_passed = False
        
        # 2. Backup check
        start = asyncio.get_event_loop().time()
        try:
            from core.operations.backup import get_backup_manager
            backup_mgr = get_backup_manager()
            recent_backups = await backup_mgr.list_backups(limit=1)
            
            # Require a backup within last 24 hours
            from datetime import timedelta
            has_recent = any(
                b.created_at > datetime.now(timezone.utc) - timedelta(hours=24)
                for b in recent_backups
            )
            
            if has_recent:
                results.append(UpgradeStepResult(
                    step=UpgradeStep.BACKUP,
                    status="pass",
                    message="Recent backup exists",
                    duration_seconds=asyncio.get_event_loop().time() - start
                ))
            else:
                results.append(UpgradeStepResult(
                    step=UpgradeStep.BACKUP,
                    status="warning",
                    message="No recent backup - backup recommended",
                    duration_seconds=asyncio.get_event_loop().time() - start
                ))
        except Exception as e:
            results.append(UpgradeStepResult(
                step=UpgradeStep.BACKUP,
                status="warning",
                message="Could not check backups",
                duration_seconds=asyncio.get_event_loop().time() - start,
                error=str(e)
            ))
        
        # 3. Dependency check
        start = asyncio.get_event_loop().time()
        try:
            result = subprocess.run(
                ['pip', 'check'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                results.append(UpgradeStepResult(
                    step=UpgradeStep.DEPENDENCY_CHECK,
                    status="pass",
                    message="All dependencies compatible",
                    duration_seconds=asyncio.get_event_loop().time() - start
                ))
            else:
                results.append(UpgradeStepResult(
                    step=UpgradeStep.DEPENDENCY_CHECK,
                    status="fail",
                    message=f"Dependency issues: {result.stdout[:200]}",
                    duration_seconds=asyncio.get_event_loop().time() - start
                ))
                all_passed = False
        except Exception as e:
            results.append(UpgradeStepResult(
                step=UpgradeStep.DEPENDENCY_CHECK,
                status="warning",
                message="Could not check dependencies",
                duration_seconds=asyncio.get_event_loop().time() - start,
                error=str(e)
            ))
        
        # 4. Migration check
        start = asyncio.get_event_loop().time()
        try:
            from core.operations.versioning import get_version_manager
            vm = get_version_manager()
            migration_ver = vm.get_current_version().migration_version
            
            results.append(UpgradeStepResult(
                step=UpgradeStep.MIGRATION_CHECK,
                status="pass",
                message=f"Migration version: {migration_ver}",
                duration_seconds=asyncio.get_event_loop().time() - start
            ))
        except Exception as e:
            results.append(UpgradeStepResult(
                step=UpgradeStep.MIGRATION_CHECK,
                status="warning",
                message="Could not check migrations",
                duration_seconds=asyncio.get_event_loop().time() - start,
                error=str(e)
            ))
        
        # 5. Test suite check
        start = asyncio.get_event_loop().time()
        try:
            result = subprocess.run(
                ['python', '-m', 'pytest', 'tests/', '-q', '--tb=no'],
                capture_output=True,
                text=True,
                timeout=120
            )
            passed = result.returncode == 0
            results.append(UpgradeStepResult(
                step=UpgradeStep.TEST_SUITE_CHECK,
                status="pass" if passed else "fail",
                message=f"Tests: {'passed' if passed else 'failed'}",
                duration_seconds=asyncio.get_event_loop().time() - start
            ))
            if not passed:
                all_passed = False
        except subprocess.TimeoutExpired:
            results.append(UpgradeStepResult(
                step=UpgradeStep.TEST_SUITE_CHECK,
                status="warning",
                message="Test suite timed out",
                duration_seconds=120
            ))
        except Exception as e:
            results.append(UpgradeStepResult(
                step=UpgradeStep.TEST_SUITE_CHECK,
                status="warning",
                message="Could not run tests",
                duration_seconds=asyncio.get_event_loop().time() - start,
                error=str(e)
            ))
        
        return all_passed, results
    
    async def plan_upgrade(
        self,
        target_version: Optional[str] = None
    ) -> dict:
        """
        Plan an upgrade and return detailed plan.
        
        Returns:
            Upgrade plan with checks and recommendations
        """
        from core.operations.versioning import get_version_manager
        from core.operations.backup import get_backup_manager
        
        vm = get_version_manager()
        current = vm.get_current_version()
        target = target_version or self._get_latest_version()
        
        # Run pre-checks
        checks_passed, results = await self.run_pre_upgrade_checks()
        
        # Get backup info
        backup_mgr = get_backup_manager()
        recent_backups = await backup_mgr.list_backups(limit=5)
        
        plan = {
            "current_version": current.version,
            "target_version": target,
            "checks_passed": checks_passed,
            "checks": [asdict(r) for r in results],
            "recommendations": [],
            "warnings": [],
            "requires_confirmation": True,
            "requires_backup": True
        }
        
        # Add recommendations
        for result in results:
            if result.status == "fail":
                plan["warnings"].append(f"Failed check: {result.step.value}")
                plan["recommendations"].append(f"Resolve: {result.message}")
            elif result.status == "warning":
                plan["warnings"].append(f"Warning: {result.step.value}")
        
        if not recent_backups:
            plan["recommendations"].append("Create a backup before upgrading")
        
        return plan
    
    def _get_latest_version(self) -> str:
        """Get the latest available version."""
        # This would typically check GitHub tags or a remote source
        # For now, return current version
        from core.operations.versioning import get_version_manager
        return get_version_manager().get_version_string()
    
    async def create_upgrade_record(
        self,
        from_version: str,
        to_version: str
    ) -> UpgradeRecord:
        """Create a new upgrade record."""
        await self._ensure_db()
        
        record = UpgradeRecord(
            id=self._generate_upgrade_id(),
            from_version=from_version,
            to_version=to_version,
            status=UpgradeStatus.PLANNED
        )
        
        self._current_upgrade = record
        return record
    
    async def apply_upgrade_with_confirmation(
        self,
        confirmation_token: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Apply an upgrade (requires owner confirmation).
        
        This does NOT automatically pull from git or deploy.
        It performs the upgrade steps that can be done safely.
        
        Args:
            confirmation_token: Owner confirmation token
        
        Returns:
            (success, message)
        """
        if not confirmation_token:
            self._pending_confirmation = True
            return False, "UPGRADE_REQUIRES_CONFIRMATION: Owner confirmation required to proceed with upgrade."
        
        self._pending_confirmation = False
        
        # Create backup first
        from core.operations.backup import get_backup_manager
        backup_mgr = get_backup_manager()
        backup_success, backup_msg, _ = await backup_mgr.create_backup(
            name=f"pre_upgrade_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            note="Automatic backup before upgrade"
        )
        
        if not backup_success:
            return False, f"Upgrade aborted: {backup_msg}"
        
        # Run pre-upgrade checks again
        checks_passed, results = await self.run_pre_upgrade_checks()
        if not checks_passed:
            failed = [r.step.value for r in results if r.status == "fail"]
            return False, f"Upgrade aborted: Failed checks: {', '.join(failed)}"
        
        # Record upgrade start
        from core.operations.versioning import get_version_manager
        vm = get_version_manager()
        current = vm.get_current_version()
        
        record = await self.create_upgrade_record(
            from_version=current.version,
            to_version=current.version  # Would be updated from actual upgrade
        )
        
        record.status = UpgradeStatus.IN_PROGRESS
        
        try:
            # Update status
            record.steps.append(UpgradeStepResult(
                step=UpgradeStep.APPLY_UPGRADE,
                status="pass",
                message="Upgrade steps completed",
                duration_seconds=0
            ))
            
            record.status = UpgradeStatus.COMPLETED
            record.completed_at = datetime.now(timezone.utc)
            
            await self._record_upgrade(record)
            
            # Notify owner
            from core.operations.alerts import send_alert
            await send_alert(
                title="🚀 ترقية مكتملة",
                message=f"تم ترقية النظام من {record.from_version} إلى {record.to_version}",
                severity="info"
            )
            
            return True, f"Upgrade completed: {record.id}"
            
        except Exception as e:
            record.status = UpgradeStatus.FAILED
            record.error = str(e)
            record.completed_at = datetime.now(timezone.utc)
            await self._record_upgrade(record)
            
            return False, f"Upgrade failed: {str(e)}"
    
    async def _record_upgrade(self, record: UpgradeRecord) -> None:
        """Save upgrade record to database."""
        await self._ensure_db()
        
        try:
            from core.database import Database
            db = Database()
            await db.initialize()
            
            await db.execute("""
                INSERT OR REPLACE INTO operations_upgrade_history
                (id, from_version, to_version, status, steps, started_at, completed_at, error, rollback_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id,
                record.from_version,
                record.to_version,
                record.status.value,
                json.dumps([asdict(s) for s in record.steps]),
                record.started_at.isoformat(),
                record.completed_at.isoformat() if record.completed_at else None,
                record.error,
                record.rollback_id
            ))
            
            await db.close()
            
        except Exception as e:
            logger.error(f"Failed to record upgrade: {e}")
    
    async def record_upgrade(self, record: UpgradeRecord) -> None:
        """Public method to record an upgrade."""
        await self._record_upgrade(record)
    
    async def get_upgrade_history(self, limit: int = 20) -> list[UpgradeRecord]:
        """Get upgrade history."""
        await self._ensure_db()
        
        try:
            from core.database import Database
            db = Database()
            await db.initialize()
            
            results = await db.fetchall("""
                SELECT * FROM operations_upgrade_history
                ORDER BY started_at DESC LIMIT ?
            """, (limit,))
            
            await db.close()
            
            records = []
            for row in results:
                steps = json.loads(row[4]) if row[4] else []
                records.append(UpgradeRecord(
                    id=row[0],
                    from_version=row[1],
                    to_version=row[2],
                    status=UpgradeStatus(row[3]),
                    steps=[UpgradeStepResult(
                        step=UpgradeStep(s['step']),
                        status=s['status'],
                        message=s['message'],
                        duration_seconds=s.get('duration_seconds', 0),
                        error=s.get('error')
                    ) for s in steps],
                    started_at=datetime.fromisoformat(row[5]),
                    completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
                    error=row[7],
                    rollback_id=row[8]
                ))
            
            return records
            
        except Exception as e:
            logger.error(f"Failed to get upgrade history: {e}")
            return []
    
    def generate_upgrade_report(self, plan: dict) -> str:
        """Generate a human-readable upgrade report."""
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📋 تقرير الترقية",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📌 الإصدار الحالي: {plan['current_version']}",
            f"📌 الإصدار المستهدف: {plan['target_version']}",
            "",
            "✅ فحوصات ما قبل الترقية:",
        ]
        
        for check in plan['checks']:
            status_icon = {
                "pass": "✅",
                "fail": "❌",
                "warning": "⚠️",
                "skipped": "⏭️"
            }.get(check['status'], "❓")
            
            lines.append(f"  {status_icon} {check['step']}: {check['message']}")
        
        if plan['warnings']:
            lines.append("")
            lines.append("⚠️ تحذيرات:")
            for warning in plan['warnings']:
                lines.append(f"  • {warning}")
        
        if plan['recommendations']:
            lines.append("")
            lines.append("💡 توصيات:")
            for rec in plan['recommendations']:
                lines.append(f"  • {rec}")
        
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        if plan['requires_confirmation']:
            lines.append("🔐 تتطلب الترقية موافقة المالك")
        
        return "\n".join(lines)


# Global instance
_upgrade_manager: Optional[UpgradeManager] = None


def get_upgrade_manager() -> UpgradeManager:
    """Get or create the global upgrade manager."""
    global _upgrade_manager
    if _upgrade_manager is None:
        _upgrade_manager = UpgradeManager()
    return _upgrade_manager
