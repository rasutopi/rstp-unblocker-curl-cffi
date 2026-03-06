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
        response.headers["Access-Control-Allow-Headers"] = "*"

    return response


@app.api_route("/", methods=["GET", "POST"])
async def proxy(request: Request, url: str = None):
    if not url:
        return PlainTextResponse("Missing url", status_code=400)

    try:
        incoming_cookies = request.headers.get("cookie")

        # ===== Header構築 =====
        headers = {
            "User-Agent": request.headers.get("user-agent")
            or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/136 Safari/537.36",

            "Accept": request.headers.get("accept", "*/*"),

            "Accept-Language": request.headers.get("accept-language", "en-US,en;q=0.9"),

            "Referer": request.headers.get("referer", ""),

            "Origin": request.headers.get("origin", ""),

            # 圧縮防止
            "Accept-Encoding": "identity",

            # WAF対策
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document"
        }
        
        # Range系
        if range_header := request.headers.get("range"):
            headers["Range"] = range_header

        if if_range := request.headers.get("if-range"):
            headers["If-Range"] = if_range

        if incoming_cookies:
            headers["Cookie"] = incoming_cookies

        # ===== body処理 =====
        body = None
        if request.method in ("POST", "PUT", "PATCH"):
            body = await request.body()

        # ===== upstream request =====
        r = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=body,
            impersonate="chrome136",
            allow_redirects=False,
            timeout=(10, 300),
            stream=True,
            verify=False
        )

        content_type = r.headers.get(
            "content-type",
            "application/octet-stream"
        )

        # ===== Stream Generator（超重要）=====
        def stream_response():
            try:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        yield chunk
            finally:
                r.close()

        response = StreamingResponse(
            stream_response(),
            status_code=r.status_code,
            media_type=content_type
        )

        # ===== Header転送（安全版）=====
        excluded_headers = {
            "transfer-encoding",
            "connection",
            "content-encoding"
        }

        for key, value in r.headers.items():
            if key.lower() in excluded_headers:
                continue
            response.headers[key] = value

        # ===== Set-Cookie =====
        try:
            for c in r.headers.get_list("set-cookie"):
                response.headers.append("Set-Cookie", c)
        except Exception:
            pass

        return response

    except Exception as e:
        return PlainTextResponse(
            f"Proxy error: {str(e)}",
            status_code=500
        )
