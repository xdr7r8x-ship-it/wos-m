import importlib
import tempfile
import os
from pathlib import Path


def test_settings_load_from_env_reads_dotenv_values(monkeypatch, tmp_path):
    """Settings should read required values from a temporary .env file."""
    # Create a temporary .env file with test values
    test_env = tmp_path / ".env"
    test_env.write_text("""
DISCORD_BOT_TOKEN=test-bot-token
DISCORD_APPLICATION_ID=123456789012345678
OWNER_DISCORD_ID=123456789012345678
WOSM_DEMO_MODE=false
""")
    
    # Patch the BASE_DIR to point to tmp_path
    import config.settings as settings_module
    monkeypatch.setattr(settings_module, 'BASE_DIR', tmp_path)
    
    # Also patch dotenv.load_dotenv to load from tmp_path
    import dotenv
    original_load = dotenv.load_dotenv
    def patched_load(*args, **kwargs):
        return original_load(test_env, *args, **kwargs)
    monkeypatch.setattr(dotenv, 'load_dotenv', patched_load)
    
    # Clear any cached settings
    for name in [
        "DISCORD_BOT_TOKEN",
        "DISCORD_APPLICATION_ID",
        "OWNER_DISCORD_ID",
        "WOSM_DEMO_MODE",
    ]:
        monkeypatch.delenv(name, raising=False)

    reloaded = importlib.reload(settings_module)

    assert reloaded.settings.bot.token == "test-bot-token"
    assert reloaded.settings.bot.application_id == "123456789012345678"
    assert reloaded.settings.bot.owner_id == "123456789012345678"
    assert reloaded.settings.demo_mode is False
