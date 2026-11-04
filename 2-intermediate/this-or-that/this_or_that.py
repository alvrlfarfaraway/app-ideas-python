"""This or That: dua gambar muncul, pilih yang lebih kamu suka, lalu pasangan berikutnya tampil.

Setiap pilihan disimpan di SQLite, dan papan peringkat menampilkan 10 pilihan
teratas. Gambar bawaan adalah kartu makanan dan minuman yang digambar dari
emoji berwarna (font Segoe UI Emoji). Folder gambar sendiri juga bisa dipakai.

Jalankan:
    python this_or_that.py
    python this_or_that.py --folder "C:/foto/kucing"     # pakai gambar sendiri (.jpg/.png)
    python this_or_that.py --top                          # papan peringkat di terminal
"""

import argparse
import os
import random
import sqlite3
import sys
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

DEFAULT_DB = os.path.join(os.path.expanduser("~"), ".app-ideas-python", "this-or-that.db")
CARD = (320, 320)
ANIMATION_FRAMES = 12
FRAME_MS = 16

BUILTIN = (  # (nama, emoji, warna latar)
    ("Bakso", "🍲", "#f4d6c6"), ("Mie Ayam", "🍜", "#ffe2b8"), ("Nasi Goreng", "🍛", "#ffd4a3"),
    ("Sate", "🍢", "#f7cfc4"), ("Martabak", "🥞", "#f9e3b0"), ("Pisang Goreng", "🍌", "#fff0a8"),
    ("Es Kelapa", "🥥", "#d9efe2"), ("Kopi", "☕", "#e6d5c8"), ("Teh Manis", "🍵", "#dcebc8"),
    ("Jeruk", "🍊", "#ffdcb3"), ("Durian", "🍈", "#e5efc0"), ("Pizza", "🍕", "#ffd9b8"),
    ("Burger", "🍔", "#f2dcc0"), ("Sushi", "🍣", "#dfe8f3"), ("Es Krim", "🍦", "#f3dcef"),
    ("Donat", "🍩", "#f6d2dd"),
)
IMAGE_TYPES = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")


def _font(names, size):
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def emoji_card(name, emoji, color, size=CARD):
    """Kartu bergambar emoji berwarna dengan nama di bawahnya."""
    image = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(image)
    emoji_font = _font(["seguiemj.ttf", "NotoColorEmoji.ttf"], 109)
    draw.text((size[0] / 2, size[1] * 0.42), emoji, font=emoji_font, anchor="mm", embedded_color=True)
    label = _font(["segoeuib.ttf", "DejaVuSans-Bold.ttf"], 30)
    draw.text((size[0] / 2, size[1] * 0.84), name, font=label, anchor="mm", fill="#2b2b2b")
    return image


def photo_card(path, size=CARD):
    """Gambar dari berkas, dipotong tengah menjadi persegi, dengan nama berkas di bawahnya."""
    with Image.open(path) as source:
        image = source.convert("RGB")
    side = min(image.size)
    left, top = (image.width - side) // 2, (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side)).resize(size, Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image)
    name = os.path.splitext(os.path.basename(path))[0].replace("_", " ").replace("-", " ")
    font = _font(["segoeuib.ttf", "DejaVuSans-Bold.ttf"], 26)
    draw.rectangle((0, size[1] - 50, size[0], size[1]), fill="#000000")
    draw.text((size[0] / 2, size[1] - 25), name[:22], font=font, anchor="mm", fill="#ffffff")
    return image


def load_items(folder=None):
    """Daftar (nama, fungsi pembuat gambar). Minimal dua item."""
    if folder:
        files = sorted(f for f in os.listdir(folder) if f.lower().endswith(IMAGE_TYPES))
        items = [(os.path.splitext(f)[0], (lambda p=os.path.join(folder, f): photo_card(p))) for f in files]
    else:
        items = [(name, (lambda n=name, e=emoji, c=color: emoji_card(n, e, c))) for name, emoji, color in BUILTIN]
    if len(items) < 2:
        raise ValueError("Butuh minimal dua gambar.")
    if len({name for name, _ in items}) != len(items):
        raise ValueError("Nama gambar harus berbeda-beda.")
    return items


class Matchmaker:
    """Urutan pasangan: setiap item tampil seadil mungkin, dan pasangan yang sama tidak muncul berturut-turut."""

    def __init__(self, names, rng=None):
        if len(names) < 2:
            raise ValueError("Butuh minimal dua item.")
        self.names = list(names)
        self.rng = rng or random.Random()
        self.queue = []
        self.last = None

    def next_pair(self):
        for _ in range(20):
            if len(self.queue) < 2:
                order = self.names[:]
                self.rng.shuffle(order)
                self.queue += order
            a, b = self.queue.pop(0), self.queue.pop(0)
            if a == b:  # bisa terjadi di sambungan antara dua putaran acak
                self.queue.insert(0, b)
                continue
            pair = (a, b) if self.rng.random() < 0.5 else (b, a)
            if self.last is None or set(pair) != set(self.last):
                self.last = pair
                return pair
        self.last = pair
        return pair


def connect(path):
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("""CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, winner TEXT NOT NULL, loser TEXT NOT NULL, voted_at TEXT NOT NULL,
        CHECK (winner <> loser))""")
    return db


def vote(db, winner, loser, clock=datetime.now):
    with db:
        db.execute("INSERT INTO votes (winner, loser, voted_at) VALUES (?, ?, ?)",
                   (winner, loser, clock().isoformat(timespec="seconds")))


def leaderboard(db, limit=10):
    """[(nama, menang, tampil, persen menang)] urut menang terbanyak, lalu persentase, lalu nama."""
    rows = db.execute("""
        SELECT name, SUM(won) AS wins, COUNT(*) AS shown FROM (
            SELECT winner AS name, 1 AS won FROM votes UNION ALL SELECT loser, 0 FROM votes)
        GROUP BY name""").fetchall()
    table = [(name, wins, shown, 100 * wins / shown) for name, wins, shown in rows]
    table.sort(key=lambda r: (-r[1], -r[3], r[0]))
    return table[:limit]


def format_leaderboard(rows):
    if not rows:
        return "Belum ada suara."
    lines = [f"{'#':>2}  {'Pilihan':<16} {'Menang':>6} {'Tampil':>6} {'%':>5}"]
    for rank, (name, wins, shown, percent) in enumerate(rows, start=1):
        lines.append(f"{rank:>2}. {name:<16} {wins:>6} {shown:>6} {percent:>4.0f}%")
    return "\n".join(lines)


# --- tampilan Tkinter --------------------------------------------------------------

class ThisOrThatApp:
    def __init__(self, root, items, db, rng=None, animate=True):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.root = root
        self.db = db
        self.items = dict(items)
        self.matcher = Matchmaker(list(self.items), rng)
        self.animate = animate
        self.cache = {}
        self.pair = None
        self.busy = False
        root.title("This or That")
        root.resizable(False, False)
        ttk.Label(root, text="Mana yang lebih kamu suka?", font=("Segoe UI", 16, "bold"), padding=(0, 10, 0, 0)).pack()
        ttk.Label(root, text="Klik gambar, atau tekan ← / →", foreground="#666").pack()
        self.width = CARD[0] * 2 + 160
        self.canvas = tk.Canvas(root, width=self.width, height=CARD[1] + 30, highlightthickness=0, background="#f4f2ec")
        self.canvas.pack(padx=12, pady=8)
        self.canvas.create_text(self.width / 2, CARD[1] / 2 + 15, text="atau", font=("Segoe UI", 14, "bold"),
                                fill="#888")
        self.cards = [self.canvas.create_image(0, 15, anchor="nw") for _ in range(2)]
        self.canvas.tag_raise(self.canvas.find_all()[0])  # teks "atau" di atas kartu yang sedang meluncur
        self.frames = [self.canvas.create_rectangle(0, 0, 0, 0, outline="", width=6) for _ in range(2)]
        for side, card in enumerate(self.cards):
            self.canvas.tag_bind(card, "<Button-1>", lambda _e, s=side: self.choose(s))
        bar = ttk.Frame(root, padding=(12, 0))
        bar.pack(fill="x")
        ttk.Button(bar, text="Lewati", command=self.show_next).pack(side="left")
        self.status = tk.StringVar()
        ttk.Label(bar, textvariable=self.status, foreground="#555").pack(side="left", padx=10)
        board = ttk.LabelFrame(root, text="10 teratas", padding=8)
        board.pack(fill="x", padx=12, pady=10)
        self.board = tk.Text(board, height=11, width=48, font=("Consolas", 10), state="disabled", relief="flat",
                             background=root.cget("background"))
        self.board.pack(fill="x")
        root.bind("<Left>", lambda _e: self.choose(0))
        root.bind("<Right>", lambda _e: self.choose(1))
        self.refresh_board()
        self.show_next(animate=False)

    def card_photo(self, name):
        from PIL import ImageTk

        if name not in self.cache:
            self.cache[name] = ImageTk.PhotoImage(self.items[name](), master=self.root)
        return self.cache[name]

    def x_for(self, side):
        return 30 if side == 0 else self.width - CARD[0] - 30

    def show_next(self, animate=None):
        animate = self.animate if animate is None else animate
        self.pair = self.matcher.next_pair()
        for side, name in enumerate(self.pair):
            self.canvas.itemconfigure(self.cards[side], image=self.card_photo(name))
            self.canvas.coords(self.frames[side], 0, 0, 0, 0)
            self.canvas.itemconfigure(self.frames[side], outline="")
        if animate:
            self.slide_in(0)
        else:
            for side in (0, 1):
                self.canvas.coords(self.cards[side], self.x_for(side), 15)
        return self.pair

    def slide_in(self, frame):
        """Kartu meluncur masuk dari kedua sisi, melambat di akhir (ease-out)."""
        progress = 1 - (1 - frame / ANIMATION_FRAMES) ** 3
        offset = (1 - progress) * (CARD[0] + 40)
        self.canvas.coords(self.cards[0], self.x_for(0) - offset, 15)
        self.canvas.coords(self.cards[1], self.x_for(1) + offset, 15)
        if frame < ANIMATION_FRAMES:
            self.busy = True
            self.root.after(FRAME_MS, lambda: self.slide_in(frame + 1))
        else:
            self.busy = False

    def choose(self, side):
        if self.busy or not self.pair:
            return None
        winner, loser = self.pair[side], self.pair[1 - side]
        vote(self.db, winner, loser)
        x = self.x_for(side)
        self.canvas.coords(self.frames[side], x - 3, 12, x + CARD[0] + 3, CARD[1] + 18)
        self.canvas.itemconfigure(self.frames[side], outline="#2a9d55")
        self.status.set(f"Kamu memilih {winner} daripada {loser}.")
        self.refresh_board()
        if self.animate:
            self.busy = True
            self.root.after(250, lambda: self.show_next())
        else:
            self.show_next()
        return winner

    def refresh_board(self):
        self.board.configure(state="normal")
        self.board.delete("1.0", "end")
        self.board.insert("1.0", format_leaderboard(leaderboard(self.db)))
        self.board.configure(state="disabled")


def main(argv=None, gui=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Pilih salah satu dari dua gambar.")
    parser.add_argument("--folder", help="folder berisi gambar sendiri (.jpg, .png, ...)")
    parser.add_argument("--db", default=DEFAULT_DB, help="berkas database suara")
    parser.add_argument("--top", action="store_true", help="tampilkan papan peringkat lalu keluar")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    db = connect(args.db)
    try:
        if args.top:
            print(format_leaderboard(leaderboard(db)))
            return 0
        try:
            items = load_items(args.folder)
        except (OSError, ValueError) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        (gui or run_gui)(items, db)
    finally:
        db.close()
    return 0


def run_gui(items, db):
    import tkinter as tk

    root = tk.Tk()
    ThisOrThatApp(root, items, db)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())
