import os
import argparse
import subprocess
import sys
import requests
from typing import Optional

from pipecat.transports.services.helpers.daily_rest import DailyRESTHelper, DailyRoomObject, DailyRoomProperties, DailyRoomParams

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from dotenv import load_dotenv
load_dotenv(override=True)


# ------------ Configuration ------------ #

MAX_SESSION_TIME = 5 * 60  # 5 minutes
REQUIRED_ENV_VARS = [
    'DAILY_API_KEY',
    'OPENAI_API_KEY',
    'ELEVENLABS_API_KEY',
    'ELEVENLABS_VOICE_ID',
    'FLY_API_KEY',
    'FLY_APP_NAME',]

FLY_API_HOST = os.getenv("FLY_API_HOST", "https://api.machines.dev/v1")
FLY_APP_NAME = os.getenv("FLY_APP_NAME", "mds-moderator")
FLY_API_KEY = os.getenv("FLY_API_KEY", "")
FLY_HEADERS = {
    'Authorization': f"Bearer {FLY_API_KEY}",
    'Content-Type': 'application/json'
}

daily_rest_helper = DailyRESTHelper(
    os.getenv("DAILY_API_KEY", ""),
    os.getenv("DAILY_API_URL", 'https://api.daily.co/v1'))


def create_room() -> DailyRoomObject:
    params = DailyRoomParams(
        properties=DailyRoomProperties()
    )
    try:
        room: DailyRoomObject = daily_rest_helper.create_room(params=params)
        return room
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to provision room {e}")


# ----------------- API ----------------- #

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

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
    try:
        data = await request.json()
        # Is this a webhook creation request?
        if "test" in data:
            return JSONResponse({"test": True})
        system_prompt = data.get("system_prompt")
        sprite_folder = data.get("sprite_folder")
    except Exception as e:
        system_prompt = None
        sprite_folder = None

    room = create_room()
    # Give the agent a token to join the session
    token = daily_rest_helper.get_token(room.url, MAX_SESSION_TIME)

    if not room or not token:
        raise HTTPException(
            status_code=500, detail=f"Failed to get token for room: {room.url}")

    # Launch a new fly.io machine, or run as a shell process (not recommended)
    run_as_process = os.getenv("RUN_AS_PROCESS", False)

    if run_as_process:
        try:
            env = os.environ.copy()
            if system_prompt:
                env["SYSTEM_PROMPT"] = system_prompt
            subprocess.Popen(
                [f"python3 -m bot -u {room.url} -t {token}"],
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
    user_token = daily_rest_helper.get_token(room.url, MAX_SESSION_TIME)

    return JSONResponse({
        "room_url": room.url,
        "token": user_token,
    })

def deploy_bot():
    # Create a new room
    try:
        room = create_room()
    except HTTPException as e:
        print(f"Unable to provision room: {e.detail}")
        return False

    # Get a token for the bot
    token = daily_rest_helper.get_token(room.url, MAX_SESSION_TIME)

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

    parser = argparse.ArgumentParser(description="Pipecat Bot Runner")
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
        rv = deploy_bot()
        if not rv:
            sys.exit(1)
        sys.exit(0)

    try:
        import uvicorn

        uvicorn.run(
            "bot_runner:app",
            host=config.host,
            port=config.port,
            reload=config.reload
        )

    except KeyboardInterrupt:
        print("Pipecat runner shutting down...")
