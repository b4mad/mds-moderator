import asyncio
import os
import random
import sys

import aiohttp
from dotenv import load_dotenv
from loguru import logger

from pipecat.frames.frames import LLMFullResponseEndFrame, TextFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.logger import FrameLogger
from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.transports.services.daily import (DailyParams,
                                               DailyTranscriptionSettings,
                                               DailyTransport)
from runner import configure

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

# List of German names
german_names = [
    "Anna",
    "Max",
    "Sophie",
    "Felix",
    "Emma",
    "Paul",
    "Lena",
    "Lukas",
    "Marie",
    "Jonas",
    "Laura",
    "Tim",
    "Julia",
    "David",
    "Lisa",
    "Niklas",
]


async def main(room_url):
    async with aiohttp.ClientSession() as session:
        # transport = DailyTransport(
        #     room_url, None, "Say One Thing", DailyParams(audio_out_enabled=True))

        transport = DailyTransport(
            room_url,
            token,
            random.choice(german_names),
            DailyParams(
                audio_out_enabled=True,
                transcription_enabled=True,
                transcription_settings=DailyTranscriptionSettings(language="de", tier="nova", model="2-general"),
            ),
        )

        tts = ElevenLabsTTSService(
            aiohttp_session=session,
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
            model="eleven_multilingual_v2",
        )

        runner = PipelineRunner()

        frame_logger_1 = FrameLogger("FL1", "green")
        frame_logger_2 = FrameLogger("FL2", "red")

        task = PipelineTask(Pipeline([tts, frame_logger_1, transport.output(), frame_logger_2]))

        # Register an event handler so we can play the audio when the
        # participant joins.
        @transport.event_handler("on_participant_joined")
        async def on_participant_joined(transport, participant):
            participant_name = participant["info"]["userName"] or ""
            transport.capture_participant_transcription(participant["id"])
            await asyncio.sleep(2)
            await task.queue_frames([TextFrame(f"Hallo, wie geht es {participant_name}?")])
            await task.queue_frame(LLMFullResponseEndFrame())

            # sleep for a bit to give the participant time to hear the audio
            # await task.queue_frames([TextFrame(f"Wer bist du?")])
            # await task.queue_frames([EndFrame()])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            participant_name = participant["info"]["userName"] or ""
            await task.queue_frames([TextFrame(f"Auf wiedersehen {participant_name}")])
            await task.queue_frame(LLMFullResponseEndFrame())
            logger.info(f"Participant {participant_name} left")

        await runner.run(task)


if __name__ == "__main__":
    (url, token, bot_name) = configure()
    asyncio.run(main(url))
