"""
WOS-M Operations Control System - Health Monitoring

This module provides comprehensive health checking for the bot,
database, APIs, and all integrated services.
"""

import asyncio
import hashlib
import os
import platform
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import psutil

try:
    import discord
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class CheckSeverity(Enum):
    """Severity levels for individual checks."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""
    name: str
    status: str  # pass, fail, warning
    severity: CheckSeverity
    message_ar: str
    message_en: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: Optional[dict] = None
    suggested_action: Optional[str] = None


@dataclass
class HealthStatusReport:
    """Complete health status report."""
    overall_status: HealthStatus
    checks: list[HealthCheckResult]
    severity: CheckSeverity
    message_ar: str
    message_en: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    suggested_action: Optional[str] = None
    uptime_seconds: float = 0.0
    version: str = "1.0.0"

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/reporting."""
        return {
            "overall_status": self.overall_status.value,
            "severity": self.severity.value,
            "message_ar": self.message_ar,
            "message_en": self.message_en,
            "timestamp": self.timestamp.isoformat(),
            "uptime_seconds": self.uptime_seconds,
            "version": self.version,
            "checks_count": len(self.checks),
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "severity": c.severity.value,
                    "message_en": c.message_en,
                    "suggested_action": c.suggested_action
                }
                for c in self.checks
            ]
        }


# Bot start time for uptime calculation
BOT_START_TIME: Optional[float] = None


def set_bot_start_time() -> None:
    """Set the bot start time for uptime calculation."""
    global BOT_START_TIME
    if BOT_START_TIME is None:
        BOT_START_TIME = time.time()


def get_uptime_seconds() -> float:
    """Get bot uptime in seconds."""
    if BOT_START_TIME is None:
        return 0.0
    return time.time() - BOT_START_TIME


def _read_version() -> str:
    """Read current version from VERSION file."""
    try:
        version_file = Path("VERSION")
        if version_file.exists():
            return version_file.read_text().strip()
    except Exception:
        pass
    return "1.0.0"


def _safe_check(name: str, severity: CheckSeverity, check_func, 
                success_ar: str, success_en: str, 
                failure_ar: str, failure_en: str,
                **kwargs) -> HealthCheckResult:
    """Safely run a health check and handle exceptions."""
    try:
        result = check_func(**kwargs)
        if result.get("status") == "pass":
            return HealthCheckResult(
                name=name,
                status="pass",
                severity=severity,
                message_ar=success_ar,
                message_en=success_en,
                data=result.get("data"),
                suggested_action=result.get("suggested_action")
            )
        else:
            return HealthCheckResult(
                name=name,
                status="fail",
                severity=severity,
                message_ar=result.get("message_ar", failure_ar),
                message_en=result.get("message_en", failure_en),
                suggested_action=result.get("suggested_action")
            )
    except Exception as e:
        return HealthCheckResult(
            name=name,
            status="fail",
            severity=severity,
            message_ar=f"خطأ في الفحص: {type(e).__name__}",
            message_en=f"Check error: {type(e).__name__}",
            suggested_action="Check system logs"
        )


# ==================== Individual Health Checks ====================

def check_bot_process() -> dict:
    """Check if bot process is running."""
    pid = os.getpid()
    try:
        process = psutil.Process(pid)
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent(interval=0.1)
        return {
            "status": "pass",
            "data": {
                "pid": pid,
                "memory_mb": round(memory_mb, 2),
                "cpu_percent": round(cpu_percent, 2),
                "status": process.status()
            }
        }
    except Exception as e:
        return {
            "status": "fail",
            "message_ar": f"فشل في قراءة حالة العملية: {e}",
            "message_en": f"Failed to read process status: {e}",
            "suggested_action": "Restart the bot"
        }


def check_discord_connection() -> dict:
    """Check Discord gateway connection."""
    if not DISCORD_AVAILABLE:
        return {
            "status": "warning",
            "message_ar": "مكتبة Discord غير متاحة",
            "message_en": "Discord library not available",
            "suggested_action": "Install discord.py"
        }
    
    # Check if we have a bot instance with gateway connection
    # This will be updated by the actual bot
    from core.bot import WOSMBot
    
    try:
        if hasattr(WOSMBot, '_instance') and WOSMBot._instance is not None:
            bot = WOSMBot._instance
            if bot.is_closed():
                return {
                    "status": "fail",
                    "message_ar": "البوت غير متصل بـ Discord",
                    "message_en": "Bot not connected to Discord",
                    "suggested_action": "Check bot token and restart"
                }
            return {
                "status": "pass",
                "data": {
                    "logged_in": True,
                    "latency": bot.latency if hasattr(bot, 'latency') else None
                }
            }
    except Exception:
        pass
    
    return {
        "status": "warning",
        "message_ar": "لم يتم ربط البوت بعد",
        "message_en": "Bot not yet initialized",
        "suggested_action": "Wait for bot initialization"
    }


def check_discord_latency() -> dict:
    """Check Discord API latency."""
    if not DISCORD_AVAILABLE:
        return {"status": "warning", "message_ar": "غير متاح", "message_en": "Not available"}
    
    try:
        from core.bot import WOSMBot
        if hasattr(WOSMBot, '_instance') and WOSMBot._instance is not None:
            bot = WOSMBot._instance
            latency = getattr(bot, 'latency', None)
            if latency is not None:
                if latency < 0.2:
                    return {"status": "pass", "data": {"latency_ms": round(latency * 1000, 2)}}
                elif latency < 0.5:
                    return {
                        "status": "warning",
                        "message_ar": f"زمن الاستجابة مرتفع: {latency*1000:.0f}ms",
                        "message_en": f"High latency: {latency*1000:.0f}ms",
                        "suggested_action": "Check network connection"
                    }
                else:
                    return {
                        "status": "fail",
                        "message_ar": f"زمن الاستجابة حرج: {latency*1000:.0f}ms",
                        "message_en": f"Critical latency: {latency*1000:.0f}ms",
                        "suggested_action": "Investigate network issues"
                    }
    except Exception:
        pass
    
    return {"status": "warning", "message_ar": "غير متاح", "message_en": "Not available"}


async def check_database_connection() -> dict:
    """Check database connection and basic operations."""
    try:
        from core.database import Database
        db = Database()
        await db.initialize()
        
        # Test read
        result = await db.fetchone("SELECT 1 as test")
        if result is None or result.get("test") != 1:
            return {
                "status": "fail",
                "message_ar": "فشل في قراءة البيانات",
                "message_en": "Database read test failed"
            }
        
        # Test write
        await db.execute("SELECT 1")
        
        # Check tables
        tables = await db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
        table_count = len(tables) if tables else 0
        
        await db.close()
        
        return {
            "status": "pass",
            "data": {
                "tables_count": table_count,
                "connection": "active"
            }
        }
    except Exception as e:
        return {
            "status": "fail",
            "message_ar": f"فشل الاتصال بقاعدة البيانات: {type(e).__name__}",
            "message_en": f"Database connection failed: {type(e).__name__}",
            "suggested_action": "Check database file and permissions"
        }


async def check_database_tables() -> dict:
    """Check if required tables exist."""
    required_tables = [
        'players', 'alliances', 'gift_codes', 'gift_redemptions',
        'settings', 'permissions', 'audit_logs'
    ]
    
    try:
        from core.database import Database
        db = Database()
        await db.initialize()
        
        existing = await db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
        existing_names = [t['name'] for t in existing] if existing else []
        
        missing = [t for t in required_tables if t not in existing_names]
        
        await db.close()
        
        if missing:
            return {
                "status": "fail",
                "message_ar": f"جداول مفقودة: {', '.join(missing)}",
                "message_en": f"Missing tables: {', '.join(missing)}",
                "suggested_action": "Run database migrations"
            }
        
        return {
            "status": "pass",
            "data": {"required_tables": len(required_tables), "existing": len(existing_names)}
        }
    except Exception as e:
        return {
            "status": "fail",
            "message_ar": f"فشل في فحص الجداول: {e}",
            "message_en": f"Failed to check tables: {e}"
        }


def check_disk_space() -> dict:
    """Check available disk space."""
    try:
        usage = psutil.disk_usage('/')
        percent = usage.percent
        free_gb = usage.free / (1024**3)
        
        if percent > 95:
            return {
                "status": "fail",
                "message_ar": f"مساحة القرص حرجة: {percent:.1f}% مستخدم",
                "message_en": f"Critical disk usage: {percent:.1f}% used",
                "suggested_action": "Free up disk space immediately"
            }
        elif percent > 85:
            return {
                "status": "warning",
                "message_ar": f"مساحة القرص منخفضة: {percent:.1f}% مستخدم",
                "message_en": f"Low disk space: {percent:.1f}% used",
                "suggested_action": "Consider freeing up disk space"
            }
        
        return {
            "status": "pass",
            "data": {
                "percent_used": round(percent, 2),
                "free_gb": round(free_gb, 2)
            }
        }
    except Exception as e:
        return {"status": "fail", "message_ar": f"فشل: {e}", "message_en": f"Failed: {e}"}


def check_memory_usage() -> dict:
    """Check memory usage."""
    try:
        mem = psutil.virtual_memory()
        percent = mem.percent
        available_mb = mem.available / (1024**2)
        
        if percent > 95:
            return {
                "status": "fail",
                "message_ar": f"استخدام الذاكرة حرج: {percent:.1f}%",
                "message_en": f"Critical memory usage: {percent:.1f}%",
                "suggested_action": "Investigate memory leak or restart"
            }
        elif percent > 85:
            return {
                "status": "warning",
                "message_ar": f"استخدام الذاكرة مرتفع: {percent:.1f}%",
                "message_en": f"High memory usage: {percent:.1f}%",
                "suggested_action": "Monitor memory usage"
            }
        
        return {
            "status": "pass",
            "data": {
                "percent": round(percent, 2),
                "available_mb": round(available_mb, 2)
            }
        }
    except Exception as e:
        return {"status": "fail", "message_ar": f"فشل: {e}", "message_en": f"Failed: {e}"}


def check_python_version() -> dict:
    """Check Python version compatibility."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        return {
            "status": "fail",
            "message_ar": f"إصدار Python غير مدعوم: {version.major}.{version.minor}",
            "message_en": f"Unsupported Python version: {version.major}.{version.minor}",
            "suggested_action": "Upgrade to Python 3.10+"
        }
    return {
        "status": "pass",
        "data": {"version": f"{version.major}.{version.minor}.{version.micro}"}
    }


def check_package_versions() -> dict:
    """Check critical package versions."""
    critical_packages = {
        'discord': '2.0.0',
        'aiosqlite': '0.17.0',
        'pydantic': '2.0.0'
    }
    
    results = {}
    issues = []
    
    for package, min_version in critical_packages.items():
        try:
            if package == 'discord':
                import discord
                version = discord.__version__
            elif package == 'aiosqlite':
                import aiosqlite
                version = aiosqlite.version
            elif package == 'pydantic':
                import pydantic
                version = pydantic.VERSION
            else:
                version = "unknown"
            
            results[package] = version
        except ImportError:
            results[package] = "not_installed"
            issues.append(package)
    
    if issues:
        return {
            "status": "fail",
            "message_ar": f"حزم مفقودة: {', '.join(issues)}",
            "message_en": f"Missing packages: {', '.join(issues)}",
            "suggested_action": "Install required packages"
        }
    
    return {"status": "pass", "data": {"packages": results}}


async def check_queue_status() -> dict:
    """Check process queue status."""
    try:
        from core.process_queue import ProcessQueue
        
        if not hasattr(ProcessQueue, '_instance') or ProcessQueue._instance is None:
            return {
                "status": "warning",
                "message_ar": "قائمة العمليات غير مهيأة",
                "message_en": "Process queue not initialized"
            }
        
        queue = ProcessQueue._instance
        size = getattr(queue, 'queue_size', 0) if hasattr(queue, 'queue_size') else 0
        active = getattr(queue, 'active_workers', 0) if hasattr(queue, 'active_workers') else 0
        
        if size > 100:
            return {
                "status": "warning",
                "message_ar": f"قائمة العمليات متراكمة: {size} عنصر",
                "message_en": f"Queue backlog: {size} items",
                "data": {"size": size, "active_workers": active}
            }
        
        return {
            "status": "pass",
            "data": {"size": size, "active_workers": active}
        }
    except Exception as e:
        return {
            "status": "warning",
            "message_ar": f"فشل في فحص القائمة: {e}",
            "message_en": f"Failed to check queue: {e}"
        }


async def check_wos_api() -> dict:
    """Check WOS API status."""
    try:
        from config.settings import settings
        
        if not settings.api.wos_api_base_url:
            return {
                "status": "warning",
                "message_ar": "WOS API غير مُعد",
                "message_en": "WOS API not configured"
            }
        
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=5)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{settings.api.wos_api_base_url}/health") as resp:
                if resp.status == 200:
                    return {"status": "pass", "data": {"status_code": 200}}
                else:
                    return {
                        "status": "warning",
                        "message_ar": f"WOS API responded with {resp.status}",
                        "message_en": f"WOS API responded with {resp.status}"
                    }
    except aiohttp.ClientConnectorError:
        return {
            "status": "warning",
            "message_ar": "WOS API غير متصل",
            "message_en": "WOS API unreachable"
        }
    except Exception:
        return {
            "status": "warning",
            "message_ar": "WOS API غير متاح",
            "message_en": "WOS API not available"
        }


async def check_gift_api() -> dict:
    """Check Gift API status."""
    try:
        from config.settings import settings
        
        gift_url = settings.api.wos_gift_public_endpoint
        if not gift_url:
            return {
                "status": "warning",
                "message_ar": "Gift API غير مُعد",
                "message_en": "Gift API not configured"
            }
        
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=5)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(f"{gift_url}/health", timeout=5) as resp:
                    if resp.status == 200:
                        return {"status": "pass", "data": {"status_code": 200}}
            except Exception:
                pass
            
            return {
                "status": "warning",
                "message_ar": "Gift API لا يستجيب",
                "message_en": "Gift API not responding"
            }
    except Exception:
        return {
            "status": "warning",
            "message_ar": "Gift API غير متاح",
            "message_en": "Gift API not available"
        }


async def check_captcha_service() -> dict:
    """Check captcha service status."""
    try:
        from config.settings import settings
        
        if not settings.api.captcha_service_url:
            return {
                "status": "warning",
                "message_ar": "خدمة CAPTCHA غير مُعدّة",
                "message_en": "Captcha service not configured"
            }
        
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=5)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{settings.api.captcha_service_url}/health") as resp:
                if resp.status == 200:
                    return {"status": "pass"}
        
        return {
            "status": "warning",
            "message_ar": "خدمة CAPTCHA لا تستجيب",
            "message_en": "Captcha service not responding"
        }
    except Exception:
        return {
            "status": "warning",
            "message_ar": "خدمة CAPTCHA غير متاحة",
            "message_en": "Captcha service not available"
        }


async def check_rate_limiter() -> dict:
    """Check rate limiter status."""
    try:
        from integrations.rate_limiter import RateLimiter
        
        if not hasattr(RateLimiter, '_instance') or RateLimiter._instance is None:
            return {
                "status": "warning",
                "message_ar": "Rate Limiter غير مهيأ",
                "message_en": "Rate limiter not initialized"
            }
        
        limiter = RateLimiter._instance
        current = getattr(limiter, 'current_calls', 0)
        limit = getattr(limiter, 'max_calls', 60)
        
        return {
            "status": "pass",
            "data": {
                "current_calls": current,
                "limit": limit,
                "usage_percent": round(current / limit * 100, 1) if limit > 0 else 0
            }
        }
    except Exception:
        return {
            "status": "warning",
            "message_ar": "فشل في فحص Rate Limiter",
            "message_en": "Failed to check rate limiter"
        }


async def check_audit_log() -> dict:
    """Check audit log functionality."""
    try:
        from core.database import Database
        db = Database()
        await db.initialize()
        
        # Check if audit_logs table exists and is writable
        result = await db.fetchone("SELECT COUNT(*) as cnt FROM audit_logs")
        count = result.get('cnt', 0) if result else 0
        
        await db.close()
        
        return {
            "status": "pass",
            "data": {"total_logs": count}
        }
    except Exception as e:
        return {
            "status": "warning",
            "message_ar": f"مشكلة في سجل التدقيق: {e}",
            "message_en": f"Audit log issue: {e}"
        }


def check_backup_path() -> dict:
    """Check backup directory status."""
    backup_path = os.environ.get('OPS_BACKUP_PATH', 'backups')
    
    try:
        Path(backup_path).mkdir(parents=True, exist_ok=True)
        
        # Check write permissions
        test_file = Path(backup_path) / '.health_check_test'
        test_file.write_text('test')
        test_file.unlink()
        
        return {
            "status": "pass",
            "data": {"path": backup_path, "writable": True}
        }
    except Exception as e:
        return {
            "status": "fail",
            "message_ar": f"مسار النسخ الاحتياطي لا يعمل: {e}",
            "message_en": f"Backup path not working: {e}",
            "suggested_action": "Check backup directory permissions"
        }


def check_environment_variables() -> dict:
    """Check required environment variables."""
    required = ['DISCORD_BOT_TOKEN']
    optional = ['DOTENV_READ', 'OPS_BACKUP_ENABLED', 'OPS_ALERTS_ENABLED']
    
    missing_required = []
    missing_optional = []
    
    for var in required:
        if not os.environ.get(var):
            missing_required.append(var)
    
    for var in optional:
        if not os.environ.get(var):
            missing_optional.append(var)
    
    if missing_required:
        return {
            "status": "fail",
            "message_ar": f"متغيرات مطلوبة مفقودة: {', '.join(missing_required)}",
            "message_en": f"Missing required env vars: {', '.join(missing_required)}",
            "suggested_action": "Set required environment variables"
        }
    
    return {
        "status": "pass",
        "data": {
            "required_set": True,
            "optional_missing": missing_optional
        }
    }


def check_docker_health() -> dict:
    """Check Docker container health (if running in Docker)."""
    try:
        # Check if we're in a container
        if Path('/.dockerenv').exists():
            # Try to read Docker health status
            health_file = Path('/dev/health')
            if health_file.exists():
                status = health_file.read_text().strip()
                if status == 'healthy':
                    return {"status": "pass", "data": {"docker_health": "healthy"}}
                else:
                    return {
                        "status": "warning",
                        "message_ar": f"Docker health: {status}",
                        "message_en": f"Docker health: {status}"
                    }
        
        return {
            "status": "warning",
            "message_ar": "غير يعمل داخل Docker",
            "message_en": "Not running in Docker"
        }
    except Exception:
        return {
            "status": "warning",
            "message_ar": "فشل في فحص Docker",
            "message_en": "Docker check failed"
        }


# ==================== Main Health Check Function ====================

async def run_full_health_check() -> HealthStatusReport:
    """
    Run all health checks and return a comprehensive report.
    
    Returns:
        HealthStatusReport with overall status and all check results
    """
    set_bot_start_time()
    
    checks: list[HealthCheckResult] = []
    
    # Run synchronous checks
    checks.append(_safe_check(
        "bot_process", CheckSeverity.INFO,
        check_bot_process,
        "عملية البوت تعمل بشكل طبيعي",
        "Bot process running normally",
        "فشل في عملية البوت",
        "Bot process failed"
    ))
    
    checks.append(_safe_check(
        "python_version", CheckSeverity.INFO,
        check_python_version,
        "إصدار Python مدعوم",
        "Python version supported",
        "إصدار Python غير مدعوم",
        "Unsupported Python version"
    ))
    
    checks.append(_safe_check(
        "disk_space", CheckSeverity.WARNING,
        check_disk_space,
        "مساحة القرص كافية",
        "Disk space adequate",
        "مساحة القرص حرجة",
        "Critical disk space"
    ))
    
    checks.append(_safe_check(
        "memory_usage", CheckSeverity.WARNING,
        check_memory_usage,
        "استخدام الذاكرة طبيعي",
        "Memory usage normal",
        "استخدام الذاكرة حرج",
        "Critical memory usage"
    ))
    
    checks.append(_safe_check(
        "environment", CheckSeverity.CRITICAL,
        check_environment_variables,
        "جميع المتغيرات المطلوبة مضبوطة",
        "All required variables set",
        "متغيرات مطلوبة مفقودة",
        "Required variables missing"
    ))
    
    checks.append(_safe_check(
        "backup_path", CheckSeverity.WARNING,
        check_backup_path,
        "مسار النسخ الاحتياطي يعمل",
        "Backup path operational",
        "مشكلة في مسار النسخ الاحتياطي",
        "Backup path issue"
    ))
    
    # Run async checks
    checks.append(_safe_check(
        "database_connection", CheckSeverity.CRITICAL,
        lambda: asyncio.run(check_database_connection()),
        "قاعدة البيانات متصلة",
        "Database connected",
        "فشل في قاعدة البيانات",
        "Database failed"
    ))
    
    try:
        db_check = await check_database_connection()
        if db_check.get("status") == "pass":
            checks.append(_safe_check(
                "database_tables", CheckSeverity.ERROR,
                lambda: asyncio.run(check_database_tables()),
                "جميع الجداول موجودة",
                "All tables present",
                "جداول مفقودة",
                "Missing tables"
            ))
    except Exception:
        pass
    
    checks.append(_safe_check(
        "queue_status", CheckSeverity.INFO,
        lambda: asyncio.run(check_queue_status()),
        "قائمة العمليات تعمل",
        "Queue operational",
        "مشكلة في قائمة العمليات",
        "Queue issue"
    ))
    
    checks.append(_safe_check(
        "rate_limiter", CheckSeverity.INFO,
        lambda: asyncio.run(check_rate_limiter()),
        "Rate Limiter يعمل",
        "Rate limiter operational",
        "فشل في Rate Limiter",
        "Rate limiter failed"
    ))
    
    checks.append(_safe_check(
        "audit_log", CheckSeverity.INFO,
        lambda: asyncio.run(check_audit_log()),
        "سجل التدقيق يعمل",
        "Audit log operational",
        "مشكلة في سجل التدقيق",
        "Audit log issue"
    ))
    
    checks.append(_safe_check(
        "wos_api", CheckSeverity.WARNING,
        lambda: asyncio.run(check_wos_api()),
        "WOS API متاح",
        "WOS API available",
        "WOS API غير متاح",
        "WOS API unavailable"
    ))
    
    checks.append(_safe_check(
        "gift_api", CheckSeverity.WARNING,
        lambda: asyncio.run(check_gift_api()),
        "Gift API متاح",
        "Gift API available",
        "Gift API غير متاح",
        "Gift API unavailable"
    ))
    
    checks.append(_safe_check(
        "captcha_service", CheckSeverity.INFO,
        lambda: asyncio.run(check_captcha_service()),
        "خدمة CAPTCHA متاحة",
        "Captcha service available",
        "خدمة CAPTCHA غير متاحة",
        "Captcha service unavailable"
    ))
    
    checks.append(_safe_check(
        "discord_connection", CheckSeverity.INFO,
        check_discord_connection,
        "Discord متصل",
        "Discord connected",
        "Discord غير متصل",
        "Discord not connected"
    ))
    
    checks.append(_safe_check(
        "discord_latency", CheckSeverity.INFO,
        check_discord_latency,
        "زمن استجابة Discord طبيعي",
        "Discord latency normal",
        "زمن استجابة Discord مرتفع",
        "High Discord latency"
    ))
    
    checks.append(_safe_check(
        "package_versions", CheckSeverity.ERROR,
        check_package_versions,
        "جميع الحزم متوفرة",
        "All packages available",
        "حزم مفقودة",
        "Missing packages"
    ))
    
    checks.append(_safe_check(
        "docker_health", CheckSeverity.INFO,
        check_docker_health,
        "Docker صحي",
        "Docker healthy",
        "مشكلة في Docker",
        "Docker issue"
    ))
    
    # Calculate overall status
    failed_critical = [c for c in checks if c.severity == CheckSeverity.CRITICAL and c.status == "fail"]
    failed_error = [c for c in checks if c.severity == CheckSeverity.ERROR and c.status == "fail"]
    failed_warning = [c for c in checks if c.severity == CheckSeverity.WARNING and c.status == "fail"]
    passed = [c for c in checks if c.status == "pass"]
    
    if failed_critical:
        overall = HealthStatus.UNHEALTHY
        severity = CheckSeverity.CRITICAL
        msg_ar = f"فشل {len(failed_critical)} فحص حرج"
        msg_en = f"{len(failed_critical)} critical checks failed"
        action = "اصلاح المشاكل الحرجة فوراً"
    elif failed_error:
        overall = HealthStatus.UNHEALTHY
        severity = CheckSeverity.ERROR
        msg_ar = f"فشل {len(failed_error)} فحص خطير"
        msg_en = f"{len(failed_error)} error checks failed"
        action = "اصلاح المشاكل الخطيرة"
    elif failed_warning:
        overall = HealthStatus.DEGRADED
        severity = CheckSeverity.WARNING
        msg_ar = f"{len(failed_warning)} تحذيرات"
        msg_en = f"{len(failed_warning)} warnings"
        action = "مراقبة المشاكل"
    else:
        overall = HealthStatus.HEALTHY
        severity = CheckSeverity.INFO
        msg_ar = "جميع الفحوصات ناجحة"
        msg_en = "All checks passed"
        action = None
    
    return HealthStatusReport(
        overall_status=overall,
        checks=checks,
        severity=severity,
        message_ar=msg_ar,
        message_en=msg_en,
        uptime_seconds=get_uptime_seconds(),
        version=_read_version(),
        suggested_action=action
    )


def run_health_check_sync() -> dict:
    """Run health check synchronously for CLI usage."""
    try:
        report = asyncio.run(run_full_health_check())
        return report.to_dict()
    except Exception as e:
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


if __name__ == "__main__":
    import json
    result = run_health_check_sync()
    print(json.dumps(result, indent=2, default=str))
