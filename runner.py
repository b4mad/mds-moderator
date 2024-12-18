import argparse
import os
import time
import urllib

import requests


def configure():
    parser = argparse.ArgumentParser(description="MDS Bot")
    parser.add_argument("-u", "--url", type=str, required=False, help="URL of the Daily room to join")
    parser.add_argument(
        "-k",
        "--apikey",
        type=str,
        required=False,
        help="Daily API Key (needed to create an owner token for the room)",
    )
    parser.add_argument(
        "-t",
        "--token",
        type=str,
        required=False,
        help="Room token (needed to join the room as a participant)",
    )
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        required=False,
        help="Name of the bot client",
    )

    args, unknown = parser.parse_known_args()

    url = args.url or os.getenv("DAILY_SAMPLE_ROOM_URL")
    key = args.apikey or os.getenv("DAILY_API_KEY")
    name = args.name or os.getenv("BOT_NAME", "Chatbot")

    if not url:
        raise Exception(
            "No Daily room specified. use the -u/--url option from the command line,"
            " or set DAILY_SAMPLE_ROOM_URL in your environment to specify a Daily room URL."
        )

    if not key:
        raise Exception(
            "No Daily API key specified. use the -k/--apikey option from the command line,"
            " or set DAILY_API_KEY in your environment to specify a Daily API key, available"
            " from https://dashboard.daily.co/developers."
        )

    # Create a meeting token for the given room with an expiration 1 hour in
    # the future.
    room_name: str = urllib.parse.urlparse(url).path[1:]
    expiration: float = time.time() + 60 * 60

    if not args.token:
        res: requests.Response = requests.post(
            "https://api.daily.co/v1/meeting-tokens",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "properties": {
                    "room_name": room_name,
                    "is_owner": True,
                    "exp": expiration,
                }
            },
        )

        if res.status_code != 200:
            raise Exception(f"Failed to create meeting token: {res.status_code} {res.text}")

        token: str = res.json()["token"]
    else:
        token = args.token

    return (url, token, name)
