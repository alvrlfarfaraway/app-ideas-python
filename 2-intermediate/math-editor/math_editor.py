"""Math Editor: dokumen teks dengan rumus matematika, disimpan dan dibuka lagi utuh.

Rumus ditulis dalam LaTeX di antara $...$ (dalam kalimat) atau $$...$$ (baris
sendiri), lalu digambar oleh matplotlib.mathtext. Format teks:
    **tebal**   *miring*   [warna=#c0392b]teks berwarna[/warna]   ![keterangan](gambar.png)

Dokumen disimpan sebagai berkas .mathdoc (JSON). Gambar yang disisipkan ikut
disimpan di dalamnya (base64), jadi dokumen tetap utuh walau dipindah.

Jalankan:
    python math_editor.py                         # jendela Tkinter
    python math_editor.py tugas.mathdoc           # buka dokumen
    python math_editor.py tugas.mathdoc --html tugas.html   # ekspor HTML (rumus sebagai SVG)
"""

import argparse
import base64
import html
import io
import json
import mimetypes
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
from matplotlib import mathtext  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402

FORMAT_VERSION = 1
MIN_FONT, MAX_FONT = 8, 40
MAX_IMAGE_BYTES = 5_000_000

TOKEN_RE = re.compile(
    r"(?P<display>\$\$(?P<display_tex>.+?)\$\$)"
    r"|(?P<inline>(?<!\\)\$(?P<inline_tex>[^$\n]+?)(?<!\\)\$)"
    r"|(?P<image>!\[(?P<alt>[^\]]*)\]\((?P<src>[^)\s]+)\))"
    r"|(?P<bold>\*\*(?P<bold_text>.+?)\*\*(?!\*))"  # ***x*** : tebal di luar, miring di dalam
    r"|(?P<italic>(?<![*\w])\*(?P<italic_text>[^*\n]+?)\*(?![*\w]))"
    r"|(?P<color>\[warna=(?P<color_value>#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\](?P<color_text>.+?)\[/warna\])",
    re.DOTALL,
)


class DocumentError(Exception):
    """Kesalahan berkas dokumen yang ditampilkan ke pengguna."""


# --- mengurai teks -------------------------------------------------------------

def parse(text):
    """Pecah teks menjadi potongan (jenis, isi, gaya).

    Jenis: 'text', 'math' (dalam kalimat), 'display' (rumus baris sendiri), 'image'.
    Gaya untuk teks: kumpulan dari 'bold', 'italic', dan 'color:#rrggbb'.
    """
    segments = []

    def walk(chunk, styles):
        position = 0
        for match in TOKEN_RE.finditer(chunk):
            if match.start() > position:
                segments.append(("text", _unescape(chunk[position:match.start()]), frozenset(styles)))
            kind = match.lastgroup if match.lastgroup in ("display", "inline", "image", "bold", "italic",
                                                          "color") else _outer_group(match)
            if kind == "display":
                segments.append(("display", match.group("display_tex").strip(), frozenset(styles)))
            elif kind == "inline":
                segments.append(("math", match.group("inline_tex").strip(), frozenset(styles)))
            elif kind == "image":
                segments.append(("image", match.group("src"), frozenset({f"alt:{match.group('alt')}"})))
            elif kind == "bold":
                walk(match.group("bold_text"), styles | {"bold"})
            elif kind == "italic":
                walk(match.group("italic_text"), styles | {"italic"})
            elif kind == "color":
                walk(match.group("color_text"), styles | {f"color:{_full_hex(match.group('color_value'))}"})
            position = match.end()
        if position < len(chunk):
            segments.append(("text", _unescape(chunk[position:]), frozenset(styles)))

    walk(text, frozenset())
    return [s for s in segments if s[0] != "text" or s[1]]


def _outer_group(match):
    for name in ("display", "inline", "image", "bold", "italic", "color"):
        if match.group(name) is not None:
            return name
    return None


def _unescape(text):
    return text.replace("\\$", "$")


def _full_hex(value):
    value = value.lower()
    return "#" + "".join(ch * 2 for ch in value[1:]) if len(value) == 4 else value


def formulas(text):
    return [s[1] for s in parse(text) if s[0] in ("math", "display")]


# --- menggambar rumus ------------------------------------------------------------

def render_formula(tex, size=14, color="#1d1d1b", fmt="png", dpi=120):
    """Bytes gambar rumus. ValueError dengan pesan yang bisa dibaca kalau LaTeX-nya salah."""
    buffer = io.BytesIO()
    try:
        mathtext.math_to_image(f"${tex}$", buffer, prop=FontProperties(size=size), dpi=dpi, format=fmt,
                               color=color)
    except ValueError as error:
        first = str(error).strip().splitlines()
        detail = first[-1] if first else "LaTeX tidak valid"
        raise ValueError(f"Rumus '{tex}' tidak bisa dibaca: {detail}") from None
    return buffer.getvalue()


def check_formulas(text):
    """Daftar pesan kesalahan untuk rumus yang tidak bisa digambar."""
    errors = []
    for tex in formulas(text):
        try:
            render_formula(tex, fmt="svg")
        except ValueError as error:
            errors.append(str(error))
    return errors


# --- berkas dokumen -------------------------------------------------------------

def collect_images(text, base_dir="."):
    """{src: data-URI} untuk gambar yang dirujuk teks dan ada di disk."""
    images = {}
    for kind, src, _ in parse(text):
        if kind != "image" or src in images or src.startswith("data:"):
            continue
        path = src if os.path.isabs(src) else os.path.join(base_dir, src)
        if not os.path.isfile(path):
            continue
        if os.path.getsize(path) > MAX_IMAGE_BYTES:
            raise DocumentError(f"Gambar {src} lebih dari 5 MB.")
        mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as handle:
            images[src] = f"data:{mime};base64,{base64.b64encode(handle.read()).decode('ascii')}"
    return images


def save_document(path, text, font_size=12, images=None):
    if not MIN_FONT <= font_size <= MAX_FONT:
        raise DocumentError(f"Ukuran huruf harus {MIN_FONT}-{MAX_FONT}.")
    data = {"format": "mathdoc", "version": FORMAT_VERSION, "font_size": font_size, "text": text,
            "images": images if images is not None else collect_images(text, os.path.dirname(os.path.abspath(path)))}
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)
    os.replace(temp, path)
    return data


def load_document(path):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        raise DocumentError(f"Berkas {path} tidak ada.") from None
    except (OSError, ValueError):
        raise DocumentError(f"Berkas {path} bukan dokumen .mathdoc yang valid.") from None
    if not isinstance(data, dict) or data.get("format") != "mathdoc" or not isinstance(data.get("text"), str):
        raise DocumentError(f"Berkas {path} bukan dokumen .mathdoc yang valid.")
    if data.get("version", 0) > FORMAT_VERSION:
        raise DocumentError("Dokumen dibuat dengan versi Math Editor yang lebih baru.")
    size = data.get("font_size", 12)
    images = data.get("images") if isinstance(data.get("images"), dict) else {}
    return {"text": data["text"], "font_size": size if isinstance(size, int) and MIN_FONT <= size <= MAX_FONT else 12,
            "images": {k: v for k, v in images.items() if isinstance(v, str) and v.startswith("data:")}}


def image_bytes(src, images, base_dir="."):
    """Bytes gambar dari dokumen (data-URI) atau dari disk. None kalau tidak ada."""
    uri = images.get(src) or (src if src.startswith("data:") else None)
    if uri:
        try:
            return base64.b64decode(uri.split(",", 1)[1])
        except (IndexError, ValueError):
            return None
    path = src if os.path.isabs(src) else os.path.join(base_dir, src)
    if os.path.isfile(path):
        with open(path, "rb") as handle:
            return handle.read()
    return None


def export_html(text, font_size=12, images=None, title="Dokumen"):
    """HTML mandiri: rumus sebagai SVG di dalam halaman, gambar sebagai data-URI."""
    images = images or {}
    parts = []
    for kind, value, styles in parse(text):
        if kind == "text":
            chunk = html.escape(value).replace("\n", "<br>\n")
            if "bold" in styles:
                chunk = f"<strong>{chunk}</strong>"
            if "italic" in styles:
                chunk = f"<em>{chunk}</em>"
            color = next((s.split(":", 1)[1] for s in styles if s.startswith("color:")), None)
            if color:
                chunk = f'<span style="color:{color}">{chunk}</span>'
            parts.append(chunk)
        elif kind in ("math", "display"):
            try:
                # Ukuran huruf halaman dalam px; SVG matplotlib memakai pt (1 px = 0,75 pt).
                points = (font_size + 4) * 0.75 * (1.35 if kind == "display" else 1.0)
                svg = render_formula(value, size=points, fmt="svg")
                svg = svg.decode("utf-8")
                svg = svg[svg.index("<svg"):]
                css = "display" if kind == "display" else "inline"
                parts.append(f'<span class="math {css}" title="{html.escape(value)}">{svg}</span>')
            except ValueError as error:
                parts.append(f'<span class="error">{html.escape(str(error))}</span>')
        elif kind == "image":
            uri = images.get(value) or (value if value.startswith(("data:", "https://")) else None)
            alt = next((s[4:] for s in styles if s.startswith("alt:")), "")
            if uri:
                parts.append(f'<img src="{html.escape(uri)}" alt="{html.escape(alt)}">')
            else:
                parts.append(f'<span class="error">[gambar {html.escape(value)} tidak ditemukan]</span>')
    body = "".join(parts)
    return f"""<!DOCTYPE html>
<html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
body {{ max-width: 760px; margin: 32px auto; padding: 0 20px; font: {font_size + 4}px/1.6 Cambria, Georgia, serif; color: #1d1d1b; }}
.math.inline svg {{ vertical-align: middle; }}
.math.display {{ display: block; text-align: center; margin: .6em 0; }}
img {{ max-width: 100%; display: block; margin: .6em 0; }}
.error {{ color: #b3261e; font: 14px monospace; }}
</style></head><body>
{body}
</body></html>
"""


# --- tampilan Tkinter -------------------------------------------------------------

SAMPLE = """Persamaan Kuadrat

Akar-akar dari **ax² + bx + c = 0** dicari dengan rumus abc:

$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$

Nilai $D = b^2 - 4ac$ disebut *diskriminan*:
- [warna=#2a7d46]D > 0[/warna]: dua akar real berbeda
- [warna=#2e78c7]D = 0[/warna]: dua akar kembar
- [warna=#c0392b]D < 0[/warna]: tidak ada akar real

Contoh: $x^2 - 5x + 6 = 0$ punya $D = 25 - 24 = 1$, jadi $x_1 = 3$ dan $x_2 = 2$.

Luas di bawah kurva $y = x^2$ dari 0 sampai 1:
$$\\int_0^1 x^2\\,dx = \\frac{1}{3}$$
"""


class MathEditorApp:
    def __init__(self, root, path=None, ask_open=None, ask_save=None, ask_formula=None, notify=None):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.root = root
        self.path = None
        self.images = {}
        self.photos = []
        self.job = None
        self.ask_open = ask_open or self._ask_open
        self.ask_save = ask_save or self._ask_save
        self.ask_formula = ask_formula or self._ask_formula
        self.notify = notify or self._notify
        self.font_size = tk.IntVar(value=12)

        root.title("Math Editor")
        bar = ttk.Frame(root, padding=(10, 8))
        bar.pack(fill="x")
        for text, command in (("Baru", self.new), ("Buka…", self.open), ("Simpan", self.save),
                              ("Ekspor HTML…", self.export)):
            ttk.Button(bar, text=text, command=command).pack(side="left", padx=(0, 4))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(bar, text="∑ Rumus", command=self.insert_formula).pack(side="left", padx=(0, 4))
        ttk.Button(bar, text="Gambar…", command=self.insert_image).pack(side="left", padx=(0, 4))
        ttk.Button(bar, text="B", width=3, command=lambda: self.wrap("**", "**")).pack(side="left")
        ttk.Button(bar, text="I", width=3, command=lambda: self.wrap("*", "*")).pack(side="left", padx=2)
        ttk.Button(bar, text="Warna…", command=self.color).pack(side="left")
        ttk.Label(bar, text="Ukuran huruf").pack(side="left", padx=(12, 4))
        ttk.Spinbox(bar, from_=MIN_FONT, to=MAX_FONT, width=4, textvariable=self.font_size,
                    command=self.refresh).pack(side="left")

        panes = ttk.PanedWindow(root, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self.source = tk.Text(panes, wrap="word", undo=True, font=("Consolas", 11), width=50, height=26)
        self.preview = tk.Text(panes, wrap="word", width=56, height=26, padx=14, pady=10, background="#fffdf7",
                               cursor="arrow")
        panes.add(self.source, weight=1)
        panes.add(self.preview, weight=1)
        self.status = tk.StringVar()
        ttk.Label(root, textvariable=self.status, foreground="#555", padding=(10, 0, 10, 8)).pack(anchor="w")
        self.source.bind("<<Modified>>", self.on_modified)
        root.bind("<Control-s>", lambda _e: self.save())
        root.bind("<Control-o>", lambda _e: self.open())
        if path:
            self.load(path)
        else:
            self.set_text(SAMPLE)

    # --- teks -----------------------------------------------------------------
    @property
    def text(self):
        return self.source.get("1.0", "end-1c")

    def set_text(self, text):
        self.source.delete("1.0", "end")
        self.source.insert("1.0", text)
        self.source.edit_modified(False)
        self.refresh()

    def on_modified(self, _event=None):
        if self.source.edit_modified():
            self.source.edit_modified(False)
            if self.job:
                self.root.after_cancel(self.job)
            self.job = self.root.after(300, self.refresh)

    def wrap(self, before, after):
        try:
            start, end = self.source.index("sel.first"), self.source.index("sel.last")
        except self.tk.TclError:
            start = end = self.source.index("insert")
        self.source.insert(end, after)
        self.source.insert(start, before)
        self.refresh()

    def insert_formula(self):
        tex = self.ask_formula()
        if not tex:
            return
        try:
            render_formula(tex, fmt="svg")
        except ValueError as error:
            self.notify(str(error))
            return
        self.source.insert("insert", f"${tex}$")
        self.refresh()

    def insert_image(self):
        from tkinter import filedialog

        path = filedialog.askopenfilename(parent=self.root, title="Pilih gambar",
                                          filetypes=[("Gambar", "*.png *.jpg *.jpeg *.gif")])
        if path:
            self.add_image(path)

    def add_image(self, path):
        name = os.path.basename(path)
        self.images.update(collect_images(f"![]({path})"))
        self.images[name] = self.images.pop(path)
        self.source.insert("insert", f"\n![{os.path.splitext(name)[0]}]({name})\n")
        self.refresh()

    def color(self):
        from tkinter import colorchooser

        _, chosen = colorchooser.askcolor(parent=self.root, title="Warna teks")
        if chosen:
            self.wrap(f"[warna={chosen}]", "[/warna]")

    # --- pratinjau --------------------------------------------------------------
    def refresh(self):
        from PIL import Image, ImageTk

        self.job = None
        try:
            size = max(MIN_FONT, min(MAX_FONT, int(self.font_size.get())))
        except (ValueError, self.tk.TclError):
            size = 12
        p = self.preview
        p.configure(state="normal")
        p.delete("1.0", "end")
        self.photos = []
        base = ("Cambria", size)
        p.configure(font=base)
        p.tag_configure("error", foreground="#b3261e", font=("Consolas", max(8, size - 2)))
        p.tag_configure("center", justify="center")
        errors = 0
        base_dir = os.path.dirname(os.path.abspath(self.path)) if self.path else "."
        for kind, value, styles in parse(self.text):
            if kind == "text":
                tags = self._style_tag(styles, size)
                p.insert("end", value, tags)
            elif kind in ("math", "display"):
                try:
                    data = render_formula(value, size=size * (1.4 if kind == "display" else 1.05))
                    photo = ImageTk.PhotoImage(Image.open(io.BytesIO(data)), master=self.root)
                    self.photos.append(photo)
                    if kind == "display":
                        p.insert("end", "\n", ("center",))
                    p.image_create("end", image=photo, align="center", padx=2)
                    if kind == "display":
                        p.tag_add("center", "end-2c", "end-1c")
                        p.insert("end", "\n")
                except ValueError as error:
                    errors += 1
                    p.insert("end", f"[{error}]", ("error",))
            elif kind == "image":
                data = image_bytes(value, self.images, base_dir)
                if data is None:
                    p.insert("end", f"[gambar {value} tidak ditemukan]", ("error",))
                    continue
                with Image.open(io.BytesIO(data)) as image:
                    image.thumbnail((420, 320))
                    photo = ImageTk.PhotoImage(image.convert("RGBA"), master=self.root)
                self.photos.append(photo)
                p.image_create("end", image=photo)
        p.configure(state="disabled")
        count = len(formulas(self.text))
        name = os.path.basename(self.path) if self.path else "dokumen baru"
        self.status.set(f"{name} | {count} rumus" + (f" | {errors} rumus salah" if errors else ""))

    def _style_tag(self, styles, size):
        weight = "bold" if "bold" in styles else "normal"
        slant = "italic" if "italic" in styles else "roman"
        color = next((s.split(":", 1)[1] for s in styles if s.startswith("color:")), "#1d1d1b")
        name = f"s-{weight}-{slant}-{color}-{size}"
        self.preview.tag_configure(name, font=("Cambria", size, weight, slant), foreground=color)
        return (name,)

    # --- berkas ---------------------------------------------------------------------
    def new(self):
        self.path = None
        self.images = {}
        self.font_size.set(12)
        self.set_text("")

    def open(self):
        path = self.ask_open()
        if path:
            self.load(path)

    def load(self, path):
        try:
            doc = load_document(path)
        except DocumentError as error:
            self.notify(str(error))
            return False
        self.path = path
        self.images = doc["images"]
        self.font_size.set(doc["font_size"])
        self.set_text(doc["text"])
        return True

    def save(self):
        path = self.path or self.ask_save(".mathdoc", [("Dokumen Math Editor", "*.mathdoc")])
        if not path:
            return None
        images = dict(collect_images(self.text, os.path.dirname(os.path.abspath(path))))
        images.update({k: v for k, v in self.images.items() if k in self.text})
        try:
            save_document(path, self.text, int(self.font_size.get()), images)
        except (DocumentError, OSError, ValueError) as error:
            self.notify(str(error))
            return None
        self.path = path
        self.images = images
        self.refresh()
        self.status.set(self.status.get() + " | tersimpan")
        return path

    def export(self):
        path = self.ask_save(".html", [("HTML", "*.html")])
        if path:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(export_html(self.text, int(self.font_size.get()), self.images,
                                         title=os.path.basename(self.path or "Dokumen")))
            self.status.set(f"Diekspor ke {os.path.basename(path)}")
        return path

    def _ask_open(self):
        from tkinter import filedialog

        return filedialog.askopenfilename(parent=self.root, filetypes=[("Dokumen Math Editor", "*.mathdoc")])

    def _ask_save(self, extension, types):
        from tkinter import filedialog

        return filedialog.asksaveasfilename(parent=self.root, defaultextension=extension, filetypes=types)

    def _ask_formula(self):
        from tkinter import simpledialog

        return simpledialog.askstring("Sisipkan rumus", "Rumus LaTeX, misalnya \\frac{a}{b} atau x^2 + y^2 = r^2:",
                                      parent=self.root)

    def _notify(self, message):
        from tkinter import messagebox

        messagebox.showwarning("Math Editor", message, parent=self.root)


def main(argv=None, gui=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Editor dokumen dengan rumus matematika.")
    parser.add_argument("document", nargs="?", help="berkas .mathdoc")
    parser.add_argument("--html", help="ekspor dokumen ke HTML lalu keluar")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.html:
        if not args.document:
            parser.error("--html butuh nama berkas .mathdoc")
        try:
            doc = load_document(args.document)
        except DocumentError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        with open(args.html, "w", encoding="utf-8") as handle:
            handle.write(export_html(doc["text"], doc["font_size"], doc["images"], os.path.basename(args.document)))
        for message in check_formulas(doc["text"]):
            print(f"Peringatan: {message}", file=sys.stderr)
        print(f"HTML ditulis ke {args.html} ({len(formulas(doc['text']))} rumus)")
        return 0
    (gui or run_gui)(args.document)
    return 0


def run_gui(path=None):
    import tkinter as tk

    root = tk.Tk()
    MathEditorApp(root, path)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())
