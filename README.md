<div align="center">

# 🤖 DevPulse Bot

**Your personal GitHub monitoring assistant in Telegram.**

[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)](#)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

</div>

DevPulse tracks your favorite GitHub repositories and reports back to you via Telegram. Never miss a new star, fork, or issue!

## 🚀 Features
- Track multiple repositories effortlessly.
- Real-time on-demand status checks.
- Built with modern Python `asyncio` and `aiogram 3.x`.

## 🛠️ Setup & Run

### Using Docker (Recommended)
1. Clone the repository.
2. Build and run the container:
```bash
docker build -t devpulse-bot .
docker run -d --env TELEGRAM_TOKEN="your_bot_token" devpulse-bot
```

### Manual Setup
1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Run the bot:
```bash
TELEGRAM_TOKEN="your_bot_token" python src/bot.py
```

## 💬 Commands
- `/start` - Welcome message and instructions
- `/track <owner/repo>` - Start tracking a repository (e.g., `/track verf1CT/flutter-architect`)
- `/untrack <owner/repo>` - Stop tracking
- `/status` - Get the latest stars, forks, and issues for your tracked repos

## 🤝 Contributing
Contributions are always welcome!

## 📄 License
MIT License.