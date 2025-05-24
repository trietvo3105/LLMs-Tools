import sys
import re
from pathlib import Path
import gradio as gr

FILE = Path(__file__).resolve()
ROOT = FILE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from base.utils import get_stream_v2
from cv_job_analyze import CvJobDescriptionAnalyzer


def gradio_app(cv_file, job_desc, model_name):
    api_key = None
    if model_name in ["llama3.2", "deepseek-r1:1.5b"]:
        api_key = "ollama"
    cv_job_analyzer = CvJobDescriptionAnalyzer(model_name, api_key)
    cv_job_analyzer.get_cv_content(cv_file=cv_file)
    cv_job_analyzer.get_job_description(job_desc=job_desc)
    analyzed_result = cv_job_analyzer.analyze(stream=True)
    yield from get_stream_v2(analyzed_result)


def main():
    view = gr.Interface(
        fn=gradio_app,
        inputs=[
            gr.File(
                file_count="single", file_types=[".pdf"], label="Upload your CV in PDF"
            ),
            gr.Textbox(lines=15, label="Paste the job description here..."),
            gr.Dropdown(choices=["gpt-4o-mini", "llama3.2", "deepseek-r1:1.5b"]),
        ],
        outputs=[
            gr.Markdown(label="CV analyzing result according to the job description:")
        ],
        flagging_mode="never",
    )
    view.launch(inbrowser=True)


if __name__ == "__main__":
    main()
