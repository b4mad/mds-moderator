import unittest

from pipecat.frames.frames import TranscriptionFrame, UserStartedSpeakingFrame
from pipecat.processors.frame_processor import FrameDirection

from processors import ConversationProcessor


class TestConversationProcessor(unittest.IsolatedAsyncioTestCase):
    async def test_conversation_processor(self):
        processor = ConversationProcessor()

        # Create an array of dicts with sample conversation data
        conversation_data = [
            {
                "user_id": "user1",
                "text": "Hello, how are you?",
                "timestamp": "2023-07-13T10:00:00.000000Z",
            },
            {
                "user_id": "user2",
                "text": "I'm doing well, thanks!",
                "timestamp": "2023-07-13T10:00:05.000000Z",
            },
            {
                "user_id": "user1",
                "text": "That's great to hear!",
                "timestamp": "2023-07-13T10:00:10.000000Z",
            },
        ]

        # Process the frames
        # processor._aggregating = True
        await processor.process_frame(UserStartedSpeakingFrame(), FrameDirection.DOWNSTREAM)
        for entry in conversation_data:
            frame = TranscriptionFrame(entry["text"], entry["user_id"], entry["timestamp"])
            await processor.process_frame(frame, FrameDirection.DOWNSTREAM)

        # Check the conversation history
        history = processor._aggregation_detailed
        self.assertEqual(len(history), len(conversation_data))

        # Check the contents of the conversation history
        for i, entry in enumerate(conversation_data):
            self.assertEqual(history[i]["user_id"], entry["user_id"])
            self.assertEqual(history[i]["text"], entry["text"])
            # Convert datetime to ISO 8601 string
            timestamp_str = history[i]["timestamp"].isoformat(timespec="microseconds") + "Z"
            self.assertEqual(timestamp_str, entry["timestamp"])


if __name__ == "__main__":
    unittest.main()
