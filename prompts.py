import os

default_content = "You are a helpful assistant. Always respond politely and concisely."

LLM_BASE_PROMPT = {
    "role": "system",
    "content": os.getenv("SYSTEM_PROMPT", default_content)
}
