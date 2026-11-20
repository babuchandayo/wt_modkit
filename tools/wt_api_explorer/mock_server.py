"""動作確認用のモックサーバー（ゲームなしでツールを試すため）。
応答の形はコミュニティ情報をもとにした想定で、実際のゲームの応答とは異なる可能性がある。
  python mock_server.py   → http://127.0.0.1:8111
"""
import json
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def body(path):
    if path == "/state":
        return {"valid": True, "H, m": random.randint(0, 3000), "TAS, km/h": random.randint(200, 600),
                "throttle 1, %": 100, "Vy, m/s": round(random.uniform(-5, 5), 1)}
    if path == "/indicators":
        return {"valid": True, "army": "air", "type": "bf-109f-4", "speed": random.random() * 200}
    if path == "/map_obj.json":
        return [{"type": "aircraft", "color": "#fa0C00", "icon": "Player", "x": random.random(), "y": random.random()}
                for _ in range(random.randint(1, 4))]
    if path == "/map_info.json":
        return {"grid_steps": [4096.0, 4096.0], "map_min": [-32768.0, -32768.0], "map_max": [32768.0, 32768.0], "valid": True}
    if path == "/gamechat":
        return [{"id": 1, "msg": "hello", "sender": "test", "enemy": False, "mode": "All", "time": 12}]
    if path == "/hudmsg":
        return {"events": [], "damage": [{"id": 1, "msg": "test destroyed something", "time": 30}]}
    return None


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/map.img":
            data, ct = b"\x89PNG\r\n\x1a\n" + b"\0" * 100, "image/png"
        else:
            b = body(path)
            if b is None:
                self.send_error(404)
                return
            data, ct = json.dumps(b).encode(), "application/json"
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8111), H).serve_forever()
