import asyncio
import datetime
import os
import sys
from asyncio import Task
from typing import Optional

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from pipecat.frames.frames import EndFrame, TextFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response import \
    LLMAssistantResponseAggregator
from pipecat.processors.logger import FrameLogger
from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.services.daily import (DailyParams,
                                               DailyTranscriptionSettings,
                                               DailyTransport)
from pipecat.vad.silero import SileroVADAnalyzer

from processors import BucketLogger, ConversationLogger, ConversationProcessor
from prompts import get_llm_base_prompt
from runner import configure
from talking_animation import TalkingAnimation

load_dotenv(override=True)


DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")

logger.remove(0)
current_time_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
logger.add(f"./logs/{current_time_str}_trace.log", level="TRACE")
logger.add(sys.stderr, level="DEBUG")
# logger.opt(ansi=True)

# Get the system prompt from environment variable
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "You are a friendly chatbot.")


async def main(room_url: str, token: str, bot_name: str):
    logger.info(f"Bot Name: {bot_name}")
    logger.info(f"System Prompt: {SYSTEM_PROMPT}")
    talking_animation = TalkingAnimation()

    async with aiohttp.ClientSession() as session:
        transport = DailyTransport(
            room_url,
            token,
            bot_name,
            DailyParams(
                audio_out_enabled=True,
                camera_out_enabled=True,
                camera_out_width=talking_animation.sprite_width,
                camera_out_height=talking_animation.sprite_height,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
                transcription_enabled=True,
                transcription_settings=DailyTranscriptionSettings(language="de", tier="nova", model="2-general"),
            ),
        )

        tts = ElevenLabsTTSService(
            aiohttp_session=session,
            api_key=os.getenv("ELEVENLABS_API_KEY", ""),
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", ""),
            model="eleven_multilingual_v2",
        )
        llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o")

        messages = [get_llm_base_prompt(bot_name)]

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

        pipeline_components.append(talking_animation)
        pipeline_components.append(transport.output())
        assistant_response = LLMAssistantResponseAggregator(messages)
        pipeline_components.append(assistant_response)

        if DEBUG:
            conversation_logger = ConversationLogger(messages, f"./logs/conversation-{current_time_str}.log")
            frame_logger_4 = FrameLogger("FL4", "red")
            pipeline_components.append(frame_logger_4)
            pipeline_components.append(conversation_logger)
        else:
            conversation_logger = BucketLogger(
                messages,
                os.getenv("S3_BUCKET_NAME", "mds-moderator"),
                f"conversation-{current_time_str}",
            )
            pipeline_components.append(conversation_logger)

        pipeline = Pipeline(pipeline_components)

        # https://github.com/pipecat-ai/pipecat/issues/456
        #  Interruptions not working with websocket-server
        #  maybe this fixes interruptions

        task = PipelineTask(pipeline, PipelineParams(allow_interruptions=False))
        await task.queue_frame(talking_animation.quiet_frame())

        participant_count = 0
        participants_joined = False
        end_timer: Optional[Task] = None

        async def end_session_if_empty():
            logger.info("Starting 1-minute timer.")
            await asyncio.sleep(60)  # Wait for 2 minutes
            if not participants_joined:
                logger.info("No participants joined after 1 minute. Ending session.")
                await task.queue_frame(EndFrame())

        @transport.event_handler("on_participant_joined")
        async def on_participant_joined(transport, participant):
            nonlocal participant_count, participants_joined, end_timer
            participant_count += 1
            participants_joined = True
            if end_timer:
                end_timer.cancel()
            transport.capture_participant_transcription(participant["id"])
            participant_name = participant["info"]["userName"] or ""
            logger.info(f"Participant {participant_name} joined. Total participants: {participant_count}")
            conversation_processor.add_user_mapping(participant["id"], participant_name)
            await task.queue_frames(
                [TextFrame(f"Hallo {participant_name}! Ich bin {bot_name}. Willkommen in unserem Gespräch!")]
            )

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            nonlocal participant_count, participants_joined, end_timer
            participant_count -= 1
            participant_name = participant["info"]["userName"] or ""
            logger.info(f"Participant {participant_name} left. Total participants: {participant_count}")
            await task.queue_frames(
                [
                    TextFrame(
                        f"Auf Wiedersehen {participant_name}! Ich, {bot_name}, wünsche dir alles Gute und hoffe, wir sehen uns bald wieder."
                    )
                ]
            )
            if participant_count == 0:
                logger.info("No participants left.")
                participants_joined = False
                if end_timer:
                    end_timer.cancel()
                end_timer = asyncio.create_task(end_session_if_empty())

        # Start the end_session_if_empty timer when the bot joins the room
        end_timer = asyncio.create_task(end_session_if_empty())

        runner = PipelineRunner()

        await runner.run(task)
        conversation_logger.log_messages()
        logger.info("The conversation has ended. This is the final transcript:")
        logger.info(messages)
        logger.info("Bye!")


if __name__ == "__main__":
    (url, token, bot_name) = configure()
    asyncio.run(main(url, token, bot_name))
