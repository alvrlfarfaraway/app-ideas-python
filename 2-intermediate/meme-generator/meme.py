"""Meme Generator: buka gambar, tambahkan teks atas/bawah, atur warna, ukuran, dan font, lalu simpan.

Gambar meme selalu digambar oleh Pillow (kelas Meme), lalu ditampilkan di Canvas.
Jadi yang terlihat di jendela sama persis dengan berkas yang disimpan.
Teks bisa diseret ke mana saja, dan bentuk (persegi, lingkaran, coretan) bisa
digambar di atas gambar.

Jalankan:
    python meme.py                    # jendela, mulai dengan gambar contoh
    python meme.py foto.jpg
    python meme.py foto.jpg --top "SAAT KODE JALAN" --bottom "TAPI TIDAK TAHU KENAPA" -o meme.png
"""

import argparse
import math
import os
import sys
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFont

FONT_DIRS = [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"), "/usr/share/fonts/truetype/dejavu",
             "/Library/Fonts"]
FONTS = {  # nama tampilan -> berkas font
    "Impact": "impact.ttf",
    "Arial Black": "ariblk.ttf",
    "Comic Sans": "comicbd.ttf",
    "Segoe UI Bold": "segoeuib.ttf",
    "Georgia Bold": "georgiab.ttf",
    "Verdana Bold": "verdanab.ttf",
    "DejaVu Sans Bold": "DejaVuSans-Bold.ttf",
}
MAX_SIDE = 900  # gambar besar diperkecil supaya muat di layar dan cepat digambar ulang


def find_font(name):
    """Path berkas font, atau None kalau tidak ada di komputer ini."""
    filename = FONTS.get(name, name)
    for folder in FONT_DIRS:
        path = os.path.join(folder, filename)
        if os.path.isfile(path):
            return path
    return None


def available_fonts():
    return [name for name in FONTS if find_font(name)]


def load_font(name, size):
    path = find_font(name)
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


@dataclass
class TextItem:
    text: str
    x: float  # posisi tengah, 0..1 dari lebar gambar
    y: float  # posisi tengah, 0..1 dari tinggi gambar
    size: int = 48
    color: str = "#ffffff"
    font: str = "Impact"
    outline: bool = True
    uppercase: bool = True

    @property
    def shown(self):
        return self.text.upper() if self.uppercase else self.text


@dataclass
class Shape:
    kind: str  # "rect", "oval", atau "pen"
    points: list  # koordinat piksel
    color: str = "#ff3b30"
    width: int = 6


def wrap_text(draw, text, font, max_width):
    """Pecah teks menjadi beberapa baris supaya tidak lebih lebar dari max_width piksel."""
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if draw.textlength(trial, font=font) <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


@dataclass
class Meme:
    image: Image.Image
    texts: list = field(default_factory=list)
    shapes: list = field(default_factory=list)

    @classmethod
    def open(cls, path):
        with Image.open(path) as source:
            image = source.convert("RGB")
        if max(image.size) > MAX_SIDE:
            image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
        meme = cls(image)
        meme.texts = [TextItem("", 0.5, 0.1), TextItem("", 0.5, 0.9)]  # teks atas dan bawah
        return meme

    @property
    def top(self):
        return self.texts[0]

    @property
    def bottom(self):
        return self.texts[1]

    def text_layout(self, item, draw):
        """(baris, font, kotak x0, y0, x1, y1) untuk satu teks, dengan pusat di (x, y)."""
        font = load_font(item.font, item.size)
        lines = wrap_text(draw, item.shown, font, self.image.width * 0.94)
        ascent, descent = font.getmetrics()
        line_height = ascent + descent
        width = max((draw.textlength(line, font=font) for line in lines), default=0)
        height = line_height * len(lines)
        cx, cy = item.x * self.image.width, item.y * self.image.height
        # Jaga agar seluruh teks tetap di dalam gambar (misalnya teks atas yang menjadi dua baris).
        margin = 8
        cx = min(max(cx, width / 2 + margin), self.image.width - width / 2 - margin) \
            if width + 2 * margin < self.image.width else self.image.width / 2
        cy = min(max(cy, height / 2 + margin), self.image.height - height / 2 - margin) \
            if height + 2 * margin < self.image.height else self.image.height / 2
        box = (cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2)
        return lines, font, line_height, box

    def render(self):
        image = self.image.copy()
        draw = ImageDraw.Draw(image)
        for shape in self.shapes:
            if shape.kind == "pen":
                if len(shape.points) > 1:
                    draw.line(shape.points, fill=shape.color, width=shape.width, joint="curve")
                r = shape.width / 2
                for x, y in (shape.points[0], shape.points[-1]):
                    draw.ellipse((x - r, y - r, x + r, y + r), fill=shape.color)
            else:
                (x0, y0), (x1, y1) = shape.points
                box = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
                (draw.rectangle if shape.kind == "rect" else draw.ellipse)(box, outline=shape.color, width=shape.width)
        for item in self.texts:
            if not item.text.strip():
                continue
            lines, font, line_height, (x0, y0, _, _) = self.text_layout(item, draw)
            stroke = max(2, item.size // 14) if item.outline else 0
            box_width = self.text_layout(item, draw)[3][2] - x0
            for index, line in enumerate(lines):
                offset = (box_width - draw.textlength(line, font=font)) / 2
                draw.text((x0 + offset, y0 + index * line_height), line, font=font, fill=item.color,
                          stroke_width=stroke, stroke_fill="#000000")
        return image

    def hit_text(self, px, py):
        """Indeks teks di bawah titik piksel (px, py), dari yang paling atas. None kalau tidak ada."""
        draw = ImageDraw.Draw(self.image.copy())
        for index in range(len(self.texts) - 1, -1, -1):
            item = self.texts[index]
            if not item.text.strip():
                continue
            x0, y0, x1, y1 = self.text_layout(item, draw)[3]
            if x0 - 10 <= px <= x1 + 10 and y0 - 10 <= py <= y1 + 10:
                return index
        return None

    def move_text(self, index, px, py):
        self.texts[index].x = min(1.0, max(0.0, px / self.image.width))
        self.texts[index].y = min(1.0, max(0.0, py / self.image.height))

    def save(self, path):
        lower = path.lower()
        if lower.endswith(".png"):
            self.render().save(path, "PNG")
        elif lower.endswith((".jpg", ".jpeg")):
            self.render().save(path, "JPEG", quality=92)
        else:
            raise ValueError("Simpan sebagai .png atau .jpg.")
        return path


def demo_image(size=(800, 600)):
    """Gambar contoh: langit senja dengan matahari dan bukit (dibuat sendiri, bebas hak cipta)."""
    width, height = size
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        t = y / height
        draw.line((0, y, width, y), fill=(int(40 + 200 * t), int(60 + 90 * t), int(140 - 60 * t)))
    draw.ellipse((width * 0.6, height * 0.35, width * 0.6 + 150, height * 0.35 + 150), fill=(255, 196, 92))
    for i, color in enumerate(((48, 70, 60), (30, 48, 42))):
        points = [(x, height * (0.62 + 0.08 * i) + 40 * math.sin(x / (90 + 40 * i) + i)) for x in range(0, width + 10, 10)]
        draw.polygon(points + [(width, height), (0, height)], fill=color)
    return image


# --- tampilan Tkinter --------------------------------------------------------------

class MemeApp:
    def __init__(self, root, meme, notify=None, ask_save=None):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.root = root
        self.meme = meme
        self.notify = notify or self._notify
        self.ask_save = ask_save or self._ask_save
        self.photo = None
        self.drag = None
        self.mode = tk.StringVar(value="move")
        self.shape_color = "#ff3b30"
        fonts = available_fonts() or ["(bawaan)"]

        root.title("Meme Generator")
        panel = ttk.Frame(root, padding=12)
        panel.pack(side="left", fill="y")
        self.top_var = tk.StringVar(value=meme.top.text)
        self.bottom_var = tk.StringVar(value=meme.bottom.text)
        for label, var in (("Teks atas", self.top_var), ("Teks bawah", self.bottom_var)):
            ttk.Label(panel, text=label).pack(anchor="w")
            ttk.Entry(panel, textvariable=var, width=32).pack(fill="x", pady=(2, 8))
            var.trace_add("write", lambda *_: self.on_text())
        ttk.Label(panel, text="Font").pack(anchor="w")
        self.font_var = tk.StringVar(value=meme.top.font if meme.top.font in fonts else fonts[0])
        ttk.Combobox(panel, textvariable=self.font_var, values=fonts, state="readonly").pack(fill="x", pady=(2, 8))
        self.font_var.trace_add("write", lambda *_: self.on_style())
        ttk.Label(panel, text="Ukuran teks").pack(anchor="w")
        self.size_var = tk.IntVar(value=meme.top.size)
        ttk.Scale(panel, from_=16, to=120, variable=self.size_var, command=lambda _v: self.on_style()).pack(fill="x")
        color_row = ttk.Frame(panel)
        color_row.pack(fill="x", pady=8)
        ttk.Button(color_row, text="Warna teks…", command=self.pick_text_color).pack(side="left")
        self.color_swatch = tk.Label(color_row, width=3, background=meme.top.color, relief="solid", borderwidth=1)
        self.color_swatch.pack(side="left", padx=6)
        self.outline_var = tk.BooleanVar(value=True)
        self.upper_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(panel, text="Garis tepi hitam", variable=self.outline_var, command=self.on_style).pack(anchor="w")
        ttk.Checkbutton(panel, text="Huruf kapital", variable=self.upper_var, command=self.on_style).pack(anchor="w")

        ttk.Separator(panel).pack(fill="x", pady=10)
        ttk.Label(panel, text="Mouse di gambar:").pack(anchor="w")
        for value, label in (("move", "Seret teks"), ("rect", "Gambar persegi"), ("oval", "Gambar lingkaran"),
                             ("pen", "Coretan bebas")):
            ttk.Radiobutton(panel, text=label, value=value, variable=self.mode).pack(anchor="w")
        shape_row = ttk.Frame(panel)
        shape_row.pack(fill="x", pady=6)
        ttk.Button(shape_row, text="Warna bentuk…", command=self.pick_shape_color).pack(side="left")
        ttk.Button(shape_row, text="Hapus bentuk", command=self.clear_shapes).pack(side="left", padx=6)

        ttk.Separator(panel).pack(fill="x", pady=10)
        ttk.Button(panel, text="Buka gambar…", command=self.open_image).pack(fill="x")
        ttk.Button(panel, text="Simpan meme…", command=self.save).pack(fill="x", pady=6)
        self.status = tk.StringVar(value="Seret teks di gambar untuk memindahkannya.")
        ttk.Label(panel, textvariable=self.status, foreground="#555", wraplength=230).pack(anchor="w")

        self.canvas = tk.Canvas(root, highlightthickness=0, background="#222")
        self.canvas.pack(side="left", padx=(0, 12), pady=12)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        root.bind("<Control-s>", lambda _e: self.save())
        self.on_style()

    # --- teks dan gaya ----------------------------------------------------------
    def on_text(self):
        self.meme.top.text = self.top_var.get()
        self.meme.bottom.text = self.bottom_var.get()
        self.redraw()

    def on_style(self):
        for item in self.meme.texts:
            item.font = self.font_var.get()
            item.size = int(float(self.size_var.get()))
            item.outline = self.outline_var.get()
            item.uppercase = self.upper_var.get()
        self.redraw()

    def set_text_color(self, color):
        for item in self.meme.texts:
            item.color = color
        self.color_swatch.configure(background=color)
        self.redraw()

    def pick_text_color(self):
        from tkinter import colorchooser

        _, color = colorchooser.askcolor(color=self.meme.top.color, parent=self.root)
        if color:
            self.set_text_color(color)

    def pick_shape_color(self):
        from tkinter import colorchooser

        _, color = colorchooser.askcolor(color=self.shape_color, parent=self.root)
        if color:
            self.shape_color = color

    def clear_shapes(self):
        self.meme.shapes.clear()
        self.redraw()

    # --- gambar -----------------------------------------------------------------
    def redraw(self):
        from PIL import ImageTk

        image = self.meme.render()
        self.photo = ImageTk.PhotoImage(image, master=self.root)
        self.canvas.configure(width=image.width, height=image.height)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")

    def on_press(self, event):
        mode = self.mode.get()
        if mode == "move":
            index = self.meme.hit_text(event.x, event.y)
            self.drag = ("text", index) if index is not None else None
        else:
            point = (event.x, event.y)
            shape = Shape(mode, [point] if mode == "pen" else [point, point], self.shape_color)
            self.meme.shapes.append(shape)
            self.drag = ("shape", shape)

    def on_drag(self, event):
        if not self.drag:
            return
        kind, target = self.drag
        if kind == "text":
            self.meme.move_text(target, event.x, event.y)
        elif target.kind == "pen":
            target.points.append((event.x, event.y))
        else:
            target.points[1] = (event.x, event.y)
        self.redraw()

    def on_release(self, event):
        if self.drag and self.drag[0] == "shape":
            shape = self.drag[1]
            if shape.kind != "pen" and shape.points[0] == shape.points[1]:
                self.meme.shapes.remove(shape)  # klik tanpa menyeret
        self.drag = None
        self.redraw()

    def open_image(self):
        from tkinter import filedialog

        path = filedialog.askopenfilename(parent=self.root, filetypes=[("Gambar", "*.jpg *.jpeg *.png *.gif *.bmp")])
        if not path:
            return
        try:
            new = Meme.open(path)
        except OSError as error:
            self.notify(f"Gambar tidak bisa dibuka: {error}")
            return
        for old, item in zip(self.meme.texts, new.texts):
            item.text, item.size, item.color, item.font = old.text, old.size, old.color, old.font
        self.meme = new
        self.on_style()

    def save(self):
        path = self.ask_save()
        if not path:
            return None
        try:
            self.meme.save(path)
        except (ValueError, OSError) as error:
            self.notify(str(error))
            return None
        self.status.set(f"Tersimpan: {os.path.basename(path)}")
        return path

    def _ask_save(self):
        from tkinter import filedialog

        return filedialog.asksaveasfilename(parent=self.root, defaultextension=".png",
                                            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg")])

    def _notify(self, message):
        from tkinter import messagebox

        messagebox.showwarning("Meme Generator", message, parent=self.root)


def main(argv=None, gui=None):
    parser = argparse.ArgumentParser(description="Buat meme dari gambar.")
    parser.add_argument("image", nargs="?", help="gambar dasar (kosong: gambar contoh)")
    parser.add_argument("--top", default="", help="teks atas")
    parser.add_argument("--bottom", default="", help="teks bawah")
    parser.add_argument("--font", default="Impact", help=f"font: {', '.join(FONTS)}")
    parser.add_argument("--size", type=int, default=56, help="ukuran teks (piksel)")
    parser.add_argument("--color", default="#ffffff", help="warna teks, misalnya #ffffff")
    parser.add_argument("-o", "--output", help="simpan langsung ke berkas, tanpa jendela")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        meme = Meme.open(args.image) if args.image else Meme(demo_image(), [TextItem("", 0.5, 0.1),
                                                                             TextItem("", 0.5, 0.9)])
    except OSError as error:
        print(f"Error: gambar tidak bisa dibuka ({error})", file=sys.stderr)
        return 1
    meme.top.text, meme.bottom.text = args.top, args.bottom
    for item in meme.texts:
        item.font, item.size, item.color = args.font, args.size, args.color
    if args.output:
        try:
            meme.save(args.output)
        except (ValueError, OSError) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        print(f"Meme disimpan ke {args.output}")
        return 0
    (gui or run_gui)(meme)
    return 0


def run_gui(meme):
    import tkinter as tk

    root = tk.Tk()
    root.resizable(False, False)
    MemeApp(root, meme)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())
