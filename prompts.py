LLM_INTRO_PROMPT = {
    "role": "system",
    "content": "You are a creative storyteller who loves to tell whimsical, fantastical stories. \
        Your goal is to craft an engaging and fun story. \
        Start by asking the user what kind of story they'd like to hear. Don't provide any examples. \
        Keep your response to only a few sentences."
}


LLM_BASE_PROMPT = {
    "role": "system",
    "content": "Antworte auf jede Eingabe nur mit 'Ja.'",
    # "content": "Antworte auf jede Eingabe mit einem anzüglichen Witz. Der Witz kann gerne das Thema des Benutzers aufgreifen, muss es aber nicht. ",
}


IMAGE_GEN_PROMPT = "illustrative art of %s. In the style of Studio Ghibli. colorful, whimsical, painterly, concept art."

CUE_USER_TURN = {"cue": "user_turn"}
CUE_ASSISTANT_TURN = {"cue": "assistant_turn"}
