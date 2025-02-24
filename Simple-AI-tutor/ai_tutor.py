import os
import re
import argparse
from pathlib import Path
import sys

from flask import Flask, render_template, Response, request

FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
from base.base_class import BasePromptGenerator
from base.utils import get_stream


class AITutor(BasePromptGenerator):
    def __init__(self, model_name, api_key=None):
        super().__init__(model_name, api_key)
        self.system_prompt = """
            You are an AI tutor whose objective is answering the questions on diverse topics, such as Python coding, algorithms, \
            computer vision, large language model, academic research, general knowledge, etc. 
            Your response should be clear, structured and engaging with example code snippets and best practices \
                if the question is about coding. Use examples, analogies, and step-by-step explainations when needed. \
                Response in Markdown format.
            Below are some examples of how you should response:
                Example 1: Simple Factual Answer
                    User: What is photosynthesis?
                    Tutor: Photosynthesis is the process by which plants convert sunlight into energy. \
                        They use sunlight, water, and carbon dioxide to produce glucose and oxygen.
                
                Example 2: Explaining a Concept in coding
                    User: What is a Python dictionary?
                    Tutor: A dictionary in Python is a data structure that stores key-value pairs. \
                        It is similar to a real-world dictionary where words (keys) have definitions (values). Example:
                    ```
                    student = {"name": "Alice", "age": 20, "grade": "A"}
                    print(student["name"])  # Output: Alice
                    ```
                
                Example 3: Coding a Function
                    User: Write a Python function to check if a number is prime.
                    Tutor: Here is a function to check for prime numbers:
                    ```
                    def is_prime(n):
                        if n < 2:
                            return False
                        for i in range(2, int(n ** 0.5) + 1):
                            if n % i == 0:
                                return False
                        return True

                    print(is_prime(7))  # Output: True
                    ```
                    This function checks divisibility up to the square root of n, optimizing performance.
                
                Example 4: Step-by-Step Explanation
                    User: How does the Pythagorean theorem work?
                    You: The Pythagorean theorem states that in a right triangle, the square of the hypotenuse is equal \
                        to the sum of the squares of the other two sides (a² + b² = c²).
                    For example, if one side is 3 and the other is 4, then:
                    3² + 4² = 9 + 16 = 25 → √25 = 5, so the hypotenuse is 5.
                
                Example 5: Concept Explanation with Analogy
                    User: What is an API?
                    Bot: An API (Application Programming Interface) is like a waiter in a restaurant. \
                        Just like a waiter takes your order to the kitchen and brings back food, an API allows \
                            different software applications to communicate. It sends requests and returns responses.        
            """
        self.system_prompt = re.sub(r"\t+| {2,}", " ", self.system_prompt)
        self.last_question = None
        self.last_response = None

    def get_question(self, question):
        self.last_question = question

    def get_user_prompt(self, question):
        user_prompt = f"""
            Here is my question:
            {question}
            Please respond in Markdown format.
        """
        user_prompt = re.sub(r"\t+| {2,}", " ", user_prompt)
        return user_prompt

    def get_response(self, stream=False):
        if self.last_question is None:
            return

        message = self.create_message(
            self.system_prompt, self.get_user_prompt(self.last_question)
        )
        self.last_response = self.inference(
            model_name=self.model_name, message=message, stream=stream
        )
        return self.last_response


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
    tutor = AITutor(model_name=model_name, api_key=api_key)

    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/chat")
    def chat():
        user_message = request.args.get("message", "")

        if not user_message:
            return Response("Error: Empty message", status=400, mimetype="text/plain")

        tutor.get_question(user_message)  # Store the message for streaming
        return Response("Message received", mimetype="text/plain")

    @app.route("/stream")
    def stream():
        model_response = tutor.get_response(stream=True)
        if tutor.last_response is not None:
            return Response(
                get_stream(tutor.last_response), mimetype="text/event-stream"
            )

    app.run()


if __name__ == "__main__":
    args = parse_arguments()
    main(**vars(args))
