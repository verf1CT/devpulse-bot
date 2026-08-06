import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aiohttp
import aiosqlite

logging.basicConfig(level=logging.INFO)
bot = Bot(token=os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN"))
dp = Dispatcher()
DB_FILE = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tracked_repos (
                user_id INTEGER,
                repo_name TEXT,
                PRIMARY KEY (user_id, repo_name)
            )
        ''')
        await db.commit()

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
    user_id = message.from_user.id
    
    async with aiosqlite.connect(DB_FILE) as db:
        try:
            await db.execute("INSERT INTO tracked_repos (user_id, repo_name) VALUES (?, ?)", (user_id, repo))
            await db.commit()
            await message.answer(f"✅ Now tracking `{repo}`", parse_mode="Markdown")
        except aiosqlite.IntegrityError:
            await message.answer(f"ℹ️ You are already tracking `{repo}`", parse_mode="Markdown")

@dp.message(Command("untrack"))
async def cmd_untrack(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /untrack <owner/repo>")
        return
    
    repo = parts[1]
    user_id = message.from_user.id
    
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("DELETE FROM tracked_repos WHERE user_id = ? AND repo_name = ?", (user_id, repo))
        await db.commit()
        if cursor.rowcount > 0:
            await message.answer(f"❌ Stopped tracking `{repo}`", parse_mode="Markdown")
        else:
            await message.answer("This repo is not being tracked by you.")

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    user_id = message.from_user.id
    repos = []
    
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT repo_name FROM tracked_repos WHERE user_id = ?", (user_id,)) as cursor:
            async for row in cursor:
                repos.append(row[0])
                
    if not repos:
        await message.answer("No repositories are currently being tracked by you.")
        return

    await message.answer("📊 Fetching stats...")
    
    async with aiohttp.ClientSession() as session:
        for repo in repos:
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
    print("Initializing database...")
    await init_db()
    print("Starting DevPulse bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())