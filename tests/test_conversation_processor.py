import unittest

from pipecat.frames.frames import TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection

from processors import ConversationProcessor


class TestConversationProcessor(unittest.IsolatedAsyncioTestCase):
    async def test_conversation_processor(self):
        processor = ConversationProcessor()

        # Create an array of dicts with sample conversation data
        conversation_data = [
            {"user_id": "user1", "text": "Hello, how are you?", "timestamp": "2023-07-13T10:00:00"},
            {"user_id": "user2", "text": "I'm doing well, thanks!", "timestamp": "2023-07-13T10:00:05"},
            {"user_id": "user1", "text": "That's great to hear!", "timestamp": "2023-07-13T10:00:10"},
        ]

        # Process the frames
        for entry in conversation_data:
            frame = TranscriptionFrame(entry["text"], entry["user_id"], entry["timestamp"])
            await processor.process_frame(frame, FrameDirection.DOWNSTREAM)

        # Check the conversation history
        history = processor.get_conversation_history()
        self.assertEqual(len(history), len(conversation_data))

        # Check the contents of the conversation history
        for i, entry in enumerate(conversation_data):
            self.assertEqual(history[i]["user_id"], entry["user_id"])
            self.assertEqual(history[i]["text"], entry["text"])
            self.assertEqual(history[i]["timestamp"], entry["timestamp"])

        # Test get_last_n_entries method
        last_two = processor.get_last_n_entries(2)
        self.assertEqual(len(last_two), 2)
        self.assertEqual(last_two[0]["text"], conversation_data[-2]["text"])
        self.assertEqual(last_two[1]["text"], conversation_data[-1]["text"])


if __name__ == "__main__":
    unittest.main()
