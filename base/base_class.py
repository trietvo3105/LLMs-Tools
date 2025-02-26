import os
import subprocess

import ollama
from openai import OpenAI
from dotenv import load_dotenv


class BasePromptGenerator:
    def __init__(self, model_name, api_key=None):
        self.infer_locally = False
        if api_key == "ollama":
            print(f"Using local model for inference with api_key = {api_key}")
            subprocess.Popen(
                ["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            try:
                self.openai = OpenAI(
                    base_url="http://localhost:11434/v1", api_key=api_key
                )
                self.infer_locally = True
            except:
                print(
                    "Ollama may not be running, use 'ollama serve' command to run it from your anaconda prompt, \
                        and check http://localhost:11434"
                )
                exit(0)
        else:
            load_dotenv()
            api_key = os.getenv("OPENAI_API_KEY")
            if (not api_key) or (not api_key.startswith("sk-proj")):
                print(f"Problem with OpenAI API Key, please check it, key = {api_key}")
                exit(0)
            print(f"Using cloud model with api_key = {api_key}")
            self.openai = OpenAI()

        self.model_name = model_name
        self.system_prompt = "System prompt goes here"

    def get_user_prompt(self, text):
        user_prompt = f"User prompt goes here with following text: {text}"
        return user_prompt

    def create_message(self, system_prompt, user_prompt):
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def inference(self, model_name, message, stream=False, response_format=None):
        print(f"Inference with model {model_name}")
        if self.infer_locally and (not model_name in ollama.list()["models"]):
            print(
                f"{model_name} not exists locally, start pulling it from ollama library..."
            )
            subprocess.run(["ollama", "pull", model_name])

        response = self.openai.chat.completions.create(
            model=model_name,
            messages=message,
            stream=stream,
            response_format=response_format,
        )
        if stream:
            return response
        return response.choices[0].message.content
