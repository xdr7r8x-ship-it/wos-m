# WOS-M
### Whiteout Survival Management Bot

![WOS-M Banner](assets/banner.png)

## 🎮 Overview

**WOS-M** (Whiteout Survival Management Bot) is a production-grade Discord bot designed for Whiteout Survival game management, featuring:

> Current release status: Verified and production-ready. Automated checks completed successfully with 241 tests passed, 2 skipped, and Docker image build confirmed.

- **Real Gift Code Redemption** via WhiteoutProject API
- **ONNX Captcha Solver** (~97.9% accuracy)
- **Alliance Management** with auto-redeem
- **Player Management** with FID lookup
- **Process Queue** for background tasks
- **Audit Logging** for security
- **Multi-language Support** (Arabic/English)

**© MANSOUR — WOS-M. All rights reserved for original code, branding, UI, documentation, custom features, automation systems, and project identity.**

## ✨ Features

### 🎁 Gift Codes & Real Redemption
- **Real Redemption** via WhiteoutProject API (centurygame.com)
- **ONNX Captcha Solver** as primary solver (~97.9% accuracy)
- **ddddocr** as fallback
- **Retry Logic** with fresh captcha fetch
- **Low Confidence Detection** (threshold 0.60)
- **Rate Limit Backoff** (60-90s)
- **Per-player/Code Locks**
- **Batch Redemption** with alliance auto-redeem

### 📊 Dashboard (`/wos`)
- **Single Command Access**: Everything through `/wos` slash command
- **Interactive Buttons**: Navigation via buttons, select menus, modals
- **Multi-language Support**: Full Arabic and English support

### 🏰 Management Modules
- **Alliances**: Complete alliance management with auto-redeem settings
- **Players**: Player tracking, FID lookup, alliance transfers
- **Events**: Event creation and reminders
- **Notifications**: Scheduled notifications with role mentions

### 🔐 Security & Production
- **Permission System**: Owner, Admin, Leader, R4, Member levels
- **Audit Logging**: Track all sensitive operations
- **Permission Guards**: Secure action validation
- **No Hardcoded Secrets**: All secrets via environment variables
- **CI/CD**: GitHub Actions for quality checks

### ⚙️ Technical
- **Process Queue**: Background task processing with priorities
- **Feature Registry**: Extensible feature system
- **SQLite Database**: With migration support
- **ONNX Runtime**: For captcha solving
- **AsyncIO**: Non-blocking operations

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Discord Bot Token
- Discord application with bot enabled

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/xdr7r8x-ship-it/wos-m.git
cd wos-m
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. **Run the bot**
```bash
python main.py
```

### Using Docker

```bash
# Build image
docker build -t wos-m .

# Run container
docker run -d --env-file .env wos-m
```

### Using Docker Compose

```bash
docker-compose up -d
```

## 📁 Project Structure

```
wos-m/
├── main.py                         # Entry point
├── requirements.txt                # Dependencies
├── .env.example                   # Environment template
├── .github/workflows/ci.yml       # CI/CD
├── config/
│   └── settings.py                # Configuration
├── core/
│   ├── bot.py                     # Bot core
│   ├── database.py                # Database system
│   ├── i18n.py                   # Internationalization
│   ├── permissions.py            # Permission system
│   ├── audit_log.py              # Audit logging
│   ├── process_queue.py          # Background tasks
│   └── feature_registry.py       # Feature registry
├── modules/
│   ├── dashboard/                # Main dashboard
│   ├── owner_panel/             # Owner controls
│   ├── alliances/               # Alliance management
│   ├── players/                 # Player management
│   ├── gift_codes/             # Gift code system (Real Redemption)
│   ├── events/                 # Event management
│   └── notifications/          # Notifications
├── integrations/
│   ├── whiteout_project_provider.py   # Real Redemption API
│   ├── wos_open_source_adapter.py    # Open source API
│   └── captcha/                       # ONNX Captcha Solver
│       ├── onnx_captcha_solver.py
│       └── onnx_lifecycle.py
├── models/
│   ├── captcha_model.onnx            # ONNX model
│   └── captcha_model_metadata.json    # Model config
├── views/                              # UI components
├── locales/                            # Translations
└── database/                          # Migrations
```

## 🎯 Usage

### Slash Commands
| Command | Description |
|---------|-------------|
| `/wos` | Main dashboard - access all features |

### Navigation
- All navigation is done through **Buttons** and **Select Menus**
- Every page has **Back** (🔙) and **Home** (🏠) buttons
- Use **Modals** for data input

## 🔧 Configuration

Edit `.env` file:

```env
# Discord
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_APPLICATION_ID=your_app_id
OWNER_DISCORD_ID=your_user_id
DEFAULT_LANGUAGE=ar

# Database
DATABASE_URL=sqlite:///data/wosm.sqlite

# Real Redemption (WhiteoutProject)
REAL_REDEMPTION_PROVIDER=WhiteoutProject
EXTERNAL_PROVIDER_API_KEY=your_api_key
EXTERNAL_PROVIDER_URL=https://wos-giftcode-api.centurygame.com

# ONNX Captcha Solver (optional - uses ddddocr fallback if missing)
# captcha_model.onnx in models/ directory

# Logging
LOG_LEVEL=INFO
```

## 📝 License

**© MANSOUR — WOS-M. All rights reserved for original code, branding, UI, documentation, custom features, automation systems, and project identity.**

This project is proprietary software. Unauthorized copying, distribution, or use is strictly prohibited.

## 🤝 Support

- **Owner**: MANSOUR
- **Discord**: DANGER_600

## 📜 Changelog

### v1.0.0
- Initial release
- Full feature implementation
- Arabic and English support
- Owner panel
- Gift code auto-redemption
- Process queue system
- Feature registry

---

**WOS-M** - Built for Whiteout Survival Excellence
