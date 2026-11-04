"""Drawing App: menggambar dengan mouse di jendela Tkinter, lalu simpan sebagai PNG/JPG.

Setiap goresan dan bentuk disimpan sebagai data (kelas Drawing). Data itu
digambar ke Canvas Tkinter saat menggambar, dan digambar ulang dengan Pillow
saat disimpan. Canvas Tkinter sendiri hanya bisa diekspor ke PostScript.

Jalankan:
    python drawing_app.py
"""

import math
from dataclasses import dataclass, field

TOOLS = (
    ("pen", "Pena"),
    ("eraser", "Penghapus"),
    ("line", "Garis"),
    ("rect", "Persegi"),
    ("oval", "Lingkaran"),
    ("star", "Bintang"),
)
SHAPES = ("line", "rect", "oval", "star")
PALETTE = ("#1d1d1b", "#7a7a75", "#d1495b", "#e8871e", "#edc531", "#2a9d55", "#2e78c7", "#6c4ab6", "#8a5a3b")
BACKGROUND = "#ffffff"
MIN_SIZE, MAX_SIZE = 1, 40


@dataclass
class Item:
    kind: str  # "stroke" atau salah satu SHAPES
    points: list  # stroke: titik-titik; bentuk: [(x0, y0), (x1, y1)]
    color: str
    width: int
    fill: bool = False


def star_points(x0, y0, x1, y1, spikes=5):
    """Titik bintang yang pas di dalam kotak (x0, y0)-(x1, y1)."""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = abs(x1 - x0) / 2, abs(y1 - y0) / 2
    points = []
    for i in range(spikes * 2):
        scale = 1 if i % 2 == 0 else 0.45
        angle = -math.pi / 2 + i * math.pi / spikes
        points.append((cx + rx * scale * math.cos(angle), cy + ry * scale * math.sin(angle)))
    return points


def normalized_box(points):
    (x0, y0), (x1, y1) = points[0], points[-1]
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


@dataclass
class Drawing:
    width: int = 900
    height: int = 600
    background: str = BACKGROUND
    items: list = field(default_factory=list)
    history: list = field(default_factory=list)  # salinan daftar item sebelum tiap perubahan

    def _remember(self):
        self.history.append(list(self.items))

    def add(self, item):
        if item.kind == "stroke" and not item.points:
            raise ValueError("Goresan butuh setidaknya satu titik.")
        if item.kind in SHAPES and len(item.points) != 2:
            raise ValueError("Bentuk butuh titik awal dan titik akhir.")
        self._remember()
        self.items.append(item)

    def clear(self):
        if self.items:
            self._remember()
            self.items = []

    def undo(self):
        if not self.history:
            return False
        self.items = self.history.pop()
        return True

    def render(self):
        """Gambar ulang semua item ke PIL.Image."""
        from PIL import Image, ImageDraw

        image = Image.new("RGB", (self.width, self.height), self.background)
        draw = ImageDraw.Draw(image)
        for item in self.items:
            render_item(draw, item)
        return image

    def save(self, path):
        """Simpan sebagai PNG atau JPG (ditentukan dari ekstensi berkas)."""
        lower = path.lower()
        if lower.endswith(".png"):
            self.render().save(path, "PNG")
        elif lower.endswith((".jpg", ".jpeg")):
            self.render().save(path, "JPEG", quality=95)
        else:
            raise ValueError("Simpan sebagai .png, .jpg, atau .jpeg.")


def render_item(draw, item):
    w = item.width
    if item.kind == "stroke":
        if len(item.points) > 1:
            draw.line(item.points, fill=item.color, width=w, joint="curve")
        r = w / 2  # ujung bulat, sama dengan capstyle=ROUND di Tkinter
        for x, y in (item.points[0], item.points[-1]):
            draw.ellipse((x - r, y - r, x + r, y + r), fill=item.color)
        return
    x0, y0, x1, y1 = normalized_box(item.points)
    fill = item.color if item.fill else None
    if item.kind == "line":
        draw.line(item.points, fill=item.color, width=w)
    elif item.kind == "rect":
        draw.rectangle((x0, y0, x1, y1), outline=item.color, fill=fill, width=w)
    elif item.kind == "oval":
        draw.ellipse((x0, y0, x1, y1), outline=item.color, fill=fill, width=w)
    elif item.kind == "star":
        points = star_points(x0, y0, x1, y1)
        draw.polygon(points, outline=item.color, fill=fill, width=w)


# --- tampilan Tkinter ----------------------------------------------------------

class DrawingApp:
    def __init__(self, root, drawing=None):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.root = root
        self.drawing = drawing or Drawing()
        self.tool = tk.StringVar(value="pen")
        self.color = PALETTE[0]
        self.size = tk.IntVar(value=6)
        self.fill = tk.BooleanVar(value=False)
        self.current = None  # item yang sedang digambar
        self.preview_id = None

        root.title("Drawing App")
        bar = ttk.Frame(root, padding=(10, 8))
        bar.pack(fill="x")
        for key, label in TOOLS:
            ttk.Radiobutton(bar, text=label, value=key, variable=self.tool, command=self.update_status).pack(side="left")
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        self.swatches = {}
        for color in PALETTE:
            swatch = tk.Canvas(bar, width=22, height=22, highlightthickness=2, highlightbackground="#d0d0d0",
                               background=color, cursor="hand2")
            swatch.pack(side="left", padx=1)
            swatch.bind("<Button-1>", lambda _e, c=color: self.set_color(c))
            self.swatches[color] = swatch
        ttk.Button(bar, text="Warna lain…", command=self.pick_color).pack(side="left", padx=(6, 0))
        self.current_swatch = tk.Canvas(bar, width=28, height=22, highlightthickness=1,
                                        highlightbackground="#888", background=self.color)
        self.current_swatch.pack(side="left", padx=6)

        bar2 = ttk.Frame(root, padding=(10, 0, 10, 8))
        bar2.pack(fill="x")
        ttk.Label(bar2, text="Ukuran").pack(side="left")
        ttk.Scale(bar2, from_=MIN_SIZE, to=MAX_SIZE, variable=self.size, length=160,
                  command=lambda _v: self.on_size()).pack(side="left", padx=6)
        self.size_label = ttk.Label(bar2, width=5)
        self.size_label.pack(side="left")
        ttk.Checkbutton(bar2, text="Isi bentuk", variable=self.fill).pack(side="left", padx=(10, 0))
        ttk.Button(bar2, text="Simpan…", command=self.save).pack(side="right")
        ttk.Button(bar2, text="Bersihkan", command=self.clear).pack(side="right", padx=6)
        ttk.Button(bar2, text="Urungkan", command=self.undo).pack(side="right")

        self.canvas = tk.Canvas(root, width=self.drawing.width, height=self.drawing.height,
                                background=self.drawing.background, highlightthickness=1,
                                highlightbackground="#c9c4b8", cursor="crosshair")
        self.canvas.pack(padx=10, pady=(0, 6))
        self.status = tk.StringVar()
        ttk.Label(root, textvariable=self.status, foreground="#555", padding=(10, 0, 10, 8)).pack(fill="x")

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        root.bind("<Control-z>", lambda _e: self.undo())
        root.bind("<Control-s>", lambda _e: self.save())
        self.set_color(self.color)
        self.on_size()

    # --- pengaturan --------------------------------------------------------
    def set_color(self, color):
        self.color = color
        self.current_swatch.configure(background=color)
        for value, swatch in self.swatches.items():
            swatch.configure(highlightbackground="#1d1d1b" if value == color else "#d0d0d0")
        if self.tool.get() == "eraser":
            self.tool.set("pen")
        self.update_status()

    def pick_color(self):
        from tkinter import colorchooser

        _, chosen = colorchooser.askcolor(color=self.color, parent=self.root, title="Pilih warna")
        if chosen:
            self.set_color(chosen)

    def on_size(self):
        value = int(round(float(self.size.get())))
        self.size.set(value)
        self.size_label.configure(text=f"{value} px")
        self.update_status()

    def update_status(self):
        name = dict(TOOLS)[self.tool.get()]
        self.status.set(f"{name} | ukuran {self.size.get()} px | Ctrl+Z urungkan | Ctrl+S simpan")

    # --- menggambar -------------------------------------------------------
    def on_press(self, event):
        tool = self.tool.get()
        width = int(self.size.get())
        point = (event.x, event.y)
        if tool in ("pen", "eraser"):
            color = self.drawing.background if tool == "eraser" else self.color
            self.current = Item("stroke", [point], color, width)
        else:
            self.current = Item(tool, [point, point], self.color, width, self.fill.get())
        self.redraw_preview()

    def on_drag(self, event):
        if not self.current:
            return
        point = (event.x, event.y)
        if self.current.kind == "stroke":
            if point != self.current.points[-1]:
                self.current.points.append(point)
        else:
            self.current.points[1] = point
        self.redraw_preview()

    def on_release(self, event):
        if not self.current:
            return
        self.on_drag(event)
        item, self.current = self.current, None
        self.canvas.delete("preview")
        if item.kind in SHAPES and item.points[0] == item.points[1]:
            return  # klik tanpa menyeret: tidak ada bentuk
        self.drawing.add(item)
        self.draw_item(item, tag="item")

    def redraw_preview(self):
        self.canvas.delete("preview")
        if self.current:
            self.draw_item(self.current, tag="preview")

    def draw_item(self, item, tag):
        c = self.canvas
        w = item.width
        if item.kind == "stroke":
            if len(item.points) > 1:
                flat = [v for point in item.points for v in point]
                c.create_line(*flat, fill=item.color, width=w, capstyle="round", joinstyle="round", tags=tag)
            else:
                (x, y), r = item.points[0], w / 2
                c.create_oval(x - r, y - r, x + r, y + r, fill=item.color, outline="", tags=tag)
            return
        x0, y0, x1, y1 = normalized_box(item.points)
        fill = item.color if item.fill else ""
        if item.kind == "line":
            (ax, ay), (bx, by) = item.points
            c.create_line(ax, ay, bx, by, fill=item.color, width=w, capstyle="round", tags=tag)
        elif item.kind == "rect":
            c.create_rectangle(x0, y0, x1, y1, outline=item.color, fill=fill, width=w, tags=tag)
        elif item.kind == "oval":
            c.create_oval(x0, y0, x1, y1, outline=item.color, fill=fill, width=w, tags=tag)
        elif item.kind == "star":
            flat = [v for point in star_points(x0, y0, x1, y1) for v in point]
            c.create_polygon(*flat, outline=item.color, fill=fill, width=w, tags=tag)

    def redraw_all(self):
        self.canvas.delete("all")
        for item in self.drawing.items:
            self.draw_item(item, tag="item")

    # --- tombol ---------------------------------------------------------------
    def undo(self):
        if self.drawing.undo():
            self.redraw_all()

    def clear(self):
        self.drawing.clear()
        self.redraw_all()

    def save(self, path=None):
        from tkinter import filedialog, messagebox

        if path is None:
            path = filedialog.asksaveasfilename(
                parent=self.root, title="Simpan gambar", defaultextension=".png",
                filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg")])
        if not path:
            return None
        try:
            self.drawing.save(path)
        except (ValueError, OSError) as error:
            messagebox.showerror("Gagal menyimpan", str(error), parent=self.root)
            return None
        self.status.set(f"Tersimpan: {path}")
        return path


def main():
    import tkinter as tk

    root = tk.Tk()
    root.resizable(False, False)
    DrawingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
