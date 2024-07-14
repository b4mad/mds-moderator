from datetime import datetime
from typing import List


from pipecat.frames.frames import (
    Frame,
    UserStoppedSpeakingFrame,
    TranscriptionFrame,
    InterimTranscriptionFrame,
    UserStartedSpeakingFrame
)
from pipecat.processors.aggregators.llm_response import LLMResponseAggregator

from loguru import logger

class ConversationProcessor(LLMResponseAggregator):
    """
    This frame processor keeps track of a conversation by capturing TranscriptionFrames
    and aggregating the text along with timestamps and user IDs in a conversation array.

    Attributes:
        conversation (list): A list of dictionaries containing conversation entries.
        user_mapping (dict): A dictionary mapping user_ids to participant names.
    """

    def __init__(self, messages: List[dict] = []):
        super().__init__(
            messages=messages,
            role="user",
            start_frame=UserStartedSpeakingFrame,
            end_frame=UserStoppedSpeakingFrame,
            accumulator_frame=TranscriptionFrame,
            interim_accumulator_frame=InterimTranscriptionFrame
        )
        self._aggregation_detailed = []
        self.user_mapping = {}

    def add_user_mapping(self, user_id: str, participant_name: str):
        """
        Stores a mapping between user_id and participant_name.

        Args:
            user_id (str): The user's ID.
            participant_name (str): The participant's name.
        """
        self.user_mapping[user_id] = participant_name

    # def __init__(self, messages: List[dict] = []):
    #     super().__init__()
    #     self._messages = messages
    #     self._aggregation = []
    #     self._role = "user"

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, self._accumulator_frame):
            if self._aggregating:
                # timestamp has the format "2024-07-14T10:18:19.766929Z"
                # parse it into a datetime object
                timestamp = datetime.fromisoformat(frame.timestamp[:-1])
                entry = {
                    "user_id": frame.user_id,
                    "text": frame.text,
                    "timestamp": timestamp
                }
                self._aggregation_detailed.append(entry)

    # async def process_frame(self, frame: Frame, direction: FrameDirection):
    #     await super().process_frame(frame, direction)
    #     logger.debug(f"ConversationProcessor: {frame}")

    #     if isinstance(frame, UserStoppedSpeakingFrame):
    #         # Send an app message to the UI
    #         # await self.push_frame(DailyTransportMessageFrame(CUE_ASSISTANT_TURN))
    #         # await self.push_frame(DailyTransportMessageFrame(CUE_ASSISTANT_TURN))
    #         await self._push_aggregation()
    #     elif isinstance(frame, TranscriptionFrame):
    #         entry = {
    #             "user_id": frame.user_id,
    #             "text": frame.text,
    #             "timestamp": frame.timestamp
    #         }
    #         self._aggregation.append(entry)
    #     elif isinstance(frame, LLMMessagesFrame):
    #         # llm response
    #         logger.debug(f"LLM response: {frame.messages}")
    #     else:
    #         # Pass the frame along unchanged
    #         await self.push_frame(frame, direction)

    async def _push_aggregation(self):
        self._aggregation = self.format_aggregation()
        self._aggregation_detailed = []
        await super()._push_aggregation()

    # async def _push_aggregation(self):
    #     if len(self._aggregation) > 0:

    #         self._messages.append({"role": self._role, "content": self.format_aggregation()})

    #         # Reset the aggregation. Reset it before pushing it down, otherwise
    #         # if the tasks gets cancelled we won't be able to clear things up.
    #         self._aggregation = []

    #         frame = LLMMessagesFrame(self._messages)
    #         logger.debug(f"Pushing LLMMessagesFrame: {self._messages}")
    #         await self.push_frame(frame)

    def format_aggregation(self):
        """
        Formats the aggregation into a multi-line string.
        """
        formatted = []
        for entry in self._aggregation_detailed:
            user_id = entry['user_id']
            username = self.user_mapping.get(user_id, user_id)  # Use username if available, otherwise use user_id
            timestamp = entry['timestamp'].strftime("%H:%M:%S")
            formatted.append(f"{timestamp} | {username} | {entry['text']}")
        return "\n".join(formatted)

    def get_conversation_history(self):
        """
        Returns the entire conversation history.
        """
        return self._messages

    def get_last_n_entries(self, n):
        """
        Returns the last n entries of the conversation.
        """
        return self._messages[-n:]
