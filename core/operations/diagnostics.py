"""
WOS-M Operations Control System - Diagnostics

This module provides diagnostic tools for troubleshooting.
"""

import asyncio
import logging
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DiagnosticsCollector:
    """
    Collects diagnostic information for troubleshooting.
    """
    
    def __init__(self):
        self._start_time = datetime.now(timezone.utc)
    
    def get_system_info(self) -> dict:
        """Get system information."""
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "python_executable": sys.executable,
        }
    
    def get_environment_info(self) -> dict:
        """Get environment variables (excluding secrets)."""
        env_info = {}
        secret_patterns = ['token', 'key', 'secret', 'password', 'auth', 'credential']
        
        for key, value in os.environ.items():
            key_lower = key.lower()
            if any(pattern in key_lower for pattern in secret_patterns):
                env_info[key] = "[REDACTED]"
            else:
                env_info[key] = value
        
        return env_info
    
    def get_directory_structure(self) -> dict:
        """Get directory structure."""
        structure = {}
        
        for item in Path('.').iterdir():
            if item.name.startswith('.'):
                continue
            
            if item.is_dir():
                structure[item.name] = "DIR"
            else:
                size = item.stat().st_size
                structure[item.name] = f"FILE ({size} bytes)"
        
        return structure
    
    def get_dependencies_info(self) -> list[dict]:
        """Get installed packages information."""
        packages = []
        
        try:
            import subprocess
            result = subprocess.run(
                ['pip', 'list', '--format=json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                critical = ['discord', 'aiosqlite', 'pydantic', 'aiohttp', 'psutil']
                
                for pkg in data:
                    if pkg['name'].lower() in critical:
                        packages.append({
                            "name": pkg['name'],
                            "version": pkg['version']
                        })
        except Exception as e:
            logger.error(f"Failed to get dependencies: {e}")
        
        return packages
    
    def get_disk_usage(self) -> dict:
        """Get disk usage information."""
        try:
            import psutil
            usage = psutil.disk_usage('/')
            return {
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent_used": usage.percent
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_memory_info(self) -> dict:
        """Get memory usage information."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                "total_mb": round(mem.total / (1024**2), 2),
                "available_mb": round(mem.available / (1024**2), 2),
                "percent_used": mem.percent,
                "process_memory_mb": round(psutil.Process().memory_info().rss / (1024**2), 2)
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def run_diagnostics(self) -> dict:
        """Run all diagnostics and return a comprehensive report."""
        diagnostics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": self.get_system_info(),
            "disk": self.get_disk_usage(),
            "memory": self.get_memory_info(),
            "dependencies": self.get_dependencies_info(),
            "checks": {}
        }
        
        # Run basic checks
        try:
            from core.operations.health import run_full_health_check
            health = await run_full_health_check()
            diagnostics["checks"]["health"] = health.to_dict()
        except Exception as e:
            diagnostics["checks"]["health"] = {"error": str(e)}
        
        # Check database
        try:
            from core.database import Database
            db = Database()
            await db.initialize()
            tables = await db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
            diagnostics["checks"]["database"] = {
                "status": "connected",
                "tables_count": len(tables) if tables else 0
            }
            await db.close()
        except Exception as e:
            diagnostics["checks"]["database"] = {"status": "error", "error": str(e)}
        
        # Check bot status
        try:
            from core.bot import WOSMBot
            if hasattr(WOSMBot, '_instance') and WOSMBot._instance:
                bot = WOSMBot._instance
                diagnostics["checks"]["bot"] = {
                    "status": "running" if not bot.is_closed() else "stopped",
                    "latency": getattr(bot, 'latency', None),
                    "guilds": len(bot.guilds) if hasattr(bot, 'guilds') else 0
                }
            else:
                diagnostics["checks"]["bot"] = {"status": "not_initialized"}
        except Exception as e:
            diagnostics["checks"]["bot"] = {"status": "error", "error": str(e)}
        
        return diagnostics
    
    def format_diagnostics(self, diagnostics: Optional[dict] = None) -> str:
        """Format diagnostics for display."""
        if diagnostics is None:
            diagnostics = {}
        
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "🔍 System Diagnostics",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "💻 **System:**",
            f"  Platform: {diagnostics.get('system', {}).get('platform', 'N/A')}",
            f"  Release: {diagnostics.get('system', {}).get('platform_release', 'N/A')}",
            f"  Python: {diagnostics.get('system', {}).get('python_version', 'N/A')[:50]}",
            "",
            "💾 **Disk:**",
            f"  Used: {diagnostics.get('disk', {}).get('used_gb', 'N/A')} GB / {diagnostics.get('disk', {}).get('total_gb', 'N/A')} GB",
            f"  Free: {diagnostics.get('disk', {}).get('free_gb', 'N/A')} GB ({diagnostics.get('disk', {}).get('percent_used', 'N/A')}%)",
            "",
            "🧠 **Memory:**",
            f"  Used: {diagnostics.get('memory', {}).get('percent_used', 'N/A')}%",
            f"  Process: {diagnostics.get('memory', {}).get('process_memory_mb', 'N/A')} MB",
            "",
            "🗄️ **Database:**",
            f"  Status: {diagnostics.get('checks', {}).get('database', {}).get('status', 'N/A')}",
            f"  Tables: {diagnostics.get('checks', {}).get('database', {}).get('tables_count', 'N/A')}",
            "",
            "🤖 **Bot:**",
            f"  Status: {diagnostics.get('checks', {}).get('bot', {}).get('status', 'N/A')}",
            f"  Guilds: {diagnostics.get('checks', {}).get('bot', {}).get('guilds', 'N/A')}",
            f"  Latency: {diagnostics.get('checks', {}).get('bot', {}).get('latency', 'N/A')}",
            "",
            "📦 **Dependencies:**",
        ]
        
        for dep in diagnostics.get('dependencies', []):
            lines.append(f"  • {dep['name']}: {dep['version']}")
        
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        return "\n".join(lines)


# Global instance
_diagnostics: Optional[DiagnosticsCollector] = None


def get_diagnostics() -> DiagnosticsCollector:
    """Get or create the diagnostics collector."""
    global _diagnostics
    if _diagnostics is None:
        _diagnostics = DiagnosticsCollector()
    return _diagnostics
