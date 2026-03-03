from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
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
        # --- クライアントからヘッダー取得 ---
        incoming_cookies = request.headers.get("cookie")

        headers = {
            "User-Agent": request.headers.get("user-agent"),
            "Accept": request.headers.get("accept"),
            "Accept-Language": request.headers.get("accept-language"),
        }

        if incoming_cookies:
            headers["Cookie"] = incoming_cookies

        # --- upstreamへリクエスト ---
        r = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=await request.body(),
            impersonate="chrome136",
            allow_redirects=False,
            timeout=20,
        )

        # --- Content-Type を必ず取得 ---
        content_type = r.headers.get("content-type", "application/octet-stream")

        # --- レスポンス作成 ---
        response = Response(
            content=r.content,
            status_code=r.status_code,
            media_type=content_type
        )

        # --- 危険ヘッダー除外して転送 ---
        excluded_headers = {
            "content-encoding",
            "content-length",
            "transfer-encoding",
            "connection"
        }

        for key, value in r.headers.items():
            if key.lower() in excluded_headers:
                continue
            response.headers[key] = value

        # --- Set-Cookie 転送 ---
        try:
            cookies = r.headers.get_list("set-cookie")
            for c in cookies:
                response.headers.append("Set-Cookie", c)
        except Exception:
            pass

        return response

    except Exception as e:
        return PlainTextResponse("Proxy error: " + str(e), status_code=500)
