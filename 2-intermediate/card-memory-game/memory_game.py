"""Card Memory Game: buka dua kartu, cari pasangan gambarnya sebelum waktu habis.

Logika permainan (kelas MemoryGame dan Stats) terpisah dari tampilan Tkinter,
jadi bisa diuji tanpa membuka jendela.

Jalankan:
    python memory_game.py
"""

import json
import math
import os
import random
import time
from dataclasses import dataclass

HIDDEN, VISIBLE, MATCHED = "hidden", "visible", "matched"


@dataclass(frozen=True)
class Level:
    key: str
    name: str
    size: int  # grid size x size kartu
    time_limit: int  # detik


LEVELS = (
    Level("easy", "Mudah", 4, 90),
    Level("medium", "Sedang", 6, 180),
    Level("hard", "Sulit", 8, 300),
)
LEVEL_BY_KEY = {level.key: level for level in LEVELS}

SHAPES = ("circle", "square", "triangle", "diamond", "star", "hexagon", "cross", "ring")
COLORS = ("#d1495b", "#2e78c7", "#2a9d55", "#d9900f")  # merah, biru, hijau, jingga


def pick_symbols(pairs, rng=random):
    """Pilih `pairs` gambar berbeda (bentuk, warna).

    Bentuk diutamakan berbeda dulu; warna baru dipakai sebagai pembeda setelah
    kedelapan bentuk habis, supaya level Mudah tidak bergantung pada warna saja.
    """
    if not 1 <= pairs <= len(SHAPES) * len(COLORS):
        raise ValueError(f"Jumlah pasangan harus 1 sampai {len(SHAPES) * len(COLORS)}.")
    shapes = list(SHAPES)
    rng.shuffle(shapes)
    color_offset = rng.randrange(len(COLORS))
    symbols = []
    for i in range(pairs):
        shape = shapes[i % len(shapes)]
        color = COLORS[(i + i // len(shapes) + color_offset) % len(COLORS)]
        symbols.append((shape, color))
    return symbols


class MemoryGame:
    """Satu permainan. Waktu dibaca dari `clock` (detik) supaya tes tidak perlu menunggu."""

    def __init__(self, size, time_limit=None, rng=random, clock=time.monotonic):
        if size < 2 or size * size % 2:
            raise ValueError("Ukuran grid harus genap dan minimal 2 (misalnya 4 untuk 4x4).")
        self.size = size
        self.time_limit = time_limit
        self.clock = clock
        symbols = pick_symbols(size * size // 2, rng)
        self.cards = symbols * 2
        rng.shuffle(self.cards)
        self.states = [HIDDEN] * len(self.cards)
        self.first = None  # indeks kartu pertama yang sedang terbuka
        self.pending = None  # dua kartu tidak cocok yang masih terlihat, menunggu ditutup
        self.moves = 0
        self.started_at = None
        self.finished_at = None
        self.result = None  # None, "won", atau "lost"

    # --- waktu -------------------------------------------------------------
    def start(self):
        self.started_at = self.clock()

    @property
    def running(self):
        return self.started_at is not None and self.result is None

    def elapsed(self):
        if self.started_at is None:
            return 0.0
        end = self.finished_at if self.finished_at is not None else self.clock()
        return end - self.started_at

    def remaining(self):
        if self.time_limit is None:
            return None
        return max(0.0, self.time_limit - self.elapsed())

    def check_timeout(self):
        """Tandai kalah kalau waktu habis. True kalau baru saja kalah."""
        if self.running and self.time_limit is not None and self.elapsed() >= self.time_limit:
            self.finished_at = self.started_at + self.time_limit
            self.result = "lost"
            return True
        return False

    # --- kartu -------------------------------------------------------------
    def hide_pending(self):
        """Tutup kembali dua kartu yang tidak cocok. Mengembalikan indeks yang ditutup."""
        if not self.pending:
            return ()
        closed = self.pending
        for index in closed:
            self.states[index] = HIDDEN
        self.pending = None
        return closed

    def flip(self, index):
        """Buka satu kartu. Hasil: 'ignored', 'first', 'match', 'mismatch', 'won', atau 'lost'."""
        if self.check_timeout():
            return "lost"
        if not self.running or not 0 <= index < len(self.cards):
            return "ignored"
        self.hide_pending()  # klik berikutnya langsung menutup pasangan yang salah
        if self.states[index] != HIDDEN:
            return "ignored"
        self.states[index] = VISIBLE
        if self.first is None:
            self.first = index
            return "first"
        first, self.first = self.first, None
        self.moves += 1
        if self.cards[first] == self.cards[index]:
            self.states[first] = self.states[index] = MATCHED
            if all(state == MATCHED for state in self.states):
                self.finished_at = self.clock()
                self.result = "won"
                return "won"
            return "match"
        self.pending = (first, index)
        return "mismatch"


class Stats:
    """Jumlah menang/kalah dan waktu terbaik per level, disimpan sebagai JSON."""

    def __init__(self, path):
        self.path = path
        self.data = {level.key: {"wins": 0, "losses": 0, "best": None} for level in LEVELS}
        self._load()

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as handle:
                saved = json.load(handle)
        except FileNotFoundError:
            return
        except (OSError, ValueError):
            return  # berkas rusak: mulai dari nol, berkas lama ditimpa saat permainan berikutnya selesai
        if not isinstance(saved, dict):
            return
        for key, entry in self.data.items():
            item = saved.get(key)
            if not isinstance(item, dict):
                continue
            for field in ("wins", "losses"):
                if isinstance(item.get(field), int) and item[field] >= 0:
                    entry[field] = item[field]
            if isinstance(item.get("best"), (int, float)) and item["best"] > 0:
                entry["best"] = float(item["best"])

    def record(self, level_key, won, seconds=None):
        """Catat hasil. Mengembalikan True kalau ini rekor waktu baru."""
        entry = self.data[level_key]
        record = False
        if won:
            entry["wins"] += 1
            if entry["best"] is None or seconds < entry["best"]:
                entry["best"] = round(seconds, 1)
                record = True
        else:
            entry["losses"] += 1
        self._save()
        return record

    def _save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        temp = self.path + ".tmp"
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, indent=2)
        os.replace(temp, self.path)

    def summary(self, level_key):
        entry = self.data[level_key]
        best = format_seconds(entry["best"]) if entry["best"] is not None else "-"
        return f"Menang {entry['wins']} | Kalah {entry['losses']} | Terbaik {best}"


def format_seconds(seconds):
    """62.34 -> '1:02,3'; 9.0 -> '0:09,0' (koma desimal ala Indonesia)."""
    tenths = int(round(seconds * 10))
    minutes, rest = divmod(tenths, 600)
    return f"{minutes}:{rest // 10:02d},{rest % 10}"


DEFAULT_STATS = os.path.join(os.path.expanduser("~"), ".app-ideas-python", "memory-stats.json")


# --- tampilan Tkinter -----------------------------------------------------

CARD = 72  # ukuran kartu (px)
GAP = 8
BACK, BACK_LINE = "#264653", "#2f5a6a"
FACE, FACE_MATCHED = "#fbfaf6", "#e4efe7"
HIDE_DELAY_MS = 800


def blend(color, background, amount):
    """Campur dua warna hex. amount=0 -> color, amount=1 -> background."""
    a = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(background[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * amount):02x}" for x, y in zip(a, b))


def shape_points(shape, cx, cy, r):
    """Titik poligon untuk bentuk bersudut; None untuk lingkaran/cincin."""
    if shape == "square":
        s = r * 0.85
        return [cx - s, cy - s, cx + s, cy - s, cx + s, cy + s, cx - s, cy + s]
    if shape == "triangle":
        return [cx, cy - r, cx + r * 0.95, cy + r * 0.75, cx - r * 0.95, cy + r * 0.75]
    if shape == "diamond":
        return [cx, cy - r, cx + r * 0.8, cy, cx, cy + r, cx - r * 0.8, cy]
    if shape in ("star", "hexagon"):
        count = 5 if shape == "star" else 6
        points = []
        steps = count * 2 if shape == "star" else count
        for i in range(steps):
            radius = r if shape == "hexagon" or i % 2 == 0 else r * 0.45
            angle = -math.pi / 2 + i * 2 * math.pi / steps
            points += [cx + radius * math.cos(angle), cy + radius * math.sin(angle)]
        return points
    if shape == "cross":
        a, b = r * 0.32, r
        return [cx - a, cy - b, cx + a, cy - b, cx + a, cy - a, cx + b, cy - a, cx + b, cy + a, cx + a, cy + a,
                cx + a, cy + b, cx - a, cy + b, cx - a, cy + a, cx - b, cy + a, cx - b, cy - a, cx - a, cy - a]
    return None


class MemoryApp:
    def __init__(self, root, stats_path=DEFAULT_STATS, rng=random):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.root = root
        self.rng = rng
        self.stats = Stats(stats_path)
        self.game = None
        self.hide_job = None
        self.tick_job = None

        root.title("Card Memory Game")
        root.resizable(False, False)
        bar = ttk.Frame(root, padding=(12, 10, 12, 4))
        bar.pack(fill="x")
        ttk.Label(bar, text="Level:").pack(side="left")
        self.level_var = tk.StringVar(value="easy")
        for level in LEVELS:
            ttk.Radiobutton(bar, text=f"{level.name} ({level.size}x{level.size})", value=level.key,
                            variable=self.level_var, command=self.new_board).pack(side="left", padx=(6, 0))
        self.start_button = ttk.Button(bar, text="Mulai", command=self.start)
        self.start_button.pack(side="right")

        info = ttk.Frame(root, padding=(12, 0, 12, 6))
        info.pack(fill="x")
        self.timer_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.stats_var = tk.StringVar()
        ttk.Label(info, textvariable=self.timer_var, font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Label(info, textvariable=self.status_var).pack(side="left", padx=12)
        ttk.Label(info, textvariable=self.stats_var, foreground="#555").pack(side="right")

        self.canvas = tk.Canvas(root, highlightthickness=0, background="#e9e6df")
        self.canvas.pack(padx=12, pady=(0, 12))
        self.canvas.bind("<Button-1>", self.on_click)
        self.new_board()

    @property
    def level(self):
        return LEVEL_BY_KEY[self.level_var.get()]

    def new_board(self):
        """Susun kartu tertutup untuk level terpilih. Permainan baru jalan setelah tombol Mulai."""
        self._cancel_jobs()
        self.game = MemoryGame(self.level.size, self.level.time_limit, rng=self.rng)
        side = self.level.size * (CARD + GAP) - GAP
        self.canvas.configure(width=side, height=side)
        self.start_button.configure(text="Mulai")
        self.status_var.set("Tekan Mulai untuk memulai.")
        self.timer_var.set(f"Batas {format_seconds(self.level.time_limit)}")
        self.stats_var.set(self.stats.summary(self.level.key))
        self.draw()

    def start(self):
        if self.game.started_at is not None:
            self.new_board()  # tombol "Ulangi": kocok ulang
        self.game.start()
        self.start_button.configure(text="Ulangi")
        self.status_var.set(f"{len(self.game.cards) // 2} pasangan tersisa")
        self.tick()

    def tick(self):
        game = self.game
        if game.check_timeout():
            self.finish()
            return
        if game.running:
            self.timer_var.set(f"Sisa {format_seconds(game.remaining())}")
            self.tick_job = self.root.after(100, self.tick)

    def card_at(self, x, y):
        col, row = int(x // (CARD + GAP)), int(y // (CARD + GAP))
        if x % (CARD + GAP) > CARD or y % (CARD + GAP) > CARD:
            return None  # klik di celah antarkartu
        if 0 <= col < self.game.size and 0 <= row < self.game.size:
            return row * self.game.size + col
        return None

    def on_click(self, event):
        index = self.card_at(event.x, event.y)
        if index is None:
            return
        if self.hide_job:
            self.root.after_cancel(self.hide_job)
            self.hide_job = None
        result = self.game.flip(index)
        if result == "mismatch":
            self.hide_job = self.root.after(HIDE_DELAY_MS, self.hide_pending)
        matched = self.game.states.count(MATCHED) // 2
        if self.game.running:
            self.status_var.set(f"{len(self.game.cards) // 2 - matched} pasangan tersisa | {self.game.moves} langkah")
        self.draw()
        if result in ("won", "lost"):
            self.finish()

    def hide_pending(self):
        self.hide_job = None
        self.game.hide_pending()
        self.draw()

    def finish(self):
        from tkinter import messagebox

        self._cancel_jobs()
        game = self.game
        self.draw()
        if game.result == "won":
            seconds = game.elapsed()
            record = self.stats.record(self.level.key, True, seconds)
            self.timer_var.set(f"Waktu {format_seconds(seconds)}")
            self.status_var.set(f"Selesai dalam {game.moves} langkah")
            message = f"Selamat! Semua pasangan ditemukan dalam {format_seconds(seconds)} ({game.moves} langkah)."
            if record:
                message += "\nIni rekor baru untuk level ini!"
            title = "Selamat!"
        else:
            self.stats.record(self.level.key, False)
            self.timer_var.set("Sisa 0:00,0")
            self.status_var.set("Waktu habis")
            message = "Waktu habis. Tekan Main lagi untuk mencoba lagi."
            title = "Waktu habis"
        self.stats_var.set(self.stats.summary(self.level.key))
        self.start_button.configure(text="Main lagi")
        self.root.after(50, lambda: messagebox.showinfo(title, message, parent=self.root))

    def _cancel_jobs(self):
        for name in ("hide_job", "tick_job"):
            job = getattr(self, name)
            if job:
                self.root.after_cancel(job)
                setattr(self, name, None)

    def draw(self):
        c = self.canvas
        c.delete("all")
        for index, state in enumerate(self.game.states):
            row, col = divmod(index, self.game.size)
            x0, y0 = col * (CARD + GAP), row * (CARD + GAP)
            x1, y1 = x0 + CARD, y0 + CARD
            if state == HIDDEN:
                c.create_rectangle(x0, y0, x1, y1, fill=BACK, outline=BACK)
                c.create_rectangle(x0 + 8, y0 + 8, x1 - 8, y1 - 8, outline=BACK_LINE, width=2)
                c.create_oval(x0 + 26, y0 + 26, x1 - 26, y1 - 26, outline=BACK_LINE, width=2)
                continue
            shape, color = self.game.cards[index]
            matched = state == MATCHED
            c.create_rectangle(x0, y0, x1, y1, fill=FACE_MATCHED if matched else FACE,
                               outline="#2a9d55" if matched else "#c9c4b8", width=2)
            self.draw_shape(shape, color, (x0 + x1) / 2, (y0 + y1) / 2, CARD * 0.32, faded=matched)

    def draw_shape(self, shape, color, cx, cy, r, faded=False):
        c = self.canvas
        if faded:
            color = blend(color, FACE_MATCHED, 0.45)
        if shape == "circle":
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")
        elif shape == "ring":
            inset = r * 0.2
            c.create_oval(cx - r + inset, cy - r + inset, cx + r - inset, cy + r - inset, outline=color, width=r * 0.4)
        else:
            c.create_polygon(shape_points(shape, cx, cy, r), fill=color, outline="")


def main():
    import tkinter as tk

    root = tk.Tk()
    MemoryApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
