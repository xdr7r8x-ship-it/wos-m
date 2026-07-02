# WOS-M Developer Notes
# © MANSOUR — WOS-M. All rights reserved.

## Project Overview
WOS-M is a Discord bot for managing Whiteout Survival game alliances, gift codes, and player features.

## Entry Points

### Main Entry
```
python main.py
```
- Initializes bot with Discord API token
- Loads all modules and features
- Syncs slash commands

### Check Modes
```
python main.py --check      # Static checks (no .env required)
python main.py --check-runtime  # Runtime checks (requires .env)
```

### Scripts
```
python scripts/security_scan.py      # Scan for hardcoded secrets
python scripts/discord_runtime_smoke.py  # Runtime smoke test
```

## Architecture

### Core Modules
| Module | Purpose |
|--------|---------|
| `core/bot.py` | Main bot class, interaction dispatcher |
| `core/database.py` | SQLite database operations |
| `core/permissions.py` | Permission levels (owner/admin/member) |
| `core/audit_log.py` | Audit logging for admin actions |
| `core/feature_registry.py` | Feature toggle system |
| `core/i18n.py` | Internationalization (ar/en) |
| `core/interaction_registry.py` | Button/select callback registry |
| `core/process_queue.py` | Background task queue |

### Feature Modules
| Module | Features |
|--------|----------|
| `modules/alliances/` | Alliance CRUD, member management |
| `modules/players/` | Player management |
| `modules/gift_codes/` | Gift code creation, redemption |
| `modules/owner_panel/` | Owner-only dashboard |
| `modules/maintenance/` | Maintenance mode |
| `modules/notifications/` | Notification system |
| `modules/themes/` | Theme management |
| `modules/settings/` | Bot settings |
| `modules/dashboard/` | Main dashboard views |
| `modules/events/` | Event management |
| `modules/attendance/` | Attendance tracking |
| `modules/bear_tracking/` | Bear tracking |
| `modules/ministers/` | Minister management |

### Integrations
| File | Purpose |
|------|---------|
| `integrations/whiteout_project_provider.py` | Real gift redemption API |
| `integrations/wos_open_source_adapter.py` | Open source alternative |
| `integrations/gift_code_client.py` | Gift code HTTP client |
| `integrations/captcha_service.py` | CAPTCHA solving |

## Commands

### Slash Commands
- `/wos` - Main dashboard

### Button Callbacks (34 registered)
- Navigation buttons (back, home, etc.)
- Alliance management buttons
- Gift code buttons
- Owner panel buttons

### Select Menus (8 registered)
- Language selector
- Theme selector
- Various dropdowns

## Environment Variables

### Required
```env
DISCORD_BOT_TOKEN=          # Discord bot token
DISCORD_APPLICATION_ID=     # Discord application ID
OWNER_DISCORD_ID=           # Bot owner's Discord ID
DATABASE_URL=               # SQLite URL (e.g., sqlite:///data/wosm.sqlite)
```

### Optional
```env
WOSM_DEMO_MODE=false        # Enable demo mode
DEFAULT_LANGUAGE=ar         # Default locale
REAL_REDEMPTION_PROVIDER=WhiteoutProject
WOS_GIFT_PUBLIC_ENDPOINT=   # Gift API endpoint
EXTERNAL_PROVIDER_API_KEY=  # Provider API key
```

## Testing

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Test Categories
- Unit tests for core modules
- Integration tests for flows
- Security scan tests
- Permission matrix tests

### Quality Gates
```bash
flake8 .              # Linting
mypy core modules     # Type checking
pip-audit             # Dependency audit
```

## Database

### Schema
- `alliances` - Alliance data
- `players` - Player data
- `gift_codes` - Gift codes
- `gift_redemptions` - Redemption history
- `permissions` - User permissions
- `audit_log` - Audit entries
- `settings` - Bot settings

### Migrations
Located in `database/migrations/__init__.py`

## Security

### Permission Levels
1. **OWNER** - Full access, bot owner only
2. **ADMIN** - Guild admin
3. **MODERATOR** - Guild moderator
4. **MEMBER** - Basic access

### Audit Logging
All sensitive operations are logged with:
- User ID
- Action type
- Timestamp
- Guild ID

## Deployment

### Local
```bash
./run.sh
```

### Docker
```bash
docker-compose up -d
```

### Systemd (Linux)
```bash
sudo cp wos-m.service /etc/systemd/system/
sudo systemctl enable wos-m
sudo systemctl start wos-m
```

## Key Fixes Applied

### 2024-07-02
- Fixed `AttributeError` on Discord Interaction objects
- Changed `setattr()` to `set()` tracking for frozen objects
- Fixed pytest warning about test return values
- Added memory cleanup for interaction tracking

## Commands Summary

```bash
# Install dependencies
pip install -r requirements.txt

# Run bot
python main.py

# Check system
python main.py --check
python main.py --check-runtime

# Run tests
python -m pytest tests/ -v

# Lint
flake8 .

# Type check
mypy core modules

# Security scan
python scripts/security_scan.py
```
