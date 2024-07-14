import asyncio
import datetime
from typing import Optional
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
    BotSpeakingFrame
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
current_time_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
logger.add(f"./logs/{current_time_str}_trace.log", level="TRACE")
logger.add(sys.stderr, level="DEBUG")
# logger.opt(ansi=True)

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
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            voice_id=os.getenv("ELEVENLABS_VOICE_ID"),
            model="eleven_multilingual_v2"
        )
        llm = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o"
        )

        # messages = [
        #     {
        #         "role": "system",
        #         "content": "Du hörst einfach nur zu.",
        #     },
        # ]
        messages = [LLM_BASE_PROMPT]


        # class FrameLogger(FrameProcessor):
        #     def __init__(self, prefix="Frame", color: Optional[str] = None):
        #         super().__init__()
        #         self._prefix = prefix
        #         self._color = color

        #     async def process_frame(self, frame: Frame, direction: FrameDirection):
        #         dir = "<" if direction is FrameDirection.UPSTREAM else ">"
        #         msg = f"{dir} {self._prefix}: {frame}"
        #         if self._color:
        #             msg = f"<{self._color}>{msg}</>"

        #         do_logging = True
        #         if isinstance(frame, AudioRawFrame):
        #             do_logging = False
        #         if isinstance(frame, BotSpeakingFrame):
        #             do_logging = False

        #         if do_logging:
        #             logger.debug(msg)

        #         await self.push_frame(frame, direction)

        user_response = LLMUserResponseAggregator(messages)
        # user_response = UserResponseAggregator()
        assistant_response = LLMAssistantResponseAggregator(messages)
        talking_animation = TalkingAnimation()
        conversation_processor = ConversationProcessor(messages)
        frame_logger_1 = FrameLogger("FL1", "green")
        frame_logger_2 = FrameLogger("FL2", "yellow")
        frame_logger_3 = FrameLogger("FL3", "yellow")
        frame_logger_4 = FrameLogger("FL4", "red")


        # pipeline = Pipeline([
        #     transport.input(),
        #     frame_logger_transport,
        #     conversation_processor,
        #     frame_logger_conversation,
        #     llm,
        #     # user_response,
        #     tts,
        #     assistant_response,
        #     # talking_animation,
        #     frame_logger,
        #     transport.output(),
        #     frame_logger_end,
        # ])

        pipeline = Pipeline([
            transport.input(),
            user_response,
            frame_logger_1,
            llm,
            frame_logger_2,
            tts,
            frame_logger_3,
            talking_animation,
            transport.output(),
            assistant_response,
            frame_logger_4,
        ])

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
            await task.queue_frames([TextFrame(f"Chatbot welcomes {participant_name}!")])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            participant_name = participant["info"]["userName"] or ''
            logger.info(f"Participant {participant_name} left")

        runner = PipelineRunner()

        await runner.run(task)
        print(messages)


if __name__ == "__main__":
    (url, token) = configure()
    asyncio.run(main(url, token))
