"""War Thunder ローカルAPI 値一覧ツール

使い方:
  python wt_api_explorer.py            … GUIで起動
  python wt_api_explorer.py --cli -n 5 … GUIなしで5回取得し、CSV/JSONを保存
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time

from collector import DEFAULT_ENDPOINTS, Collector


def run_cli(args):
    c = Collector(args.url, endpoints=DEFAULT_ENDPOINTS + args.extra)
    for i in range(args.count):
        c.poll_once()
        ok = sum(1 for s in c.status.values() if s.ok)
        print(f"[{i + 1}/{args.count}] 応答あり {ok}/{len(c.status)}  キー数 {len(c.keys)}")
        if i + 1 < args.count:
            time.sleep(args.interval)
    for ep, s in c.status.items():
        print(f"  {ep:32} {'OK' if s.ok else 'NG'}  {s.content_type or ''} {s.error}")
    stamp = time.strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(args.out, f"wt_api_keys_{stamp}.csv")
    json_path = os.path.join(args.out, f"wt_api_dump_{stamp}.json")
    c.save_csv(csv_path)
    c.save_json(json_path)
    print(f"保存: {csv_path}\n保存: {json_path}")


def run_gui(args):
    import queue
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    # tkinter はメインスレッド以外から触ると固まることがあるため、
    # 通信は作業スレッドだけが行い、結果はキュー経由でメインスレッドへ渡す。
    c = Collector(args.url, endpoints=DEFAULT_ENDPOINTS + args.extra)
    lock = threading.Lock()          # Collector を触るのは作業スレッドと保存処理だけ
    running = threading.Event()
    wake = threading.Event()         # 「1回取得」や開始時にすぐ取得させる
    clear_req = threading.Event()
    results: queue.Queue = queue.Queue()
    settings = {"url": args.url, "extra": list(args.extra), "interval": args.interval}
    busy = {"polling": False}
    snapshot = {"rows": [], "statuses": [], "polls": 0}

    root = tk.Tk()
    root.title("War Thunder ローカルAPI 値一覧")
    root.geometry("1100x650")

    top = ttk.Frame(root, padding=4)
    top.pack(fill="x")
    ttk.Label(top, text="URL").pack(side="left")
    url_var = tk.StringVar(value=args.url)
    ttk.Entry(top, textvariable=url_var, width=26).pack(side="left", padx=4)
    ttk.Label(top, text="間隔(秒)").pack(side="left")
    interval_var = tk.StringVar(value=str(args.interval))
    ttk.Entry(top, textvariable=interval_var, width=5).pack(side="left", padx=4)
    ttk.Label(top, text="追加パス").pack(side="left")
    extra_var = tk.StringVar(value=" ".join(args.extra))
    ttk.Entry(top, textvariable=extra_var, width=20).pack(side="left", padx=4)
    start_btn = ttk.Button(top, text="開始")
    start_btn.pack(side="left", padx=2)
    once_btn = ttk.Button(top, text="1回取得")
    once_btn.pack(side="left", padx=2)
    clear_btn = ttk.Button(top, text="クリア")
    clear_btn.pack(side="left", padx=2)
    ttk.Button(top, text="CSV保存", command=lambda: save("csv")).pack(side="left", padx=2)
    ttk.Button(top, text="JSON保存", command=lambda: save("json")).pack(side="left", padx=2)

    filt = ttk.Frame(root, padding=(4, 0))
    filt.pack(fill="x")
    ttk.Label(filt, text="絞り込み").pack(side="left")
    filter_var = tk.StringVar()
    ttk.Entry(filt, textvariable=filter_var, width=40).pack(side="left", padx=4)
    status_var = tk.StringVar(value="停止中")
    ttk.Label(filt, textvariable=status_var).pack(side="left", padx=8)

    ep_tree = ttk.Treeview(root, columns=("st", "ct", "size", "err"), height=len(c.endpoints) + 1)
    for col, w, t in (("#0", 220, "エンドポイント"), ("st", 60, "状態"), ("ct", 200, "Content-Type"),
                      ("size", 80, "バイト"), ("err", 400, "エラー")):
        ep_tree.heading(col, text=t)
        ep_tree.column(col, width=w, stretch=col == "err")
    ep_tree.pack(fill="x", padx=4, pady=4)

    cols = ("endpoint", "key", "type", "last_value", "min", "max", "seen_count")
    frame = ttk.Frame(root)
    frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))
    tree = ttk.Treeview(frame, columns=cols, show="headings")
    for col, w in zip(cols, (110, 300, 70, 360, 80, 80, 70)):
        tree.heading(col, text=col)
        tree.column(col, width=w, stretch=col in ("key", "last_value"))
    sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    def read_settings():
        # メインスレッドで画面の値を読み、作業スレッド用の dict に写す
        settings["url"] = url_var.get().strip().rstrip("/")
        settings["extra"] = [p if p.startswith("/") else "/" + p for p in extra_var.get().split()]
        try:
            settings["interval"] = max(0.2, float(interval_var.get()))
        except ValueError:
            settings["interval"] = 1.0

    def worker():
        while True:
            wake.wait(timeout=settings["interval"] if running.is_set() else None)
            wake.clear()
            if not running.is_set() and not once_flag.is_set():
                continue
            once_flag.clear()
            busy["polling"] = True
            results.put(None)  # 「取得中」表示のため
            with lock:
                if clear_req.is_set():
                    c.clear()
                    clear_req.clear()
                c.base_url = settings["url"]
                c.endpoints = DEFAULT_ENDPOINTS + settings["extra"]
                c.poll_once()
                snap = {"rows": list(c.rows()), "statuses": list(c.status.values()), "polls": c.polls}
            busy["polling"] = False
            results.put(snap)

    once_flag = threading.Event()
    threading.Thread(target=worker, daemon=True).start()

    def redraw():
        ep_tree.delete(*ep_tree.get_children())
        for s in snapshot["statuses"]:
            ep_tree.insert("", "end", text=s.endpoint,
                           values=("OK" if s.ok else "NG", s.content_type, s.size, s.error))
        q = filter_var.get().lower()
        tree.delete(*tree.get_children())
        shown = 0
        for r in snapshot["rows"]:
            if q and q not in (r["endpoint"] + " " + r["key"]).lower():
                continue
            v = r["last_value"]
            tree.insert("", "end", values=(r["endpoint"], r["key"], r["type"],
                                           v if len(v) < 300 else v[:300] + "…",
                                           r["min"], r["max"], r["seen_count"]))
            shown += 1
        update_status(shown)

    def update_status(shown=None):
        if shown is None:
            shown = len(tree.get_children())
        state = "取得中" if running.is_set() else "停止中"
        if busy["polling"]:
            state += "（通信中…）"
        ok = sum(1 for s in snapshot["statuses"] if s.ok)
        status_var.set(f"{state}  取得回数 {snapshot['polls']}  応答あり {ok}/{len(snapshot['statuses'])}"
                       f"  キー {len(snapshot['rows'])} (表示 {shown})")

    def pump():
        got = None
        try:
            while True:
                item = results.get_nowait()
                if item is not None:
                    got = item
        except queue.Empty:
            pass
        if got is not None:
            snapshot.update(got)
            redraw()
        else:
            update_status()
        root.after(200, pump)

    filter_var.trace_add("write", lambda *_: redraw())

    def toggle():
        read_settings()
        if running.is_set():
            running.clear()
            start_btn.config(text="開始")
        else:
            running.set()
            start_btn.config(text="停止")
            wake.set()
        update_status()

    def once():
        read_settings()
        once_flag.set()
        wake.set()

    def clear():
        clear_req.set()
        snapshot.update({"rows": [], "statuses": [], "polls": 0})
        redraw()
        if not lock.locked():
            with lock:
                if clear_req.is_set():
                    c.clear()
                    clear_req.clear()

    start_btn.config(command=toggle)
    once_btn.config(command=once)
    clear_btn.config(command=clear)

    def save(kind):
        stamp = time.strftime("%Y%m%d_%H%M%S")
        name = f"wt_api_keys_{stamp}.csv" if kind == "csv" else f"wt_api_dump_{stamp}.json"
        path = filedialog.asksaveasfilename(initialfile=name, defaultextension="." + kind,
                                            filetypes=[(kind.upper(), "*." + kind)])
        if not path:
            return
        # 通信中でも待たない: 取得が終わるまで最大数秒待ち、だめなら知らせる
        if not lock.acquire(timeout=5):
            messagebox.showwarning("保存", "通信中のため保存できませんでした。もう一度押してください。")
            return
        try:
            (c.save_csv if kind == "csv" else c.save_json)(path)
        finally:
            lock.release()
        messagebox.showinfo("保存", f"保存しました:\n{path}")

    redraw()
    root.after(200, pump)
    root.mainloop()
    running.clear()


def main():
    ap = argparse.ArgumentParser(description="War Thunder ローカルAPIの取得値一覧ツール")
    ap.add_argument("--url", default="http://127.0.0.1:8111")
    ap.add_argument("--interval", type=float, default=1.0, help="取得間隔(秒)")
    ap.add_argument("--extra", nargs="*", default=[], help="追加で試すパス (例: /info)")
    ap.add_argument("--cli", action="store_true", help="GUIを使わずに取得して保存")
    ap.add_argument("-n", "--count", type=int, default=5, help="--cli時の取得回数")
    ap.add_argument("--out", default=".", help="--cli時の保存先フォルダ")
    args = ap.parse_args()
    if args.cli:
        run_cli(args)
    else:
        try:
            run_gui(args)
        except ImportError:
            print("tkinterが見つかりません。--cli で実行してください。", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
