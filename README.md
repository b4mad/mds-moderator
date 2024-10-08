# AI Chatbot with Pipecat

This project implements an AI chatbot using the pipecat-ai framework. The bot can join a video call, understand speech,
generate responses, and communicate using text-to-speech.

## Overview

The bot uses a pipeline architecture to process audio and video frames, transcribe speech, generate responses using a
language model, and synthesize speech. It can interact with multiple participants in a video call, greeting them when
they join and saying goodbye when they leave.

## Key Components

### Processors

The project includes two custom processors defined in [processors.py](processors.py):

1. `ConversationLogger`: This processor logs the conversation to a file. It captures both user inputs and bot responses, writing them to a JSON file for later analysis or review. Conversations are stored in the `logs` directory.

2. `ConversationProcessor`: This processor manages the conversation flow. It aggregates transcribed speech from users, formats it with timestamps and usernames, and prepares it for the language model to generate responses.

### Prompts

The [prompts.py](prompts.py) file contains the base prompt for the language model. It includes:

- `LLM_BASE_PROMPT`: A dictionary that defines the system role and content for the AI's behavior.

This setup allows for easy modification of the AI's behavior. You can change the behavior in two ways:

1. By modifying the `default_content` in the `prompts.py` file.
2. By setting the `SYSTEM_PROMPT` environment variable.

#### Using the SYSTEM_PROMPT Environment Variable

You can override the default system prompt by setting the `SYSTEM_PROMPT` environment variable before running the bot. This allows you to change the bot's behavior without modifying the code. For example:

```bash
export SYSTEM_PROMPT="You are a helpful assistant. Always respond politely and concisely."
```

If the `SYSTEM_PROMPT` environment variable is not set, the bot will use the default content defined in `prompts.py`.

## Running the Bot

To run the bot and participate in a conversation, you can use the provided Makefile:

1. To start the bot:

```bash
make bot
```

2. To join a participant from the command line:

```bash
make participant
```

3. Log into daily.co and join the video call using the provided link.

```bash
open $DAILY_SAMPLE_ROOM_URL
```

Make sure you have set up the necessary environment variables and dependencies before running these commands.

## Setup

### Dependencies

To install the dependencies, you can use `pipenv install` or `poetry install`. Do not forget to activate the virtual environment before running the bot.

## Configuration

### Sprite Folder

The bot uses sprite animations for visual feedback. You can configure the sprite folder by setting the `SPRITE_FOLDER` environment variable. By default, it uses the "parkingmeter" folder. To use a different set of sprites, set the environment variable to the name of your desired folder within the `assets` directory.

Example:

```bash
export SPRITE_FOLDER=robot
```

### Environment Variables

Use the `.env` file to set the following environment variables:

```bash
DAILY_API_KEY=
ELEVENLABS_API_KEY=
FLY_API_KEY=
FLY_APP_NAME=
DEPLOYMENT_URL=
```

## Starting a Bot

You can start a bot using a simple curl command:

```bash
curl --location --request POST 'https://$DEPLOYMENT_URL/start_bot'
```

### POST Parameters

The `/start_bot` endpoint accepts the following optional parameters:

1. `test`: Used for webhook creation requests. If present, the server will return a JSON response with `{"test": true}`.
2. `system_prompt`: Allows you to override the default system prompt for the bot. This sets the bot's behavior for the session.

Example with a custom system prompt:

```bash
curl --location --request POST 'https://$DEPLOYMENT_URL/start_bot' \
--header 'Content-Type: application/json' \
--data-raw '{
    "system_prompt": "You are a helpful assistant. Always respond politely and concisely."
}'
```

The response will include a `room_url` and a `token` that can be used to join the video call with the bot.

## S3 Bucket Upload

When the `DEBUG` environment variable is not set, the bot will upload conversation logs to an S3 bucket. This feature uses the `BucketLogger` processor, which is responsible for uploading the conversation messages as JSON files to the specified S3 bucket.

To enable S3 bucket upload:

1. Ensure that the `DEBUG` environment variable is not set.
2. Configure the following environment variables in your `.env` file:
   - `AWS_ACCESS_KEY_ID`: Your AWS access key ID
   - `AWS_SECRET_ACCESS_KEY`: Your AWS secret access key
   - `AWS_REGION`: The AWS region for your S3 bucket (e.g., "us-west-2")
   - `S3_BUCKET_NAME`: The name of your S3 bucket

The `BucketLogger` will upload each message as a separate JSON file to the specified S3 bucket. The files will be named with a 6-digit zero-padded index (e.g., "000001.json", "000002.json", etc.) and will be stored in a subdirectory based on the conversation session.

This feature allows for easy storage and retrieval of conversation logs, which can be useful for analysis, debugging, or compliance purposes.

## Notes

See the [NOTES.md](NOTES.md) file for additional information and notes on the project.
