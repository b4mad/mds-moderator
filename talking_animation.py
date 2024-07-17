import os
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
from PIL import Image
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


sprites = []

script_dir = os.path.dirname(__file__)

for i in range(1, 29):
    # Build the full path to the image file
    full_path = os.path.join(script_dir, f"assets/parkingmeter{i:03}.png")
    # Get the filename without the extension to use as the dictionary key
    # Open the image and convert it to bytes
    with Image.open(full_path) as img:
        sprites.append(ImageRawFrame(image=img.tobytes(), size=img.size, format=img.format))

flipped = sprites[::-1]
sprites.extend(flipped)

# When the bot isn't talking, show a static image of the cat listening
quiet_frame = sprites[0]
talking_frame = SpriteFrame(images=sprites)


class TalkingAnimation(FrameProcessor):
    """
    This class starts a talking animation when it receives an first AudioFrame,
    and then returns to a "quiet" sprite when it sees a TTSStoppedFrame.
    """

    def __init__(self):
        super().__init__()
        self._is_talking = False

    def quiet_frame(self):
        return quiet_frame

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, AudioRawFrame):
            if not self._is_talking:
                await self.push_frame(talking_frame)
                self._is_talking = True
        elif isinstance(frame, TTSStoppedFrame):
            await self.push_frame(quiet_frame)
            self._is_talking = False

        await self.push_frame(frame)
