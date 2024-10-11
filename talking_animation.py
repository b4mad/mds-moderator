import os

from loguru import logger
from PIL import Image

from pipecat.frames.frames import (Frame, OutputImageRawFrame, SpriteFrame,
                                   TTSAudioRawFrame, TTSStoppedFrame)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

sprites = []

script_dir = os.path.dirname(__file__)
assets_dir = os.path.join(script_dir, "assets")

# Find the first subfolder in the assets directory
subfolder = os.getenv("SPRITE_FOLDER", "parkingmeter")
sprite_dir = os.path.join(assets_dir, subfolder)
logger.info(f"Using sprite folder: {sprite_dir}")

# Get all PNG files in the subfolder
png_files = sorted([f for f in os.listdir(sprite_dir) if f.lower().endswith(".png")])

for png_file in png_files:
    full_path = os.path.join(sprite_dir, png_file)
    # logger.info(f"Loading sprite: {full_path}")
    with Image.open(full_path) as img:
        sprites.append(OutputImageRawFrame(image=img.tobytes(), size=img.size, format=img.format))

# Add reversed sprites to create a loop
sprites.extend(sprites[::-1])

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
        self.sprite_width = sprites[0].size[0]
        self.sprite_height = sprites[0].size[1]

    def quiet_frame(self):
        return quiet_frame

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TTSAudioRawFrame):
            if not self._is_talking:
                await self.push_frame(talking_frame)
                self._is_talking = True
        elif isinstance(frame, TTSStoppedFrame):
            await self.push_frame(quiet_frame)
            self._is_talking = False

        await self.push_frame(frame)
