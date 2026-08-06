import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aiohttp

logging.basicConfig(level=logging.INFO)
bot = Bot(token=os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN"))
dp = Dispatcher()

# Simple in-memory storage for demonstration
TRACKED_REPOS = set()

async def fetch_repo_stats(session, repo_name):
    url = f"https://api.github.com/repos/{repo_name}"
    async with session.get(url) as response:
        if response.status == 200:
            return await response.json()
        return None

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        "🤖 **DevPulse Bot** is running!\n\n"
        "Commands:\n"
        "/track <owner/repo> - Track a GitHub repository\n"
        "/untrack <owner/repo> - Stop tracking\n"
        "/status - Get current stats for tracked repos"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

@dp.message(Command("track"))
async def cmd_track(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /track <owner/repo>")
        return
    
    repo = parts[1]
    TRACKED_REPOS.add(repo)
    await message.answer(f"✅ Now tracking `{repo}`", parse_mode="Markdown")

@dp.message(Command("untrack"))
async def cmd_untrack(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /untrack <owner/repo>")
        return
    
    repo = parts[1]
    if repo in TRACKED_REPOS:
        TRACKED_REPOS.remove(repo)
        await message.answer(f"❌ Stopped tracking `{repo}`", parse_mode="Markdown")
    else:
        await message.answer("This repo is not being tracked.")

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    if not TRACKED_REPOS:
        await message.answer("No repositories are currently being tracked.")
        return

    await message.answer("📊 Fetching stats...")
    
    async with aiohttp.ClientSession() as session:
        for repo in TRACKED_REPOS:
            stats = await fetch_repo_stats(session, repo)
            if stats:
                msg = (
                    f"⭐ **{stats['full_name']}**\n"
                    f"Stars: {stats['stargazers_count']}\n"
                    f"Forks: {stats['forks_count']}\n"
                    f"Open Issues: {stats['open_issues_count']}"
                )
                await message.answer(msg, parse_mode="Markdown")
            else:
                await message.answer(f"⚠️ Could not fetch stats for `{repo}`", parse_mode="Markdown")

async def main():
    print("Starting DevPulse bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())