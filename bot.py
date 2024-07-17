import argparse
import asyncio
import datetime
import aiohttp
import os
import sys
from typing import Optional

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response import LLMAssistantResponseAggregator, LLMUserResponseAggregator
from pipecat.frames.frames import (
    TextFrame,
)
from pipecat.processors.logger import FrameLogger
from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.services.daily import DailyParams, DailyTranscriptionSettings, DailyTransport
from pipecat.vad.silero import SileroVADAnalyzer

from runner import configure

from loguru import logger

from dotenv import load_dotenv
load_dotenv(override=True)

from prompts import LLM_BASE_PROMPT
from processors import ConversationProcessor, ConversationLogger
from talking_animation import TalkingAnimation

DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")

logger.remove(0)
current_time_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
logger.add(f"./logs/{current_time_str}_trace.log", level="TRACE")
logger.add(sys.stderr, level="DEBUG")
# logger.opt(ansi=True)

async def main(room_url: str, token: str):
    async with aiohttp.ClientSession() as session:
        transport = DailyTransport(
            room_url,
            token,
            "Chatbot",
            DailyParams(
                audio_out_enabled=True,
                camera_out_enabled=True,
                camera_out_width=1024, #1024
                camera_out_height=576, #576
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(version="v5.1"),
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
            api_key=os.getenv("ELEVENLABS_API_KEY", ""),
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", ""),
            model="eleven_multilingual_v2"
        )
        llm = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o"
        )

        messages = [LLM_BASE_PROMPT]

        # user_response = LLMUserResponseAggregator(messages)
        # user_response = UserResponseAggregator()

        pipeline_components = []
        pipeline_components.append(transport.input())

        if DEBUG:
            frame_logger_1 = FrameLogger("FL1", "green")
            pipeline_components.append(frame_logger_1)

        conversation_processor = ConversationProcessor(messages)
        pipeline_components.append(conversation_processor)
        pipeline_components.append(llm)

        if DEBUG:
            frame_logger_2 = FrameLogger("FL2", "yellow")
            pipeline_components.append(frame_logger_2)

        pipeline_components.append(tts)

        if DEBUG:
            frame_logger_3 = FrameLogger("FL3", "yellow")
            pipeline_components.append(frame_logger_3)

        talking_animation = TalkingAnimation()
        pipeline_components.append(talking_animation)
        pipeline_components.append(transport.output())
        assistant_response = LLMAssistantResponseAggregator(messages)
        pipeline_components.append(assistant_response)

        if DEBUG:
            frame_logger_4 = FrameLogger("FL4", "red")
            pipeline_components.append(frame_logger_4)
            conversation_logger = ConversationLogger(messages, f"./logs/conversation-{current_time_str}.log")
            pipeline_components.append(conversation_logger)

        pipeline = Pipeline(pipeline_components)

        task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))
        await task.queue_frame(talking_animation.quiet_frame())

        # @transport.event_handler("on_first_participant_joined")
        # async def on_first_participant_joined(transport, participant):
        #     transport.capture_participant_transcription(participant["id"])
        #     participant_name = participant["info"]["userName"] or ''
        #     logger.info(f"First participant {participant_name} joined")
        #     # await task.queue_frames([LLMMessagesFrame(messages)])
        #     # await task.queue_frames([TextFrame(f"Hallo {participant_name}!")])

        @transport.event_handler("on_participant_joined")
        async def on_participant_joined(transport, participant):
            transport.capture_participant_transcription(participant["id"])
            participant_name = participant["info"]["userName"] or ''
            logger.info(f"Participant {participant_name} joined")
            conversation_processor.add_user_mapping(participant["id"], participant_name)
            await task.queue_frames([TextFrame(f"Hallo {participant_name}!")])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            participant_name = participant["info"]["userName"] or ''
            logger.info(f"Participant {participant_name} left")
            await task.queue_frames([TextFrame(f"Auf wiedersehen {participant_name}!")])

        runner = PipelineRunner()

        await runner.run(task)
        conversation_logger.log_messages()
        print(messages)


if __name__ == "__main__":
    (url, token) = configure()
    asyncio.run(main(url, token))
