"""String Art: garis warna-warni yang bergerak, memantul di tepi jendela, dan meninggalkan jejak memudar.

Setiap garis punya titik tengah, arah gerak, sudut, panjang, dan kecepatan.
Setiap 20 ms garis bergerak sedikit dan berputar. Kalau salah satu ujungnya
menyentuh tepi, arah geraknya dipantulkan lalu diubah sedikit secara acak.
16 posisi terakhir digambar makin pudar, sehingga terlihat seperti riak.

Jalankan:
    python string_art.py
"""

import colorsys
import math
import random
import time
from collections import deque

TICK_MS = 20
TRAIL = 16
SEGMENTS = 6  # setiap garis digambar sebagai beberapa potongan bergradasi warna
BACKGROUND = (14, 17, 28)


class StringLine:
    """Satu garis yang bergerak. Tanpa Tkinter supaya mudah diuji."""

    def __init__(self, width, height, length=220, speed=6, rng=None):
        self.rng = rng or random.Random()
        self.width, self.height = width, height
        self.length = min(length, 0.9 * min(width, height))
        self.speed = speed
        half = self.length / 2
        self.x = self.rng.uniform(half, width - half)  # posisi acak di dalam jendela
        self.y = self.rng.uniform(half, height - half)
        self.heading = self.rng.uniform(0, 2 * math.pi)  # arah gerak titik tengah
        self.angle = self.rng.uniform(0, math.pi)  # sudut garis
        self.spin = self.rng.choice((-1, 1)) * self.rng.uniform(0.01, 0.04)  # putaran per langkah (radian)
        self.hue = self.rng.random()
        self.trail = deque(maxlen=TRAIL)
        self.bounces = 0
        self.trail.append(self.endpoints())

    def endpoints(self):
        dx = math.cos(self.angle) * self.length / 2
        dy = math.sin(self.angle) * self.length / 2
        return (self.x - dx, self.y - dy, self.x + dx, self.y + dy)

    def step(self):
        """Gerak satu langkah, pantulkan kalau perlu, dan simpan posisi baru ke jejak."""
        self.x += math.cos(self.heading) * self.speed
        self.y += math.sin(self.heading) * self.speed
        self.angle += self.spin
        self.hue = (self.hue + 0.004) % 1.0
        x1, y1, x2, y2 = self.endpoints()
        hit_x = min(x1, x2) <= 0 or max(x1, x2) >= self.width
        hit_y = min(y1, y2) <= 0 or max(y1, y2) >= self.height
        if hit_x or hit_y:
            vx, vy = math.cos(self.heading), math.sin(self.heading)
            # Pantulkan hanya kalau garis memang bergerak ke arah tepi itu.
            if hit_x and ((min(x1, x2) <= 0 and vx < 0) or (max(x1, x2) >= self.width and vx > 0)):
                vx = -vx
            if hit_y and ((min(y1, y2) <= 0 and vy < 0) or (max(y1, y2) >= self.height and vy > 0)):
                vy = -vy
            self.heading = math.atan2(vy, vx) + self.rng.uniform(-0.5, 0.5)  # ubah sudut secara acak
            self.spin = self.rng.choice((-1, 1)) * self.rng.uniform(0.01, 0.05)
            self.bounces += 1
            self.keep_inside()
        self.trail.append(self.endpoints())
        return self.trail[-1]

    def keep_inside(self):
        """Geser titik tengah supaya kedua ujung kembali di dalam jendela."""
        x1, y1, x2, y2 = self.endpoints()
        self.x += max(0, -min(x1, x2)) - max(0, max(x1, x2) - self.width)
        self.y += max(0, -min(y1, y2)) - max(0, max(y1, y2) - self.height)

    def resize(self, width, height):
        self.width, self.height = width, height
        self.length = min(self.length, 0.9 * min(width, height))
        self.keep_inside()


def hsv_hex(h, s=0.85, v=1.0):
    return "#" + "".join(f"{round(c * 255):02x}" for c in colorsys.hsv_to_rgb(h % 1.0, s, v))


def faded(color_hex, strength, background=BACKGROUND):
    """Campur warna dengan latar. strength 1 = warna penuh, 0 = sama dengan latar."""
    rgb = [int(color_hex[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(b + (c - b) * strength):02x}" for c, b in zip(rgb, background))


def segment_points(x1, y1, x2, y2, count=SEGMENTS):
    return [(x1 + (x2 - x1) * i / count, y1 + (y2 - y1) * i / count,
             x1 + (x2 - x1) * (i + 1) / count, y1 + (y2 - y1) * (i + 1) / count) for i in range(count)]


# --- tampilan Tkinter ---------------------------------------------------------------

class StringArtApp:
    def __init__(self, root, width=900, height=560, rng=None):
        import tkinter as tk
        from tkinter import ttk

        self.root = root
        self.rng = rng or random.Random()
        self.job = None
        root.title("String Art")
        bar = ttk.Frame(root, padding=(10, 8))
        bar.pack(fill="x")
        self.length = tk.IntVar(value=220)
        self.speed = tk.IntVar(value=6)
        self.count = tk.IntVar(value=3)
        for label, var, low, high in (("Panjang", self.length, 40, 480), ("Kecepatan", self.speed, 1, 20)):
            ttk.Label(bar, text=label).pack(side="left")
            ttk.Scale(bar, from_=low, to=high, variable=var, length=150,
                      command=lambda _v: self.apply_settings()).pack(side="left", padx=(4, 14))
        ttk.Label(bar, text="Jumlah garis").pack(side="left")
        ttk.Spinbox(bar, from_=1, to=8, width=3, textvariable=self.count, command=self.reset).pack(side="left", padx=4)
        ttk.Button(bar, text="Acak ulang", command=self.reset).pack(side="left", padx=10)
        self.pause_button = ttk.Button(bar, text="Jeda", command=self.toggle)
        self.pause_button.pack(side="left")
        self.canvas = tk.Canvas(root, width=width, height=height, highlightthickness=0,
                                background="#%02x%02x%02x" % BACKGROUND)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.on_resize)
        self.lines = []
        self.items = []
        self.size = (width, height)
        self.reset()
        self.start()

    def reset(self):
        width, height = self.size
        try:
            count = max(1, min(8, int(self.count.get())))
        except (ValueError, Exception):
            count = 3
        # Setiap garis punya kecepatan sedikit berbeda supaya lintasannya tidak sama.
        self.lines = [StringLine(width, height, int(self.length.get()), int(self.speed.get()) * self.rng.uniform(0.7, 1.3),
                                 self.rng) for _ in range(count)]
        self.canvas.delete("all")
        # Item Canvas dipakai ulang tiap langkah (lebih ringan daripada membuat garis baru terus-menerus).
        self.items = [[[self.canvas.create_line(0, 0, 0, 0, width=2, capstyle="round") for _ in range(SEGMENTS)]
                       for _ in range(TRAIL)] for _ in self.lines]

    def apply_settings(self):
        for line in self.lines:
            line.length = min(float(self.length.get()), 0.9 * min(self.size))
            line.speed = float(self.speed.get())
            line.keep_inside()

    def on_resize(self, event):
        self.size = (event.width, event.height)
        for line in self.lines:
            line.resize(*self.size)

    def start(self):
        if self.job is None:
            self.job = self.root.after(TICK_MS, self.tick)
            self.pause_button.configure(text="Jeda")

    def toggle(self):
        if self.job is None:
            self.start()
        else:
            self.root.after_cancel(self.job)
            self.job = None
            self.pause_button.configure(text="Lanjut")

    def tick(self):
        for line in self.lines:
            line.step()
        self.draw()
        # Timer Windows berbutir sekitar 15,6 ms, jadi after(20) sering menunggu 31 ms. Karena itu jadwal
        # dihitung dari waktu target: kalau satu langkah terlambat, jeda berikutnya dipendekkan.
        now = time.perf_counter()
        self.due = max(getattr(self, "due", now) + TICK_MS / 1000, now - 0.1)
        self.job = self.root.after(max(1, int((self.due - now) * 1000)), self.tick)

    def draw(self):
        for line, rows in zip(self.lines, self.items):
            trail = list(line.trail)
            for age, segments in enumerate(rows):  # age 0 = paling baru
                if age >= len(trail):
                    for item in segments:
                        self.canvas.coords(item, 0, 0, 0, 0)
                    continue
                strength = (1 - age / TRAIL) ** 1.6
                width = 3 if age == 0 else 1.5
                points = segment_points(*trail[-1 - age])
                for index, (item, coords) in enumerate(zip(segments, points)):
                    color = hsv_hex(line.hue + index * 0.06 - age * 0.01)
                    self.canvas.coords(item, *coords)
                    self.canvas.itemconfigure(item, fill=faded(color, strength), width=width)
            # Garis terbaru di atas jejak yang memudar.
            for item in rows[0]:
                self.canvas.tag_raise(item)


def main():
    import tkinter as tk

    root = tk.Tk()
    StringArtApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
