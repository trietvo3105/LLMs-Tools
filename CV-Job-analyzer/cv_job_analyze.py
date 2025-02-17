import os
import re

from openai import OpenAI
from dotenv import load_dotenv

from flask import Flask, render_template, request
from PyPDF2 import PdfReader
from markdown2 import markdown

from base.base_class import BasePromptGenerator


class CvJobDescriptionAnalyzer(BasePromptGenerator):
    def __init__(self, openai):
        super().__init__()
        self.openai = openai
        self.system_prompt = """
        You are an assistant whose job is to analyze a CV and a job description, \
            then provide a feedback on how well the CV is aligned with \
                the role described in the job description and its requirements.
        Your response should include the following:
        1. Summarize the job description by: job domain, role, principle missions and all requirements.
        2. Skill gap identification: Compare the skills listed in the resume \
            with those required in the job posting, highlighting areas where the resume may be \
                lacking or overemphasized.
        3. Keyword matching between a CV and a job posting: Match keywords from the job description \
            with the resume, determining how well they align. \
                Provide specific suggestions for missing keywords to add to the CV.
        4. Recommendations for CV improvement: Provide actionable suggestions on \
            how to enhance the resume, such as adding missing skills or rephrasing experience to \
                match job requirements.
        5. Alignment score: Display a score that represents the degree of alignment \
            between the resume and the job posting.
        6. Personalized feedback: Offer tailored advice based on the job posting, \
            guiding the user on how to optimize their CV for the best chances of success.
        7. Job market trend insights, provide broader market trends and insights, \
            such as in-demand skills and salary ranges.
        Provide responses that are concise, clear, and to the point. Respond in markdown.
        """
        self.system_prompt = re.sub(r"[ \t]+", " ", self.system_prompt)
        self.user_prompt = None
        self.job_desc = None
        self.cv_content = None
        self.cv_file = None
        self.analyze_result = None

    def get_job_description(self, job_desc):
        self.job_desc = job_desc

    def get_cv_content(self, cv_file):
        self.cv_file = cv_file
        if cv_file is not None:
            self.cv_content = ""
            pdf_reader = PdfReader(self.cv_file)
            for page in pdf_reader.pages:
                self.cv_content += page.extract_text()

    def get_user_prompt(self, job_description, cv_content):
        user_prompt = f"""
            Below is the job description and the content of the uploaded CV.
            Job description: 
            {job_description}

            CV content:
            {cv_content}
        """

        return re.sub(r"[ \t]+", " ", user_prompt)

    def analyze(self):
        self.user_prompt = self.get_user_prompt(self.job_desc, self.cv_content)
        if self.user_prompt is None:
            print("Problem with user prompt")
            exit(0)
        message = self.create_message(self.system_prompt, self.user_prompt)
        response = self.openai.chat.completions.create(
            model="gpt-4o-mini", messages=message
        )
        self.analyze_result = response.choices[0].message.content
        return self.analyze_result


def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if (not api_key) or (not api_key.startswith("sk-proj")):
        print(f"Problem with OpenAI API Key, please check it, key = {api_key}")
        exit(0)

    openai = OpenAI()
    cv_job_analyzer = CvJobDescriptionAnalyzer(openai)

    app = Flask(__name__)

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            if "text_submit" in request.form:
                cv_job_analyzer.get_job_description(request.form.get("text_input"))
            elif "pdf_submit" in request.form:
                cv_job_analyzer.get_cv_content(request.files["pdf_file"])

            if (cv_job_analyzer.job_desc is not None) and (
                cv_job_analyzer.cv_content is not None
            ):
                cv_job_analyzer.analyze()
                cv_job_analyzer.get_job_description(None)
                cv_job_analyzer.get_cv_content(None)

        analyze_result = (
            markdown(cv_job_analyzer.analyze_result)
            if cv_job_analyzer.analyze_result
            else None
        )
        return render_template(
            "index.html",
            text_content=cv_job_analyzer.job_desc,
            pdf_file=cv_job_analyzer.cv_file,
            analyze_result=analyze_result,
        )

    app.run(debug=True)


if __name__ == "__main__":
    main()
