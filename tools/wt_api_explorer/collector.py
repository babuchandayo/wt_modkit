"""War Thunder ローカルHTTP API (既定 http://127.0.0.1:8111) から値を取得し、
キーの一覧を蓄積するコア処理。標準ライブラリのみ使用。

ゲーム本体には一切触れず、ゲームが公開しているHTTPを読むだけ。
"""
from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

# 既知のエンドポイント。存在・中身はゲームのバージョンや状態(格納庫/戦闘中/機種)で変わる。
# 一覧にないものも「追加パス」で試せる。
DEFAULT_ENDPOINTS = [
    "/state",
    "/indicators",
    "/map_obj.json",
    "/map_info.json",
    "/mission.json",
    "/gamechat?lastId=0",
    "/hudmsg?lastEvt=0&lastDmg=0",
    "/map.img",
]


@dataclass
class KeyInfo:
    endpoint: str
    key: str
    types: set = field(default_factory=set)
    last_value: object = None
    min_value: float | None = None
    max_value: float | None = None
    seen_count: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0

    def update(self, value, now: float):
        self.types.add(type_name(value))
        self.last_value = value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            self.min_value = value if self.min_value is None else min(self.min_value, value)
            self.max_value = value if self.max_value is None else max(self.max_value, value)
        if self.seen_count == 0:
            self.first_seen = now
        self.seen_count += 1
        self.last_seen = now


@dataclass
class EndpointStatus:
    endpoint: str
    ok: bool = False
    http_status: int | None = None
    content_type: str = ""
    size: int = 0
    error: str = ""
    last_raw: object = None  # JSONならパース結果、それ以外はNone


def type_name(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "dict"
    return type(v).__name__


def flatten(obj, prefix: str = ""):
    """JSONを (キーパス, 値) の列に平坦化する。
    配列の要素は個数がその時々で変わるため [*] にまとめる（map_obj.json など）。
    """
    if isinstance(obj, dict):
        if not obj and prefix:
            yield prefix, obj
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            yield from flatten(v, p)
    elif isinstance(obj, list):
        p = f"{prefix}[*]" if prefix else "[*]"
        yield (f"{prefix}.length" if prefix else "length"), len(obj)
        for item in obj:
            yield from flatten(item, p)
    else:
        yield prefix or "(value)", obj


class Collector:
    def __init__(self, base_url: str = "http://127.0.0.1:8111", endpoints=None, timeout: float = 1.5):
        self.base_url = base_url.rstrip("/")
        self.endpoints = list(endpoints or DEFAULT_ENDPOINTS)
        self.timeout = timeout
        self.keys: dict[tuple[str, str], KeyInfo] = {}
        self.status: dict[str, EndpointStatus] = {}
        self.polls = 0

    def fetch(self, endpoint: str) -> EndpointStatus:
        st = EndpointStatus(endpoint)
        url = self.base_url + endpoint
        # プロキシ設定を無視してローカルへ直接つなぐ
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(url, timeout=self.timeout) as r:
                body = r.read()
                st.http_status = r.status
                st.content_type = r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            st.http_status = e.code
            st.error = f"HTTP {e.code}"
            return st
        except Exception as e:  # 接続拒否・タイムアウトなど
            st.error = f"{type(e).__name__}: {e}"
            return st
        st.size = len(body)
        st.ok = True
        if "image" in st.content_type or endpoint.endswith(".img"):
            return st
        try:
            st.last_raw = json.loads(body.decode("utf-8", errors="replace"))
        except ValueError:
            st.error = "JSONではない応答"
        return st

    def poll_once(self) -> None:
        now = time.time()
        self.polls += 1
        # 並列に取得する（ゲーム未起動時、Windowsでは接続拒否に1回2秒ほどかかるため）
        with ThreadPoolExecutor(max_workers=len(self.endpoints) or 1) as ex:
            fetched = list(ex.map(self.fetch, self.endpoints))
        for ep, st in zip(self.endpoints, fetched):
            self.status[ep] = st
            if st.last_raw is None:
                continue
            name = ep.split("?", 1)[0]
            for k, v in flatten(st.last_raw):
                info = self.keys.get((name, k))
                if info is None:
                    info = self.keys[(name, k)] = KeyInfo(name, k)
                info.update(v, now)

    def rows(self):
        for (_, _), i in sorted(self.keys.items()):
            yield {
                "endpoint": i.endpoint,
                "key": i.key,
                "type": "/".join(sorted(i.types)),
                "last_value": fmt(i.last_value),
                "min": "" if i.min_value is None else i.min_value,
                "max": "" if i.max_value is None else i.max_value,
                "seen_count": i.seen_count,
            }

    def clear(self):
        self.keys.clear()
        self.status.clear()
        self.polls = 0

    def save_csv(self, path: str):
        cols = ["endpoint", "key", "type", "last_value", "min", "max", "seen_count"]
        # Excelで文字化けしないようBOM付きUTF-8
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(self.rows())

    def save_json(self, path: str):
        data = {
            "base_url": self.base_url,
            "polls": self.polls,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "endpoints": {
                ep: {
                    "ok": s.ok, "http_status": s.http_status, "content_type": s.content_type,
                    "size": s.size, "error": s.error, "last_response": s.last_raw,
                } for ep, s in self.status.items()
            },
            "keys": list(self.rows()),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def fmt(v) -> str:
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False)
