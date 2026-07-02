"""
Gift Code Service for WOS-M
Main service that integrates ONNX captcha solver, redemption engine, and distribution API.
© MANSOUR — WOS-M. All rights reserved.
"""
import asyncio
import logging
import re
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

import discord

from integrations.gift_codes.onnx_captcha_solver import GiftCaptchaSolver
from integrations.gift_codes.redemption_engine import GiftRedemptionEngine
from integrations.gift_codes.distribution_api import GiftDistributionAPI

logger = logging.getLogger(__name__)


class GiftCodeService:
    """
    Main gift code service that integrates all components:
    - ONNX Captcha Solver
    - Redemption Engine
    - Distribution API
    """
    
    def __init__(self, bot, db: sqlite3.Connection):
        self.bot = bot
        self.db = db
        self.cursor = db.cursor()
        
        self.logger = logger
        
        # Initialize components
        self.captcha_solver = GiftCaptchaSolver(save_images=0)
        self.redemption_engine = GiftRedemptionEngine(bot, db)
        self.distribution_api = GiftDistributionAPI(bot, db)
        
        # Database tables
        self._init_database()
        
        # Active redemption batches
        self.active_batches: Dict[str, Any] = {}
        
        # Settings
        self.settings = self._load_settings()
    
    def _init_database(self):
        """Initialize required database tables."""
        # Gift Codes table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS gift_codes (
                code TEXT PRIMARY KEY,
                code_type TEXT,
                value TEXT,
                status TEXT DEFAULT 'active',
                validation_status TEXT DEFAULT 'pending',
                created_at TEXT,
                updated_at TEXT,
                redeemed_at TEXT
            )
        """)
        
        # Gift Redemptions table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS gift_redemptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                giftcode TEXT NOT NULL,
                player_id TEXT NOT NULL,
                alliance_id INTEGER,
                redeemed_at TEXT,
                status TEXT DEFAULT 'success',
                message TEXT
            )
        """)
        
        # Gift Channels table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS gift_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alliance_id INTEGER UNIQUE,
                channel_id INTEGER,
                notify_enabled INTEGER DEFAULT 1,
                scan_enabled INTEGER DEFAULT 1,
                created_at TEXT
            )
        """)
        
        # Gift Settings table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS gift_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        self.db.commit()
        self.logger.info("Gift code database tables initialized")
    
    def _load_settings(self) -> dict:
        """Load gift code settings from database."""
        settings = {
            'auto_redeem_enabled': False,
            'test_player_id': '45379845',
            'ocr_enabled': True,
            'notify_new_codes': True
        }
        
        self.cursor.execute("SELECT key, value FROM gift_settings")
        for row in self.cursor.fetchall():
            key, value = row
            if key in settings:
                if isinstance(settings[key], bool):
                    settings[key] = value == '1'
                else:
                    settings[key] = value
        
        return settings
    
    def save_setting(self, key: str, value: Any):
        """Save a setting to database."""
        str_value = '1' if isinstance(value, bool) else str(value)
        self.cursor.execute(
            "INSERT OR REPLACE INTO gift_settings (key, value) VALUES (?, ?)",
            (key, str_value)
        )
        self.db.commit()
        self.settings[key] = value
    
    async def start(self):
        """Start the gift code service."""
        await self.distribution_api.start()
        self.logger.info("Gift code service started")
    
    async def stop(self):
        """Stop the gift code service."""
        await self.distribution_api.stop()
        self.logger.info("Gift code service stopped")
    
    async def handle_message(self, message: discord.Message) -> bool:
        """
        Handle a Discord message to check for gift codes.
        Returns True if a code was found and processed.
        """
        if message.author.bot or not message.guild:
            return False
        
        # Check if this channel is configured for gift codes
        self.cursor.execute(
            "SELECT alliance_id FROM gift_channels WHERE channel_id = ? AND scan_enabled = 1",
            (message.channel.id,)
        )
        if not self.cursor.fetchone():
            return False
        
        content = message.content.strip()
        if not content:
            return False
        
        # Extract gift code
        code = self._extract_gift_code(content)
        if not code:
            return False
        
        # Process the code
        await self._process_new_code(code, source="channel", message=message)
        return True
    
    def _extract_gift_code(self, text: str) -> Optional[str]:
        """Extract gift code from text."""
        # Try single word first
        if re.match(r'^[A-Z0-9]{6,20}$', text.upper()):
            return text.upper()
        
        # Try Code: format
        code_match = re.search(r'[Cc]ode:\s*([A-Z0-9]+)', text)
        if code_match:
            return code_match.group(1).upper()
        
        # Try various formats
        patterns = [
            r'([A-Z0-9]{6,20})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).upper()
        
        return None
    
    async def _process_new_code(
        self, 
        code: str, 
        source: str = "unknown",
        message: discord.Message = None
    ):
        """Process a new gift code."""
        code = code.upper().strip()
        
        # Check if already exists
        self.cursor.execute(
            "SELECT status, validation_status FROM gift_codes WHERE code = ?",
            (code,)
        )
        existing = self.cursor.fetchone()
        
        if existing and existing[1] == 'validated':
            self.logger.info(f"Code {code} already validated, skipping")
            return
        
        # Add to database
        now = datetime.now().isoformat()
        self.cursor.execute("""
            INSERT OR IGNORE INTO gift_codes 
            (code, status, validation_status, created_at, updated_at)
            VALUES (?, 'active', 'pending', ?, ?)
        """, (code, now, now))
        self.db.commit()
        
        # Validate the code
        await self.validate_code(code)
        
        # Share to distribution API
        await self.distribution_api.add_code_to_api(code)
        
        # Notify configured channels
        if self.settings.get('notify_new_codes'):
            await self._notify_new_code(code)
    
    async def validate_code(self, code: str) -> Tuple[bool, str]:
        """Validate a gift code."""
        player_id = self.settings.get('test_player_id', '45379845')
        
        is_valid, msg = await self.redemption_engine.validate_gift_code(code, player_id)
        
        # Update database
        validation_status = 'validated' if is_valid else 'invalid'
        self.cursor.execute("""
            UPDATE gift_codes 
            SET validation_status = ?, updated_at = ?
            WHERE code = ?
        """, (validation_status, datetime.now().isoformat(), code))
        self.db.commit()
        
        return is_valid, msg
    
    async def redeem_code(
        self, 
        code: str, 
        player_id: str,
        alliance_id: int = None,
        auto: bool = False
    ) -> Tuple[bool, str]:
        """Redeem a gift code for a player."""
        success, msg = await self.redemption_engine.redeem_gift_code(
            code, player_id, alliance_id, auto
        )
        
        if success:
            # Update database
            self.cursor.execute("""
                UPDATE gift_codes 
                SET status = 'redeemed', redeemed_at = ?, updated_at = ?
                WHERE code = ?
            """, (datetime.now().isoformat(), datetime.now().isoformat(), code))
            
            # Record redemption
            self.cursor.execute("""
                INSERT INTO gift_redemptions 
                (giftcode, player_id, alliance_id, redeemed_at, status, message)
                VALUES (?, ?, ?, ?, 'success', ?)
            """, (code, player_id, alliance_id, datetime.now().isoformat(), msg))
            
            self.db.commit()
        
        return success, msg
    
    async def batch_redeem(
        self,
        code: str,
        player_ids: List[str],
        alliance_id: int = None
    ) -> Dict[str, Any]:
        """Redeem a code for multiple players."""
        results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "total": len(player_ids),
            "details": []
        }
        
        for player_id in player_ids:
            # Check if already redeemed
            self.cursor.execute("""
                SELECT COUNT(*) FROM gift_redemptions 
                WHERE giftcode = ? AND player_id = ?
            """, (code, player_id))
            
            if self.cursor.fetchone()[0] > 0:
                results["skipped"] += 1
                results["details"].append({
                    "player_id": player_id,
                    "status": "skipped",
                    "reason": "already_redeemed"
                })
                continue
            
            success, msg = await self.redeem_code(code, player_id, alliance_id)
            
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append({
                "player_id": player_id,
                "status": "success" if success else "failed",
                "message": msg
            })
            
            # Rate limiting
            await asyncio.sleep(0.5)
        
        return results
    
    async def _notify_new_code(self, code: str):
        """Notify about a new gift code."""
        try:
            self.cursor.execute("SELECT channel_id FROM gift_channels WHERE notify_enabled = 1")
            channels = self.cursor.fetchall()
            
            for (channel_id,) in channels:
                channel = self.bot.get_channel(channel_id)
                if channel and isinstance(channel, discord.TextChannel):
                    try:
                        embed = discord.Embed(
                            title="🎁 كود هدية جديد!",
                            description=f"تم اكتشاف كود جديد: `{code}`",
                            color=0x00ff00
                        )
                        embed.set_footer(text="WOS-M Gift Code System")
                        await channel.send(embed=embed)
                    except Exception as e:
                        self.logger.warning(f"Failed to notify channel {channel_id}: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
    
    def get_codes(self, status: str = None, limit: int = 50) -> List[Dict]:
        """Get gift codes from database."""
        query = "SELECT code, code_type, value, status, validation_status, created_at FROM gift_codes"
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status)
        
        query += f" ORDER BY created_at DESC LIMIT {limit}"
        
        self.cursor.execute(query, params)
        codes = []
        for row in self.cursor.fetchall():
            codes.append({
                "code": row[0],
                "type": row[1],
                "value": row[2],
                "status": row[3],
                "validation_status": row[4],
                "created_at": row[5]
            })
        
        return codes
    
    def get_redemptions(self, code: str = None, limit: int = 50) -> List[Dict]:
        """Get redemption history."""
        query = """
            SELECT giftcode, player_id, alliance_id, redeemed_at, status 
            FROM gift_redemptions
        """
        params = []
        
        if code:
            query += " WHERE giftcode = ?"
            params.append(code)
        
        query += f" ORDER BY redeemed_at DESC LIMIT {limit}"
        
        self.cursor.execute(query, params)
        redemptions = []
        for row in self.cursor.fetchall():
            redemptions.append({
                "code": row[0],
                "player_id": row[1],
                "alliance_id": row[2],
                "redeemed_at": row[3],
                "status": row[4]
            })
        
        return redemptions
    
    def get_stats(self) -> Dict[str, Any]:
        """Get gift code statistics."""
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN status = 'redeemed' THEN 1 ELSE 0 END) as redeemed,
                SUM(CASE WHEN validation_status = 'validated' THEN 1 ELSE 0 END) as validated,
                SUM(CASE WHEN validation_status = 'invalid' THEN 1 ELSE 0 END) as invalid
            FROM gift_codes
        """)
        row = self.cursor.fetchone()
        
        return {
            "total_codes": row[0] or 0,
            "active_codes": row[1] or 0,
            "redeemed_codes": row[2] or 0,
            "validated_codes": row[3] or 0,
            "invalid_codes": row[4] or 0,
            "captcha_solver_ready": self.captcha_solver.is_initialized,
            "auto_redeem_enabled": self.settings.get('auto_redeem_enabled', False)
        }
