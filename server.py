import json
import os
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).parent
PORT = int(os.environ.get("PORT", "8000"))
CLIENT_ID = os.environ.get("YAHOO_CLIENT_ID", "")
CACHE_TTL = 6 * 3600

QUERIES = [
    ("米・穀物", "コシヒカリ 5kg"),
    ("乳製品・卵", "明治おいしい牛乳 900ml"),
    ("乳製品・卵", "生卵 10個入り"),
    ("パン", "食パン 6枚"),
    ("肉・魚", "豚こま切れ 国産"),
    ("肉・魚", "鶏もも肉 国産"),
    ("肉・魚", "サーモン 刺身"),
    ("野菜・果物", "じゃがいも"),
    ("野菜・果物", "りんご ふじ"),
    ("飲料", "伊右衛門 2L"),
    ("大豆・納豆", "おかめ納豆"),
    ("冷凍食品", "味の素 冷凍餃子"),
]

_cache = {"data": None, "at": 0}
_lock = threading.Lock()


def load_snapshot():
    try:
        return json.loads((BASE / "prices.json").read_text(encoding="utf-8"))
    except Exception:
        return {"source": "Yahoo!ショッピング 商品検索API", "fetched_at": "", "items": []}


def fetch_prices():
    items = []
    for category, q in QUERIES:
        params = urllib.parse.urlencode(
            {"appid": CLIENT_ID, "query": q, "results": 5, "sort": "-score"}
        )
        url = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch?" + params
        req = urllib.request.Request(url, headers={"User-Agent": "food-price-watch/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
        pick = None
        for h in data.get("hits", []):
            if h.get("inStock") and h.get("price"):
                pick = h
                break
        if pick:
            items.append(
                {
                    "category": category,
                    "query": q,
                    "name": pick.get("name", ""),
                    "price": pick.get("price"),
                    "store": (pick.get("seller") or {}).get("name", ""),
                    "url": pick.get("url", ""),
                    "jan_code": pick.get("janCode") or "",
                }
            )
        time.sleep(1.1)
    return {
        "source": "Yahoo!ショッピング 商品検索API",
        "fetched_at": time.strftime("%Y-%m-%d", time.localtime()),
        "items": items,
    }


def get_prices():
    now = time.time()
    with _lock:
        if _cache["data"] and now - _cache["at"] < CACHE_TTL:
            return _cache["data"]
        if CLIENT_ID:
            try:
                data = fetch_prices()
                if data["items"]:
                    _cache["data"], _cache["at"] = data, now
                    return data
            except Exception:
                pass
        if not _cache["data"]:
            _cache["data"] = load_snapshot()
        return _cache["data"]


SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}

STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        for k, v in SECURITY_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/health":
            return self._send(200, b"ok", "text/plain")
        if path == "/api/prices":
            body = json.dumps(get_prices(), ensure_ascii=False).encode("utf-8")
            return self._send(200, body, "application/json; charset=utf-8")
        if path in STATIC:
            name, ctype = STATIC[path]
            f = BASE / name
            if f.exists():
                return self._send(200, f.read_bytes(), ctype)
        self._send(404, b"not found", "text/plain")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
