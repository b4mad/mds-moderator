import os

def get_llm_base_prompt(bot_name: str):
    default_content = """You are a helpful assistant. Always respond politely and concisely."""
    user_format = """You are participating in a conversation with multiple users.
User input will be formatted as follows:

timestamp | username | message_text

For example:
10:30:15 | Alice | Hello, how are you?
10:30:45 | Bob | I'm doing great, thanks!
10:31:00 | Alice | Glad to hear that!

The assistant's responses should not follow this format. They should be standalone messages.
"""

    system_prompt = os.getenv("SYSTEM_PROMPT", default_content)
    system_prompt = f"""{user_format}

{system_prompt}

You are an AI assistant named "{bot_name}". When users address you, they will use this name."""

    return {
        "role": "system",
        "content": system_prompt
    }
