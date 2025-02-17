import os
import sys
import re
import markdown2
import argparse
import time
from pathlib import Path

from flask import Flask, render_template_string
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
from base.base_class import BasePromptGenerator


class WebsiteSummarizer(BasePromptGenerator):
    def __init__(self, url, model_name="gpt-4o-mini", api_key=None):
        super().__init__(model_name=model_name, api_key=api_key)
        self.url = url
        self.title = "No title found"
        self.content = "No content found"
        self.system_prompt = "You are an assistant whose job is to summarize the content of a website. \
            What you will do is to analyze the content of the given website then to give a short but informative \
            summary about it. Your response should answer the following questions: \n\
            1. Globally, what is the website about?\n\
            2. If the website is about a company or organization then what is that company/organization and what does it do? \
            Else if it is about a person or a group of people, who are they and what are they doing?\n\
            3. What is the domain or sector that the company/organization/person works on?\n\
            4. What are the main activities of the company/organization/person?\n\
            5. Does it contain announcement or news? If yes, analyze and summarize it.\n\
            You should response in markdown."
        self.system_prompt = re.sub(r"\s\s+", " ", self.system_prompt)

    def scrape_website(self):
        # Selenium
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)
        driver.get(self.url)
        page_source = driver.page_source
        driver.quit()
        soup = BeautifulSoup(page_source, "html.parser")
        for irrelevant in soup.body(["script", "type", "img", "input"]):
            irrelevant.decompose()
        if soup.title:
            self.title = soup.title.string
        self.content = soup.get_text(separator="\n", strip=True)

    def get_user_prompt(self, url, title, content):
        user_prompt = f"Here is the website that you need to analyze and summarize: {url}. \
        Its title is {title}. Its content is as following: \n\
        {content}."
        return user_prompt

    def get_summary(self):
        self.scrape_website()
        message = self.create_message(
            self.system_prompt, self.get_user_prompt(self.url, self.title, self.content)
        )
        return self.inference(self.model_name, message)


class RenderWebsiteAndSummary:
    def __init__(self, url, summary_md):
        self.url = url
        # Convert summary markdown to HTML
        self.summary_html = markdown2.markdown(summary_md)
        # Template of the render
        self.html_template = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Website and Summary</title>
                <style>
                    .container {
                        display: flex;
                        flex-direction: row;
                        justify-content: space-between;
                    }
                    .website, .summary {
                        width: 48%;
                    }
                    .website img {
                        width: 100%;
                        height: auto;
                    }
                    .summary {
                        padding: 10px;
                        border: 1px solid #ccc;
                        background-color: #f9f9f9;
                    }
                </style>
            </head>
            <body>
                <h1>Website and Summary</h1>
                <div class="container">
                    <div class="website">
                        <h2>Website Screenshot</h2>
                        <img src="{{ url_for('static', filename='website_screenshot.png') }}" alt="Website Screenshot">
                    </div>
                    <div class="summary">
                        <h2>Summary</h2>
                        {{ summary_html|safe }}
                    </div>
                </div>
            </body>
            </html>
        """
        self.app = Flask(__name__)

        @self.app.route("/")
        def render_side_by_side():
            # Set up Selenium WebDriver
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")  # Run in headless mode
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            # Initialize the WebDriver
            driver = webdriver.Chrome(service=Service(), options=options)

            # Open the website
            driver.get(self.url)
            time.sleep(2)  # Wait for the page to load

            # Take a screenshot of the website
            screenshot_dir = FILE.parent / "static"
            if not os.path.exists(screenshot_dir):
                print("Creating 'static' folder for website screenshot")
                os.makedirs(screenshot_dir)
            screenshot_path = os.path.join(screenshot_dir, "website_screenshot.png")
            driver.save_screenshot(screenshot_path)
            driver.quit()

            # Render the template with the screenshot and summary
            return render_template_string(
                self.html_template,
                summary_html=self.summary_html,
            )

    def render(self):
        """Run Flask server"""
        self.app.run(debug=True)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Summarize a website")
    parser.add_argument("url", type=str, help="Website url")
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


def main(url, model_name, api_key):
    # Scrape the website and generate a summary
    web_summarizer = WebsiteSummarizer(url, model_name, api_key)
    summary = web_summarizer.get_summary()
    # summary = """
    # # Summary Title
    # This is a **Markdown** formatted summary.

    # - Bullet point 1
    # - Bullet point 2
    # """

    # Convert Markdown to HTML
    summary_renderer = RenderWebsiteAndSummary(url, summary)
    summary_renderer.render()


if __name__ == "__main__":
    args = parse_arguments()
    main(**vars(args))
