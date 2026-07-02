"""
Gift Code Redemption Engine for WOS-M
Based on Whiteout Project's gift_redemption module
© MANSOUR — WOS-M. All rights reserved.
"""
import asyncio
import json
import logging
import re
import sqlite3
import time
import unicodedata
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

import aiohttp
import discord

from integrations.gift_codes.onnx_captcha_solver import GiftCaptchaSolver

logger = logging.getLogger(__name__)


class GiftRedemptionEngine:
    """
    Core gift code redemption engine.
    Handles validation, captcha solving, and code redemption.
    """
    
    # WOS API Endpoints
    WOS_PLAYER_INFO_URL = "https://wos-giftcode-api.centurygame.com/api/player"
    WOS_GIFTCODE_URL = "https://wos-giftcode-api.centurygame.com/api/gift_code"
    WOS_CAPTCHA_URL = "https://wos-giftcode-api.centurygame.com/api/captcha"
    WOS_GIFTCODE_REDEMPTION_URL = "https://wos-giftcode.centurygame.com"
    WOS_ENCRYPT_KEY = "tB87#kPtkxqOS2"
    
    def __init__(self, bot, db: sqlite3.Connection):
        self.bot = bot
        self.db = db
        self.cursor = db.cursor()
        
        self.logger = logger
        self.giftlog = logging.getLogger('redemption')
        
        # Initialize captcha solver
        self.captcha_solver: Optional[GiftCaptchaSolver] = None
        self._init_captcha_solver()
        
        # Locks and cooldowns
        self._validation_lock = asyncio.Lock()
        self.last_validation_attempt_time = 0
        self.validation_cooldown = 5
        
        # Processing stats
        self.processing_stats = {
            "ocr_solver_calls": 0,
            "ocr_valid_format": 0,
            "captcha_submissions": 0,
            "server_validation_success": 0,
            "server_validation_failure": 0,
            "total_fids_processed": 0,
            "total_processing_time": 0.0
        }
        
        # Batch tracking
        self.redemption_batches: Dict[str, Any] = {}
        
        # Auto-redeem tracking
        self._revalidation_tasks: Dict[str, asyncio.Task] = {}
        self._auto_redeem_started: set = set()
    
    def _init_captcha_solver(self):
        """Initialize the ONNX captcha solver."""
        try:
            self.captcha_solver = GiftCaptchaSolver(save_images=0)
            if not self.captcha_solver.is_initialized:
                self.logger.warning("Captcha solver not initialized. ONNX model may be missing.")
                self.captcha_solver = None
            else:
                self.logger.info("Captcha solver initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize captcha solver: {e}")
            self.captcha_solver = None
    
    def clean_gift_code(self, giftcode: str) -> str:
        """Clean and normalize a gift code."""
        cleaned = ''.join(char for char in giftcode 
                        if unicodedata.category(char)[0] != 'C')
        return cleaned.strip().upper()
    
    async def fetch_captcha(self, player_id: str, session: aiohttp.ClientSession = None) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Fetch captcha image from WOS API.
        
        Returns:
            Tuple of (image_bytes, captcha_id)
        """
        try:
            close_session = session is None
            if session is None:
                connector = aiohttp.TCPConnector(ssl=False)
                session = aiohttp.ClientSession(connector=connector)
            
            data = {
                "playerId": player_id,
                "key": self.WOS_ENCRYPT_KEY
            }
            
            async with session.post(self.WOS_CAPTCHA_URL, json=data, timeout=30) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("code") == 0:
                        captcha_id = result.get("data", {}).get("id")
                        captcha_image = result.get("data", {}).get("image")
                        
                        if captcha_image:
                            # Decode base64 image
                            import base64
                            image_data = base64.b64decode(captcha_image)
                            return image_data, captcha_id
                
                self.logger.warning(f"Failed to fetch captcha: {resp.status}")
                return None, None
                
        except Exception as e:
            self.logger.error(f"Error fetching captcha: {e}")
            return None, None
        finally:
            if close_session and session:
                await session.close()
    
    async def solve_captcha(self, image_bytes: bytes, player_id: str = None) -> Tuple[Optional[str], bool, str, float]:
        """
        Solve captcha using ONNX model or fallback.
        
        Returns:
            Tuple of (solved_text, success, method, confidence)
        """
        if self.captcha_solver:
            return await self.captcha_solver.solve_captcha(image_bytes, fid=player_id)
        
        return None, False, "DISABLED", 0.0
    
    async def validate_gift_code(self, giftcode: str, player_id: str = None) -> Tuple[bool, str]:
        """
        Validate a gift code against WOS API.
        
        Returns:
            Tuple of (is_valid, message)
        """
        if not player_id:
            player_id = "45379845"  # Default test ID
        
        async with self._validation_lock:
            # Check cooldown
            now = time.time()
            if now - self.last_validation_attempt_time < self.validation_cooldown:
                await asyncio.sleep(self.validation_cooldown - (now - self.last_validation_attempt_time))
            
            self.last_validation_attempt_time = time.time()
        
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                # Get player info
                player_data = await self._get_player_info(player_id, session)
                if not player_data:
                    return False, "فشل في جلب معلومات اللاعب"
                
                # Fetch and solve captcha
                captcha_image, captcha_id = await self.fetch_captcha(player_id, session)
                if not captcha_image:
                    return False, "فشل في جلب الكابتشا"
                
                solved_captcha, success, method, confidence = await self.solve_captcha(captcha_image, player_id)
                
                if not success:
                    return False, f"فشل في حل الكابتشا (الطريقة: {method})"
                
                self.processing_stats["captcha_submissions"] += 1
                
                # Submit gift code with captcha
                is_valid, msg = await self._submit_gift_code(
                    giftcode, player_id, solved_captcha, captcha_id, session
                )
                
                return is_valid, msg
                
        except Exception as e:
            self.logger.error(f"Error validating gift code: {e}")
            return False, f"خطأ: {str(e)}"
    
    async def _get_player_info(self, player_id: str, session: aiohttp.ClientSession) -> Optional[dict]:
        """Get player information from WOS API."""
        try:
            data = {
                "playerId": player_id,
                "key": self.WOS_ENCRYPT_KEY
            }
            
            async with session.post(self.WOS_PLAYER_INFO_URL, json=data, timeout=30) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("code") == 0:
                        return result.get("data", {})
                return None
        except Exception as e:
            self.logger.error(f"Error getting player info: {e}")
            return None
    
    async def _submit_gift_code(
        self, 
        giftcode: str, 
        player_id: str, 
        captcha: str, 
        captcha_id: str,
        session: aiohttp.ClientSession
    ) -> Tuple[bool, str]:
        """Submit gift code with solved captcha to WOS API."""
        try:
            data = {
                "playerId": player_id,
                "giftcode": giftcode,
                "captcha": captcha,
                "captchaId": captcha_id,
                "key": self.WOS_ENCRYPT_KEY
            }
            
            async with session.post(self.WOS_GIFTCODE_URL, json=data, timeout=30) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    code = result.get("code")
                    
                    if code == 0:
                        self.processing_stats["server_validation_success"] += 1
                        return True, "الكود صالح"
                    elif code == 10001:
                        self.processing_stats["server_validation_failure"] += 1
                        return False, "الكود مستخدم أو غير صالح"
                    elif code == 10003:
                        self.processing_stats["server_validation_failure"] += 1
                        return False, "الكابتشا خاطئ"
                    else:
                        return False, f"خطأ غير معروف: {code}"
                
                self.processing_stats["server_validation_failure"] += 1
                return False, f"خطأ في الاتصال: {resp.status}"
                
        except Exception as e:
            self.logger.error(f"Error submitting gift code: {e}")
            return False, f"خطأ: {str(e)}"
    
    async def redeem_gift_code(
        self, 
        giftcode: str, 
        player_id: str,
        alliance_id: int = None,
        auto: bool = False
    ) -> Tuple[bool, str]:
        """
        Redeem a gift code for a player.
        
        Args:
            giftcode: The gift code to redeem
            player_id: Player ID to redeem for
            alliance_id: Optional alliance ID
            auto: Whether this is an auto-redemption
        
        Returns:
            Tuple of (success, message)
        """
        try:
            if not auto:
                is_valid, msg = await self.validate_gift_code(giftcode, player_id)
                if not is_valid:
                    return False, msg
            
            # Attempt redemption
            success, msg = await self._attempt_redemption(giftcode, player_id)
            
            if success:
                self.logger.info(f"Successfully redeemed code {giftcode} for player {player_id}")
                self.giftlog.info(f"REDEMPTION: {giftcode} -> {player_id} (alliance: {alliance_id})")
                
                # Record in database
                await self._record_redemption(giftcode, player_id, alliance_id)
            else:
                self.logger.warning(f"Failed to redeem code {giftcode}: {msg}")
            
            return success, msg
            
        except Exception as e:
            self.logger.error(f"Error redeeming gift code: {e}")
            return False, f"خطأ: {str(e)}"
    
    async def _attempt_redemption(
        self, 
        giftcode: str, 
        player_id: str
    ) -> Tuple[bool, str]:
        """Internal method to attempt actual redemption."""
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                # First get valid captcha
                captcha_image, captcha_id = await self.fetch_captcha(player_id, session)
                if not captcha_image:
                    return False, "فشل في جلب الكابتشا"
                
                solved_captcha, success, _, _ = await self.solve_captcha(captcha_image, player_id)
                if not success:
                    return False, "فشل في حل الكابتشا"
                
                # Submit for redemption
                return await self._submit_gift_code(
                    giftcode, player_id, solved_captcha, captcha_id, session
                )
                
        except Exception as e:
            self.logger.error(f"Error in redemption attempt: {e}")
            return False, f"خطأ: {str(e)}"
    
    async def _record_redemption(
        self, 
        giftcode: str, 
        player_id: str, 
        alliance_id: int = None
    ):
        """Record a successful redemption in the database."""
        try:
            now = datetime.now().isoformat()
            self.cursor.execute("""
                INSERT OR REPLACE INTO gift_redemptions 
                (giftcode, player_id, alliance_id, redeemed_at, status)
                VALUES (?, ?, ?, ?, 'success')
            """, (giftcode, player_id, alliance_id, now))
            
            # Update gift_codes status
            self.cursor.execute("""
                UPDATE gift_codes 
                SET status = 'redeemed', redeemed_at = ?
                WHERE code = ?
            """, (now, giftcode))
            
            self.db.commit()
            
        except Exception as e:
            self.logger.error(f"Error recording redemption: {e}")
    
    async def batch_redeem(
        self,
        giftcode: str,
        player_ids: List[str],
        alliance_id: int = None
    ) -> Dict[str, Any]:
        """
        Redeem a gift code for multiple players.
        
        Returns:
            Summary dict with success/failure counts
        """
        results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "details": []
        }
        
        for player_id in player_ids:
            # Check if already redeemed
            self.cursor.execute("""
                SELECT COUNT(*) FROM gift_redemptions 
                WHERE giftcode = ? AND player_id = ?
            """, (giftcode, player_id))
            
            if self.cursor.fetchone()[0] > 0:
                results["skipped"] += 1
                results["details"].append({
                    "player_id": player_id,
                    "status": "skipped",
                    "reason": "already_redeemed"
                })
                continue
            
            success, msg = await self.redeem_gift_code(giftcode, player_id, alliance_id)
            
            if success:
                results["success"] += 1
                results["details"].append({
                    "player_id": player_id,
                    "status": "success"
                })
            else:
                results["failed"] += 1
                results["details"].append({
                    "player_id": player_id,
                    "status": "failed",
                    "reason": msg
                })
            
            # Rate limiting
            await asyncio.sleep(1)
        
        return results
    
    async def get_code_status(self, giftcode: str) -> Dict[str, Any]:
        """Get the current status of a gift code."""
        self.cursor.execute("""
            SELECT code, status, validation_status, created_at, redeemed_at
            FROM gift_codes WHERE code = ?
        """, (giftcode,))
        
        row = self.cursor.fetchone()
        if not row:
            return {"found": False}
        
        return {
            "found": True,
            "code": row[0],
            "status": row[1],
            "validation_status": row[2],
            "created_at": row[3],
            "redeemed_at": row[4]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            **self.processing_stats,
            "captcha_solver_available": self.captcha_solver is not None,
            "captcha_stats": self.captcha_solver.get_stats() if self.captcha_solver else {}
        }
