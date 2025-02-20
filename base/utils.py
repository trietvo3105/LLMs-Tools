import json


def get_stream(stream_from_api):
    for chunk in stream_from_api:
        if isinstance(chunk, str):
            yield f"data: {json.dump({'content': chunk})}\n\n"
        else:
            text = chunk.choice[0].delta.content or ""
            # text.replace('```','').replace('markdown', '')
            yield f"data: {json.dump({'content': text})}"
