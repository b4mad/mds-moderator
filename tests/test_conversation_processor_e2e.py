import asyncio
import os
import unittest
from unittest.mock import patch, MagicMock

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.frames.frames import TranscriptionFrame, UserStoppedSpeakingFrame, LLMMessagesFrame
from pipecat.services.openai import OpenAILLMService
from processors import ConversationProcessor

from dotenv import load_dotenv
load_dotenv(override=True)


class TestConversationProcessorE2E(unittest.IsolatedAsyncioTestCase):
    async def test_conversation_processor_with_llm(self):
        # Mock OpenAI API response
        mock_openai_response = MagicMock()
        mock_openai_response.choices = [MagicMock(message={"content": "This is a mock LLM response."})]

        # Create pipeline components
        conversation_processor = ConversationProcessor()
        llm_service = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-3.5-turbo"
        )

        # Create pipeline
        pipeline = Pipeline([
            conversation_processor,
            llm_service,
        ])

        # Create pipeline task
        task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))

        # Sample conversation data
        conversation_data = [
            {"user_id": "user1", "text": "Hello, how are you?", "timestamp": "2023-07-13T10:00:00"},
            {"user_id": "user2", "text": "I'm doing well, thanks!", "timestamp": "2023-07-13T10:00:05"},
        ]

        # Process the frames
        for entry in conversation_data:
            frame = TranscriptionFrame(entry["text"], entry["user_id"], entry["timestamp"])
            await task.queue_frame(frame)

        # Send UserStoppedSpeakingFrame to trigger LLM processing
        await task.queue_frame(UserStoppedSpeakingFrame())

        # Run the pipeline
        # with patch('openai.ChatCompletion.acreate', return_value=mock_openai_response):
        results = []
        async for frame in task:
            results.append(frame)

        # Check the results
        self.assertTrue(any(isinstance(frame, LLMMessagesFrame) for frame in results))
        llm_messages_frame = next(frame for frame in results if isinstance(frame, LLMMessagesFrame))

        # Check the content of LLMMessagesFrame
        self.assertEqual(len(llm_messages_frame.messages), 1)
        self.assertEqual(llm_messages_frame.messages[0]['role'], 'user')
        expected_content = (
            "2023-07-13T10:00:00 - user1: Hello, how are you?\n"
            "2023-07-13T10:00:05 - user2: I'm doing well, thanks!"
        )
        self.assertEqual(llm_messages_frame.messages[0]['content'], expected_content)


if __name__ == '__main__':
    unittest.main()
