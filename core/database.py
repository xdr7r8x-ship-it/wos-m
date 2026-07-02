"""
WOS-M Database System
© MANSOUR — WOS-M. All rights reserved.
"""
import asyncio
import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, List, Tuple
import logging

from config.settings import settings

logger = logging.getLogger(__name__)


class Database:
    """Central database manager for WOS-M."""
    
    _instance = None
    _db: Optional[aiosqlite.Connection] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def initialize(self, db_path: Optional[str] = None):
        """Initialize the database connection and create tables."""
        if self._db is not None:
            return
            
        if db_path is None:
            db_path = settings.database.url.replace("sqlite:///", "")
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(db_path)
        self._db.row_factory = aiosqlite.Row
        
        await self._create_tables()
        await self._run_migrations()
        
        logger.info(f"Database initialized at {db_path}")
    
    async def _create_tables(self):
        """Create all required tables."""
        await self._db.executescript("""
            -- Bot Settings
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Language Settings
            CREATE TABLE IF NOT EXISTS language_settings (
                locale TEXT PRIMARY KEY,
                is_default BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Theme Settings
            CREATE TABLE IF NOT EXISTS theme_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Custom Buttons
            CREATE TABLE IF NOT EXISTS custom_buttons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                button_key TEXT UNIQUE NOT NULL,
                icon TEXT NOT NULL DEFAULT '',
                label_key TEXT NOT NULL,
                position INTEGER NOT NULL,
                is_enabled BOOLEAN DEFAULT 1,
                linked_feature TEXT,
                required_permission TEXT DEFAULT 'member',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Custom Texts
            CREATE TABLE IF NOT EXISTS custom_texts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text_key TEXT UNIQUE NOT NULL,
                value_ar TEXT,
                value_en TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Feature Registry
            CREATE TABLE IF NOT EXISTS feature_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_key TEXT UNIQUE NOT NULL,
                name_ar TEXT NOT NULL,
                name_en TEXT NOT NULL,
                description_ar TEXT,
                description_en TEXT,
                icon TEXT DEFAULT '⚙️',
                is_enabled BOOLEAN DEFAULT 1,
                required_permission TEXT DEFAULT 'member',
                entry_button BOOLEAN DEFAULT 1,
                handler_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Permissions
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('owner', 'global_admin', 'server_admin', 'alliance_admin', 'member')),
                guild_id TEXT,
                alliance_id INTEGER,
                granted_by TEXT,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(discord_id, guild_id)
            );
            
            -- Admins
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT UNIQUE NOT NULL,
                discord_name TEXT,
                role TEXT NOT NULL,
                added_by TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP
            );
            
            -- Audit Logs
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                user_name TEXT,
                action TEXT NOT NULL,
                category TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Process Queue
            CREATE TABLE IF NOT EXISTS process_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                task_data TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued', 'active', 'completed', 'failed', 'retry')),
                priority INTEGER NOT NULL DEFAULT 500,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                error_message TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Alliances
            CREATE TABLE IF NOT EXISTS alliances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                state_kid TEXT,
                discord_guild_id TEXT,
                discord_role_id TEXT,
                auto_gift_enabled BOOLEAN DEFAULT 0,
                gift_channel_id TEXT,
                member_count INTEGER DEFAULT 0,
                sync_enabled BOOLEAN DEFAULT 0,
                report_channel_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Alliance Settings
            CREATE TABLE IF NOT EXISTS alliance_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alliance_id INTEGER NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value TEXT,
                FOREIGN KEY (alliance_id) REFERENCES alliances(id) ON DELETE CASCADE,
                UNIQUE(alliance_id, setting_key)
            );
            
            -- Players
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fid TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                alliance_id INTEGER,
                state_kid TEXT,
                level INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                last_synced TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (alliance_id) REFERENCES alliances(id) ON DELETE SET NULL
            );
            
            -- Player History
            CREATE TABLE IF NOT EXISTS player_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                changed_by TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
            );
            
            -- Gift Codes
            CREATE TABLE IF NOT EXISTS gift_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                alliance_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'valid', 'invalid', 'expired', 'redeeming', 'redeemed', 'already_redeemed', 'failed')),
                added_by TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                redeemed_at TIMESTAMP,
                FOREIGN KEY (alliance_id) REFERENCES alliances(id) ON DELETE SET NULL
            );
            
            -- Gift Redemptions
            CREATE TABLE IF NOT EXISTS gift_redemptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                redeemed_at TIMESTAMP,
                error_message TEXT,
                provider TEXT,
                api_status TEXT,
                FOREIGN KEY (code_id) REFERENCES gift_codes(id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
            );
            
            -- Gift Redemption Batches
            CREATE TABLE IF NOT EXISTS gift_redemption_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                alliance_id INTEGER,
                total_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (alliance_id) REFERENCES alliances(id) ON DELETE SET NULL
            );
            
            -- Gift Redemption Results
            CREATE TABLE IF NOT EXISTS gift_redemption_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                player_name TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                redeemed_at TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES gift_redemption_batches(id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
            );
            
            -- Events
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_date DATE NOT NULL,
                event_time TIME,
                location TEXT,
                description TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Attendance Records
            CREATE TABLE IF NOT EXISTS attendance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'present' CHECK(status IN ('present', 'absent', 'late', 'excused')),
                recorded_by TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
            );
            
            -- Bear Hunts
            CREATE TABLE IF NOT EXISTS bear_hunts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alliance_id INTEGER,
                hunt_date DATE NOT NULL,
                location TEXT,
                total_damage INTEGER DEFAULT 0,
                is_archived BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (alliance_id) REFERENCES alliances(id) ON DELETE SET NULL
            );
            
            -- Bear Damage Records
            CREATE TABLE IF NOT EXISTS bear_damage_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hunt_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                damage INTEGER NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hunt_id) REFERENCES bear_hunts(id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
            );
            
            -- Notifications
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                notification_type TEXT NOT NULL,
                message TEXT NOT NULL,
                channel_id TEXT,
                is_repeat BOOLEAN DEFAULT 0,
                repeat_interval INTEGER,
                timezone TEXT DEFAULT 'UTC',
                scheduled_time TIME,
                is_active BOOLEAN DEFAULT 1,
                last_sent TIMESTAMP,
                next_run TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Ministers
            CREATE TABLE IF NOT EXISTS ministers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                player_id INTEGER,
                alliance_id INTEGER,
                start_date DATE,
                end_date DATE,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE SET NULL,
                FOREIGN KEY (alliance_id) REFERENCES alliances(id) ON DELETE SET NULL
            );
            
            -- Minister Assignment History
            CREATE TABLE IF NOT EXISTS minister_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                minister_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                changed_by TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (minister_id) REFERENCES ministers(id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
            );
            
            -- Backups
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_players_fid ON players(fid);
            CREATE INDEX IF NOT EXISTS idx_players_alliance ON players(alliance_id);
            CREATE INDEX IF NOT EXISTS idx_gift_codes_status ON gift_codes(status);
            CREATE INDEX IF NOT EXISTS idx_process_queue_status ON process_queue(status);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
            CREATE INDEX IF NOT EXISTS idx_custom_buttons_position ON custom_buttons(position);
        """)
        await self._db.commit()
    
    async def _run_migrations(self):
        """Run any pending migrations."""
        # Create migrations tracking table
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Get applied migrations
        async with self._db.execute("SELECT name FROM _migrations") as cursor:
            applied = {row[0] for row in await cursor.fetchall()}
        
        migrations = [
            {
                "name": "add_redemption_unique",
                "sql": """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_redemption_unique 
                    ON gift_redemptions(code_id, player_id);
                """
            }
        ]
        
        for migration in migrations:
            if migration["name"] not in applied:
                try:
                    for statement in migration["sql"].strip().split(";"):
                        stmt = statement.strip()
                        if stmt:
                            await self._db.execute(stmt)
                    await self._db.execute(
                        "INSERT INTO _migrations (name) VALUES (?)",
                        (migration["name"],)
                    )
                    await self._db.commit()
                    logger.info(f"Migration applied: {migration['name']}")
                except Exception as e:
                    logger.warning(f"Migration {migration['name']}: {e}")
                    await self._db.rollback()
    
    async def execute(self, query: str, parameters: Tuple = ()) -> aiosqlite.Cursor:
        """Execute a query."""
        return await self._db.execute(query, parameters)
    
    async def executemany(self, query: str, parameters: List[Tuple]) -> aiosqlite.Cursor:
        """Execute many queries."""
        return await self._db.executemany(query, parameters)
    
    async def fetchone(self, query: str, parameters: Tuple = ()) -> Optional[aiosqlite.Row]:
        """Fetch one row."""
        async with self._db.execute(query, parameters) as cursor:
            return await cursor.fetchone()
    
    async def fetchall(self, query: str, parameters: Tuple = ()) -> List[aiosqlite.Row]:
        """Fetch all rows."""
        async with self._db.execute(query, parameters) as cursor:
            return await cursor.fetchall()
    
    async def commit(self):
        """Commit changes."""
        await self._db.commit()
    
    async def rollback(self):
        """Rollback changes."""
        await self._db.rollback()
    
    async def close(self):
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None
    
    @property
    def connection(self) -> aiosqlite.Connection:
        """Get the database connection."""
        return self._db


db = Database()
