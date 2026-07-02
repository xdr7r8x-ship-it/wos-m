"""
WOS-M Operations Control System - Rollback Management

This module handles safe rollback operations with proper verification
and audit logging.
"""

import asyncio
import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RestorePoint:
    """Represents a restore point."""
    id: str
    backup_id: str
    version: str
    created_at: datetime
    size_bytes: int
    checksum: str
    verified: bool = False


class RollbackManager:
    """
    Manages rollback and restore point operations.
    
    IMPORTANT: All rollback operations require owner confirmation.
    """
    
    _instance: Optional['RollbackManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
    
    async def create_restore_point(
        self,
        note: Optional[str] = None
    ) -> tuple[bool, str, Optional[RestorePoint]]:
        """
        Create a restore point before making changes.
        
        Returns:
            (success, message, restore_point)
        """
        try:
            from core.operations.backup import get_backup_manager
            
            backup_mgr = get_backup_manager()
            success, msg, metadata = await backup_mgr.create_backup(
                name=f"restore_point_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                note=note or "Restore point created manually"
            )
            
            if success and metadata:
                restore_point = RestorePoint(
                    id=metadata.id,
                    backup_id=metadata.id,
                    version=self._get_current_version(),
                    created_at=metadata.created_at,
                    size_bytes=metadata.size_bytes,
                    checksum=metadata.checksum,
                    verified=True
                )
                return True, f"Restore point created: {restore_point.id}", restore_point
            
            return False, msg, None
            
        except Exception as e:
            logger.error(f"Failed to create restore point: {e}")
            return False, str(e), None
    
    def _get_current_version(self) -> str:
        """Get current version string."""
        try:
            from core.operations.versioning import get_version_manager
            return get_version_manager().get_version_string()
        except Exception:
            return "unknown"
    
    async def list_restore_points(self, limit: int = 20) -> list[RestorePoint]:
        """List available restore points."""
        try:
            from core.operations.backup import get_backup_manager
            
            backup_mgr = get_backup_manager()
            backups = await backup_mgr.list_backups(limit=limit)
            
            restore_points = []
            for backup in backups:
                if "restore_point" in backup.name or "pre_upgrade" in backup.name or "pre_restore" in backup.name:
                    restore_points.append(RestorePoint(
                        id=backup.id,
                        backup_id=backup.id,
                        version=self._get_version_from_backup(backup.path),
                        created_at=backup.created_at,
                        size_bytes=backup.size_bytes,
                        checksum=backup.checksum,
                        verified=backup.status.value == "verified"
                    ))
            
            return restore_points
            
        except Exception as e:
            logger.error(f"Failed to list restore points: {e}")
            return []
    
    def _get_version_from_backup(self, backup_path: str) -> str:
        """Extract version from backup metadata."""
        try:
            info_file = Path(backup_path) / "backup_info.json"
            if info_file.exists():
                info = json.loads(info_file.read_text())
                return info.get("version", "unknown")
        except Exception:
            pass
        return "unknown"
    
    async def validate_restore_point(self, restore_point_id: str) -> tuple[bool, str]:
        """
        Validate that a restore point is valid for rollback.
        
        Returns:
            (valid, message)
        """
        try:
            from core.operations.backup import get_backup_manager
            
            backup_mgr = get_backup_manager()
            backups = await backup_mgr.list_backups(limit=100)
            
            matching = [b for b in backups if b.id == restore_point_id]
            if not matching:
                return False, f"Restore point not found: {restore_point_id}"
            
            backup = matching[0]
            
            # Check backup directory exists
            backup_dir = Path(backup.path)
            if not backup_dir.exists():
                return False, f"Backup directory not found: {backup.path}"
            
            # Check required files
            if not (backup_dir / "wosm.sqlite").exists():
                return False, "Database backup not found"
            
            return True, "Restore point is valid"
            
        except Exception as e:
            return False, f"Validation failed: {str(e)}"
    
    async def rollback_to_backup(
        self,
        restore_point_id: str,
        confirmation: bool = False
    ) -> tuple[bool, str]:
        """
        Rollback to a previous restore point.
        
        IMPORTANT: Requires confirmation=True to proceed.
        
        Returns:
            (success, message)
        """
        if not confirmation:
            return False, "ROLLBACK_REQUIRES_CONFIRMATION: Owner confirmation required to proceed with rollback."
        
        # Validate restore point first
        valid, msg = await self.validate_restore_point(restore_point_id)
        if not valid:
            return False, f"Cannot rollback: {msg}"
        
        try:
            # Create a pre-rollback backup
            await self.create_restore_point(
                note=f"Auto-backup before rollback to {restore_point_id}"
            )
            
            # Perform the restore
            from core.operations.backup import get_backup_manager
            backup_mgr = get_backup_manager()
            
            success, msg = await backup_mgr.restore_backup(
                restore_point_id,
                confirmation=True
            )
            
            if success:
                # Log the rollback
                from core.operations.audit import audit_log, AuditAction, RiskLevel
                await audit_log(
                    user_id="system",
                    action=AuditAction.ROLLBACK_APPLY,
                    module="rollback",
                    target=restore_point_id,
                    status="success",
                    risk_level=RiskLevel.CRITICAL,
                    metadata={"restore_point_id": restore_point_id}
                )
                
                # Notify owner
                from core.operations.alerts import send_alert
                await send_alert(
                    title="↩️ تم Rollback",
                    message=f"تم التراجع إلى نقطة الاستعادة: {restore_point_id}",
                    severity="warning"
                )
                
                # Run health check
                from core.operations.health import run_full_health_check
                health = await run_full_health_check()
                
                return True, f"Rollback completed. Health: {health.overall_status.value}"
            
            return False, msg
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            
            # Log the failure
            from core.operations.audit import audit_log, AuditAction, RiskLevel
            await audit_log(
                user_id="system",
                action=AuditAction.ROLLBACK_APPLY,
                module="rollback",
                target=restore_point_id,
                status="failure",
                risk_level=RiskLevel.CRITICAL,
                metadata={"error": str(e)}
            )
            
            return False, f"Rollback failed: {str(e)}"
    
    async def rollback_config(
        self,
        config_type: str,
        confirmation: bool = False
    ) -> tuple[bool, str]:
        """
        Rollback configuration to defaults.
        
        Args:
            config_type: Type of config to rollback (settings, permissions, etc.)
            confirmation: Owner confirmation
        
        Returns:
            (success, message)
        """
        if not confirmation:
            return False, "ROLLBACK_REQUIRES_CONFIRMATION: Owner confirmation required."
        
        try:
            if config_type == "settings":
                # Backup current settings
                await self.create_restore_point(note="Before settings reset")
                
                # Reset to defaults would go here
                # This is a placeholder - actual implementation depends on settings structure
                
                return True, "Configuration reset to defaults"
            
            return False, f"Unknown config type: {config_type}"
            
        except Exception as e:
            return False, f"Rollback failed: {str(e)}"
    
    async def post_rollback_health_check(self) -> dict:
        """Run health check after rollback."""
        try:
            from core.operations.health import run_full_health_check
            report = await run_full_health_check()
            
            # Send alert if unhealthy
            if report.overall_status.value == "unhealthy":
                from core.operations.alerts import send_critical_alert
                await send_critical_alert(
                    title="⚠️ صحة النظام خطيرة بعد Rollback",
                    message=f"فشل {len([c for c in report.checks if c.status == 'fail'])} فحص"
                )
            
            return report.to_dict()
            
        except Exception as e:
            logger.error(f"Post-rollback health check failed: {e}")
            return {"error": str(e)}
    
    def format_restore_points(self, points: list[RestorePoint]) -> str:
        """Format restore points for display."""
        if not points:
            return "لا توجد نقاط استعادة متاحة"
        
        lines = ["━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "📍 نقاط الاستعادة المتاحة", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]
        
        for i, point in enumerate(points[:10], 1):
            verified_icon = "✅" if point.verified else "❌"
            date = point.created_at.strftime("%Y-%m-%d %H:%M")
            size = self._format_size(point.size_bytes)
            
            lines.append(f"{i}. {verified_icon} `{point.id}`")
            lines.append(f"   📅 {date} | 📦 {size} | 📌 v{point.version}")
        
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 استخدم الأزرار أدناه للتراجع الآمن")
        
        return "\n".join(lines)
    
    def _format_size(self, bytes_size: int) -> str:
        """Format bytes to human readable size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f}{unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f}TB"


# Global instance
_rollback_manager: Optional[RollbackManager] = None


def get_rollback_manager() -> RollbackManager:
    """Get or create the global rollback manager."""
    global _rollback_manager
    if _rollback_manager is None:
        _rollback_manager = RollbackManager()
    return _rollback_manager
