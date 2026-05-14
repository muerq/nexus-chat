"""
Простой мессенджер — Клиент (Tkinter GUI)
Запуск: python client.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import asyncio
import threading
import json
import socket

HOST = "127.0.0.1"
PORT = 9999

# ─── Цветовая схема ───────────────────────────────────────────────
BG        = "#0e0e14"
BG2       = "#161622"
BG3       = "#1e1e2e"
ACCENT    = "#7c6af7"
ACCENT2   = "#a78bfa"
MSG_OWN   = "#2d2257"
MSG_OTHER = "#1a1a2e"
TEXT      = "#e2e2f0"
TEXT_DIM  = "#6b6b8a"
GREEN     = "#4ade80"
BORDER    = "#2a2a40"
FONT_MAIN = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_SMALL= ("Segoe UI", 9)
FONT_BIG  = ("Segoe UI", 18, "bold")


class MessengerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Мессенджер")
        self.geometry("920x640")
        self.minsize(700, 500)
        self.configure(bg=BG)

        self.username = ""
        self.reader = None
        self.writer = None
        self.loop = asyncio.new_event_loop()
        self.running = False
        self.users: list[str] = []

        self._setup_styles()
        self._build_login_screen()

    # ─── Стили ───────────────────────────────────────────────────
    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Sidebar.TFrame", background=BG2)
        style.configure("Main.TFrame",    background=BG)
        style.configure(
            "User.TLabel",
            background=BG2, foreground=TEXT,
            font=FONT_MAIN, padding=(8, 4),
        )
        style.configure(
            "Online.TLabel",
            background=BG2, foreground=GREEN,
            font=FONT_SMALL,
        )
        style.configure(
            "Title.TLabel",
            background=BG2, foreground=TEXT,
            font=("Segoe UI", 13, "bold"),
        )

    # ─── Экран входа ─────────────────────────────────────────────
    def _build_login_screen(self):
        self.login_frame = tk.Frame(self, bg=BG)
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            self.login_frame, text="💬", font=("Segoe UI", 48),
            bg=BG, fg=ACCENT,
        ).pack(pady=(0, 8))

        tk.Label(
            self.login_frame, text="Мессенджер",
            font=FONT_BIG, bg=BG, fg=TEXT,
        ).pack()

        tk.Label(
            self.login_frame, text="Простой чат на Python",
            font=FONT_SMALL, bg=BG, fg=TEXT_DIM,
        ).pack(pady=(2, 24))

        # Поле имени
        tk.Label(
            self.login_frame, text="Ваше имя",
            font=FONT_SMALL, bg=BG, fg=TEXT_DIM,
        ).pack(anchor="w")

        self.name_var = tk.StringVar()
        name_entry = tk.Entry(
            self.login_frame, textvariable=self.name_var,
            font=FONT_MAIN, bg=BG3, fg=TEXT,
            insertbackground=ACCENT, relief="flat",
            width=26,
        )
        name_entry.pack(ipady=8, padx=2, pady=(4, 16))
        name_entry.bind("<Return>", lambda e: self._connect())
        name_entry.focus()

        # Поля сервера
        row = tk.Frame(self.login_frame, bg=BG)
        row.pack(fill="x", pady=(0, 20))

        tk.Label(row, text="Хост", font=FONT_SMALL, bg=BG, fg=TEXT_DIM).pack(anchor="w")
        self.host_var = tk.StringVar(value=HOST)
        tk.Entry(
            row, textvariable=self.host_var, font=FONT_MAIN,
            bg=BG3, fg=TEXT, insertbackground=ACCENT,
            relief="flat", width=14,
        ).pack(side="left", ipady=6, padx=(0, 8))

        tk.Label(row, text="Порт", font=FONT_SMALL, bg=BG, fg=TEXT_DIM).pack(side="left", padx=(0, 4))
        self.port_var = tk.StringVar(value=str(PORT))
        tk.Entry(
            row, textvariable=self.port_var, font=FONT_MAIN,
            bg=BG3, fg=TEXT, insertbackground=ACCENT,
            relief="flat", width=7,
        ).pack(side="left", ipady=6)

        self.connect_btn = tk.Button(
            self.login_frame, text="Войти в чат →",
            font=FONT_BOLD, bg=ACCENT, fg="#ffffff",
            activebackground=ACCENT2, activeforeground="#ffffff",
            relief="flat", cursor="hand2", bd=0,
            command=self._connect, padx=20, pady=10,
        )
        self.connect_btn.pack(fill="x")

        self.status_lbl = tk.Label(
            self.login_frame, text="",
            font=FONT_SMALL, bg=BG, fg=TEXT_DIM,
        )
        self.status_lbl.pack(pady=(10, 0))

    def _connect(self):
        name = self.name_var.get().strip()
        if not name:
            self.status_lbl.config(text="Введите имя", fg="#f87171")
            return
        host = self.host_var.get().strip()
        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            self.status_lbl.config(text="Неверный порт", fg="#f87171")
            return

        self.username = name
        self.status_lbl.config(text="Подключение...", fg=TEXT_DIM)
        self.connect_btn.config(state="disabled")

        threading.Thread(
            target=self._run_async_connect,
            args=(host, port),
            daemon=True,
        ).start()

    def _run_async_connect(self, host, port):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._async_connect(host, port))
        except Exception as e:
            self.after(0, lambda: self._on_connect_error(str(e)))

    async def _async_connect(self, host, port):
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=5
            )
        except Exception:
            raise ConnectionError(f"Не удалось подключиться к {host}:{port}")

        self.reader = reader
        self.writer = writer

        # Отправить имя
        await self._send({"type": "join", "username": self.username})

        # Ждём ответа сервера
        raw = await asyncio.wait_for(reader.readline(), timeout=5)
        msg = json.loads(raw.decode())

        if msg.get("type") == "error":
            raise ValueError(msg.get("text", "Ошибка"))

        # Успешное подключение
        self.running = True
        self.after(0, self._build_chat_screen)
        self.after(0, lambda: self._on_server_msg(msg))

        # Запустить цикл чтения
        await self._read_loop()

    async def _read_loop(self):
        try:
            while self.running:
                raw = await self.reader.readline()
                if not raw:
                    break
                msg = json.loads(raw.decode())
                self.after(0, lambda m=msg: self._on_server_msg(m))
        except Exception:
            pass
        finally:
            self.after(0, self._on_disconnect)

    async def _send(self, data: dict):
        if self.writer:
            line = (json.dumps(data, ensure_ascii=False) + "\n").encode()
            self.writer.write(line)
            await self.writer.drain()

    def _send_nowait(self, data: dict):
        asyncio.run_coroutine_threadsafe(self._send(data), self.loop)

    # ─── Ошибка подключения ──────────────────────────────────────
    def _on_connect_error(self, err: str):
        self.status_lbl.config(text=f"Ошибка: {err}", fg="#f87171")
        self.connect_btn.config(state="normal")

    # ─── Экран чата ──────────────────────────────────────────────
    def _build_chat_screen(self):
        self.login_frame.destroy()
        self.title(f"Мессенджер — {self.username}")

        pane = tk.PanedWindow(self, orient="horizontal", bg=BG, bd=0, sashwidth=1, sashrelief="flat")
        pane.pack(fill="both", expand=True)

        # Боковая панель (список пользователей)
        sidebar = tk.Frame(pane, bg=BG2, width=200)
        pane.add(sidebar, minsize=160)

        tk.Label(
            sidebar, text="💬 Онлайн",
            font=("Segoe UI", 13, "bold"), bg=BG2, fg=TEXT,
            pady=16, padx=16,
        ).pack(fill="x")

        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x")

        self.users_frame = tk.Frame(sidebar, bg=BG2)
        self.users_frame.pack(fill="both", expand=True, pady=8)

        # Нижняя часть сайдбара — имя пользователя
        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x")
        tk.Label(
            sidebar, text=f"● {self.username}",
            font=FONT_SMALL, bg=BG2, fg=GREEN,
            pady=12, padx=16, anchor="w",
        ).pack(fill="x")

        # Главная область
        main = tk.Frame(pane, bg=BG)
        pane.add(main, minsize=400)

        # Заголовок
        header = tk.Frame(main, bg=BG3, height=52)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header, text="# общий чат",
            font=("Segoe UI", 13, "bold"), bg=BG3, fg=TEXT,
            padx=20,
        ).pack(side="left", fill="y")

        # Область сообщений
        msg_container = tk.Frame(main, bg=BG)
        msg_container.pack(fill="both", expand=True, padx=0, pady=0)

        self.canvas = tk.Canvas(msg_container, bg=BG, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(msg_container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.msg_frame = tk.Frame(self.canvas, bg=BG)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.msg_frame, anchor="nw")

        self.msg_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Поле ввода
        input_bar = tk.Frame(main, bg=BG3, pady=12, padx=16)
        input_bar.pack(fill="x", side="bottom")

        self.msg_entry = tk.Text(
            input_bar, height=1, font=FONT_MAIN,
            bg=BG2, fg=TEXT, insertbackground=ACCENT,
            relief="flat", wrap="word", padx=12, pady=8,
        )
        self.msg_entry.pack(side="left", fill="x", expand=True, ipady=2)
        self.msg_entry.bind("<Return>", self._on_enter)
        self.msg_entry.bind("<Shift-Return>", lambda e: None)
        self.msg_entry.focus()

        send_btn = tk.Button(
            input_bar, text="➤",
            font=("Segoe UI", 14), bg=ACCENT, fg="white",
            activebackground=ACCENT2, activeforeground="white",
            relief="flat", cursor="hand2", bd=0,
            command=self._send_message, padx=14, pady=6,
        )
        send_btn.pack(side="right", padx=(10, 0))

    def _on_frame_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ─── Отправка ────────────────────────────────────────────────
    def _on_enter(self, event):
        self._send_message()
        return "break"

    def _send_message(self):
        text = self.msg_entry.get("1.0", "end").strip()
        if not text:
            return
        self.msg_entry.delete("1.0", "end")
        self._send_nowait({"type": "message", "text": text})

    # ─── Обработка сообщений от сервера ─────────────────────────
    def _on_server_msg(self, msg: dict):
        t = msg.get("type")
        if t in ("message", "welcome", "system"):
            self._add_message(msg)
        if "users" in msg:
            self._update_users(msg["users"])

    def _add_message(self, msg: dict):
        t = msg.get("type")
        time_str = msg.get("time", "")

        if t == "system" or t == "welcome":
            text = msg.get("text", "")
            lbl = tk.Label(
                self.msg_frame, text=f"{text}  {time_str}",
                font=FONT_SMALL, bg=BG, fg=TEXT_DIM,
                pady=4,
            )
            lbl.pack(fill="x", padx=20, pady=2)
        elif t == "message":
            username = msg.get("username", "?")
            text = msg.get("text", "")
            is_own = (username == self.username)

            outer = tk.Frame(self.msg_frame, bg=BG)
            outer.pack(fill="x", padx=16, pady=3, anchor="e" if is_own else "w")

            bubble_color = MSG_OWN if is_own else MSG_OTHER
            align = "e" if is_own else "w"

            bubble = tk.Frame(outer, bg=bubble_color, padx=12, pady=8)
            bubble.pack(anchor=align, padx=(120 if is_own else 0, 0 if is_own else 120))

            if not is_own:
                tk.Label(
                    bubble, text=username,
                    font=("Segoe UI", 9, "bold"),
                    bg=bubble_color, fg=ACCENT2,
                ).pack(anchor="w")

            tk.Label(
                bubble, text=text,
                font=FONT_MAIN, bg=bubble_color, fg=TEXT,
                wraplength=400, justify="left",
            ).pack(anchor="w")

            tk.Label(
                bubble, text=time_str,
                font=("Segoe UI", 8),
                bg=bubble_color, fg=TEXT_DIM,
            ).pack(anchor="e")

        self.after(50, self._scroll_bottom)

    def _scroll_bottom(self):
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def _update_users(self, users: list[str]):
        for w in self.users_frame.winfo_children():
            w.destroy()
        for u in users:
            color = GREEN if u == self.username else TEXT_DIM
            row = tk.Frame(self.users_frame, bg=BG2)
            row.pack(fill="x", padx=8, pady=2)
            tk.Label(
                row, text="●", font=FONT_SMALL,
                bg=BG2, fg=color,
            ).pack(side="left", padx=(4, 4))
            tk.Label(
                row, text=u, font=FONT_MAIN,
                bg=BG2, fg=TEXT,
            ).pack(side="left")

    # ─── Отключение ──────────────────────────────────────────────
    def _on_disconnect(self):
        self.running = False
        messagebox.showinfo("Отключено", "Соединение с сервером разорвано.")
        self.destroy()

    def destroy(self):
        self.running = False
        if self.writer:
            try:
                self.writer.close()
            except Exception:
                pass
        self.loop.call_soon_threadsafe(self.loop.stop)
        super().destroy()


if __name__ == "__main__":
    app = MessengerApp()
    app.mainloop()
