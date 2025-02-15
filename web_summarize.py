import os
import re
import markdown2
import threading
import argparse
import time

from openai import OpenAI
from dotenv import load_dotenv

from flask import Flask, render_template_string
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup


load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if (not api_key) or (not api_key.startswith("sk-proj")):
    print(f"Problem with OpenAI API Key, please check it, key = {api_key}")
    exit(0)
else:
    openai = OpenAI()


class WebsiteSummarizer:
    def __init__(self, url):
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

    def create_message(self, system_prompt, user_prompt):
        msg = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return msg

    def get_summary(self):
        self.scrape_website()
        message = self.create_message(
            self.system_prompt, self.get_user_prompt(self.url, self.title, self.content)
        )
        response = openai.chat.completions.create(model="gpt-4o-mini", messages=message)
        summary = response.choices[0].message.content
        return summary


def parse_arguments():
    parser = argparse.ArgumentParser(description="Summarize a website")
    parser.add_argument("url", type=str, help="Website url")
    args = parser.parse_args()
    return args


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
            screenshot_dir = os.path.join(os.getcwd(), "static")
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


def main(url):
    # Scrape the website and generate a summary
    web_summarizer = WebsiteSummarizer(url)
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
