import os
import re
import argparse
from pathlib import Path
import sys

from flask import Flask, render_template, Response, request
import gradio as gr

FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
from base.base_class import BasePromptGenerator
from base.utils import get_stream_v2


class AITutor(BasePromptGenerator):
    def __init__(self, model_name, api_key=None, stream=True):
        super().__init__(model_name, api_key)
        self.system_prompt = """
            You are an AI tutor whose objective is answering the questions on diverse topics, such as Python coding, algorithms, \
            computer vision, large language model, academic research, general knowledge, etc. 
            Your response should be clear, structured and engaging with example code snippets and best practices \
                if the question is about coding. Use examples, analogies, and step-by-step explainations when needed. \
                If you don't know the answer, say so. Response in Markdown format.
        """
        self.system_prompt = re.sub(r"\t+| {2,}", " ", self.system_prompt)
        self.stream = stream

    def get_user_message(self, message, history):
        return "", history + [{"role": "user", "content": message}]

    def chat(self, history):
        messages = [{"role": "system", "content": self.system_prompt}] + history
        response = self.inference(
            model_name=self.model_name, message=messages, stream=self.stream
        )
        history += [{"role": "assistant", "content": ""}]
        for chunk in response:
            history[-1]["content"] += chunk.choices[0].delta.content or ""
            yield history


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Simple AI tutor for any of your questions"
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="gpt-4o-mini",
        help="Model name for text generation, currently support OpenAI GPT and open-source Ollama (need to use 'ollama' api key) models, default is gpt-4o-mini",
    )
    parser.add_argument(
        "--api_key",
        type=str,
        default=None,
        help="API key for Ollama models, i.e. 'ollama', default is None to use your own API Key",
    )
    args = parser.parse_args()
    return args


def main(model_name, api_key):
    tutor = AITutor(model_name=model_name, api_key=api_key, stream=True)

    with gr.Blocks() as ui:
        chatbot = gr.Chatbot(type="messages")
        user_message = gr.Textbox(label="Type your message here")
        clear = gr.Button("Clear")

        user_message.submit(
            fn=tutor.get_user_message,
            inputs=[user_message, chatbot],
            outputs=[user_message, chatbot],
            queue=False,
        ).then(fn=tutor.chat, inputs=chatbot, outputs=chatbot)

        clear.click(fn=lambda: None, inputs=None, outputs=chatbot, queue=False)

    ui.launch(inbrowser=True)


if __name__ == "__main__":
    args = parse_arguments()
    main(**vars(args))
