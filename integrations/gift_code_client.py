"""
WOS-M Gift Code Client
© MANSOUR — WOS-M. All rights reserved.
"""
import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from config.settings import settings

logger = logging.getLogger(__name__)


class GiftCodeStatus:
    """Gift code status constants."""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    REDEEMING = "redeeming"
    REDEEMED = "redeemed"
    ALREADY_REDEEMED = "already_redeemed"
    FAILED = "failed"
    DEMO_MODE = "demo_mode"


class GiftCodeClient:
    """
    Client for interacting with gift code redemption API.
    
    This client handles all gift code operations including:
    - Code validation
    - Single and batch redemption
    - Captcha solving integration
    - Error handling and retry logic
    """
    
    def __init__(self):
        self.base_url = settings.api.gift_code_api_base_url
        self.timeout = settings.api.request_timeout
        self._captcha_token: Optional[str] = None
        self._captcha_expires: Optional[datetime] = None
    
    @property
    def is_demo_mode(self) -> bool:
        """Check if running in demo mode."""
        return settings.demo_mode
    
    @property
    def is_configured(self) -> bool:
        """Check if the API is properly configured."""
        return bool(self.base_url)
    
    def requires_api(self) -> bool:
        """Check if real API is required and not available."""
        if self.is_demo_mode:
            return False
        return not self.is_configured
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get request headers with captcha token if available."""
        headers = {"Content-Type": "application/json"}
        
        # Add captcha token if available and valid
        if self._captcha_token and self._captcha_expires:
            if datetime.now() < self._captcha_expires:
                headers["X-Captcha-Token"] = self._captcha_token
        
        return headers
    
    def set_captcha_token(self, token: str, expires_in_seconds: int = 300):
        """Set the captcha token with expiration."""
        self._captcha_token = token
        self._captcha_expires = datetime.now().replace(microsecond=0)
        self._captcha_expires = self._captcha_expires.replace(
            second=self._captcha_expires.second + expires_in_seconds
        )
        logger.info(f"Captcha token set, expires in {expires_in_seconds}s")
    
    async def validate_code(self, code: str) -> Dict[str, Any]:
        """
        Validate a gift code.
        
        Args:
            code: Gift code to validate
            
        Returns:
            Validation result with status
        """
        # Check if API is required
        if self.requires_api():
            return {
                "status": GiftCodeStatus.FAILED,
                "error": "GIFT_CODE_API_BASE_URL not configured and WOSM_DEMO_MODE is false",
                "production_error": True
            }
        
        if not self.is_configured():
            # Demo mode: simulate validation
            logger.warning("DEMO MODE - Using simulation for code validation")
            return self._simulate_validate(code)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/validate/{code}",
                    headers=await self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "status": data.get("status", GiftCodeStatus.VALID),
                            "rewards": data.get("rewards", []),
                            "expires_at": data.get("expires_at")
                        }
                    elif response.status == 404:
                        return {"status": GiftCodeStatus.INVALID}
                    elif response.status == 410:
                        return {"status": GiftCodeStatus.EXPIRED}
                    elif response.status == 409:
                        return {"status": GiftCodeStatus.ALREADY_REDEEMED}
                    elif response.status == 429:
                        return {"status": GiftCodeStatus.PENDING, "error": "Rate limited"}
                    else:
                        return {"status": GiftCodeStatus.INVALID, "error": f"HTTP {response.status}"}
                        
        except asyncio.TimeoutError:
            logger.error(f"Timeout validating code {code}")
            return {"status": GiftCodeStatus.PENDING, "error": "Timeout"}
        except Exception as e:
            logger.error(f"Error validating code {code}: {e}")
            return {"status": GiftCodeStatus.INVALID, "error": str(e)}
    
    def _simulate_validate(self, code: str) -> Dict[str, Any]:
        """
        Simulate code validation for testing/demo purposes.
        IMPORTANT: Results are marked as DEMO MODE.
        """
        import re
        pattern = re.compile(r'^[A-Z0-9]{6,32}$')
        
        if not pattern.match(code):
            return {
                "status": GiftCodeStatus.INVALID,
                "error": "Invalid code format",
                "demo_mode": True
            }
        
        # Simulate some codes as valid, others as invalid
        if code.upper().startswith(('TEST', 'DEMO', 'GIFT', 'WOS', 'FREE')):
            return {
                "status": GiftCodeStatus.VALID,
                "rewards": ["coins", "gems", "resources"],
                "expires_at": None,
                "demo_mode": True,
                "demo_warning": "DEMO MODE - NOT REAL REDEMPTION"
            }
        elif code.upper().startswith('EXP'):
            return {"status": GiftCodeStatus.EXPIRED, "demo_mode": True}
        elif code.upper().startswith('USED'):
            return {"status": GiftCodeStatus.ALREADY_REDEEMED, "demo_mode": True}
        else:
            return {
                "status": GiftCodeStatus.VALID,
                "demo_mode": True,
                "demo_warning": "DEMO MODE - NOT REAL REDEMPTION"
            }
    
    def _simulate_redeem(self, code: str, fid: str) -> Dict[str, Any]:
        """
        Simulate code redemption for testing/demo.
        IMPORTANT: Results are marked as DEMO MODE.
        """
        if not fid or len(fid) < 3:
            return {"status": GiftCodeStatus.INVALID, "error": "Invalid FID"}
        
        return {
            "status": GiftCodeStatus.REDEEMED,
            "rewards": ["1000 coins", "50 gems"],
            "demo_mode": True,
            "demo_warning": "DEMO MODE - NOT REAL REDEMPTION"
        }
    
    async def redeem_code(
        self,
        code: str,
        fid: str,
        captcha_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Redeem a gift code for a player.
        
        Args:
            code: Gift code
            fid: Player FID
            captcha_token: Optional captcha token
            
        Returns:
            Redemption result
        """
        # Check if API is required
        if self.requires_api():
            return {
                "status": GiftCodeStatus.FAILED,
                "error": "GIFT_CODE_API_BASE_URL not configured and WOSM_DEMO_MODE is false",
                "production_error": True
            }
        
        # Use provided captcha or stored one
        token = captcha_token or self._captcha_token
        if token:
            self.set_captcha_token(token)
        
        if not self.is_configured():
            logger.warning("DEMO MODE - Using simulation for code redemption")
            return self._simulate_redeem(code, fid)
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "code": code.upper(),
                    "fid": str(fid)
                }
                
                if token:
                    payload["captcha_token"] = token
                
                async with session.post(
                    f"{self.base_url}/redeem",
                    json=payload,
                    headers=await self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "status": GiftCodeStatus.REDEEMED,
                            "rewards": data.get("rewards", [])
                        }
                    elif response.status == 400:
                        return {"status": GiftCodeStatus.INVALID, "error": "Invalid code or FID"}
                    elif response.status == 409:
                        return {"status": GiftCodeStatus.ALREADY_REDEEMED}
                    elif response.status == 410:
                        return {"status": GiftCodeStatus.EXPIRED}
                    elif response.status == 403:
                        # Captcha required
                        captcha_url = await response.json()
                        return {
                            "status": GiftCodeStatus.PENDING,
                            "error": "Captcha required",
                            "captcha_url": captcha_url.get("captcha_url")
                        }
                    elif response.status == 429:
                        return {"status": GiftCodeStatus.PENDING, "error": "Rate limited"}
                    else:
                        return {"status": GiftCodeStatus.FAILED, "error": f"HTTP {response.status}"}
                        
        except asyncio.TimeoutError:
            logger.error(f"Timeout redeeming code {code} for {fid}")
            return {"status": GiftCodeStatus.FAILED, "error": "Timeout"}
        except Exception as e:
            logger.error(f"Error redeeming code {code} for {fid}: {e}")
            return {"status": GiftCodeStatus.FAILED, "error": str(e)}
    
    async def check_captcha_required(self, code: str) -> bool:
        """
        Check if a code requires captcha solving.
        
        Args:
            code: Gift code to check
            
        Returns:
            True if captcha is required
        """
        if not settings.has_captcha_service:
            # Check if API requires captcha
            if self.is_configured():
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            f"{self.base_url}/captcha-required/{code}",
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                return data.get("required", False)
                except:
                    pass
            
            # Demo mode: only codes starting with CAPTCHA require captcha
            if code.upper().startswith('CAPTCHA'):
                return True
        return False
    
    async def batch_validate(self, codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Validate multiple codes at once.
        
        Args:
            codes: List of codes to validate
            
        Returns:
            Dictionary mapping code to validation result
        """
        if self.requires_api():
            return {
                code: {
                    "status": GiftCodeStatus.FAILED,
                    "error": "GIFT_CODE_API_BASE_URL not configured",
                    "production_error": True
                }
                for code in codes
            }
        
        results = {}
        
        for i, code in enumerate(codes):
            results[code] = await self.validate_code(code)
            if i < len(codes) - 1:
                await asyncio.sleep(0.1)  # Rate limiting
        
        return results
    
    async def batch_redeem(
        self,
        code: str,
        fids: List[str],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Redeem a code for multiple players.
        
        Args:
            code: Gift code
            fids: List of player FIDs
            progress_callback: Optional callback for progress updates
            
        Returns:
            Batch redemption results
        """
        if self.requires_api():
            return {
                "code": code,
                "error": "GIFT_CODE_API_BASE_URL not configured",
                "production_error": True
            }
        
        results = {
            "code": code,
            "total": len(fids),
            "success": 0,
            "failed": 0,
            "requires_captcha": False,
            "details": [],
            "demo_mode": self.is_demo_mode
        }
        
        for i, fid in enumerate(fids):
            # Check captcha before starting
            if await self.check_captcha_required(code) and not self._captcha_token:
                results["requires_captcha"] = True
                results["details"].append({
                    "fid": fid,
                    "status": GiftCodeStatus.PENDING,
                    "error": "Captcha required"
                })
                continue
            
            result = await self.redeem_code(code, fid)
            
            detail = {
                "fid": fid,
                "status": result.get("status"),
                "error": result.get("error")
            }
            
            if result.get("status") == GiftCodeStatus.REDEEMED:
                results["success"] += 1
            else:
                results["failed"] += 1
            
            results["details"].append(detail)
            
            # Progress callback
            if progress_callback:
                await progress_callback(i + 1, len(fids), fid, result)
            
            await asyncio.sleep(0.3)  # Rate limiting between redemptions
        
        results["completed"] = results["success"] + results["failed"]
        return results
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if API is healthy.
        
        Returns:
            Health status with details
        """
        if self.is_demo_mode:
            return {
                "healthy": True,
                "mode": "demo",
                "message": "Running in DEMO MODE - Using simulation"
            }
        
        if not self.is_configured():
            return {
                "healthy": False,
                "mode": "production",
                "error": "GIFT_CODE_API_BASE_URL not configured",
                "message": "PRODUCTION ERROR: Gift Code API not available"
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        return {
                            "healthy": True,
                            "mode": "production",
                            "message": "Gift Code API connected"
                        }
                    else:
                        return {
                            "healthy": False,
                            "mode": "production",
                            "error": f"HTTP {response.status}",
                            "message": "Gift Code API unhealthy"
                        }
        except Exception as e:
            return {
                "healthy": False,
                "mode": "production",
                "error": str(e),
                "message": "Gift Code API unreachable"
            }


gift_code_client = GiftCodeClient()
