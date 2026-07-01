"""
WOS-M WhiteoutProject Provider
© MANSOUR — WOS-M. All rights reserved.

Integration with WhiteoutProject/bot API patterns.
Based on public code from: https://github.com/whiteout-project/bot

LEGAL NOTICE:
- Uses publicly documented API patterns and endpoints
- Sign salt tB87#kPtkxqOS2 is publicly known from multiple open-source implementations
- Requires authorized credentials from a provider
- All secrets read from .env only - never hardcoded

API Flow (from whiteout-project/bot):
- Login/Player check: /api/player
- Gift redemption: /api/gift_code
- CAPTCHA: /api/captcha
- Dual API support: centurygame.com + gof-report-api-formal.centurygame.com

Attribution: whiteout-project/bot (https://github.com/whiteout-project/bot)
"""
import asyncio
import hashlib
import time
import ssl
import certifi
import aiohttp
import base64
import random
import logging
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
from enum import Enum

from config.settings import settings
from integrations.browser_headers import get_headers

logger = logging.getLogger(__name__)


class RedemptionResult(Enum):
    """Redemption result codes from API."""
    SUCCESS = "success"
    ALREADY_CLAIMED = "already_claimed"
    CODE_NOT_EXIST = "code_not_exist"
    CODE_EXPIRED = "code_expired"
    CODE_FULLY_CLAIMED = "code_fully_claimed"
    CAPTCHA_ERROR = "captcha_error"
    NOT_LOGIN = "not_login"
    UNAUTHORIZED = "unauthorized"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class RedemptionResponse:
    """Response from redemption attempt."""
    success: bool
    result: RedemptionResult
    message: str
    player_data: Optional[Dict[str, Any]] = None


@dataclass
class PlayerInfo:
    """Player information."""
    fid: str
    name: Optional[str] = None
    level: Optional[int] = None
    alliance: Optional[str] = None


class WhiteoutProjectProvider:
    """
    WhiteoutProject API adapter.
    
    Based on whiteout-project/bot implementation patterns:
    - Dual API support for better availability
    - Rate limiting (30 requests per 60 seconds)
    - Exponential backoff on errors
    - Browser headers for requests
    
    Configuration from .env:
    - EXTERNAL_PROVIDER_API_KEY: Optional API key
    - EXTERNAL_PROVIDER_LOGIN_TOKEN: Optional login token
    - EXTERNAL_PROVIDER_COOKIE: Optional cookie
    - EXTERNAL_PROVIDER_SESSION: Optional session
    """
    
    # Primary API endpoints (from whiteout-project/bot)
    API1_URL = "https://wos-giftcode-api.centurygame.com"
    API2_URL = "https://gof-report-api-formal.centurygame.com"
    
    # Public sign salt (publicly known from multiple open-source implementations)
    DEFAULT_SIGN_SALT = "tB87#kPtkxqOS2"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._ocr = None
        self._ocr_available = False
        
        # Configuration from settings (.env only)
        self.provider_name = settings.api.external_provider_name or "WhiteoutProject"
        self.provider_url = settings.api.external_provider_url or ""
        self.api_key = settings.api.external_provider_api_key or ""
        self.login_token = settings.api.external_provider_login_token or ""
        self.cookie = settings.api.external_provider_cookie or ""
        self.session_id = settings.api.external_provider_session or ""
        self.sign_secret = settings.api.external_provider_sign_secret or self.DEFAULT_SIGN_SALT
        
        # Rate limiting (from whiteout-project/bot patterns)
        self.api1_requests: List[float] = []
        self.api2_requests: List[float] = []
        self.rate_limit_per_api = 30
        self.rate_limit_window = 60
        
        # Dual API mode
        self.dual_api_mode = False
        self.available_apis: List[int] = []
        self.request_delay = 2.0
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 3.0
        
        # Backoff configuration
        self.error_backoff_time = 30
        self.cloudflare_backoff_time = 15
        self.max_backoff_time = 300
        self.current_backoff = self.error_backoff_time
        
        self._init_ocr()
    
    def _init_ocr(self):
        """Initialize OCR for CAPTCHA solving."""
        try:
            import ddddocr
            self._ocr = ddddocr.DdddOcr(show_ad=False)
            self._ocr_available = True
            logger.info("ddddocr initialized for CAPTCHA solving")
        except ImportError:
            logger.warning("ddddorc not installed")
            self._ocr_available = False
    

    
    def is_configured(self) -> bool:
        """Check if provider is configured for redemption."""
        # Can work with just the public API (may get 40009 NOT LOGIN)
        # Or requires authorized credentials
        return True  # Always configured, but may return NOT_LOGIN
    
    def is_fully_configured(self) -> bool:
        """Check if all required credentials are present."""
        return bool(
            self.api_key or 
            self.login_token or 
            self.cookie or 
            self.session_id
        )
    
    async def init_session(self):
        """Initialize HTTP session."""
        if self.session is None:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(
                connector=connector,
                trust_env=True
            )
    
    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """Generate HMAC-MD5 signature (from whiteout-project/bot)."""
        # Sort parameters alphabetically
        sorted_params = sorted(params.items())
        param_string = "&".join(f"{k}={v}" for k, v in sorted_params)
        # Add salt
        param_string += self.sign_secret
        return hashlib.md5(param_string.encode()).hexdigest()
    
    def _get_headers(self, origin: str = "") -> Dict[str, str]:
        """Get request headers with browser randomization."""
        headers = get_headers(origin) if origin else get_headers()
        
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if self.login_token:
            headers["X-Login-Token"] = self.login_token
        if self.cookie:
            headers["Cookie"] = self.cookie
        if self.session_id:
            headers["X-Session-ID"] = self.session_id
            
        return headers
    
    def _check_rate_limit(self, api_num: int) -> float:
        """Check rate limit and return wait time if needed."""
        now = time.time()
        
        if api_num == 1:
            self.api1_requests = [t for t in self.api1_requests if now - t < self.rate_limit_window]
            if len(self.api1_requests) >= self.rate_limit_per_api:
                oldest = min(self.api1_requests)
                return self.rate_limit_window - (now - oldest)
            self.api1_requests.append(now)
        else:
            self.api2_requests = [t for t in self.api2_requests if now - t < self.rate_limit_window]
            if len(self.api2_requests) >= self.rate_limit_per_api:
                oldest = min(self.api2_requests)
                return self.rate_limit_window - (now - oldest)
            self.api2_requests.append(now)
        
        return 0
    
    async def _wait_for_rate_limit(self, api_num: int):
        """Wait if rate limited."""
        wait_time = self._check_rate_limit(api_num)
        if wait_time > 0:
            wait_time += random.uniform(0, 0.5)
            logger.warning(f"Rate limited on API{api_num}, waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
    
    def _handle_api_error(self, status: int, response_text: str) -> float:
        """Handle API errors and return backoff time."""
        if status == 429 or status == 1015:
            self.current_backoff = max(self.cloudflare_backoff_time, self.current_backoff)
            self.current_backoff *= random.uniform(1.0, 1.5)
            self.current_backoff = min(self.current_backoff * 2, self.max_backoff_time)
            return self.current_backoff
        elif status in [502, 503, 504]:
            backoff = self.current_backoff * random.uniform(0.75, 1.25)
            self.current_backoff = min(self.current_backoff * 2, self.max_backoff_time)
            return backoff
        else:
            self.current_backoff = min(self.current_backoff * 2, self.max_backoff_time)
            return self.current_backoff * random.uniform(0.75, 1.25)
    
    async def check_apis_availability(self, test_fid: str = "45379845") -> Dict[str, bool]:
        """Check which APIs are available (from whiteout-project/bot patterns)."""
        api_status = {
            "api1_available": False,
            "api2_available": False,
            "api1_url": f"{self.API1_URL}/api/player",
            "api2_url": f"{self.API2_URL}/api/player"
        }
        
        if not self.session:
            await self.init_session()
        
        # Test API 1
        try:
            now = int(time.time() * 1000)
            params = {"fid": test_fid, "time": now}
            sign = self._generate_sign(params)
            
            async with self.session.post(
                f"{self.API1_URL}/api/player",
                headers=self._get_headers(),
                data={"fid": test_fid, "time": now, "sign": sign},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                api_status["api1_available"] = resp.status in [200, 429]
        except Exception as e:
            logger.error(f"API1 availability check failed: {e}")
        
        # Test API 2
        try:
            now = int(time.time() * 1000)
            params = {"fid": test_fid, "time": now}
            sign = self._generate_sign(params)
            
            async with self.session.post(
                f"{self.API2_URL}/api/player",
                headers=self._get_headers(),
                data={"fid": test_fid, "time": now, "sign": sign},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                api_status["api2_available"] = resp.status in [200, 429]
        except Exception as e:
            logger.error(f"API2 availability check failed: {e}")
        
        # Update configuration based on availability
        if api_status["api1_available"] and api_status["api2_available"]:
            self.dual_api_mode = True
            self.available_apis = [1, 2]
            self.request_delay = 1.0
        elif api_status["api1_available"]:
            self.dual_api_mode = False
            self.available_apis = [1]
            self.request_delay = 2.0
        elif api_status["api2_available"]:
            self.dual_api_mode = False
            self.available_apis = [2]
            self.request_delay = 2.0
        else:
            self.available_apis = []
        
        return api_status
    
    async def get_player_info(self, fid: str) -> Tuple[bool, Optional[PlayerInfo], str]:
        """Get player information (from whiteout-project/bot patterns)."""
        if not self.session:
            await self.init_session()
        
        await self._wait_for_rate_limit(1)
        
        now = int(time.time() * 1000)
        params = {"fid": fid, "time": now}
        sign = self._generate_sign(params)
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.post(
                    f"{self.API1_URL}/api/player",
                    headers=self._get_headers(),
                    data={"fid": fid, "time": now, "sign": sign},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    text = await resp.text()
                    
                    if resp.status == 403:
                        return False, None, "UNAUTHORIZED"
                    
                    try:
                        result = await resp.json()
                    except:
                        return False, None, "INVALID_RESPONSE"
                    
                    if result.get("msg") == "success":
                        data = result.get("data", {})
                        player = PlayerInfo(
                            fid=fid,
                            name=data.get("name"),
                            level=data.get("level"),
                            alliance=data.get("alliance")
                        )
                        return True, player, "success"
                    elif result.get("msg") == "NOT LOGIN":
                        return False, None, "NOT_LOGIN"
                    else:
                        return False, None, result.get("msg", "LOGIN_ERROR")
                        
            except asyncio.TimeoutError:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Timeout getting player info, retry {attempt + 1}/{self.max_retries}")
                    await asyncio.sleep(self.retry_delay)
                else:
                    return False, None, "TIMEOUT"
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Error getting player info: {e}, retry {attempt + 1}/{self.max_retries}")
                    await asyncio.sleep(self.retry_delay)
                else:
                    return False, None, f"ERROR: {str(e)}"
        
        return False, None, "MAX_RETRIES"
    
    async def fetch_captcha(self, fid: str) -> Tuple[bool, Optional[bytes], str]:
        """Fetch CAPTCHA image (from whiteout-project/bot patterns)."""
        if not self.session:
            await self.init_session()
        
        await self._wait_for_rate_limit(1)
        
        now = int(time.time() * 1000)
        params = {"fid": fid, "init": 0, "time": now}
        sign = self._generate_sign(params)
        
        try:
            async with self.session.post(
                f"{self.API1_URL}/api/captcha",
                headers=self._get_headers(),
                data={"fid": fid, "time": now, "init": 0, "sign": sign},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                try:
                    captcha_json = await resp.json()
                except:
                    return False, None, "INVALID_RESPONSE"
                
                err_code = captcha_json.get("err_code")
                
                if err_code == 0:
                    img_data = captcha_json.get("data", {}).get("img", "")
                    if "," in img_data:
                        img_bytes = base64.b64decode(img_data.split(",", 1)[1])
                        return True, img_bytes, "success"
                    return False, None, "INVALID_IMAGE"
                elif err_code == 40100:
                    return False, None, "INVALID_FID"
                elif captcha_json.get("msg") == "NOT LOGIN":
                    return False, None, "NOT_LOGIN"
                else:
                    return False, None, f"CAPTCHA_ERROR_{err_code}"
                    
        except Exception as e:
            return False, None, f"ERROR: {str(e)}"
    
    def solve_captcha(self, image_bytes: bytes) -> Optional[str]:
        """Solve CAPTCHA using OCR."""
        if not self._ocr_available or self._ocr is None:
            return None
        
        try:
            return self._ocr.classification(image_bytes)
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return None
    
    async def redeem(self, code: str, fid: str) -> RedemptionResponse:
        """
        Redeem a gift code (from whiteout-project/bot patterns).
        
        Flow:
        1. Get player info
        2. Fetch CAPTCHA
        3. Solve CAPTCHA with OCR
        4. Submit redemption
        """
        if not self.session:
            await self.init_session()
        
        # Step 1: Get player info
        success, player_info, error = await self.get_player_info(fid)
        
        if not success:
            if error == "NOT_LOGIN":
                return RedemptionResponse(
                    success=False,
                    result=RedemptionResult.NOT_LOGIN,
                    message="API requires login. Configure EXTERNAL_PROVIDER_LOGIN_TOKEN"
                )
            elif error == "UNAUTHORIZED":
                return RedemptionResponse(
                    success=False,
                    result=RedemptionResult.UNAUTHORIZED,
                    message="API requires authorization. Configure EXTERNAL_PROVIDER_API_KEY"
                )
            else:
                return RedemptionResponse(
                    success=False,
                    result=RedemptionResult.ERROR,
                    message=f"Player lookup failed: {error}"
                )
        
        # Step 2: Fetch CAPTCHA
        has_captcha, captcha_bytes, captcha_error = await self.fetch_captcha(fid)
        
        if not has_captcha or captcha_bytes is None:
            if captcha_error == "NOT_LOGIN":
                return RedemptionResponse(
                    success=False,
                    result=RedemptionResult.NOT_LOGIN,
                    message="CAPTCHA requires login. Configure EXTERNAL_PROVIDER_LOGIN_TOKEN"
                )
            return RedemptionResponse(
                success=False,
                result=RedemptionResult.CAPTCHA_ERROR,
                message=f"CAPTCHA fetch failed: {captcha_error}"
            )
        
        # Step 3: Solve CAPTCHA
        captcha_solution = self.solve_captcha(captcha_bytes)
        if captcha_solution is None:
            return RedemptionResponse(
                success=False,
                result=RedemptionResult.CAPTCHA_ERROR,
                message="OCR failed to solve CAPTCHA. Install ddddocr."
            )
        
        # Step 4: Submit redemption
        await self._wait_for_rate_limit(1)
        
        now = int(time.time() * 1000)
        params = {
            "captcha_code": captcha_solution,
            "cdk": code,
            "fid": fid,
            "time": now
        }
        sign = self._generate_sign(params)
        
        for attempt in range(self.max_retries):
            try:
                async with self.session.post(
                    f"{self.API1_URL}/api/gift_code",
                    headers=self._get_headers(),
                    data={
                        "cdk": code,
                        "fid": fid,
                        "time": now,
                        "captcha_code": captcha_solution,
                        "sign": sign
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    try:
                        result = await resp.json()
                    except:
                        return RedemptionResponse(
                            success=False,
                            result=RedemptionResult.ERROR,
                            message="Invalid API response"
                        )
                    
                    err_code = result.get("err_code")
                    
                    # Map error codes (from whiteout-project/bot)
                    status_map = {
                        20000: (RedemptionResult.SUCCESS, "Successfully claimed", True),
                        40008: (RedemptionResult.ALREADY_CLAIMED, "Already claimed by this player", False),
                        40014: (RedemptionResult.CODE_NOT_EXIST, "Gift code does not exist", False),
                        40007: (RedemptionResult.CODE_EXPIRED, "Gift code has expired", False),
                        40005: (RedemptionResult.CODE_FULLY_CLAIMED, "Gift code fully claimed", False),
                        40103: (RedemptionResult.CAPTCHA_ERROR, "CAPTCHA verification failed", False),
                        40009: (RedemptionResult.NOT_LOGIN, "NOT LOGIN - requires authentication", False),
                    }
                    
                    if err_code in status_map:
                        result_enum, message, success = status_map[err_code]
                        return RedemptionResponse(
                            success=success,
                            result=result_enum,
                            message=message,
                            player_data=player_info.__dict__ if player_info else None
                        )
                    else:
                        return RedemptionResponse(
                            success=False,
                            result=RedemptionResult.UNKNOWN,
                            message=f"Unknown error code: {err_code}"
                        )
                        
            except asyncio.TimeoutError:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Timeout redeeming code, retry {attempt + 1}/{self.max_retries}")
                    await asyncio.sleep(self.retry_delay)
                else:
                    return RedemptionResponse(
                        success=False,
                        result=RedemptionResult.ERROR,
                        message="Timeout during redemption"
                    )
            except Exception as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Error redeeming code: {e}, retry {attempt + 1}/{self.max_retries}")
                    await asyncio.sleep(self.retry_delay)
                else:
                    return RedemptionResponse(
                        success=False,
                        result=RedemptionResult.ERROR,
                        message=f"Network error: {str(e)}"
                    )
        
        return RedemptionResponse(
            success=False,
            result=RedemptionResult.ERROR,
            message="Max retries exceeded"
        )
    
    async def health_check(self) -> Tuple[bool, str]:
        """Check if the provider is healthy."""
        try:
            if not self.session:
                await self.init_session()
            
            async with self.session.get(
                url=f"{self.API1_URL}/",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status < 500:
                    return True, "API endpoint reachable"
                else:
                    return False, f"API returned status {resp.status}"
                    
        except Exception as e:
            return False, f"Cannot reach API: {str(e)}"
    
    @property
    def has_ocr(self) -> bool:
        """Check if OCR is available."""
        return self._ocr_available
    
    @property
    def status(self) -> str:
        """Get current provider status."""
        if self.is_fully_configured():
            return f"Enabled ({self.provider_name})"
        elif self.is_configured():
            return f"Partial ({self.provider_name})"
        else:
            return "Locked - Missing credentials"


# Global instance
whiteout_project_provider = WhiteoutProjectProvider()
