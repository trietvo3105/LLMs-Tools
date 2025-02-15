from flask import Flask, render_template_string
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time
import os

app = Flask(__name__)

# Configuration
WEBSITE_URL = "https://example.com"  # Replace with your website URL
HTML_TEMPLATE = """
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
SUMMARY_MD = """
# My Summary

This is a **markdown** summary of the website.

- Point 1
- Point 2
- Point 3
"""


# Convert Markdown to HTML
def markdown_to_html(markdown_text):
    import markdown2

    return markdown2.markdown(markdown_text)


# Route to render the website and summary side-by-side
@app.route("/")
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
    driver.get(WEBSITE_URL)
    time.sleep(2)  # Wait for the page to load

    # Take a screenshot of the website
    screenshot_dir = os.path.join(os.getcwd(), "static")
    if not os.path.exists(screenshot_dir):
        print("Creating 'static' folder for website screenshot")
        os.makedirs(screenshot_dir)
    screenshot_path = os.path.join(screenshot_dir, "website_screenshot.png")
    driver.save_screenshot(screenshot_path)
    driver.quit()

    # Convert summary markdown to HTML
    summary_html = markdown_to_html(SUMMARY_MD)

    # Render the template with the screenshot and summary
    return render_template_string(
        HTML_TEMPLATE,
        summary_html=summary_html,
    )


if __name__ == "__main__":
    app.run(debug=True)
