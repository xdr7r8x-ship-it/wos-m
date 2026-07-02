import importlib


def test_settings_load_from_env_reads_dotenv_values(monkeypatch):
    """Settings should read required values from the local .env file even when env vars are absent."""
    for name in [
        "DISCORD_BOT_TOKEN",
        "DISCORD_APPLICATION_ID",
        "OWNER_DISCORD_ID",
        "WOSM_DEMO_MODE",
    ]:
        monkeypatch.delenv(name, raising=False)

    import config.settings as settings_module

    reloaded = importlib.reload(settings_module)

    assert reloaded.settings.bot.token == "test-bot-token"
    assert reloaded.settings.bot.application_id == "123456789012345678"
    assert reloaded.settings.bot.owner_id == "123456789012345678"
    assert reloaded.settings.demo_mode is False
