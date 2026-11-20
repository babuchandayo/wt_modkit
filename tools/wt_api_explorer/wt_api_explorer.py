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
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    c = Collector(args.url, endpoints=DEFAULT_ENDPOINTS + args.extra)
    lock = threading.Lock()
    running = threading.Event()

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
    ttk.Button(top, text="1回取得", command=lambda: threading.Thread(target=poll, daemon=True).start()).pack(side="left", padx=2)
    ttk.Button(top, text="クリア", command=lambda: (lock.acquire(), c.clear(), lock.release(), refresh())).pack(side="left", padx=2)
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

    def apply_settings():
        c.base_url = url_var.get().strip().rstrip("/")
        c.endpoints = DEFAULT_ENDPOINTS + [p if p.startswith("/") else "/" + p for p in extra_var.get().split()]

    def poll():
        with lock:
            apply_settings()
            c.poll_once()
        root.after(0, refresh)

    def refresh():
        with lock:
            rows = list(c.rows())
            statuses = list(c.status.values())
            polls = c.polls
        ep_tree.delete(*ep_tree.get_children())
        for s in statuses:
            ep_tree.insert("", "end", text=s.endpoint,
                           values=("OK" if s.ok else "NG", s.content_type, s.size, s.error))
        q = filter_var.get().lower()
        tree.delete(*tree.get_children())
        shown = 0
        for r in rows:
            if q and q not in (r["endpoint"] + " " + r["key"]).lower():
                continue
            v = r["last_value"]
            tree.insert("", "end", values=(r["endpoint"], r["key"], r["type"],
                                           v if len(v) < 300 else v[:300] + "…",
                                           r["min"], r["max"], r["seen_count"]))
            shown += 1
        status_var.set(f"{'取得中' if running.is_set() else '停止中'}  取得回数 {polls}  キー {len(rows)} (表示 {shown})")

    filter_var.trace_add("write", lambda *_: refresh())

    def loop():
        while running.is_set():
            poll()
            try:
                iv = max(0.2, float(interval_var.get()))
            except ValueError:
                iv = 1.0
            time.sleep(iv)

    def toggle():
        if running.is_set():
            running.clear()
            start_btn.config(text="開始")
        else:
            running.set()
            start_btn.config(text="停止")
            threading.Thread(target=loop, daemon=True).start()
        refresh()

    start_btn.config(command=toggle)

    def save(kind):
        stamp = time.strftime("%Y%m%d_%H%M%S")
        name = f"wt_api_keys_{stamp}.csv" if kind == "csv" else f"wt_api_dump_{stamp}.json"
        path = filedialog.asksaveasfilename(initialfile=name, defaultextension="." + kind,
                                            filetypes=[(kind.upper(), "*." + kind)])
        if not path:
            return
        with lock:
            (c.save_csv if kind == "csv" else c.save_json)(path)
        messagebox.showinfo("保存", f"保存しました:\n{path}")

    refresh()
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
