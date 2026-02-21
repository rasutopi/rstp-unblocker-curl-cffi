from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, PlainTextResponse
from curl_cffi import requests
import asyncio

app = FastAPI()

@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        return Response(status_code=204)

    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


@app.get("/")
async def proxy(url: str = None):
    if not url:
        return PlainTextResponse("Missing url", status_code=400)

    try:
        print("Proxy start:", url)

        r = requests.get(
            url,
            impersonate="chrome136",
            timeout=10,
        )

        if not r:
            raise Exception("Empty response")

        content_type = r.headers.get("content-type", "application/octet-stream")

        if "count.getloli.com" in url or ".svg" in url:
            content_type = "image/svg+xml"
        elif ".css" in url:
            content_type = "text/css"

        return Response(
            content=r.content,
            status_code=r.status_code,
            headers={
                "Content-Type": content_type,
                "Content-Disposition": "inline"
            }
        )

    except Exception as e:
        print("Proxy error:", str(e))
        return PlainTextResponse("Proxy error: " + str(e), status_code=500)

    finally:
        print("Proxy finished")