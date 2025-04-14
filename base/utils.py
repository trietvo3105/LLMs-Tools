import json
import time
import markdown2


def get_stream(stream_from_api):
    text = ""
    for chunk in stream_from_api:
        if isinstance(chunk, str):
            time.sleep(0.02)
            text += chunk
        else:
            time.sleep(0.05)
            text += chunk.choices[0].delta.content or ""
            # text.replace('```','').replace('markdown', '')
        # text_html = markdown2.markdown(text)
        yield f"data: {json.dumps({'content': text})}\n\n"  # SSE format


def get_stream_v2(stream_from_api):
    text = ""
    for chunk in stream_from_api:
        if isinstance(chunk, str):
            text += chunk
        else:
            text += chunk.choices[0].delta.content or ""
        yield text
    return text
