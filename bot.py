import asyncio
import aiohttp
import os
import sys

from PIL import Image

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response import LLMAssistantResponseAggregator, LLMUserResponseAggregator
from pipecat.processors.aggregators.user_response import UserResponseAggregator
from pipecat.frames.frames import (
    AudioRawFrame,
    ImageRawFrame,
    SpriteFrame,
    Frame,
    LLMMessagesFrame,
    TTSStoppedFrame,
    TextFrame,
    EndFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.logger import FrameLogger
from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.services.daily import DailyParams, DailyTranscriptionSettings, DailyTransport
from pipecat.vad.silero import SileroVADAnalyzer

from runner import configure

from loguru import logger

from dotenv import load_dotenv
load_dotenv(override=True)

from prompts import LLM_BASE_PROMPT, LLM_INTRO_PROMPT, CUE_USER_TURN
from utils.helpers import load_images, load_sounds
from processors import ConversationProcessor
from talking_animation import TalkingAnimation

logger.remove(0)
# logger.add(sys.stderr, level="TRACE")
logger.add(sys.stderr, level="DEBUG")


async def main(room_url: str, token):
    async with aiohttp.ClientSession() as session:
        transport = DailyTransport(
            room_url,
            token,
            "Chatbot",
            DailyParams(
                audio_out_enabled=True,
                camera_out_enabled=True,
                camera_out_width=1024,
                camera_out_height=576,
                vad_enabled=True,
                # vad_analyzer=SileroVADAnalyzer(),
                transcription_enabled=True,
                transcription_settings=DailyTranscriptionSettings(
                    language="de",
                    tier="nova",
                    model="2-general"
                )
            )
        )

        tts = ElevenLabsTTSService(
            aiohttp_session=session,
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            voice_id="w2qZgZJbxOuKVruWuVU1",
        )
        llm_service = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o"
        )

        messages = [
            {
                "role": "system",
                "content": "Du hörst einfach nur zu.",
            },
        ]
        message_history = [LLM_BASE_PROMPT]


        user_response = LLMUserResponseAggregator(message_history)
        # user_response = UserResponseAggregator()
        assistant_response = LLMAssistantResponseAggregator(message_history)
        talking_animation = TalkingAnimation()
        conversation_processor = ConversationProcessor(message_history)
        frame_logger = FrameLogger("FL: Main", "green")
        frame_logger_transport = FrameLogger("FL: Transport", "yellow")
        frame_logger_conversation = FrameLogger("FL: Conversation", "yellow")
        frame_logger_end = FrameLogger("FL: End", "red")


        pipeline = Pipeline([
            transport.input(),
            frame_logger_transport,
            conversation_processor,
            frame_logger_conversation,
            llm_service,
            # user_response,
            tts,
            assistant_response,
            # talking_animation,
            frame_logger,
            transport.output(),
            frame_logger_end,
        ])

        task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))
        await task.queue_frame(talking_animation.quiet_frame())

        # @transport.event_handler("on_first_participant_joined")
        # async def on_first_participant_joined(transport, participant):
        #     transport.capture_participant_transcription(participant["id"])
        #     participant_name = participant["info"]["userName"] or ''
        #     logger.info(f"First participant {participant_name} joined")
        #     # await task.queue_frames([TextFrame(f"Hallo {participant_name}!")])

        @transport.event_handler("on_participant_joined")
        async def on_participant_joined(transport, participant):
            transport.capture_participant_transcription(participant["id"])
            participant_name = participant["info"]["userName"] or ''
            logger.info(f"Participant {participant_name} joined")

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            participant_name = participant["info"]["userName"] or ''
            logger.info(f"Participant {participant_name} left")

        runner = PipelineRunner()

        await runner.run(task)
        print(message_history)


if __name__ == "__main__":
    (url, token) = configure()
    asyncio.run(main(url, token))
