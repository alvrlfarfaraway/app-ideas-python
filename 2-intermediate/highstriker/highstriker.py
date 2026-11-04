"""HighStriker: pukul platform, lihat puck naik di rel, dan coba bunyikan bel di puncak.

Algoritma pukulan: kekuatan s diambil dari distribusi normal (rata-rata 0,82,
simpangan 0,2). Seperti benda yang dilempar ke atas, tinggi maksimum sebanding
dengan kuadrat kecepatan awal, jadi puck naik sampai s² dari tinggi rel. Bel
berbunyi kalau s >= 1 (peluangnya sekitar 18%).

Bunyi (dentang bel, desis puck di rel, nada per poin) dibuat sendiri sebagai
berkas WAV dan diputar dengan winsound di Windows.

Jalankan:
    python highstriker.py
"""

import atexit
import math
import os
import random
import shutil
import struct
import tempfile
import wave

STRENGTH_MEAN = 0.82
STRENGTH_SD = 0.20
MIN_STRENGTH, MAX_STRENGTH = 0.15, 1.30
TARGET_POINTS = 10
RISE_TIME_AT_BELL = 0.9  # detik yang dibutuhkan puck untuk naik sampai bel dengan s = 1

# Batas bawah tiap skor (bagian dari tinggi rel). Mengikuti contoh skala di spesifikasi.
POINT_BANDS = ((1.0, 5), (0.75, 4), (0.5, 3), (0.25, 2), (0.125, 1))


def strike_strength(rng=random):
    """Kekuatan pukulan acak, dibatasi supaya tidak ada pukulan nol atau tak terhingga."""
    return min(MAX_STRENGTH, max(MIN_STRENGTH, rng.gauss(STRENGTH_MEAN, STRENGTH_SD)))


def peak_fraction(strength):
    """Tinggi maksimum puck sebagai bagian dari tinggi rel (dibatasi bel di 1,0)."""
    return min(1.0, strength ** 2)


def points_for(fraction):
    """Skor menurut jarak tempuh: 1/8-1/4 -> 1, 1/4-1/2 -> 2, 1/2-3/4 -> 3, 3/4-bel -> 4, bel -> 5."""
    for lower, points in POINT_BANDS:
        if fraction >= lower:
            return points
    return 0


def puck_path(strength, fps=60):
    """Posisi puck (0 = platform, 1 = bel) per frame animasi.

    Naik dengan perlambatan tetap: h(t) = H * (1 - (1 - t/T)^2), dengan H = s^2 dan
    waktu naik T sebanding dengan s (kecepatan awal). Kalau h mencapai 1, puck
    memantul dari bel. Setelah itu puck jatuh kembali ke platform.
    """
    height = strength ** 2
    rise = RISE_TIME_AT_BELL * strength
    path = []
    t = 0.0
    step = 1 / fps
    top_time = rise
    if height >= 1.0:  # waktu ketika puck menyentuh bel: 1 = H(1 - (1 - t/T)^2)
        top_time = rise * (1 - math.sqrt(1 - 1 / height))
    while t < top_time:
        path.append(min(1.0, height * (1 - (1 - t / rise) ** 2)))
        t += step
    peak = min(1.0, height)
    path.append(peak)
    fall = RISE_TIME_AT_BELL * math.sqrt(peak)  # jatuh bebas dari puncak
    t = step
    while t < fall:
        path.append(peak * (1 - (t / fall) ** 2))
        t += step
    path.append(0.0)
    return path


class Scoreboard:
    def __init__(self, target=TARGET_POINTS):
        self.target = target
        self.clear()

    def clear(self):
        self.attempts = 0
        self.bells = 0
        self.points = 0
        self.congratulated = False
        self.last = None

    def record(self, fraction):
        """Catat satu pukulan. Mengembalikan (poin, bel_berbunyi, baru_mencapai_target)."""
        earned = points_for(fraction)
        rang = fraction >= 1.0
        self.attempts += 1
        self.bells += rang
        self.points += earned
        self.last = (fraction, earned)
        reached = self.points >= self.target and not self.congratulated
        if reached:
            self.congratulated = True
        return earned, rang, reached

    def summary(self):
        return f"Bel berbunyi {self.bells} kali dari {self.attempts} pukulan | Poin {self.points}"


# --- bunyi ---------------------------------------------------------------------

RATE = 22050


def write_wav(path, samples):
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32000)) for s in samples))


def bell_samples(duration=1.6, base=880.0):
    """Dentang bel: beberapa nada parsial (rasio khas lonceng) yang meredup."""
    partials = ((1.0, 0.6, 2.2), (2.0, 0.3, 3.0), (2.76, 0.25, 4.0), (5.4, 0.12, 6.0))
    count = int(RATE * duration)
    return [sum(amp * math.exp(-decay * n / RATE) * math.sin(2 * math.pi * base * ratio * n / RATE)
                for ratio, amp, decay in partials) * min(1.0, n / 40) for n in range(count)]


def tone_samples(freq, duration=0.25, volume=0.5):
    count = int(RATE * duration)
    return [volume * math.sin(2 * math.pi * freq * n / RATE) * math.exp(-6 * n / count) for n in range(count)]


def rail_samples(duration=0.45):
    """Desis puck di rel: nada yang naik cepat dan pelan."""
    count = int(RATE * duration)
    phase = 0.0
    out = []
    for n in range(count):
        freq = 220 + 700 * n / count
        phase += 2 * math.pi * freq / RATE
        out.append(0.18 * math.sin(phase) * (1 - n / count))
    return out


def make_sounds(folder):
    """Tulis semua berkas WAV. Mengembalikan {nama: path}."""
    sounds = {
        "rail": rail_samples(),
        "bell": bell_samples(),
        "points-0": tone_samples(110, 0.3),
        "points-1": tone_samples(330),
        "points-2": tone_samples(392),
        "points-3": tone_samples(494),
        "points-4": tone_samples(587),
    }
    paths = {}
    for name, samples in sounds.items():
        path = os.path.join(folder, f"{name}.wav")
        write_wav(path, samples)
        paths[name] = path
    return paths


class SoundPlayer:
    def __init__(self, root=None):
        self.root = root
        self.folder = tempfile.mkdtemp(prefix="highstriker-")
        atexit.register(shutil.rmtree, self.folder, ignore_errors=True)  # berkas WAV dihapus saat program ditutup
        self.paths = make_sounds(self.folder)
        try:
            import winsound
            self.winsound = winsound
        except ImportError:
            self.winsound = None

    def play(self, name):
        if self.winsound:
            self.winsound.PlaySound(self.paths[name], self.winsound.SND_FILENAME | self.winsound.SND_ASYNC)
        elif name == "bell" and self.root is not None:
            self.root.bell()


# --- tampilan Tkinter ----------------------------------------------------------------

W, H = 420, 640
TRACK_X0, TRACK_X1 = 190, 230
CX = (TRACK_X0 + TRACK_X1) / 2
TRACK_TOP, TRACK_BOTTOM = 120, 540  # posisi y rel: 1.0 di atas, 0.0 di bawah
PUCK_H = 22


class HighStrikerApp:
    def __init__(self, root, rng=random, sound=None, alert=None):
        import tkinter as tk
        from tkinter import ttk

        self.root = root
        self.rng = rng
        self.sound = sound if sound is not None else SoundPlayer(root)
        self.alert = alert or self._congrats_box
        self.board = Scoreboard()
        self.animating = False
        self.job = None

        root.title("HighStriker")
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=W, height=H, background="#1e2a3a", highlightthickness=0)
        self.canvas.pack(padx=12, pady=(12, 6))
        self.draw_tower()

        buttons = ttk.Frame(root)
        buttons.pack()
        self.strike_button = ttk.Button(buttons, text="Strike!", command=self.strike, width=14)
        self.strike_button.pack(side="left", padx=4)
        ttk.Button(buttons, text="Clear", command=self.clear).pack(side="left", padx=4)
        self.score = tk.StringVar()
        self.message = tk.StringVar(value="Tekan Strike! (atau Spasi) untuk memukul.")
        ttk.Label(root, textvariable=self.score, font=("Segoe UI", 11, "bold")).pack(pady=(8, 0))
        ttk.Label(root, textvariable=self.message, foreground="#555").pack(pady=(2, 12))
        root.bind("<space>", lambda _e: self.strike())
        self.update_score()

    def y_for(self, fraction):
        return TRACK_BOTTOM - fraction * (TRACK_BOTTOM - TRACK_TOP)

    def draw_tower(self):
        c = self.canvas
        c.create_rectangle(0, H - 60, W, H, fill="#5b4632", outline="")  # lantai panggung
        # Pita skor di samping rel
        colors = {1: "#3d5a80", 2: "#4f7cac", 3: "#e0a458", 4: "#e07a5f", 5: "#d1495b"}
        bands = [(0.125, 0.25, 1), (0.25, 0.5, 2), (0.5, 0.75, 3), (0.75, 1.0, 4)]
        for low, high, points in bands:
            c.create_rectangle(TRACK_X1 + 6, self.y_for(high), TRACK_X1 + 30, self.y_for(low),
                               fill=colors[points], outline="#1e2a3a")
            c.create_text(TRACK_X1 + 18, (self.y_for(high) + self.y_for(low)) / 2, text=str(points),
                          fill="white", font=("Segoe UI", 10, "bold"))
        for fraction, label in ((0.125, "1/8"), (0.25, "1/4"), (0.5, "1/2"), (0.75, "3/4")):
            y = self.y_for(fraction)
            c.create_line(TRACK_X0 - 18, y, TRACK_X0 - 4, y, fill="#9fb3c8", width=2)
            c.create_text(TRACK_X0 - 22, y, text=label, anchor="e", fill="#9fb3c8", font=("Segoe UI", 9))
        # Rel dan tiang
        c.create_rectangle(TRACK_X0 - 4, TRACK_TOP - 10, TRACK_X1 + 4, TRACK_BOTTOM + 6, fill="#c9b79c",
                           outline="#8c7a60", width=2)
        c.create_rectangle(TRACK_X0 + 8, TRACK_TOP, TRACK_X1 - 8, TRACK_BOTTOM, fill="#2b2b2b", outline="")
        # Bel di puncak
        bell = [CX - 10, 50, CX + 10, 50, CX + 20, 58, CX + 24, 80, CX + 30, 96, CX + 42, 106,
                CX - 42, 106, CX - 30, 96, CX - 24, 80, CX - 20, 58]
        self.bell_items = [
            c.create_oval(CX - 6, 40, CX + 6, 52, fill="#b8860b", outline=""),  # pengait
            c.create_polygon(bell, fill="#f2c14e", outline="#b8860b", width=2, smooth=True),
            c.create_rectangle(CX - 42, 102, CX + 42, 108, fill="#d9a62e", outline=""),  # bibir bel
            c.create_oval(CX - 7, 104, CX + 7, 116, fill="#8a6408", outline=""),  # pemukul
        ]
        c.create_text(CX, 24, text="5 poin: BEL!", fill="#f2c14e", font=("Segoe UI", 11, "bold"))
        # Platform berpengungkit di dasar
        c.create_rectangle(TRACK_X0 - 40, TRACK_BOTTOM + 6, TRACK_X1 + 40, TRACK_BOTTOM + 20, fill="#8c5e3c",
                           outline="#5b3a22")
        self.lever = c.create_polygon(CX - 110, H - 74, CX + 110, H - 92, CX + 110, H - 82, CX - 110, H - 64,
                                      fill="#a0522d", outline="#5b3a22")
        c.create_text(CX, H - 30, text="Platform", fill="#e8dcc8", font=("Segoe UI", 9))
        self.puck = c.create_rectangle(TRACK_X0 + 4, 0, TRACK_X1 - 4, PUCK_H, fill="#e5e5e5", outline="#888")
        self.place_puck(0.0)
        # Teks skor di kiri menara, supaya tidak menutupi bel.
        self.flash = c.create_text((TRACK_X0 - 40) / 2, 200, text="", fill="white", font=("Segoe UI", 18, "bold"),
                                   width=TRACK_X0 - 50, justify="center")

    def place_puck(self, fraction):
        y = self.y_for(fraction)
        self.canvas.coords(self.puck, TRACK_X0 + 6, y - PUCK_H, TRACK_X1 - 6, y)

    def update_score(self):
        self.score.set(self.board.summary())

    def strike(self):
        if self.animating:
            return
        self.animating = True
        self.strike_button.configure(state="disabled")
        strength = strike_strength(self.rng)
        self.path = puck_path(strength)
        self.fraction = peak_fraction(strength)
        self.peak_index = self.path.index(max(self.path))  # frame saat skor dicatat (puncak atau kena bel)
        self.frame = 0
        self.canvas.itemconfigure(self.flash, text="")
        self.canvas.move(self.lever, 0, 10)  # pengungkit tertekan
        self.root.after(80, lambda: self.canvas.move(self.lever, 0, -10))
        self.sound.play("rail")
        self.animate()

    def animate(self):
        position = self.path[self.frame]
        self.place_puck(position)
        if self.frame == self.peak_index:
            self.on_peak()
        self.frame += 1
        if self.frame < len(self.path):
            self.job = self.root.after(16, self.animate)
        else:
            self.job = None
            self.animating = False
            self.strike_button.configure(state="normal")

    def on_peak(self):
        earned, rang, reached = self.board.record(self.fraction)
        self.update_score()
        if rang:
            self.sound.play("bell")
            self.vibrate()
            text, color = "DING!\n+5", "#f2c14e"
        else:
            self.sound.play(f"points-{earned}")
            text, color = (f"+{earned}" if earned else "Kurang kuat!"), "white"
        self.canvas.itemconfigure(self.flash, text=text, fill=color)
        self.message.set(f"Puck naik {round(self.fraction * 100)}% dari rel, dapat {earned} poin.")
        if reached:
            self.root.after(400, lambda: self.alert(
                f"Selamat! Kamu mengumpulkan {self.board.points} poin dalam {self.board.attempts} pukulan "
                f"(bel berbunyi {self.board.bells} kali)."))

    def vibrate(self, step=0):
        """Bel bergoyang kiri-kanan dengan simpangan yang mengecil."""
        if step > 0:
            for item in self.bell_items:
                self.canvas.move(item, -self._bell_offset, 0)
        if step >= 16:
            self._bell_offset = 0
            return
        self._bell_offset = round(6 * math.exp(-step / 6) * (1 if step % 2 == 0 else -1))
        for item in self.bell_items:
            self.canvas.move(item, self._bell_offset, 0)
        self.root.after(30, lambda: self.vibrate(step + 1))

    def clear(self):
        self.board.clear()
        self.update_score()
        self.canvas.itemconfigure(self.flash, text="")
        self.message.set("Skor dibersihkan. Tekan Strike! untuk memukul.")

    def _congrats_box(self, message):
        from tkinter import messagebox

        messagebox.showinfo("Selamat!", message, parent=self.root)


def main():
    import tkinter as tk

    root = tk.Tk()
    HighStrikerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
