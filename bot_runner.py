import os
import argparse
import subprocess
import sys
import requests
import uuid
import asyncio
import uvicorn
from typing import Optional
from pathlib import Path
import aiohttp
from contextlib import asynccontextmanager
from loguru import logger

from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper, DailyRoomObject, DailyRoomProperties, DailyRoomParams

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from dotenv import load_dotenv
load_dotenv(override=True)


# ------------ Configuration ------------ #

MAX_SESSION_TIME = int(os.getenv('MAX_SESSION_TIME', 5 * 60))  # Default: 5 minutes
REQUIRED_ENV_VARS = [
    'DAILY_API_KEY',
    'OPENAI_API_KEY',
    'ELEVENLABS_API_KEY',
    'ELEVENLABS_VOICE_ID',
    'FLY_API_KEY',
    'FLY_APP_NAME',
    'MAX_SESSION_TIME',]

FLY_API_HOST = os.getenv("FLY_API_HOST", "https://api.machines.dev/v1")
FLY_APP_NAME = os.getenv("FLY_APP_NAME", "mds-moderator")
FLY_API_KEY = os.getenv("FLY_API_KEY", "")
FLY_HEADERS = {
    'Authorization': f"Bearer {FLY_API_KEY}",
    'Content-Type': 'application/json'
}

daily_helpers = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    aiohttp_session = aiohttp.ClientSession()
    daily_helpers["rest"] = DailyRESTHelper(
        daily_api_key=os.getenv("DAILY_API_KEY", ""),
        daily_api_url=os.getenv("DAILY_API_URL", 'https://api.daily.co/v1'),
        aiohttp_session=aiohttp_session
    )
    yield
    await aiohttp_session.close()


async def create_room() -> DailyRoomObject:
    # Use specified room URL, or create a new one if not specified
    room_url = os.getenv("off_DAILY_SAMPLE_ROOM_URL", "")

    if not room_url:
        params = DailyRoomParams(
            properties=DailyRoomProperties()
        )
        try:
            room: DailyRoomObject = await daily_helpers["rest"].create_room(params=params)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Unable to provision room {e}")
    else:
        # Check passed room URL exists, we should assume that it already has a sip set up
        try:
            room: DailyRoomObject = await daily_helpers["rest"].get_room_from_url(room_url)
        except Exception:
            raise HTTPException(
                status_code=500, detail=f"Room not found: {room_url}")
    return room


# ----------------- API ----------------- #

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Mount the static directory
STATIC_DIR = "frontend/out"
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")

# ----------------- Main ----------------- #


def spawn_fly_machine(room_url: str, token: str, system_prompt: Optional[str] = None, sprite_folder: Optional[str] = None):
    # Use the same image as the bot runner
    res = requests.get(f"{FLY_API_HOST}/apps/{FLY_APP_NAME}/machines", headers=FLY_HEADERS)
    if res.status_code != 200:
        raise Exception(f"Unable to get machine info from Fly: {res.text}")
    image = res.json()[0]['config']['image']

    # Machine configuration
    cmd = f"/app/.venv/bin/python3 bot.py -u {room_url} -t {token}"
    cmd = cmd.split()
    worker_props = {
        "config": {
            "image": image,
            "auto_destroy": True,
            "init": {
                "cmd": cmd
            },
            "restart": {
                "policy": "no"
            },
            "guest": {
                "cpu_kind": "shared",
                "cpus": 1,
                "memory_mb": 1024
            },
            "env": {}
        },
    }

    if system_prompt:
        worker_props["config"]["env"]["SYSTEM_PROMPT"] = system_prompt

    if sprite_folder:
        worker_props["config"]["env"]["SPRITE_FOLDER"] = sprite_folder

    bot_name = os.getenv("BOT_NAME", "Chatbot")
    worker_props["config"]["env"]["BOT_NAME"] = bot_name

    # Spawn a new machine instance
    res = requests.post(
        f"{FLY_API_HOST}/apps/{FLY_APP_NAME}/machines",
        headers=FLY_HEADERS,
        json=worker_props)

    if res.status_code != 200:
        raise Exception(f"Problem starting a bot worker: {res.text}")

    # Wait for the machine to enter the started state
    vm_id = res.json()['id']

    res = requests.get(
        f"{FLY_API_HOST}/apps/{FLY_APP_NAME}/machines/{vm_id}/wait?state=started",
        headers=FLY_HEADERS)

    if res.status_code != 200:
        raise Exception(f"Bot was unable to enter started state: {res.text}")

    print(f"Machine joined room: {room_url}")


@app.post("/start_bot")
async def start_bot(request: Request) -> JSONResponse:
    if os.getenv("DUMMY_BOT", False):
        # Simulate bot spawning without actually creating a room or spawning a bot
        dummy_room_url = f"https://example.daily.co/{uuid.uuid4()}"
        dummy_token = f"dummy_token_{uuid.uuid4()}"
        return JSONResponse({
            "room_url": dummy_room_url,
            "token": dummy_token,
        })

    try:
        data = await request.json()
        logger.info(f"Starting bot with request: {data}")
        # Is this a webhook creation request?
        if "test" in data:
            return JSONResponse({"test": True})
        system_prompt = data.get("system_prompt") or os.getenv("SYSTEM_PROMPT")
        sprite_folder = data.get("sprite_folder")
    except Exception as e:
        system_prompt = os.getenv("SYSTEM_PROMPT")
        sprite_folder = None

    room = await create_room()

    # Give the agent a token to join the session
    token = await daily_helpers["rest"].get_token(room.url, MAX_SESSION_TIME)

    if not room or not token:
        raise HTTPException(
            status_code=500, detail=f"Failed to get token for room: {room.url}")

    # Launch a new fly.io machine, or run as a shell process (not recommended)
    run_as_process = os.getenv("RUN_AS_PROCESS", False)
    if run_as_process:
        print(f"Running as process")
    else:
        print(f"Running as VM")

    if run_as_process:
        try:
            env = os.environ.copy()
            if system_prompt:
                env["SYSTEM_PROMPT"] = system_prompt
            # check if we run inside a docker container
            if os.path.exists("/app/.venv/bin/python"):
                cmd = f"/app/.venv/bin/python bot.py -u {room.url} -t {token}"
            else:
                cmd = f"pipenv run python bot.py -u {room.url} -t {token}"
            subprocess.Popen(
                [cmd],
                shell=True,
                bufsize=1,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                env=env)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to start subprocess: {e}")
    else:
        try:
            spawn_fly_machine(room.url, token, system_prompt, sprite_folder)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to spawn VM: {e}")

    # Grab a token for the user to join with
    user_token = await daily_helpers["rest"].get_token(room.url, MAX_SESSION_TIME)

    return JSONResponse({
        "room_url": room.url,
        "token": user_token,
    })

@app.get("/{path_name:path}", response_class=FileResponse)
async def catch_all(path_name: Optional[str] = ""):
    if path_name == "":
        return FileResponse(f"{STATIC_DIR}/index.html")

    file_path = Path(STATIC_DIR) / (path_name or "")

    if file_path.is_file():
        return file_path

    html_file_path = file_path.with_suffix(".html")
    if html_file_path.is_file():
        return FileResponse(html_file_path)

    raise HTTPException(status_code=404, detail="File not found")

async def deploy_bot():
    # Create a new room
    try:
        room = await create_room()
    except HTTPException as e:
        print(f"Unable to provision room: {e.detail}")
        return False

    # Get a token for the bot
    token = await daily_helpers["rest"].get_token(room.url, MAX_SESSION_TIME)

    if not room or not token:
        print(f"Failed to get token for room: {room.url}")
        return False

    # Deploy the bot to Fly
    try:
        spawn_fly_machine(room.url, token)
        print(f"Bot deployed successfully to room: {room.url}")
    except Exception as e:
        print(f"Failed to spawn VM: {e}")
        return False

    return True

if __name__ == "__main__":
    # Check environment variables
    for env_var in REQUIRED_ENV_VARS:
        if env_var not in os.environ:
            raise Exception(f"Missing environment variable: {env_var}.")

    parser = argparse.ArgumentParser(description="MDS Bot Runner")
    parser.add_argument("--host", type=str,
                        default=os.getenv("HOST", "0.0.0.0"), help="Host address")
    parser.add_argument("--port", type=int,
                        default=os.getenv("PORT", 7860), help="Port number")
    parser.add_argument("--reload", action="store_true",
                        default=False, help="Reload code on change")
    parser.add_argument("--deploy-bot", action="store_true",
                        default=False, help="Immediately deploy a bot to Fly")
    config = parser.parse_args()

    if config.deploy_bot:
        rv = asyncio.run(deploy_bot())
        if not rv:
            sys.exit(1)
        sys.exit(0)

    try:
        uvicorn.run(
            "bot_runner:app",
            host=config.host,
            port=config.port,
            reload=config.reload
        )

    except KeyboardInterrupt:
        print("Pipecat runner shutting down...")
