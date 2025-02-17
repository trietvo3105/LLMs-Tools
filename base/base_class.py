class BasePromptGenerator:
    def __init__(self):
        self.system_prompt = "System prompt goes here"

    def get_user_prompt(self, text):
        user_prompt = f"User prompt goes here with following text: {text}"
        return user_prompt

    def create_message(self, system_prompt, user_prompt):
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
