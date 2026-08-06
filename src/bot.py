import os
import asyncio
import logging
import datetime
from io import BytesIO
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
import aiohttp
import aiosqlite
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
        await db.execute('''
            CREATE TABLE IF NOT EXISTS repo_stats_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_name TEXT,
                timestamp DATETIME,
                stars INTEGER,
                forks INTEGER
            )
        ''')
        await db.commit()

async def fetch_repo_stats(session, repo_name):
    url = f"https://api.github.com/repos/{repo_name}"
    async with session.get(url) as response:
        if response.status == 200:
            return await response.json()
        return None

async def sync_repo_stats():
    """Background task to fetch and save stats for all tracked repos."""
    logging.info("Running background sync...")
    repos = set()
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT DISTINCT repo_name FROM tracked_repos") as cursor:
            async for row in cursor:
                repos.add(row[0])
                
    if not repos:
        return

    now = datetime.datetime.now()
    async with aiohttp.ClientSession() as session:
        async with aiosqlite.connect(DB_FILE) as db:
            for repo in repos:
                stats = await fetch_repo_stats(session, repo)
                if stats:
                    await db.execute('''
                        INSERT INTO repo_stats_history (repo_name, timestamp, stars, forks)
                        VALUES (?, ?, ?, ?)
                    ''', (repo, now, stats['stargazers_count'], stats['forks_count']))
            await db.commit()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        "🤖 **DevPulse Bot** is running!\n\n"
        "Commands:\n"
        "/track <owner/repo> - Track a GitHub repository\n"
        "/untrack <owner/repo> - Stop tracking\n"
        "/status - Get current stats for tracked repos\n"
        "/graph <owner/repo> - Show stars growth graph"
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
            
            # Immediately fetch initial stats so graph isn't empty
            async with aiohttp.ClientSession() as session:
                stats = await fetch_repo_stats(session, repo)
                if stats:
                    await db.execute('''
                        INSERT INTO repo_stats_history (repo_name, timestamp, stars, forks)
                        VALUES (?, ?, ?, ?)
                    ''', (repo, datetime.datetime.now(), stats['stargazers_count'], stats['forks_count']))
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

@dp.message(Command("graph"))
async def cmd_graph(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /graph <owner/repo>")
        return
    
    repo = parts[1]
    
    timestamps = []
    stars = []
    
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT timestamp, stars FROM repo_stats_history WHERE repo_name = ? ORDER BY timestamp ASC", (repo,)) as cursor:
            async for row in cursor:
                timestamps.append(datetime.datetime.fromisoformat(row[0]))
                stars.append(row[1])
                
    if not timestamps:
        await message.answer(f"No historical data for `{repo}` yet. Try again later.", parse_mode="Markdown")
        return

    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, stars, marker='o', linestyle='-', color='#3A96D6')
    plt.title(f"Stars Growth: {repo}")
    plt.xlabel("Time")
    plt.ylabel("Stars")
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Format x-axis
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    plt.gcf().autofmt_xdate()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    
    photo = BufferedInputFile(buf.read(), filename="graph.png")
    await message.answer_photo(photo, caption=f"📊 Growth history for {repo}")

async def main():
    print("Initializing database...")
    await init_db()
    
    print("Starting background scheduler...")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(sync_repo_stats, 'interval', hours=4)
    scheduler.start()
    
    print("Starting DevPulse bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())