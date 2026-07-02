"""
WOS-M Configuration Settings
© MANSOUR — WOS-M. All rights reserved.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import dotenv

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Load environment variables from the local .env file when present.
dotenv.load_dotenv(BASE_DIR / ".env", override=False)


@dataclass
class BotConfig:
    """Bot core configuration."""
    token: str = ""
    application_id: str = ""
    owner_id: str = ""
    owner_name: str = "MANSOUR"
    owner_discord: str = "DANGER_600"
    debug: bool = False


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str = "sqlite:///data/wosm.sqlite"
    backup_dir: Path = field(default_factory=lambda: DATA_DIR / "backups")
    pool_size: int = 5
    max_overflow: int = 10


@dataclass
class APIConfig:
    """External API configurations."""
    wos_api_base_url: str = ""
    gift_code_api_base_url: str = ""
    wos_gift_public_endpoint: str = "https://wos-giftcode-api.centurygame.com"
    wos_player_public_endpoint: str = "https://wos-giftcode-api.centurygame.com"
    captcha_service_url: str = ""
    captcha_service_token: str = ""
    ocr_service_url: str = ""
    use_local_ocr: bool = False  # Set to true when CAPTCHA_SERVICE_URL=local-ddddocr
    # External Redemption Provider (for authorized API access)
    external_provider_api_key: str = ""
    external_provider_url: str = ""
    external_provider_name: str = "WoSTools"
    external_provider_login_token: str = ""  # Set at runtime only
    external_provider_sign_secret: str = ""   # Optional custom sign salt
    external_provider_cookie: str = ""         # Optional cookie
    external_provider_session: str = ""       # Optional session ID
    # Real Redemption Provider selection
    real_redemption_provider: str = "WhiteoutProject"  # "WhiteoutProject" or "Generic"
    request_timeout: int = 30
    rate_limit_calls: int = 10
    rate_limit_period: int = 60


@dataclass
class ProcessQueueConfig:
    """Process queue configuration."""
    enabled: bool = True
    max_retries: int = 3
    retry_delay: int = 60
    batch_size: int = 50
    crash_recovery_enabled: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Path = field(default_factory=lambda: DATA_DIR / "logs" / "wosm.log")
    audit_log_file: Path = field(default_factory=lambda: DATA_DIR / "logs" / "audit.log")
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5


@dataclass
class Settings:
    """Main settings container."""
    bot: BotConfig = field(default_factory=BotConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    api: APIConfig = field(default_factory=APIConfig)
    process_queue: ProcessQueueConfig = field(default_factory=ProcessQueueConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Theme defaults
    default_language: str = "ar"
    theme_color_primary: int = 0x3498db
    theme_color_success: int = 0x2ecc71
    theme_color_warning: int = 0xf39c12
    theme_color_error: int = 0xe74c3c
    theme_color_info: int = 0x1abc9c
    theme_embed_footer: str = "WOS-M"
    
    # Demo mode - MUST BE FALSE for production
    demo_mode: bool = False
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.demo_mode
    
    @property
    def has_gift_api(self) -> bool:
        """Check if Gift Code API is configured."""
        return bool(self.api.gift_code_api_base_url)
    
    @property
    def has_captcha_service(self) -> bool:
        """Check if Captcha service is configured."""
        return bool(self.api.captcha_service_url and self.api.captcha_service_token)
    
    @classmethod
    def load_from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        settings = cls()
        
        settings.bot.token = os.getenv("DISCORD_BOT_TOKEN", "")
        settings.bot.application_id = os.getenv("DISCORD_APPLICATION_ID", "")
        settings.bot.owner_id = os.getenv("OWNER_DISCORD_ID", "")
        settings.bot.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        settings.database.url = os.getenv("DATABASE_URL", settings.database.url)
        settings.database.backup_dir = Path(os.getenv("BACKUP_DIR", settings.database.backup_dir))
        
        settings.api.wos_api_base_url = os.getenv("WOS_API_BASE_URL", "")
        settings.api.gift_code_api_base_url = os.getenv("GIFT_CODE_API_BASE_URL", "")
        settings.api.captcha_service_url = os.getenv("CAPTCHA_SERVICE_URL", "")
        settings.api.captcha_service_token = os.getenv("CAPTCHA_SERVICE_TOKEN", "")
        settings.api.ocr_service_url = os.getenv("OCR_SERVICE_URL", "")
        
        # Detect local ddddocr usage
        settings.api.use_local_ocr = (
            settings.api.captcha_service_url == "local-ddddocr" or
            settings.api.captcha_service_token == "local"
        )
        
        # External Redemption Provider
        settings.api.external_provider_api_key = os.getenv("EXTERNAL_PROVIDER_API_KEY", "")
        settings.api.external_provider_url = os.getenv("EXTERNAL_PROVIDER_URL", "")
        settings.api.external_provider_name = os.getenv("EXTERNAL_PROVIDER_NAME", "WoSTools")
        # Note: EXTERNAL_PROVIDER_LOGIN_TOKEN should NEVER be committed to git
        # It must be set via environment variable at runtime
        settings.api.external_provider_login_token = os.getenv("EXTERNAL_PROVIDER_LOGIN_TOKEN", "")
        settings.api.external_provider_cookie = os.getenv("EXTERNAL_PROVIDER_COOKIE", "")
        settings.api.external_provider_session = os.getenv("EXTERNAL_PROVIDER_SESSION", "")
        
        # Real Redemption Provider selection
        settings.api.real_redemption_provider = os.getenv("REAL_REDEMPTION_PROVIDER", "WhiteoutProject")
        
        # Demo mode - must be explicitly enabled
        demo_mode_str = os.getenv("WOSM_DEMO_MODE", "false").lower()
        settings.demo_mode = demo_mode_str == "true"
        
        settings.logging.level = os.getenv("LOG_LEVEL", settings.logging.level)
        settings.default_language = os.getenv("DEFAULT_LANGUAGE", settings.default_language)
        
        # Theme colors
        if color := os.getenv("THEME_COLOR_PRIMARY"):
            settings.theme_color_primary = int(color, 16)
        if color := os.getenv("THEME_COLOR_SUCCESS"):
            settings.theme_color_success = int(color, 16)
        if color := os.getenv("THEME_COLOR_WARNING"):
            settings.theme_color_warning = int(color, 16)
        if color := os.getenv("THEME_COLOR_ERROR"):
            settings.theme_color_error = int(color, 16)
        if color := os.getenv("THEME_COLOR_INFO"):
            settings.theme_color_info = int(color, 16)
            
        return settings


settings = Settings.load_from_env()
