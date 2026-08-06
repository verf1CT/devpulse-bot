from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
import aiosqlite
import os
import json

app = FastAPI(title="DevPulse SaaS")

app.add_middleware(SessionMiddleware, secret_key="devpulse_super_secret")

# Ensure static and templates dirs exist
os.makedirs("src/static", exist_ok=True)
os.makedirs("src/templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="src/static"), name="static")
templates = Jinja2Templates(directory="src/templates")

DB_FILE = "bot.db"

# Mock OAuth for Demo
@app.get("/login")
async def login(request: Request):
    request.session['user'] = {'login': 'pro_user', 'avatar_url': 'https://avatars.githubusercontent.com/u/9919?s=200&v=4'}
    return RedirectResponse(url="/")

@app.get("/logout")
async def logout(request: Request):
    request.session.pop('user', None)
    return RedirectResponse(url="/")

@app.get("/")
async def read_dashboard(request: Request):
    user = request.session.get('user')
    repos_data = []
    
    if user and os.path.exists(DB_FILE):
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT DISTINCT repo_name FROM tracked_repos") as cursor:
                repos = [row[0] async for row in cursor]
                
            for repo in repos:
                async with db.execute("SELECT stars, forks, timestamp FROM repo_stats_history WHERE repo_name = ? ORDER BY timestamp DESC LIMIT 1", (repo,)) as cursor:
                    latest = await cursor.fetchone()
                
                async with db.execute("SELECT timestamp, stars FROM repo_stats_history WHERE repo_name = ? ORDER BY timestamp ASC", (repo,)) as cursor:
                    history_timestamps = []
                    history_stars = []
                    async for row in cursor:
                        history_timestamps.append(row[0])
                        history_stars.append(row[1])
                
                if latest:
                    repos_data.append({
                        "name": repo,
                        "stars": latest[0],
                        "forks": latest[1],
                        "last_updated": latest[2],
                        "history_timestamps": history_timestamps,
                        "history_stars": history_stars
                    })

    return templates.TemplateResponse("index.html", {"request": request, "repos": repos_data, "user": user})
