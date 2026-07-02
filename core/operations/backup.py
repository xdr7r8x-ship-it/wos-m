"""
WOS-M Operations Control System - Backup & Restore

This module handles safe backup and restore operations for the database
and configuration files.
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class BackupStatus(Enum):
    """Status of a backup operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"
    RESTORED = "restored"


# Files and patterns to NEVER include in backups
EXCLUDED_PATTERNS = {
    '.env', '.env.example',
    '*.pyc', '*.pyo', '__pycache__',
    '.git', '.github',
    '*.log', '*.sqlite-journal',
    'node_modules', '.venv', 'venv',
    '.pytest_cache', '.mypy_cache',
    '*.onnx', '*.model',  # ML models are large
    'data/wosm.sqlite'  # Main DB will be backed up separately
}


@dataclass
class BackupMetadata:
    """Metadata for a backup."""
    id: str
    name: str
    path: str
    size_bytes: int
    checksum: str  # SHA256 hash
    status: BackupStatus
    included_files: list[str] = field(default_factory=list)
    excluded_files: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verified_at: Optional[datetime] = None
    restored_at: Optional[datetime] = None
    note: Optional[str] = None


class BackupManager:
    """
    Manages backup and restore operations.
    """
    
    _instance: Optional['BackupManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._backups_dir = Path(os.environ.get('OPS_BACKUP_PATH', 'backups'))
        self._retention_days = int(os.environ.get('OPS_BACKUP_RETENTION_DAYS', '14'))
        self._enabled = os.environ.get('OPS_BACKUP_ENABLED', 'true').lower() == 'true'
        self._backup_counter = 0
        self._ensure_db()
    
    def _ensure_db(self) -> None:
        """Ensure backup metadata table exists."""
        try:
            self._backups_dir.mkdir(parents=True, exist_ok=True)
            db_path = self._backups_dir / 'backups_metadata.db'
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    size_bytes INTEGER,
                    checksum TEXT,
                    status TEXT NOT NULL,
                    included_files TEXT,
                    excluded_files TEXT,
                    created_at TEXT NOT NULL,
                    verified_at TEXT,
                    restored_at TEXT,
                    note TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to initialize backup database: {e}")
    
    def _generate_backup_id(self) -> str:
        """Generate a unique backup ID."""
        self._backup_counter += 1
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"BACKUP-{timestamp}-{self._backup_counter:04d}"
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded from backup."""
        path_str = str(path)
        name = path.name
        
        for pattern in EXCLUDED_PATTERNS:
            if pattern.startswith('*'):
                if name.endswith(pattern[1:]):
                    return True
            elif pattern in path_str or pattern == name:
                return True
        
        return False
    
    async def create_backup(
        self,
        name: Optional[str] = None,
        note: Optional[str] = None,
        include_logs: bool = False
    ) -> tuple[bool, str, Optional[BackupMetadata]]:
        """
        Create a new backup.
        
        Args:
            name: Optional name for the backup
            note: Optional note about the backup
            include_logs: Whether to include log files
        
        Returns:
            (success, message, backup_metadata)
        """
        if not self._enabled:
            return False, "Backups are disabled", None
        
        backup_id = self._generate_backup_id()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = name or f"backup_{timestamp}"
        backup_dir = self._backups_dir / f"{backup_id}"
        
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            included = []
            excluded = []
            total_size = 0
            
            # Backup database
            db_path = Path("data/wosm.sqlite")
            if db_path.exists():
                db_backup = backup_dir / "wosm.sqlite"
                shutil.copy2(db_path, db_backup)
                checksum = self._calculate_checksum(db_backup)
                included.append("data/wosm.sqlite")
                total_size += db_backup.stat().st_size
            
            # Backup configuration files
            config_files = [
                "config/settings.py",
                "locales/ar.json",
                "locales/en.json",
                "VERSION"
            ]
            
            for config_file in config_files:
                src = Path(config_file)
                if src.exists():
                    dst = backup_dir / config_file
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    included.append(config_file)
                    total_size += dst.stat().st_size
            
            # Backup operations data
            ops_db = self._backups_dir / 'backups_metadata.db'
            if ops_db.exists():
                dst = backup_dir / 'backups_metadata.db'
                shutil.copy2(ops_db, dst)
                included.append('backups_metadata.db')
                total_size += dst.stat().st_size
            
            # Write backup info
            info = {
                "backup_id": backup_id,
                "name": backup_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "included_files": included,
                "version": self._get_version(),
                "note": note
            }
            
            with open(backup_dir / "backup_info.json", 'w') as f:
                json.dump(info, f, indent=2)
            
            # Create metadata
            metadata = BackupMetadata(
                id=backup_id,
                name=backup_name,
                path=str(backup_dir),
                size_bytes=total_size,
                checksum=checksum if 'checksum' in locals() else "N/A",
                status=BackupStatus.COMPLETED,
                included_files=included,
                excluded_files=list(EXCLUDED_PATTERNS),
                note=note
            )
            
            # Save to metadata database
            self._save_metadata(metadata)
            
            # Cleanup old backups
            await self._cleanup_old_backups()
            
            logger.info(f"Backup created: {backup_id}")
            return True, f"Backup created successfully: {backup_id}", metadata
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False, f"Backup failed: {str(e)}", None
    
    def _get_version(self) -> str:
        """Get current version."""
        try:
            return Path("VERSION").read_text().strip()
        except Exception:
            return "unknown"
    
    def _save_metadata(self, metadata: BackupMetadata) -> None:
        """Save backup metadata to database."""
        try:
            db_path = self._backups_dir / 'backups_metadata.db'
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO backups 
                (id, name, path, size_bytes, checksum, status, included_files, 
                 excluded_files, created_at, verified_at, restored_at, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.id,
                metadata.name,
                metadata.path,
                metadata.size_bytes,
                metadata.checksum,
                metadata.status.value,
                json.dumps(metadata.included_files),
                json.dumps(metadata.excluded_files),
                metadata.created_at.isoformat(),
                metadata.verified_at.isoformat() if metadata.verified_at else None,
                metadata.restored_at.isoformat() if metadata.restored_at else None,
                metadata.note
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save backup metadata: {e}")
    
    async def verify_backup(self, backup_id: str) -> tuple[bool, str]:
        """
        Verify a backup is valid and restorable.
        
        Returns:
            (success, message)
        """
        backup_dir = self._backups_dir / backup_id
        
        if not backup_dir.exists():
            return False, f"Backup not found: {backup_id}"
        
        # Check required files
        required = ["wosm.sqlite", "backup_info.json"]
        for req in required:
            if not (backup_dir / req).exists():
                return False, f"Missing required file: {req}"
        
        # Verify database
        db_path = backup_dir / "wosm.sqlite"
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            conn.close()
            
            if len(tables) < 5:
                return False, "Database appears corrupted or incomplete"
            
        except Exception as e:
            return False, f"Database verification failed: {e}"
        
        # Update status
        await self._update_backup_status(backup_id, BackupStatus.VERIFIED)
        
        return True, "Backup verified successfully"
    
    async def list_backups(self, limit: int = 20) -> list[BackupMetadata]:
        """List available backups."""
        try:
            db_path = self._backups_dir / 'backups_metadata.db'
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM backups 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            backups = []
            for row in rows:
                backups.append(BackupMetadata(
                    id=row[0],
                    name=row[1],
                    path=row[2],
                    size_bytes=row[3],
                    checksum=row[4],
                    status=BackupStatus(row[5]),
                    included_files=json.loads(row[6]) if row[6] else [],
                    excluded_files=json.loads(row[7]) if row[7] else [],
                    created_at=datetime.fromisoformat(row[8]),
                    verified_at=datetime.fromisoformat(row[9]) if row[9] else None,
                    restored_at=datetime.fromisoformat(row[10]) if row[10] else None,
                    note=row[11]
                ))
            
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
    
    async def restore_backup(
        self,
        backup_id: str,
        confirmation: bool = False
    ) -> tuple[bool, str]:
        """
        Restore from a backup.
        
        IMPORTANT: Requires confirmation=True to proceed.
        
        Returns:
            (success, message)
        """
        if not confirmation:
            return False, "RESTORATION_ABORTED: Confirmation required. Set confirmation=True to proceed."
        
        backup_dir = self._backups_dir / backup_id
        
        if not backup_dir.exists():
            return False, f"Backup not found: {backup_id}"
        
        # Verify first
        valid, msg = await self.verify_backup(backup_id)
        if not valid:
            return False, f"Cannot restore invalid backup: {msg}"
        
        try:
            # Create a pre-restore backup first
            await self.create_backup(
                name=f"pre_restore_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                note="Automatic backup before restore"
            )
            
            # Restore database
            src_db = backup_dir / "wosm.sqlite"
            dst_db = Path("data/wosm.sqlite")
            
            if src_db.exists():
                shutil.copy2(src_db, dst_db)
            
            # Restore config files
            for config_file in ["locales/ar.json", "locales/en.json"]:
                src = backup_dir / config_file
                if src.exists():
                    shutil.copy2(src, Path(config_file))
            
            # Update metadata
            await self._update_backup_status(backup_id, BackupStatus.RESTORED)
            
            logger.info(f"Backup restored: {backup_id}")
            return True, f"Backup restored successfully: {backup_id}"
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False, f"Restore failed: {str(e)}"
    
    async def delete_backup(self, backup_id: str) -> tuple[bool, str]:
        """Delete a backup."""
        backup_dir = self._backups_dir / backup_id
        
        if not backup_dir.exists():
            return False, f"Backup not found: {backup_id}"
        
        try:
            shutil.rmtree(backup_dir)
            logger.info(f"Backup deleted: {backup_id}")
            return True, f"Backup deleted: {backup_id}"
        except Exception as e:
            return False, f"Delete failed: {str(e)}"
    
    async def _cleanup_old_backups(self) -> int:
        """Delete backups older than retention period."""
        cutoff = datetime.now(timezone.utc) - __import__('datetime').timedelta(days=self._retention_days)
        deleted = 0
        
        try:
            backups = await self.list_backups(limit=1000)
            for backup in backups:
                if backup.created_at < cutoff:
                    success, _ = await self.delete_backup(backup.id)
                    if success:
                        deleted += 1
            
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old backups")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
        
        return deleted
    
    async def _update_backup_status(
        self,
        backup_id: str,
        status: BackupStatus
    ) -> None:
        """Update backup status."""
        try:
            db_path = self._backups_dir / 'backups_metadata.db'
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            if status == BackupStatus.VERIFIED:
                cursor.execute(
                    "UPDATE backups SET status = ?, verified_at = ? WHERE id = ?",
                    (status.value, datetime.now(timezone.utc).isoformat(), backup_id)
                )
            elif status == BackupStatus.RESTORED:
                cursor.execute(
                    "UPDATE backups SET status = ?, restored_at = ? WHERE id = ?",
                    (status.value, datetime.now(timezone.utc).isoformat(), backup_id)
                )
            else:
                cursor.execute(
                    "UPDATE backups SET status = ? WHERE id = ?",
                    (status.value, backup_id)
                )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update backup status: {e}")


# Global instance
_manager: Optional[BackupManager] = None


def get_backup_manager() -> BackupManager:
    """Get or create the global backup manager."""
    global _manager
    if _manager is None:
        _manager = BackupManager()
    return _manager
