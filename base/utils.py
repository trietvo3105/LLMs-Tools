import json
import time
import markdown2


def get_stream(stream_from_api):
    text = ""
    # full_text = ""

    # for chunk in stream_from_api:
    #     full_text += chunk  # Append new text
    #     html_content = markdown2.markdown(full_text)  # Convert Markdown to HTML
    #     yield f"data: {html_content}\n\n"  # SSE format
    #     time.sleep(0.5)  # Simulating delay
    for chunk in stream_from_api:
        if isinstance(chunk, str):
            text += chunk
        else:
            text += chunk.choices[0].delta.content or ""
            # text.replace('```','').replace('markdown', '')
        text_html = markdown2.markdown(text)
        yield f"data: {json.dumps({'content': text_html})}\n\n"  # SSE format
        time.sleep(0.15)
