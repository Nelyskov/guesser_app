"""
Price Guesser — Parser GUI
Tkinter-based GUI for scraping products from Wildberries, Ozon, Lamoda, ЦУМ
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
import json
import os
import sys
from datetime import datetime

# Make sure project root is in path
sys.path.insert(0, os.path.dirname(__file__))

from db import Database
from parsers.wildberries import WildberriesParser
from parsers.ozon import OzonParser
from parsers.lamoda import LamodaParser
from parsers.tsum import TsumParser
from face_filter import check_url, check_file

PARSERS = {
    "Wildberries": WildberriesParser,
    "Ozon":        OzonParser,
    "Lamoda":      LamodaParser,
    "ЦУМ":         TsumParser,
}

# ── colour palette ──────────────────────────────────────────────
BG       = "#0f0f13"
BG2      = "#1a1a22"
BG3      = "#24242f"
ACCENT   = "#7c6af7"
ACCENT2  = "#a78bfa"
SUCCESS  = "#34d399"
WARN     = "#fbbf24"
ERR      = "#f87171"
TEXT     = "#e2e8f0"
TEXT2    = "#94a3b8"
BORDER   = "#2e2e3e"


class LogQueue:
    """Thread-safe log message queue."""
    def __init__(self):
        self.q = queue.Queue()

    def put(self, msg: str, level: str = "info"):
        self.q.put((msg, level))

    def drain(self):
        items = []
        try:
            while True:
                items.append(self.q.get_nowait())
        except queue.Empty:
            pass
        return items


class ParserGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Price Guesser · Parser")
        self.configure(bg=BG)
        self.geometry("980x720")
        self.minsize(820, 600)
        self.resizable(True, True)

        self.log_queue   = LogQueue()
        self.running     = False
        self.db          = None
        self.parse_thread = None

        self._apply_styles()
        self._build_ui()
        self._poll_logs()

    # ── styles ──────────────────────────────────────────────────
    def _apply_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(".",
            background=BG, foreground=TEXT,
            fieldbackground=BG3, troughcolor=BG2,
            bordercolor=BORDER, focuscolor=ACCENT,
            relief="flat", font=("Segoe UI", 10))

        style.configure("TFrame",   background=BG)
        style.configure("TLabel",   background=BG,  foreground=TEXT)
        style.configure("TEntry",   fieldbackground=BG3, foreground=TEXT,
                         insertcolor=TEXT, relief="flat", padding=6)

        style.configure("TCombobox",
            fieldbackground=BG3, foreground=TEXT,
            selectbackground=ACCENT, selectforeground=TEXT,
            arrowcolor=ACCENT2, relief="flat", padding=6)
        style.map("TCombobox", fieldbackground=[("readonly", BG3)])

        style.configure("TCheckbutton",
            background=BG, foreground=TEXT,
            indicatorcolor=BG3, indicatorrelief="flat")
        style.map("TCheckbutton",
            indicatorcolor=[("selected", ACCENT), ("active", ACCENT2)])

        style.configure("TNotebook",       background=BG2, tabmargins=0)
        style.configure("TNotebook.Tab",
            background=BG3, foreground=TEXT2,
            padding=[16, 8], font=("Segoe UI", 10))
        style.map("TNotebook.Tab",
            background=[("selected", BG)],
            foreground=[("selected", TEXT)])

        style.configure("Treeview",
            background=BG2, foreground=TEXT,
            fieldbackground=BG2, rowheight=28,
            borderwidth=0, relief="flat")
        style.configure("Treeview.Heading",
            background=BG3, foreground=ACCENT2,
            relief="flat", borderwidth=0)
        style.map("Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", TEXT)])

        style.configure("Horizontal.TProgressbar",
            troughcolor=BG3, background=ACCENT,
            thickness=6, relief="flat", borderwidth=0)

    # ── main UI ─────────────────────────────────────────────────
    def _build_ui(self):
        # ── header ──
        hdr = tk.Frame(self, bg=BG2, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="⬡", font=("Segoe UI", 22), bg=BG2,
                 fg=ACCENT).pack(side="left", padx=(18, 6), pady=8)
        tk.Label(hdr, text="Price Guesser", font=("Segoe UI", 15, "bold"),
                 bg=BG2, fg=TEXT).pack(side="left", pady=8)
        tk.Label(hdr, text="parser dashboard", font=("Segoe UI", 10),
                 bg=BG2, fg=TEXT2).pack(side="left", padx=(6, 0), pady=14)

        self.status_dot = tk.Label(hdr, text="●", font=("Segoe UI", 14),
                                   bg=BG2, fg=TEXT2)
        self.status_dot.pack(side="right", padx=(0, 18))
        self.status_lbl = tk.Label(hdr, text="Idle", font=("Segoe UI", 9),
                                   bg=BG2, fg=TEXT2)
        self.status_lbl.pack(side="right", padx=(0, 6))

        # ── body ──
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=12)

        # Левая панель — скроллируемый Canvas
        left_outer = tk.Frame(body, bg=BG, width=320)
        left_outer.pack(side="left", fill="y")
        left_outer.pack_propagate(False)

        canvas = tk.Canvas(left_outer, bg=BG, highlightthickness=0,
                           width=310)
        canvas.pack(side="left", fill="both", expand=True)

        left_sb = tk.Scrollbar(left_outer, orient="vertical",
                               command=canvas.yview)
        # Скроллбар появляется только когда нужен
        canvas.configure(yscrollcommand=left_sb.set)

        left = tk.Frame(canvas, bg=BG)
        left_window = canvas.create_window((0, 0), window=left,
                                           anchor="nw", width=300)

        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Показываем скроллбар только если контент не влезает
            total = canvas.bbox("all")
            visible = canvas.winfo_height()
            if total and total[3] > visible:
                left_sb.pack(side="right", fill="y")
            else:
                left_sb.pack_forget()

        left.bind("<Configure>", _on_frame_configure)

        # Скролл колёсиком мыши
        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        sep = tk.Frame(body, bg=BORDER, width=1)
        sep.pack(side="left", fill="y", padx=10)

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        self._build_settings(left)
        self._build_right(right)

    # ── LEFT: settings panel ─────────────────────────────────────
    def _build_settings(self, parent):
        def section(text):
            f = tk.Frame(parent, bg=BG)
            f.pack(fill="x", pady=(14, 4))
            tk.Label(f, text=text.upper(), font=("Segoe UI", 8, "bold"),
                     bg=BG, fg=ACCENT2).pack(anchor="w")
            tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=(0, 8))

        def lbl(p, t):
            tk.Label(p, text=t, font=("Segoe UI", 9),
                     bg=BG, fg=TEXT2).pack(anchor="w", pady=(6, 1))

        # ── DB ──
        section("База данных")
        lbl(parent, "Host")
        self.db_host = ttk.Entry(parent)
        self.db_host.insert(0, "localhost")
        self.db_host.pack(fill="x")

        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(4, 0))
        portf = tk.Frame(row, bg=BG)
        portf.pack(side="left", fill="x", expand=True)
        lbl(portf, "Port")
        self.db_port = ttk.Entry(portf, width=7)
        self.db_port.insert(0, "5432")
        self.db_port.pack(fill="x")
        dbf = tk.Frame(row, bg=BG)
        dbf.pack(side="left", fill="x", expand=True, padx=(8, 0))
        lbl(dbf, "Database")
        self.db_name = ttk.Entry(dbf)
        self.db_name.insert(0, "price_guesser")
        self.db_name.pack(fill="x")

        lbl(parent, "User")
        self.db_user = ttk.Entry(parent)
        self.db_user.insert(0, "postgres")
        self.db_user.pack(fill="x")

        lbl(parent, "Password")
        self.db_pass = ttk.Entry(parent, show="●")
        self.db_pass.pack(fill="x")

        self.btn_connect = tk.Button(parent, text="Подключить БД",
            font=("Segoe UI", 9, "bold"), bg=BG3, fg=ACCENT2,
            activebackground=ACCENT, activeforeground=TEXT,
            relief="flat", cursor="hand2", pady=7,
            command=self._connect_db)
        self.btn_connect.pack(fill="x", pady=(10, 0))

        # ── Parser ──
        section("Парсер")

        lbl(parent, "Сайт")
        self.site_var = tk.StringVar(value="Wildberries")
        self.site_cb  = ttk.Combobox(parent, textvariable=self.site_var,
            values=list(PARSERS.keys()), state="readonly")
        self.site_cb.pack(fill="x")

        lbl(parent, "Поисковый запрос")
        self.query_entry = ttk.Entry(parent)
        self.query_entry.insert(0, "кроссовки")
        self.query_entry.pack(fill="x")

        row2 = tk.Frame(parent, bg=BG)
        row2.pack(fill="x", pady=(4, 0))
        mxf = tk.Frame(row2, bg=BG)
        mxf.pack(side="left", fill="x", expand=True)
        lbl(mxf, "Макс. товаров")
        self.max_var = tk.StringVar(value="100")
        self.max_spin = ttk.Combobox(mxf, textvariable=self.max_var,
            values=["50", "100", "200", "500"], width=7)
        self.max_spin.pack(fill="x")

        dlf = tk.Frame(row2, bg=BG)
        dlf.pack(side="left", fill="x", expand=True, padx=(8, 0))
        lbl(dlf, "Задержка (сек)")
        self.delay_var = tk.StringVar(value="1.5")
        self.delay_spin = ttk.Combobox(dlf, textvariable=self.delay_var,
            values=["0.5", "1.0", "1.5", "2.0", "3.0"], width=7)
        self.delay_spin.pack(fill="x")

        lbl(parent, "Мин. цена (₽)")
        self.minprice_entry = ttk.Entry(parent)
        self.minprice_entry.insert(0, "500")
        self.minprice_entry.pack(fill="x")

        lbl(parent, "Макс. цена (₽)")
        self.maxprice_entry = ttk.Entry(parent)
        self.maxprice_entry.insert(0, "0")
        self.maxprice_entry.pack(fill="x", pady=(0, 4))
        tk.Label(parent, text="0 = без ограничений", font=("Segoe UI", 8),
                 bg=BG, fg=TEXT2).pack(anchor="w")

        # ── Фильтр лиц ──
        section("Фильтр фото")

        self.face_filter_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text="Пропускать фото с лицами",
            variable=self.face_filter_var).pack(anchor="w")

        tk.Label(parent, text="Строгость:", font=("Segoe UI", 9),
                 bg=BG, fg=TEXT2).pack(anchor="w", pady=(8, 1))
        self.face_sens_var = tk.StringVar(value="Средняя")
        ttk.Combobox(parent, textvariable=self.face_sens_var,
            values=["Мягкая", "Средняя", "Строгая"],
            state="readonly").pack(fill="x")
        tk.Label(parent,
            text="Мягкая = меньше пропусков\nСтрогая = меньше ложных срабатываний",
            font=("Segoe UI", 8), bg=BG, fg=TEXT2, justify="left").pack(anchor="w")

        # ── Actions ──
        section("Управление")

        self.btn_start = tk.Button(parent, text="▶  Запустить парсинг",
            font=("Segoe UI", 10, "bold"), bg=ACCENT, fg=TEXT,
            activebackground=ACCENT2, activeforeground=TEXT,
            relief="flat", cursor="hand2", pady=10,
            command=self._start_parsing)
        self.btn_start.pack(fill="x")

        self.btn_stop = tk.Button(parent, text="■  Остановить",
            font=("Segoe UI", 10), bg=BG3, fg=ERR,
            activebackground=ERR, activeforeground=TEXT,
            relief="flat", cursor="hand2", pady=10,
            command=self._stop_parsing, state="disabled")
        self.btn_stop.pack(fill="x", pady=(6, 0))

        self.btn_copy_log = tk.Button(parent, text="📋  Копировать лог",
            font=("Segoe UI", 9), bg=BG3, fg=TEXT2,
            activebackground=BG2, activeforeground=TEXT,
            relief="flat", cursor="hand2", pady=7,
            command=self._copy_log)
        self.btn_copy_log.pack(fill="x", pady=(6, 0))

        self.btn_clear = tk.Button(parent, text="🗑  Очистить лог",
            font=("Segoe UI", 9), bg=BG3, fg=TEXT2,
            activebackground=BG2, activeforeground=TEXT,
            relief="flat", cursor="hand2", pady=7,
            command=self._clear_log)
        self.btn_clear.pack(fill="x", pady=(6, 0))

        # ── progress ──
        self.progress_var = tk.IntVar(value=0)
        self.progress     = ttk.Progressbar(parent, variable=self.progress_var,
            maximum=100, style="Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(14, 2))
        self.progress_lbl = tk.Label(parent, text="0 / 0",
            font=("Segoe UI", 9), bg=BG, fg=TEXT2)
        self.progress_lbl.pack(anchor="e")

    # ── RIGHT: tabs ──────────────────────────────────────────────
    def _build_right(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True)

        # tab 1: log
        log_frame = tk.Frame(nb, bg=BG)
        nb.add(log_frame, text="  Лог  ")

        self.log_text = scrolledtext.ScrolledText(
            log_frame, bg=BG2, fg=TEXT,
            font=("Consolas", 9), relief="flat",
            insertbackground=TEXT, wrap="word",
            selectbackground=ACCENT, padx=10, pady=10,
            state="disabled")
        self.log_text.pack(fill="both", expand=True)

        self.log_text.tag_configure("info",    foreground=TEXT)
        self.log_text.tag_configure("success", foreground=SUCCESS)
        self.log_text.tag_configure("warn",    foreground=WARN)
        self.log_text.tag_configure("error",   foreground=ERR)
        self.log_text.tag_configure("dim",     foreground=TEXT2)
        self.log_text.tag_configure("accent",  foreground=ACCENT2)

        # tab 2: results table
        tbl_frame = tk.Frame(nb, bg=BG)
        nb.add(tbl_frame, text="  Товары  ")
        self._build_table(tbl_frame)

        # tab 3: stats
        stats_frame = tk.Frame(nb, bg=BG)
        nb.add(stats_frame, text="  Статистика  ")
        self._build_stats(stats_frame)

    def _build_table(self, parent):
        cols = ("id", "site", "name", "price", "url")
        self.tree = ttk.Treeview(parent, columns=cols,
            show="headings", selectmode="browse")

        widths = {"id": 60, "site": 110, "name": 340, "price": 100, "url": 200}
        heads  = {"id": "ID", "site": "Сайт", "name": "Название",
                  "price": "Цена ₽", "url": "Ссылка"}
        for c in cols:
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=widths[c], minwidth=40)

        sb_y = ttk.Scrollbar(parent, orient="vertical",   command=self.tree.yview)
        sb_x = ttk.Scrollbar(parent, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        sb_y.pack(side="right",  fill="y")
        sb_x.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

        tk.Button(parent, text="Обновить из БД",
            font=("Segoe UI", 9), bg=BG3, fg=ACCENT2,
            activebackground=ACCENT, activeforeground=TEXT,
            relief="flat", cursor="hand2", pady=6,
            command=self._refresh_table).pack(fill="x", side="bottom")

    def _build_stats(self, parent):
        self.stats_frame_inner = tk.Frame(parent, bg=BG)
        self.stats_frame_inner.pack(fill="both", expand=True, padx=20, pady=20)
        self._render_stats()

    # ── DB connect ───────────────────────────────────────────────
    def _connect_db(self):
        cfg = {
            "host":     self.db_host.get().strip(),
            "port":     int(self.db_port.get().strip() or 5432),
            "dbname":   self.db_name.get().strip(),
            "user":     self.db_user.get().strip(),
            "password": self.db_pass.get(),
        }
        try:
            self.db = Database(cfg)
            self.db.init_schema()
            self._log("✓ БД подключена и схема готова", "success")
            self.btn_connect.configure(bg=SUCCESS, fg=BG, text="✓ Подключено")
            self._set_status("Connected", SUCCESS)
        except Exception as e:
            self._log(f"✗ Ошибка подключения: {e}", "error")
            messagebox.showerror("DB Error", str(e))

    # ── parse control ────────────────────────────────────────────
    def _start_parsing(self):
        if self.running:
            return
        if not self.db:
            messagebox.showwarning("Нет БД", "Сначала подключите базу данных.")
            return

        site      = self.site_var.get()
        query     = self.query_entry.get().strip()
        max_items = int(self.max_var.get() or 100)
        delay     = float(self.delay_var.get() or 1.5)
        min_price = int(self.minprice_entry.get() or 0)
        max_price = int(self.maxprice_entry.get() or 0)
        use_face_filter = self.face_filter_var.get()
        face_sens       = self.face_sens_var.get()

        if not query:
            messagebox.showwarning("Пустой запрос", "Введите поисковый запрос.")
            return

        self.running = True
        self._set_status("Parsing…", ACCENT2)
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.progress_var.set(0)
        self.progress.configure(maximum=max_items)

        ParserCls = PARSERS[site]

        self.parse_thread = threading.Thread(
            target=self._run_parser,
            args=(ParserCls, query, max_items, delay, min_price, max_price,
                  use_face_filter, face_sens),
            daemon=True)
        self.parse_thread.start()

    def _run_parser(self, ParserCls, query, max_items, delay,
                    min_price, max_price, use_face_filter=False, face_sens="Средняя"):
        # Параметры строгости фильтра лиц
        sens_map = {
            "Мягкая":  (1.05, 3),
            "Средняя": (1.1,  4),
            "Строгая": (1.2,  6),
        }
        scale, neighbors = sens_map.get(face_sens, (1.1, 4))

        try:
            parser = ParserCls(
                log_fn   = self.log_queue.put,
                stop_fn  = lambda: not self.running,
                delay    = delay,
                min_price= min_price,
                max_price= max_price,
            )
            saved = 0
            for product in parser.parse(query, max_items):
                if not self.running:
                    break

                # ── Фильтр лиц ──────────────────────────────────
                if use_face_filter and product.get("image_url"):
                    try:
                        from face_filter import download_image, has_face
                        img = download_image(product["image_url"])
                        if img is not None and has_face(
                                img, min_confidence=scale,
                                min_neighbors=neighbors):
                            self.log_queue.put(
                                f"  👤 пропуск (лицо): {product['name'][:50]}",
                                "warn")
                            continue
                    except Exception as fe:
                        self.log_queue.put(f"  face_filter error: {fe}", "dim")

                try:
                    self.db.upsert_product(product)
                    saved += 1
                    self.log_queue.put(
                        f"✓ [{product['site']}] {product['name'][:60]}  "
                        f"— {product['price']:,}₽", "success")
                    self.after(0, self._inc_progress, saved, max_items)
                except Exception as e:
                    self.log_queue.put(f"  DB error: {e}", "error")

            self.log_queue.put(
                f"\n{'─'*50}\nГотово! Сохранено товаров: {saved}", "accent")
        except Exception as e:
            self.log_queue.put(f"Критическая ошибка: {e}", "error")
        finally:
            self.after(0, self._parsing_done)

    def _inc_progress(self, done, total):
        self.progress_var.set(done)
        self.progress_lbl.configure(text=f"{done} / {total}")

    def _parsing_done(self):
        self.running = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self._set_status("Idle", TEXT2)
        self._refresh_table()
        self._render_stats()

    def _stop_parsing(self):
        self.running = False
        self._log("Остановка…", "warn")
        self.btn_stop.configure(state="disabled")

    # ── table / stats ────────────────────────────────────────────
    def _refresh_table(self):
        if not self.db:
            return
        for row in self.tree.get_children():
            self.tree.delete(row)
        for p in self.db.get_all_products():
            name_short = p["name"][:55] + "…" if len(p["name"]) > 55 else p["name"]
            self.tree.insert("", "end", values=(
                p["id"], p["site"], name_short,
                f"{p['price']:,}", p["image_url"][:60]))

    def _render_stats(self):
        for w in self.stats_frame_inner.winfo_children():
            w.destroy()

        stats = self.db.get_stats() if self.db else {}

        items = [
            ("Всего товаров",      stats.get("total", 0),          ACCENT2),
            ("Уникальных сайтов",  stats.get("sites", 0),          SUCCESS),
            ("Средняя цена ₽",     f"{stats.get('avg_price',0):,.0f}", WARN),
            ("Мин. цена ₽",        f"{stats.get('min_price',0):,}", TEXT),
            ("Макс. цена ₽",       f"{stats.get('max_price',0):,}", TEXT),
        ]
        for i, (label, value, color) in enumerate(items):
            card = tk.Frame(self.stats_frame_inner, bg=BG2,
                            relief="flat", padx=20, pady=14)
            card.grid(row=i//3, column=i%3, padx=8, pady=8, sticky="nsew")
            tk.Label(card, text=str(value),
                font=("Segoe UI", 22, "bold"), bg=BG2, fg=color).pack()
            tk.Label(card, text=label,
                font=("Segoe UI", 9), bg=BG2, fg=TEXT2).pack()

        for c in range(3):
            self.stats_frame_inner.columnconfigure(c, weight=1)

        if self.db:
            by_site = self.db.get_stats_by_site()
            if by_site:
                tk.Frame(self.stats_frame_inner, bg=BORDER, height=1)\
                    .grid(row=2, column=0, columnspan=3, sticky="ew",
                          pady=(12, 4))
                tk.Label(self.stats_frame_inner,
                    text="ПО САЙТАМ", font=("Segoe UI", 8, "bold"),
                    bg=BG, fg=ACCENT2)\
                    .grid(row=3, column=0, columnspan=3, sticky="w", pady=(0, 6))
                for j, (site, cnt, avg) in enumerate(by_site):
                    sf = tk.Frame(self.stats_frame_inner, bg=BG2, padx=14, pady=10)
                    sf.grid(row=4 + j//3, column=j%3, padx=8, pady=4, sticky="nsew")
                    tk.Label(sf, text=site, font=("Segoe UI", 10, "bold"),
                             bg=BG2, fg=TEXT).pack(anchor="w")
                    tk.Label(sf, text=f"{cnt} товаров · ср. {avg:,.0f}₽",
                             font=("Segoe UI", 9), bg=BG2, fg=TEXT2).pack(anchor="w")

    # ── log helpers ──────────────────────────────────────────────
    def _log(self, msg: str, level: str = "info"):
        self.log_queue.put(msg, level)

    def _poll_logs(self):
        for msg, level in self.log_queue.drain():
            self._append_log(msg, level)
        self.after(120, self._poll_logs)

    def _append_log(self, msg: str, level: str):
        self.log_text.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] ", "dim")
        self.log_text.insert("end", msg + "\n", level)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _copy_log(self):
        text = self.log_text.get("1.0", "end")
        self.clipboard_clear()
        self.clipboard_append(text)
        self.btn_copy_log.configure(text="✓  Скопировано!")
        self.after(2000, lambda: self.btn_copy_log.configure(text="📋  Копировать лог"))

    def _set_status(self, text: str, color: str):
        self.status_lbl.configure(text=text)
        self.status_dot.configure(fg=color)


if __name__ == "__main__":
    app = ParserGUI()
    app.mainloop()
