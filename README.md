# AI Chatbot with Pipecat

This project implements an AI chatbot using the pipecat-ai framework. The bot can join a video call, understand speech, generate responses, and communicate using text-to-speech.

## Overview

The bot uses a pipeline architecture to process audio and video frames, transcribe speech, generate responses using a language model, and synthesize speech. It can interact with multiple participants in a video call, greeting them when they join and saying goodbye when they leave.

## Key Components

### Processors

The project includes two custom processors defined in [processors.py](processors.py):

1. `ConversationLogger`: This processor logs the conversation to a file. It captures both user inputs and bot responses, writing them to a JSON file for later analysis or review. Conversations are stored in the `logs` directory.

2. `ConversationProcessor`: This processor manages the conversation flow. It aggregates transcribed speech from users, formats it with timestamps and usernames, and prepares it for the language model to generate responses.

### Prompts

The [prompts.py](prompts.py) file contains the base prompt for the language model. Currently, it includes:

- `LLM_BASE_PROMPT`: A dictionary that defines the system role and content for the AI's behavior.

This setup allows for easy modification of the AI's behavior by changing the prompt in this file.

## Running the Bot

To run the bot and participate in a conversation, you can use the provided Makefile:

1. To start the bot:
   ```
   make bot
   ```

2. To join a participant from the command line:
   ```
   make participant
   ```

3. Log into daily.co and join the video call using the provided link.
   ```
   open $DAILY_SAMPLE_ROOM_URL
   ```

Make sure you have set up the necessary environment variables and dependencies before running these commands.

## Setup

```bash
pipenv install
```

## Configuration

### Sprite Folder

The bot uses sprite animations for visual feedback. You can configure the sprite folder by setting the `SPRITE_FOLDER` environment variable. By default, it uses the "parkingmeter" folder. To use a different set of sprites, set the environment variable to the name of your desired folder within the `assets` directory.

Example:
```
export SPRITE_FOLDER=robot
```

## Notes

* TTS: TextFrames have to end with punctuation, otherwise TTS will not kick in
* Don't add a processor twice to a pipeline
