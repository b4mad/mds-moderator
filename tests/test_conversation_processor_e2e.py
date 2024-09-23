import os
import unittest

from dotenv import load_dotenv
from pipecat.frames.frames import (
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    StopTaskFrame,
    TextFrame,
    TranscriptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response import LLMAssistantResponseAggregator
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.processors.logger import FrameLogger
from pipecat.services.openai import OpenAILLMService

from processors import ConversationProcessor

load_dotenv(override=True)


class TestConversationProcessorE2E(unittest.IsolatedAsyncioTestCase):
    class TokenCollector(FrameProcessor):
        def __init__(self, name):
            self.name = name
            self.tokens: list[str] = []
            self.start_collecting = False

        def __str__(self):
            return self.name

        async def process_frame(self, frame, direction):
            await super().process_frame(frame, direction)

            if isinstance(frame, LLMFullResponseStartFrame):
                self.start_collecting = True
            elif isinstance(frame, TextFrame) and self.start_collecting:
                self.tokens.append(frame.text)
            elif isinstance(frame, LLMFullResponseEndFrame):
                self.start_collecting = False

            await self.push_frame(frame, direction)

    async def test_conversation_processor_with_llm(self):
        conversation_processor = ConversationProcessor()
        llm_service = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-3.5-turbo")

        # F841 token_collector = self.TokenCollector("token_collector")
        messages = [
            {
                "role": "system",
                "content": "You are a helpful LLM in a WebRTC call. Your goal is to demonstrate your capabilities in a succinct way."
                " Your output will be converted to audio so don't include special characters in your answers. Respond to what the user"
                " said in a creative and helpful way.",
            },
        ]
        # F841 tma_in = LLMUserResponseAggregator(messages)
        tma_out = LLMAssistantResponseAggregator(messages)
        frame_logger = FrameLogger("FL")
        # context = OpenAILLMContext()
        # llm_context_aggregator = LLMContextAggregator(context=context)

        pipeline = Pipeline(
            [
                # tma_in,
                frame_logger,
                conversation_processor,
                frame_logger,
                llm_service,
                frame_logger,
                # token_collector,
                # llm_context_aggregator,
                tma_out,
                frame_logger,
                conversation_processor,
                frame_logger,
            ]
        )

        task = PipelineTask(pipeline, PipelineParams(allow_interruptions=False))
        await task.queue_frames(
            [
                UserStartedSpeakingFrame(),
                TranscriptionFrame(
                    text="Hello, how are you?",
                    user_id="user1",
                    timestamp="2023-07-13T10:00:00",
                ),
                UserStoppedSpeakingFrame(),
                UserStartedSpeakingFrame(),
                TranscriptionFrame(
                    text="I'm doing well, thanks!",
                    user_id="user2",
                    timestamp="2023-07-13T10:00:05",
                ),
                UserStoppedSpeakingFrame(),
                StopTaskFrame(),
            ]
        )

        runner = PipelineRunner()
        await runner.run(task)

        # Check that we have an LLM response
        # self.assertTrue(len(token_collector.tokens) > 0)

        # Check the content of LLMMessagesFrame
        print(messages)
        print(tma_out._messages)

        # llm_messages_frame = next(frame for frame in tma_out.frames if isinstance(frame, LLMMessagesFrame))
        # self.assertEqual(len(llm_messages_frame.messages), 2)  # User message and assistant response
        # self.assertEqual(llm_messages_frame.messages[0]['role'], 'user')
        # expected_content = (
        #     "2023-07-13T10:00:00 - user1: Hello, how are you?\n"
        #     "2023-07-13T10:00:05 - user2: I'm doing well, thanks!"
        # )
        # self.assertEqual(llm_messages_frame.messages[0]['content'], expected_content)
        # self.assertEqual(llm_messages_frame.messages[1]['role'], 'assistant')
        # self.assertEqual(llm_messages_frame.messages[1]['content'], ''.join(token_collector.tokens))


if __name__ == "__main__":
    unittest.main()
