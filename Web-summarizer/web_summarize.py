import os
import sys
import re
import markdown2
import argparse
import time
from pathlib import Path
import json

from flask import Flask, render_template, Response
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
from base.base_class import BasePromptGenerator
from base.utils import get_stream


class WebsiteSummarizer(BasePromptGenerator):
    def __init__(self, url, model_name="gpt-4o-mini", api_key=None):
        super().__init__(model_name=model_name, api_key=api_key)
        self.url = url
        self.title = "No title found"
        self.content = "No content found"
        self.links = ["No link found"]
        self.all_website_details = "No information available"
        self.system_prompt = "You are an assistant whose job is to summarize the content of a website. \
            What you will do is to analyze the content of the given website then to give an informative \
            summary about it. Here are some example questions/ that you should response to, any additional \
            question is welcome, giving example for what is talked about is recommended: \n\
            1. Globally, what is the website about?\n\
            2. If the website is about a company or organization then what is that company/organization and what does it do? \
            Else if it is about a person or a group of people, who are they and what are they doing?\n\
            3. What is the domain or sector that the company/organization/person works on?\n\
            4. What are the main objectives and activities of the company/organization/person?\n\
            5. If the website provides products, services, etc., what is the their basic information \
                 (such as what they are, in which forms they are provided, what the pricing is, etc.)? \n\
            6. Does it contain announcement or news? If yes, analyze and summarize it.\n\
            You should response in markdown."
        self.system_prompt = re.sub(r"\t+| {2,}", " ", self.system_prompt)
        self.relevant_links_system_prompt = """
            You are an assistant who is provided with a list of links found on a website \
                and is able to decide which links are the most relevant \
                to include in a summary of that website, such as links to \
                About page, or Company page, or Product page, or Careers/Jobs page.
            You should response in JSON format similar to the below example:
            {
                "links": [
                    {"type": "About page", "url": "https://www.full.url/about"},
                    {"type": "Careers page", "url": "https://www.another.full.url/careers"}
                ]
            }
        """
        self.relevant_links_system_prompt = re.sub(
            r"\t+| {2,}", " ", self.relevant_links_system_prompt
        )
        # self.get_main_information()

    def get_main_information(self):
        self.title, self.content, self.links = self.scrape_website(
            self.url, screenshot=True
        )

    def scrape_website(self, url, screenshot=False):
        # Selenium
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)
        driver.get(url)

        if screenshot:
            time.sleep(1)  # Wait for the page to load
            # Take a screenshot of the website
            screenshot_dir = FILE.parent / "static"
            if not os.path.exists(screenshot_dir):
                print("Creating 'static' folder for website screenshot")
                os.makedirs(screenshot_dir)
            screenshot_path = os.path.join(screenshot_dir, "website_screenshot.png")
            driver.save_screenshot(screenshot_path)

        page_source = driver.page_source
        driver.quit()

        soup = BeautifulSoup(page_source, "html.parser")
        if soup.title:
            title = soup.title.string
        if soup.body:
            for irrelevant in soup.body(["script", "type", "img", "input"]):
                irrelevant.decompose()
            content = soup.get_text(separator="\n", strip=True)
        else:
            content = ""
        links = [
            anchor.get("href") for anchor in soup.find_all("a") if anchor.get("href")
        ]
        return title, content, links

    def get_content(self, title, content):
        content = f"""
            Website title: {title},
            Website content: {content}\n
        """
        return re.sub(r"\t| {2,}", " ", content)

    def get_relevant_links_user_prompt(self):
        links = "\n".join(self.links)
        relevant_links_user_prompt = f"""
            Below is the list of the links found on the website of {self.url}, \
            please decide which of the links are relevant for making the summary \
            of the website. Please response with full HTTPS URL in JSON format. \
            Do not include Terms of Service, Policies, Privacy and emails links.
            Links (some might be relative links):
        """
        relevant_links_user_prompt = re.sub(
            r"\t+| {2,}", " ", relevant_links_user_prompt
        )
        relevant_links_user_prompt += links
        return relevant_links_user_prompt

    def build_relevant_links(self):
        message = self.create_message(
            self.relevant_links_system_prompt, self.get_relevant_links_user_prompt()
        )
        response = self.inference(
            self.model_name, message=message, response_format={"type": "json_object"}
        )
        return json.loads(response)

    def get_all_website_details(self):
        all_website_details = "Home page:"
        self.get_main_information()
        all_website_details += self.get_content(self.title, self.content)
        dict_relevant_links = self.build_relevant_links()
        for subpage_info in dict_relevant_links["links"]:
            print(f"Reading {subpage_info['type']} with url: {subpage_info['url']}")
            all_website_details += f"{subpage_info['type']}:"
            title, content, _ = self.scrape_website(subpage_info["url"])
            all_website_details += self.get_content(title, content)
        return all_website_details

    def get_user_prompt(self):
        user_prompt = f"""
        Here is the website that you need to analyze and summarize: {self.url}. \
        Its title is {self.title}. 
        Its contents of its homepage and other relevant pages are as following, \
            please use them to make an informative and detailed summary of the website \
            in markdown:
        {self.all_website_details}
        """
        return user_prompt

    def get_summary(self, stream=False):
        self.all_website_details = self.get_all_website_details()
        message = self.create_message(self.system_prompt, self.get_user_prompt())
        return self.inference(self.model_name, message, stream=stream)


class RenderWebsiteAndSummary:
    def __init__(self, url, summary_response_from_model):
        self.url = url
        # Convert summary markdown to HTML
        if isinstance(summary_response_from_model, str):
            self.summary_html = markdown2.markdown(summary_response_from_model)
        else:
            self.summary_html = summary_response_from_model  # ""
        self.stream_generator = get_stream(self.summary_html)


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
    summary = web_summarizer.get_summary(stream=True)

    # Convert Markdown to HTML
    summary_renderer = RenderWebsiteAndSummary(url, summary)

    app = Flask(__name__)

    @app.route("/")
    def render_side_by_side():
        # Render the template with the screenshot and summary
        return render_template(
            "index.html",
            # summary_html=summary_renderer.summary_html,
        )

    @app.route("/stream")
    def stream():
        return Response(summary_renderer.stream_generator, mimetype="text/event-stream")

    app.run()


if __name__ == "__main__":
    args = parse_arguments()
    main(**vars(args))
