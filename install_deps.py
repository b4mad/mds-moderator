import torch

# Download (cache) the Silero VAD model
torch.hub.load(repo_or_dir="snakers4/silero-vad:v5.1", model="silero_vad", force_reload=True)
