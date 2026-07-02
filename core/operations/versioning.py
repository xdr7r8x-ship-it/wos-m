"""
WOS-M Operations Control System - Version Management

This module handles version tracking, metadata, and changelog management.
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class VersionInfo:
    """Information about a version."""
    version: str
    major: int
    minor: int
    patch: int
    build_date: str
    commit_hash: Optional[str] = None
    branch: Optional[str] = None
    build_type: str = "release"
    migration_version: int = 0
    changelog: Optional[str] = None


class VersionManager:
    """
    Manages version information and changelog.
    """
    
    VERSION_FILE = Path("VERSION")
    CHANGELOG_FILE = Path("CHANGELOG.md")
    BUILD_INFO_FILE = Path("build_info.json")
    
    def __init__(self):
        self._current_version: Optional[VersionInfo] = None
        self._load_current_version()
    
    def _load_current_version(self) -> None:
        """Load current version information."""
        version_str = self._read_version_file()
        if version_str:
            parts = version_str.strip().split('.')
            self._current_version = VersionInfo(
                version=version_str.strip(),
                major=int(parts[0]) if len(parts) > 0 else 1,
                minor=int(parts[1]) if len(parts) > 1 else 0,
                patch=int(parts[2]) if len(parts) > 2 else 0,
                build_date=datetime.now(timezone.utc).isoformat(),
                commit_hash=self._get_git_commit(),
                branch=self._get_git_branch(),
                migration_version=self._get_migration_version()
            )
    
    def _read_version_file(self) -> str:
        """Read version from VERSION file."""
        try:
            if self.VERSION_FILE.exists():
                return self.VERSION_FILE.read_text().strip()
        except Exception as e:
            logger.warning(f"Failed to read VERSION file: {e}")
        return "1.0.0"
    
    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None
    
    def _get_git_branch(self) -> Optional[str]:
        """Get current git branch."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None
    
    def _get_migration_version(self) -> int:
        """Get current migration version from database."""
        try:
            import sqlite3
            from pathlib import Path
            
            db_path = Path("data/wosm.sqlite")
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='_migrations'
                """)
                
                if cursor.fetchone():
                    cursor.execute("SELECT COUNT(*) FROM _migrations")
                    count = cursor.fetchone()[0]
                    conn.close()
                    return count
                
                conn.close()
        except Exception:
            pass
        return 0
    
    def get_current_version(self) -> VersionInfo:
        """Get current version information."""
        if self._current_version is None:
            self._load_current_version()
        return self._current_version or VersionInfo(
            version="1.0.0",
            major=1, minor=0, patch=0,
            build_date=datetime.now(timezone.utc).isoformat()
        )
    
    def get_version_string(self) -> str:
        """Get version as string."""
        return self.get_current_version().version
    
    def parse_version(self, version_str: str) -> tuple[int, int, int]:
        """Parse version string into components."""
        parts = version_str.strip().split('.')
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return major, minor, patch
    
    def compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two versions.
        
        Returns:
            -1 if v1 < v2
             0 if v1 == v2
             1 if v1 > v2
        """
        parts1 = self.parse_version(v1)
        parts2 = self.parse_version(v2)
        
        for p1, p2 in zip(parts1, parts2):
            if p1 < p2:
                return -1
            elif p1 > p2:
                return 1
        return 0
    
    def is_newer(self, version: str) -> bool:
        """Check if given version is newer than current."""
        return self.compare_versions(version, self.get_version_string()) > 0
    
    def is_older(self, version: str) -> bool:
        """Check if given version is older than current."""
        return self.compare_versions(version, self.get_version_string()) < 0
    
    def save_version_info(self) -> None:
        """Save current version info to build_info.json."""
        version_info = self.get_current_version()
        
        build_info = {
            "version": version_info.version,
            "major": version_info.major,
            "minor": version_info.minor,
            "patch": version_info.patch,
            "build_date": version_info.build_date,
            "commit_hash": version_info.commit_hash,
            "branch": version_info.branch,
            "migration_version": version_info.migration_version
        }
        
        try:
            with open(self.BUILD_INFO_FILE, 'w') as f:
                json.dump(build_info, f, indent=2)
            logger.info(f"Version info saved: {version_info.version}")
        except Exception as e:
            logger.error(f"Failed to save build info: {e}")
    
    def add_changelog_entry(self, version: str, changes: list[str], change_type: str = "Added") -> None:
        """Add an entry to the changelog."""
        if not self.CHANGELOG_FILE.exists():
            self._create_initial_changelog()
        
        try:
            with open(self.CHANGELOG_FILE, 'r') as f:
                content = f.read()
            
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            entry = f"\n## [{version}] - {date}\n\n"
            entry += f"### {change_type}\n"
            for change in changes:
                entry += f"- {change}\n"
            
            # Insert after header
            lines = content.split('\n')
            insert_idx = 2  # After title and blank line
            lines.insert(insert_idx, entry)
            
            with open(self.CHANGELOG_FILE, 'w') as f:
                f.write('\n'.join(lines))
            
            logger.info(f"Changelog updated: {version}")
            
        except Exception as e:
            logger.error(f"Failed to update changelog: {e}")
    
    def _create_initial_changelog(self) -> None:
        """Create initial changelog file."""
        content = f"""# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [{self.get_version_string()}] - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
### Added
- Initial release

"""
        try:
            with open(self.CHANGELOG_FILE, 'w') as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Failed to create changelog: {e}")
    
    def get_changelog_summary(self, lines: int = 50) -> str:
        """Get changelog summary."""
        try:
            if self.CHANGELOG_FILE.exists():
                content = self.CHANGELOG_FILE.read_text()
                return '\n'.join(content.split('\n')[:lines])
        except Exception:
            pass
        return "Changelog not available"
    
    def generate_release_notes(self) -> str:
        """Generate release notes for current version."""
        version_info = self.get_current_version()
        
        notes = [
            f"# Release Notes - {version_info.version}",
            f"",
            f"**Build Date:** {version_info.build_date}",
            f"**Git Commit:** {version_info.commit_hash or 'N/A'}",
            f"**Branch:** {version_info.branch or 'N/A'}",
            f"**Migration Version:** {version_info.migration_version}",
            f"",
            f"## Changes",
            f""
        ]
        
        # Add changelog if available
        try:
            if self.CHANGELOG_FILE.exists():
                content = self.CHANGELOG_FILE.read_text()
                # Extract current version section
                current_ver = version_info.version
                lines = content.split('\n')
                capturing = False
                change_lines = []
                
                for line in lines:
                    if f"[{current_ver}]" in line:
                        capturing = True
                        continue
                    if capturing and line.startswith('## ['):
                        break
                    if capturing and line.strip():
                        change_lines.append(line)
                
                if change_lines:
                    notes.extend(change_lines)
                else:
                    notes.append("No changes documented.")
        except Exception:
            notes.append("Changelog not available.")
        
        return '\n'.join(notes)
    
    def get_full_info(self) -> dict:
        """Get full version information as dictionary."""
        info = self.get_current_version()
        return {
            "version": info.version,
            "major": info.major,
            "minor": info.minor,
            "patch": info.patch,
            "build_date": info.build_date,
            "commit_hash": info.commit_hash,
            "branch": info.branch,
            "migration_version": info.migration_version
        }


# Global instance
_version_manager: Optional[VersionManager] = None


def get_version_manager() -> VersionManager:
    """Get or create the global version manager."""
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionManager()
    return _version_manager
