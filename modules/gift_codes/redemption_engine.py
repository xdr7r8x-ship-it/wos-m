"""
WOS-M Gift Codes Redemption Engine
© MANSOUR — WOS-M. All rights reserved.

This module provides the core redemption engine for gift codes.
"""
import asyncio
from typing import Dict, Any, Optional, List, Callable
import logging
import re

from config.settings import settings
from integrations.gift_code_client import gift_code_client, GiftCodeStatus as APIStatus
from integrations.captcha_service import captcha_service
from integrations.whiteout_project_provider import (
    whiteout_project_provider,
    RedemptionStatus as WPStatus,
)
from modules.gift_codes.service import gift_code_service
from modules.gift_codes.models import GiftCodeStatus as ModelStatus
from core.database import db

logger = logging.getLogger(__name__)


class RedemptionEngine:
    """
    Core engine for gift code redemption operations.
    
    Features:
    - Single and batch redemption
    - Captcha solving integration
    - Process queue integration
    - Progress tracking
    - Auto retry on failure
    """
    
    def __init__(self):
        self._captcha_cache: Dict[str, str] = {}
        self._active_redeemers: Dict[str, asyncio.Task] = {}
        self._auto_redeem_enabled: Dict[int, bool] = {}  # alliance_id -> enabled
    
    def is_auto_redeem_enabled(self, alliance_id: Optional[int] = None) -> bool:
        """Check if auto redeem is enabled for an alliance."""
        if alliance_id is None:
            return any(self._auto_redeem_enabled.values())
        return self._auto_redeem_enabled.get(alliance_id, False)
    
    def set_auto_redeem(self, alliance_id: int, enabled: bool):
        """Enable or disable auto redeem for an alliance."""
        self._auto_redeem_enabled[alliance_id] = enabled
        logger.info(f"Auto redeem {'enabled' if enabled else 'disabled'} for alliance {alliance_id}")
    
    async def solve_captcha_if_needed(self, code: str) -> Optional[str]:
        """
        Solve captcha if required for the code.
        
        Args:
            code: Gift code to check
            
        Returns:
            Captcha token if solved, None otherwise
        """
        # Check if captcha is required
        requires_captcha = await gift_code_client.check_captcha_required(code)
        
        if not requires_captcha:
            return None
        
        # Check cache first
        if code in self._captcha_cache:
            return self._captcha_cache[code]
        
        # Try to solve captcha
        try:
            # Get captcha image/data from API
            captcha_data = await self._get_captcha_data(code)
            
            if captcha_data:
                # Solve using captcha service
                solution = await captcha_service.solve_image_captcha(captcha_data)
                
                if solution:
                    token = f"captcha_{solution}_{code}"
                    self._captcha_cache[code] = token
                    gift_code_client.set_captcha_token(token)
                    return token
                    
        except Exception as e:
            logger.error(f"Error solving captcha for {code}: {e}")
        
        return None
    
    async def _get_captcha_data(self, code: str) -> Optional[bytes]:
        """Get captcha image data for a code."""
        # This would typically fetch from the game API
        # For now, return None to skip captcha
        return None
    
    async def _redeem_via_whiteout_project(
        self,
        code: str,
        player_id: int,
        player_fid: str,
    ) -> Dict[str, Any]:
        """
        Real WhiteoutProject redemption path.
        This is the ONLY valid path for CenturyGame real redemption.
        """
        result = await whiteout_project_provider.redeem(code, player_fid)
        
        status = result.status
        raw = result.raw_response or {}
        message = result.message or status.value
        
        status_map = {
            WPStatus.SUCCESS: ModelStatus.REDEEMED,
            WPStatus.RECEIVED: ModelStatus.ALREADY_REDEEMED,
            WPStatus.SAME_TYPE_EXCHANGE: ModelStatus.REDEEMED,
            WPStatus.TIME_ERROR: ModelStatus.EXPIRED,
            WPStatus.CDK_NOT_FOUND: ModelStatus.INVALID,
            WPStatus.USAGE_LIMIT: ModelStatus.FAILED,
            WPStatus.NOT_LOGIN: ModelStatus.FAILED,
            WPStatus.UNAUTHORIZED: ModelStatus.FAILED,
            WPStatus.LOGIN_FAILED: ModelStatus.FAILED,
            WPStatus.CAPTCHA_INVALID: ModelStatus.FAILED,
            WPStatus.CAPTCHA_ERROR: ModelStatus.FAILED,
            WPStatus.CAPTCHA_TOO_FREQUENT: ModelStatus.PENDING,
            WPStatus.CAPTCHA_FETCH_ERROR: ModelStatus.FAILED,
            WPStatus.SOLVER_ERROR: ModelStatus.FAILED,
            WPStatus.OCR_DISABLED: ModelStatus.FAILED,
            WPStatus.SIGN_ERROR: ModelStatus.FAILED,
            WPStatus.TIMEOUT_RETRY: ModelStatus.PENDING,
            WPStatus.CONNECTION_ERROR: ModelStatus.PENDING,
            WPStatus.UNKNOWN_API_RESPONSE: ModelStatus.FAILED,
            WPStatus.ERROR: ModelStatus.FAILED,
        }
        
        model_status = status_map.get(status, ModelStatus.FAILED)
        
        # Get gift code from DB
        gift_code = await gift_code_service.get_code_by_code(code)
        if gift_code:
            await gift_code_service.update_code_status(gift_code.id, model_status)
        
        # Add redemption record
        error_msg = None if status in [
            WPStatus.SUCCESS, WPStatus.RECEIVED, WPStatus.SAME_TYPE_EXCHANGE
        ] else message
        
        await gift_code_service.add_redemption(
            gift_code.id if gift_code else 0,
            player_id,
            model_status.value,
            error_message=error_msg,
        )
        
        if status in [WPStatus.SUCCESS, WPStatus.RECEIVED, WPStatus.SAME_TYPE_EXCHANGE]:
            return {
                "success": True,
                "provider": "WhiteoutProject",
                "status": model_status.value,
                "api_status": status.value,
                "message": message,
                "raw_response": raw,
                "rewards": [],
            }
        
        return {
            "success": False,
            "provider": "WhiteoutProject",
            "status": model_status.value,
            "api_status": status.value,
            "error": status.value,
            "message": message,
            "raw_response": raw,
        }
    
    async def redeem_code(
        self,
        code: str,
        player_id: int,
        player_fid: Optional[str] = None,
        skip_validation: bool = False
    ) -> Dict[str, Any]:
        """
        Redeem a code for a player.
        
        Args:
            code: Gift code
            player_id: Database player ID
            player_fid: Player FID (optional)
            skip_validation: Skip code validation if already validated
            
        Returns:
            Redemption result with full details
        """
        code = code.upper().strip()
        
        # Validate code format
        if not self._validate_code_format(code):
            return {
                "success": False,
                "error": "invalid_format",
                "message": "Code format is invalid"
            }
        
        # Get code from database
        gift_code = await gift_code_service.get_code_by_code(code)
        
        if not gift_code:
            # Add code to database if not exists
            code_id = await gift_code_service.add_code(code)
            gift_code = await gift_code_service.get_code(code_id)
        
        if not gift_code:
            return {
                "success": False,
                "error": "code_not_found",
                "message": "Code not found in database"
            }
        
        # Check if already redeemed globally
        if gift_code.status == ModelStatus.REDEEMED:
            return {
                "success": False,
                "error": "already_redeemed",
                "message": "Code has already been redeemed"
            }
        
        # Check if already redeemed by this player
        if await gift_code_service.check_code_exists(code, player_id):
            return {
                "success": False,
                "error": "already_redeemed_by_player",
                "message": "You have already redeemed this code"
            }
        
        # Get FID if not provided
        if not player_fid:
            row = await db.fetchone("SELECT fid FROM players WHERE id = ?", (player_id,))
            if row:
                player_fid = row["fid"]
        
        if not player_fid:
            return {
                "success": False,
                "error": "no_fid",
                "message": "Player FID not found"
            }
        
        # Update status to redeeming
        await gift_code_service.update_code_status(gift_code.id, ModelStatus.REDEEMING)
        
        # Provider routing - WhiteoutProject is the ONLY valid path for real redemption
        provider = getattr(settings.api, "real_redemption_provider", "WhiteoutProject")
        
        if provider.lower() == "whiteoutproject":
            # Use WhiteoutProject provider - this handles captcha internally
            return await self._redeem_via_whiteout_project(
                code=code,
                player_id=player_id,
                player_fid=player_fid,
            )
        
        # Generic/Custom provider fallback - uses gift_code_client
        # Solve captcha if needed
        captcha_token = await self.solve_captcha_if_needed(code)
        
        if captcha_token is None and await gift_code_client.check_captcha_required(code):
            await gift_code_service.update_code_status(gift_code.id, ModelStatus.PENDING)
            return {
                "success": False,
                "error": "captcha_required",
                "message": "Captcha solving is required"
            }
        
        # Attempt redemption via Generic provider
        try:
            result = await gift_code_client.redeem_code(code, player_fid, captcha_token)
            
            status = APIStatus(result.get("status", "failed"))
            
            if status == APIStatus.REDEEMED:
                # Success
                await gift_code_service.update_code_status(gift_code.id, ModelStatus.REDEEMED)
                await gift_code_service.add_redemption(
                    gift_code.id, player_id, ModelStatus.REDEEMED.value
                )
                
                logger.info(f"Successfully redeemed code {code} for player {player_id}")
                
                return {
                    "success": True,
                    "status": ModelStatus.REDEEMED.value,
                    "rewards": result.get("rewards", []),
                    "message": "Code redeemed successfully"
                }
            
            else:
                # Handle specific status
                model_status = self._map_api_status(status)
                
                if status == APIStatus.ALREADY_REDEEMED:
                    model_status = ModelStatus.ALREADY_REDEEMED
                
                await gift_code_service.update_code_status(gift_code.id, model_status)
                await gift_code_service.add_redemption(
                    gift_code.id, player_id, model_status.value,
                    error_message=result.get("error")
                )
                
                return {
                    "success": False,
                    "status": model_status.value,
                    "error": result.get("error", status.value),
                    "message": f"Redemption failed: {result.get('error', status.value)}"
                }
                
        except Exception as e:
            logger.error(f"Error redeeming code {code} for player {player_id}: {e}")
            await gift_code_service.update_code_status(gift_code.id, ModelStatus.FAILED)
            
            return {
                "success": False,
                "error": "redemption_error",
                "message": str(e)
            }
    
    def _validate_code_format(self, code: str) -> bool:
        """Validate gift code format."""
        pattern = re.compile(r'^[A-Z0-9]{6,32}$')
        return bool(pattern.match(code))
    
    def _map_api_status(self, api_status: APIStatus) -> ModelStatus:
        """Map API status to model status."""
        mapping = {
            APIStatus.VALID: ModelStatus.VALID,
            APIStatus.INVALID: ModelStatus.INVALID,
            APIStatus.EXPIRED: ModelStatus.EXPIRED,
            APIStatus.REDEEMING: ModelStatus.REDEEMING,
            APIStatus.REDEEMED: ModelStatus.REDEEMED,
            APIStatus.ALREADY_REDEEMED: ModelStatus.ALREADY_REDEEMED,
            APIStatus.FAILED: ModelStatus.FAILED,
            APIStatus.PENDING: ModelStatus.PENDING,
        }
        return mapping.get(api_status, ModelStatus.FAILED)
    
    async def batch_redeem(
        self,
        code: str,
        alliance_id: Optional[int] = None,
        player_ids: Optional[List[int]] = None,
        progress_callback: Optional[Callable] = None,
        notification_channel: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Batch redeem a code for multiple players.
        
        Args:
            code: Gift code
            alliance_id: Alliance ID (if redeeming for alliance)
            player_ids: List of player IDs (if specific players)
            progress_callback: Callback for progress updates
            notification_channel: Discord channel for progress notifications
            
        Returns:
            Batch result with full statistics
        """
        code = code.upper().strip()
        
        # Validate code format
        if not self._validate_code_format(code):
            return {
                "success": False,
                "error": "invalid_format",
                "message": "Invalid code format"
            }
        
        # Create batch
        batch_id = await gift_code_service.create_batch(code, alliance_id)
        
        # Get players
        if player_ids is None:
            if alliance_id:
                rows = await db.fetchall(
                    "SELECT id, fid, name FROM players WHERE alliance_id = ? AND is_active = 1",
                    (alliance_id,)
                )
            else:
                rows = await db.fetchall(
                    "SELECT id, fid, name FROM players WHERE is_active = 1"
                )
        else:
            rows = await db.fetchall(
                "SELECT id, fid, name FROM players WHERE id IN ({})".format(
                    ",".join("?" * len(player_ids))
                ),
                tuple(player_ids)
            )
        
        player_ids = [row["id"] for row in rows]
        players_info = {row["id"]: {"fid": row["fid"], "name": row["name"]} for row in rows}
        
        total = len(player_ids)
        await gift_code_service.update_batch(batch_id, total=total, status="processing")
        
        success_count = 0
        failure_count = 0
        results = []
        
        for i, player_id in enumerate(player_ids):
            player_info = players_info.get(player_id, {})
            player_fid = player_info.get("fid")
            
            if not player_fid:
                result = {
                    "player_id": player_id,
                    "player_name": player_info.get("name", "Unknown"),
                    "success": False,
                    "error": "no_fid",
                    "status": ModelStatus.FAILED.value
                }
                failure_count += 1
            else:
                # Redeem code
                redeem_result = await self.redeem_code(code, player_id, player_fid)
                
                result = {
                    "player_id": player_id,
                    "player_name": player_info.get("name", "Unknown"),
                    "success": redeem_result.get("success", False),
                    "error": redeem_result.get("error"),
                    "status": redeem_result.get("status"),
                    "rewards": redeem_result.get("rewards", [])
                }
                
                if redeem_result.get("success"):
                    success_count += 1
                else:
                    failure_count += 1
            
            # Add batch result
            await gift_code_service.add_batch_result(
                batch_id=batch_id,
                player_id=player_id,
                player_name=player_info.get("name", "Unknown"),
                status=result.get("status", ModelStatus.FAILED.value),
                error_message=result.get("error")
            )
            
            # Update batch progress
            await gift_code_service.update_batch(
                batch_id,
                success=success_count,
                failure=failure_count
            )
            
            # Progress callback
            if progress_callback:
                await progress_callback(i + 1, total, player_info.get("name"), result)
            
            results.append(result)
            
            # Rate limiting
            await asyncio.sleep(0.3)
        
        # Mark batch as completed
        final_status = "completed" if failure_count == 0 else ("partial" if success_count > 0 else "failed")
        await gift_code_service.update_batch(
            batch_id,
            status=final_status,
            success=success_count,
            failure=failure_count
        )
        
        logger.info(f"Batch {batch_id} completed: {success_count}/{total} successful")
        
        return {
            "batch_id": batch_id,
            "code": code,
            "total": total,
            "success": success_count,
            "failure": failure_count,
            "status": final_status,
            "results": results
        }
    
    async def auto_redeem_for_alliance(
        self,
        code: str,
        alliance_id: int,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Auto redeem a code for all active players in an alliance.
        
        Args:
            code: Gift code
            alliance_id: Alliance ID
            progress_callback: Optional progress callback
            
        Returns:
            Batch result
        """
        # Check if auto redeem is enabled
        if not self.is_auto_redeem_enabled(alliance_id):
            logger.warning(f"Auto redeem not enabled for alliance {alliance_id}")
            return {
                "success": False,
                "error": "auto_redeem_disabled",
                "message": "Auto redeem is not enabled for this alliance"
            }
        
        return await self.batch_redeem(
            code=code,
            alliance_id=alliance_id,
            progress_callback=progress_callback
        )
    
    async def auto_redeem_all_alliances(
        self,
        code: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Auto redeem a code for all alliances with auto redeem enabled.
        
        Args:
            code: Gift code
            progress_callback: Optional progress callback
            
        Returns:
            Combined results for all alliances
        """
        all_results = []
        total_success = 0
        total_failure = 0
        
        for alliance_id, enabled in self._auto_redeem_enabled.items():
            if enabled:
                result = await self.auto_redeem_for_alliance(
                    code, alliance_id, progress_callback
                )
                all_results.append({
                    "alliance_id": alliance_id,
                    **result
                })
                total_success += result.get("success", 0)
                total_failure += result.get("failure", 0)
        
        return {
            "code": code,
            "alliances_count": len(all_results),
            "total_success": total_success,
            "total_failure": total_failure,
            "alliance_results": all_results
        }
    
    async def process_pending_codes(self) -> Dict[str, Any]:
        """Process all pending codes for auto redemption."""
        # Get all codes that need processing
        rows = await db.fetchall(
            """SELECT * FROM gift_codes 
               WHERE status IN ('pending', 'valid') 
               AND alliance_id IS NOT NULL"""
        )
        
        processed = 0
        success = 0
        failure = 0
        
        for row in rows:
            alliance_id = row["alliance_id"]
            code = row["code"]
            
            if self.is_auto_redeem_enabled(alliance_id):
                result = await self.auto_redeem_for_alliance(code, alliance_id)
                processed += 1
                success += result.get("success", 0)
                failure += result.get("failure", 0)
        
        return {
            "processed_codes": processed,
            "total_success": success,
            "total_failure": failure
        }
    
    async def retry_failed_redemptions(self) -> Dict[str, Any]:
        """Retry all failed/unconfirmed redemptions."""
        rows = await db.fetchall(
            """SELECT * FROM gift_codes 
               WHERE status IN ('failed', 'pending', 'redeeming') 
               AND datetime(added_at, '+1 hour') < datetime('now')"""
        )
        
        retried = 0
        succeeded = 0
        
        for row in rows:
            code = row["code"]
            code_id = row["id"]
            
            # Get players who need to retry
            redemption_rows = await db.fetchall(
                """SELECT * FROM gift_redemptions 
                   WHERE code_id = ? AND status != 'redeemed'""",
                (code_id,)
            )
            
            for redemption in redemption_rows:
                result = await self.redeem_code(code, redemption["player_id"])
                
                if result.get("success"):
                    succeeded += 1
                
                retried += 1
            
            await asyncio.sleep(1)  # Rate limiting
        
        return {
            "retried": retried,
            "succeeded": succeeded
        }


redemption_engine = RedemptionEngine()
