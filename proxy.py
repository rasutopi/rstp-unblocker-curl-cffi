from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse, StreamingResponse
from curl_cffi import requests

app = FastAPI()


@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        response = Response(status_code=204)
    else:
        response = await call_next(request)

    origin = request.headers.get("origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = request.headers.get(
            "access-control-request-headers", "*"
        )

    return response


@app.api_route("/", methods=["GET", "POST"])
async def proxy(request: Request, url: str = None):
    if not url:
        return PlainTextResponse("Missing url", status_code=400)

    try:
        # ---- クライアントヘッダ取得 ----
        incoming_cookies = request.headers.get("cookie")

        headers = {
            "User-Agent": request.headers.get("user-agent"),
            "Accept": request.headers.get("accept"),
            "Accept-Language": request.headers.get("accept-language"),
            "Referer": request.headers.get("referer"),
            "Origin": request.headers.get("origin"),
        }

        # Range系
        range_header = request.headers.get("range")
        if range_header:
            headers["Range"] = range_header

        if_range = request.headers.get("if-range")
        if if_range:
            headers["If-Range"] = if_range

        if incoming_cookies:
            headers["Cookie"] = incoming_cookies

        # ---- body処理 ----
        body = None
        if request.method in ("POST", "PUT", "PATCH"):
            body = await request.body()

        # ---- upstream request ----
        r = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=body,
            impersonate="chrome136",
            allow_redirects=False,
            timeout=(10, 300),
            stream=True
        )

        content_type = r.headers.get("content-type", "application/octet-stream")

        response = StreamingResponse(
            r.iter_content(chunk_size=65536),
            status_code=r.status_code,
            media_type=content_type
        )

        # ---- ヘッダ転送 ----
        excluded_headers = {
            "transfer-encoding",
            "connection",
        }

        for key, value in r.headers.items():
            if key.lower() in excluded_headers:
                continue
            response.headers[key] = value

        # ---- Set-Cookie ----
        try:
            cookies = r.headers.get_list("set-cookie")
            for c in cookies:
                response.headers.append("Set-Cookie", c)
        except Exception:
            pass

        return response

    except Exception as e:
        return PlainTextResponse("Proxy error: " + str(e), status_code=500)
