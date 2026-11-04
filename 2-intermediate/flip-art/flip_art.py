"""Flip Art: susun beberapa gambar menjadi animasi, atur kecepatan dan efek transisinya.

Animasi dijalankan sendiri dengan after() milik Tkinter. Kurva transisi
(ease, ease-in, ease-out, ease-in-out) dihitung dari definisi cubic-bezier CSS.
Pillow dipakai untuk membuka JPG, mengubah ukuran, mencampur dua frame
(crossfade), dan menyimpan GIF.

Jalankan:
    python flip_art.py            # mulai dengan 8 slot kosong
    python flip_art.py --demo     # isi slot dengan 8 frame contoh (bola memantul)
"""

import argparse
import math
import sys

from PIL import Image, ImageDraw

DEFAULT_SLOTS = 8
DISPLAY_SIZE = (480, 360)
THUMB_SIZE = (96, 72)
STEP_MS = 40  # satu langkah crossfade (25 langkah per detik)
SPEEDS = (1500, 1100, 800, 600, 450, 340, 250, 180, 130, 100)  # jeda (ms) untuk kecepatan 1 (lambat) .. 10 (cepat)
BACKDROP = (24, 24, 27)

# Titik kontrol cubic-bezier, sama dengan kata kunci CSS transition-timing-function.
TRANSITIONS = {
    "none": None,
    "ease": (0.25, 0.1, 0.25, 1.0),
    "ease-in": (0.42, 0.0, 1.0, 1.0),
    "ease-out": (0.0, 0.0, 0.58, 1.0),
    "ease-in-out": (0.42, 0.0, 0.58, 1.0),
    "linear": (0.0, 0.0, 1.0, 1.0),
}


def cubic_bezier(x1, y1, x2, y2):
    """Fungsi easing f(t) dari cubic-bezier(x1, y1, x2, y2), seperti di CSS.

    Kurva melalui (0,0) dan (1,1). Untuk waktu t dicari parameter u dengan
    bezier_x(u) = t (bisection, karena x naik monoton untuk 0 <= x1, x2 <= 1),
    lalu hasilnya bezier_y(u).
    """
    def coord(u, a, b):
        return 3 * (1 - u) ** 2 * u * a + 3 * (1 - u) * u ** 2 * b + u ** 3

    def ease(t):
        if t <= 0:
            return 0.0
        if t >= 1:
            return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(50):
            mid = (lo + hi) / 2
            if coord(mid, x1, x2) < t:
                lo = mid
            else:
                hi = mid
        return coord((lo + hi) / 2, y1, y2)

    return ease


EASINGS = {name: (cubic_bezier(*points) if points else None) for name, points in TRANSITIONS.items()}


def interval_for(speed):
    """Kecepatan 1..10 -> jeda antarframe (ms)."""
    if not 1 <= speed <= len(SPEEDS):
        raise ValueError(f"Kecepatan harus 1 sampai {len(SPEEDS)}.")
    return SPEEDS[int(speed) - 1]


def timeline(frame_count, interval_ms, transition="none"):
    """Langkah-langkah satu putaran animasi: daftar (frame_a, frame_b, alpha, durasi_ms).

    Tiap frame tampil penuh selama paruh pertama jeda. Kalau ada transisi, paruh
    kedua dipakai untuk crossfade ke frame berikutnya mengikuti kurva easing.
    Tanpa transisi, frame tampil penuh selama seluruh jeda.
    """
    if frame_count < 1:
        return []
    if transition not in TRANSITIONS:
        raise ValueError(f"Transisi '{transition}' tidak dikenal.")
    easing = EASINGS[transition]
    if frame_count == 1 or easing is None:
        return [(i, i, 0.0, interval_ms) for i in range(frame_count)]
    steps = []
    hold = interval_ms // 2
    fade_steps = max(1, round((interval_ms - hold) / STEP_MS))
    fade_ms = (interval_ms - hold) / fade_steps
    for i in range(frame_count):
        nxt = (i + 1) % frame_count
        steps.append((i, i, 0.0, hold))
        for k in range(1, fade_steps + 1):
            steps.append((i, nxt, easing(k / fade_steps), fade_ms))
    return steps


def fit(image, size, background=BACKDROP):
    """Perkecil/perbesar gambar agar muat di `size` tanpa terpotong (letterbox)."""
    image = image.convert("RGB")
    scale = min(size[0] / image.width, size[1] / image.height)
    resized = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))),
                           Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, background)
    canvas.paste(resized, ((size[0] - resized.width) // 2, (size[1] - resized.height) // 2))
    return canvas


def render_step(frames, step):
    a, b, alpha, _ = step
    if a == b or alpha <= 0:
        return frames[a]
    if alpha >= 1:
        return frames[b]
    return Image.blend(frames[a], frames[b], alpha)


class FlipArt:
    """Daftar slot (gambar atau None). Tanpa Tkinter supaya mudah diuji."""

    def __init__(self, slots=DEFAULT_SLOTS):
        self.slots = [None] * slots
        self.names = [None] * slots

    def set(self, index, image, name=None):
        self.slots[index] = image.convert("RGB")
        self.names[index] = name

    def remove(self, index):
        self.slots[index] = None
        self.names[index] = None

    def clear(self):
        self.slots = [None] * len(self.slots)
        self.names = [None] * len(self.names)

    def add_slot(self):
        self.slots.append(None)
        self.names.append(None)
        return len(self.slots) - 1

    def move(self, source, target):
        """Pindahkan isi slot `source` ke posisi `target` (yang lain bergeser)."""
        if source == target:
            return
        for items in (self.slots, self.names):
            items.insert(target, items.pop(source))

    @property
    def filled(self):
        """Indeks slot yang berisi gambar, berurutan."""
        return [i for i, image in enumerate(self.slots) if image is not None]

    @property
    def can_start(self):
        return bool(self.filled)

    def frames(self, size=DISPLAY_SIZE):
        return [fit(self.slots[i], size) for i in self.filled]

    def save_gif(self, path, interval_ms, transition="none", size=DISPLAY_SIZE):
        frames = self.frames(size)
        if not frames:
            raise ValueError("Belum ada gambar untuk disimpan.")
        steps = timeline(len(frames), interval_ms, transition)
        images = [render_step(frames, step) for step in steps]
        # GIF menyimpan durasi dalam satuan 10 ms.
        durations = [max(20, int(round(step[3] / 10)) * 10) for step in steps]
        images[0].save(path, save_all=True, append_images=images[1:], duration=durations, loop=0,
                       optimize=False, disposal=1)
        with Image.open(path) as saved:
            return saved.n_frames  # Pillow menggabungkan frame berurutan yang identik


def demo_frames(count=8, size=(320, 240)):
    """Frame contoh: bola yang memantul dan memipih saat menyentuh lantai."""
    frames = []
    floor = size[1] - 40
    for i in range(count):
        t = i / count
        height = abs(math.cos(math.pi * t))  # 1 di atas, 0 di lantai
        radius = 26
        squash = 1 + 0.35 * max(0.0, 1 - height * 4)  # memipih di dekat lantai
        cx = 40 + (size[0] - 80) * t
        cy = floor - radius / squash - height * (floor - 70)
        img = Image.new("RGB", size, (250, 246, 236))
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, floor, size[0], size[1]), fill=(214, 204, 186))
        shadow = 30 * (1.2 - height * 0.6)
        draw.ellipse((cx - shadow, floor - 5, cx + shadow, floor + 5), fill=(190, 178, 158))
        draw.ellipse((cx - radius * squash, cy - radius / squash, cx + radius * squash, cy + radius / squash),
                     fill=(209, 73, 91))
        draw.text((10, 10), f"frame {i + 1}", fill=(120, 110, 100))
        frames.append(img)
    return frames


# --- tampilan Tkinter ------------------------------------------------------------

def play_sound(kind):
    """Bunyi berbeda untuk menambah, menghapus, dan memindah gambar (Windows). Diam di sistem lain."""
    try:
        import winsound
    except ImportError:
        return
    flags = {"add": winsound.MB_ICONASTERISK, "remove": winsound.MB_ICONHAND, "move": winsound.MB_OK,
             "clear": winsound.MB_ICONEXCLAMATION}
    winsound.MessageBeep(flags.get(kind, winsound.MB_OK))


class FlipArtApp:
    def __init__(self, root, art=None, sound=play_sound):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.root = root
        self.art = art or FlipArt()
        self.sound = sound
        self.thumb_images = {}
        self.display_image = None
        self.job = None
        self.steps = []
        self.frames = []
        self.position = 0
        self.drag_source = None

        root.title("Flip Art")
        config = ttk.LabelFrame(root, text="Konfigurasi", padding=10)
        config.pack(fill="x", padx=12, pady=(12, 6))
        self.slot_frame = ttk.Frame(config)
        self.slot_frame.pack(fill="x")
        self.slot_widgets = []

        options = ttk.Frame(config)
        options.pack(fill="x", pady=(10, 0))
        ttk.Label(options, text="Kecepatan transisi: lambat").pack(side="left")
        self.speed = tk.IntVar(value=5)
        ttk.Scale(options, from_=1, to=len(SPEEDS), variable=self.speed, length=180,
                  command=lambda _v: self.on_speed()).pack(side="left", padx=6)
        ttk.Label(options, text="cepat").pack(side="left")
        self.speed_label = ttk.Label(options, width=12)
        self.speed_label.pack(side="left", padx=(8, 16))
        ttk.Label(options, text="Efek:").pack(side="left")
        self.transition = tk.StringVar(value="ease-in-out")
        ttk.Combobox(options, textvariable=self.transition, state="readonly", width=14,
                     values=list(TRANSITIONS)).pack(side="left", padx=4)
        self.transition.trace_add("write", lambda *_: self.restart_if_running())
        ttk.Button(options, text="+ Slot", command=self.add_slot).pack(side="right")

        ops = ttk.Frame(root, padding=(12, 0))
        ops.pack(fill="x")
        ttk.Button(ops, text="Clear Configuration", command=self.clear).pack(side="left")
        self.start_button = ttk.Button(ops, text="Start Animation", command=self.toggle)
        self.start_button.pack(side="left", padx=6)
        ttk.Button(ops, text="Simpan GIF…", command=self.save_gif).pack(side="right")

        self.display = tk.Label(root, background="#18181b", width=DISPLAY_SIZE[0], height=DISPLAY_SIZE[1])
        self.display.pack(padx=12, pady=12)
        self.status = tk.StringVar(value="Klik + untuk menambah gambar .jpg. Seret thumbnail untuk mengubah urutan.")
        ttk.Label(root, textvariable=self.status, foreground="#555", padding=(12, 0, 12, 10)).pack(anchor="w")
        self.blank = self._photo(Image.new("RGB", DISPLAY_SIZE, BACKDROP))
        self.display.configure(image=self.blank)
        self.on_speed()
        self.build_slots()

    def _photo(self, image):
        from PIL import ImageTk

        return ImageTk.PhotoImage(image, master=self.root)

    # --- slot ----------------------------------------------------------------
    def build_slots(self):
        tk = self.tk
        for widgets in self.slot_widgets:
            widgets["frame"].destroy()
        self.slot_widgets = []
        self.thumb_images = {}
        per_row = 8
        for index, image in enumerate(self.art.slots):
            frame = tk.Frame(self.slot_frame)
            frame.grid(row=index // per_row, column=index % per_row, padx=4, pady=4)
            thumb = tk.Label(frame, width=THUMB_SIZE[0], height=THUMB_SIZE[1], background="#ecebe6",
                             highlightthickness=3, highlightbackground="#ecebe6", text=str(index + 1),
                             compound="center", foreground="#aaa")
            thumb.pack()
            if image is not None:
                photo = self._photo(fit(image, THUMB_SIZE, background=(236, 235, 230)))
                self.thumb_images[index] = photo
                thumb.configure(image=photo, text="", cursor="fleur")
            else:
                blank = self._photo(Image.new("RGB", THUMB_SIZE, (236, 235, 230)))
                self.thumb_images[index] = blank
                thumb.configure(image=blank)
            button = tk.Button(frame, text="−" if image is not None else "+", width=3,
                               command=lambda i=index: self.on_slot_button(i))
            button.pack(pady=(3, 0))
            thumb.bind("<ButtonPress-1>", lambda _e, i=index: self.on_drag_start(i))
            thumb.bind("<ButtonRelease-1>", self.on_drag_end)
            self.slot_widgets.append({"frame": frame, "thumb": thumb, "button": button})
        self.update_start_button()

    def on_slot_button(self, index):
        if self.art.slots[index] is not None:
            self.art.remove(index)
            self.sound("remove")
            self.after_change()
            return
        from tkinter import filedialog, messagebox

        path = filedialog.askopenfilename(parent=self.root, title="Pilih gambar",
                                          filetypes=[("Gambar JPEG", "*.jpg *.jpeg"),
                                                     ("Gambar lain", "*.png *.gif *.bmp")])
        if not path:
            return
        try:
            self.load_into(index, path)
        except OSError as error:
            messagebox.showerror("Gagal membuka gambar", str(error), parent=self.root)

    def load_into(self, index, path):
        import os

        with Image.open(path) as image:
            self.art.set(index, image.copy(), os.path.basename(path))
        self.sound("add")
        self.after_change()

    def add_slot(self):
        self.art.add_slot()
        self.build_slots()

    def on_drag_start(self, index):
        self.drag_source = index if self.art.slots[index] is not None else None

    def on_drag_end(self, event):
        source, self.drag_source = self.drag_source, None
        if source is None:
            return
        target_widget = self.root.winfo_containing(event.x_root, event.y_root)
        for index, widgets in enumerate(self.slot_widgets):
            if target_widget in (widgets["thumb"], widgets["frame"]) and index != source:
                self.art.move(source, index)
                self.sound("move")
                self.after_change()
                return

    def after_change(self):
        self.build_slots()
        self.restart_if_running()

    def clear(self):
        self.stop()
        self.art.clear()
        self.sound("clear")
        self.build_slots()
        self.display.configure(image=self.blank)

    def update_start_button(self):
        running = self.job is not None
        self.start_button.configure(text="Stop Animation" if running else "Start Animation",
                                    state="normal" if self.art.can_start or running else "disabled")

    # --- animasi -----------------------------------------------------------
    @property
    def interval(self):
        return interval_for(int(self.speed.get()))

    def on_speed(self):
        value = int(round(float(self.speed.get())))
        self.speed.set(value)
        self.speed_label.configure(text=f"jeda {self.interval} ms")
        self.restart_if_running()

    def toggle(self):
        if self.job is None:
            self.start()
        else:
            self.stop()

    def start(self):
        if not self.art.can_start:
            return
        self.frames = self.art.frames()
        self.frame_slots = self.art.filled
        self.steps = timeline(len(self.frames), self.interval, self.transition.get())
        self.position = 0
        self.job = "starting"
        self.update_start_button()
        self.tick()

    def stop(self):
        if self.job not in (None, "starting"):
            self.root.after_cancel(self.job)
        self.job = None
        self.highlight(None)
        self.update_start_button()

    def restart_if_running(self):
        if self.job is not None:
            self.stop()
            if self.art.can_start:
                self.start()

    def tick(self):
        step = self.steps[self.position % len(self.steps)]
        self.display_image = self._photo(render_step(self.frames, step))
        self.display.configure(image=self.display_image)
        a, b, alpha, duration = step
        self.highlight(self.frame_slots[b if alpha >= 0.5 else a])
        self.position += 1
        self.job = self.root.after(max(1, int(round(duration))), self.tick)

    def highlight(self, slot):
        for index, widgets in enumerate(self.slot_widgets):
            color = "#e8871e" if index == slot else "#ecebe6"
            widgets["thumb"].configure(highlightbackground=color)

    def save_gif(self):
        from tkinter import filedialog, messagebox

        if not self.art.can_start:
            messagebox.showinfo("Simpan GIF", "Tambahkan gambar dulu.", parent=self.root)
            return
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".gif",
                                            filetypes=[("GIF", "*.gif")], title="Simpan animasi")
        if path:
            count = self.art.save_gif(path, self.interval, self.transition.get())
            self.status.set(f"Tersimpan: {path} ({count} frame GIF)")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Susun gambar menjadi animasi.")
    parser.add_argument("--demo", action="store_true", help="isi slot dengan 8 frame contoh")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    import tkinter as tk

    art = FlipArt()
    if args.demo:
        for index, frame in enumerate(demo_frames()):
            art.set(index, frame, f"contoh-{index + 1}")
    root = tk.Tk()
    root.resizable(False, False)
    FlipArtApp(root, art)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
