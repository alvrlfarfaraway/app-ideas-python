"""QR Code Badge Generator: isi data peserta, buat badge nama dengan QR code yang bisa dipindai.

QR code berisi kartu kontak (vCard), jadi saat dipindai ponsel langsung
menawarkan "simpan kontak" berisi nama, email, Twitter, dan GitHub.
QR dibuat dengan segno (padanan Python untuk paket NPM qrcode-generator di
spesifikasi), dan badge digambar dengan Pillow.

Jalankan:
    python badge.py                                    # jendela Tkinter
    python badge.py --name "Rina Kartika" --email rina@example.com --twitter rinakartika \\
        --github rinakartika --event "PyCon ID 2026" -o badge.png
"""

import argparse
import io
import os
import re
import sys
import tempfile

import segno
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1050, 675  # 3,5 x 2,25 inci pada 300 dpi
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
TWITTER_RE = re.compile(r"^@[A-Za-z0-9_]{1,15}$")
GITHUB_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")
FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")


def normalize_twitter(value):
    """'rina' -> '@rina'. Tanda @ ditambahkan otomatis kalau belum ada."""
    value = value.strip()
    return value if not value or value.startswith("@") else "@" + value


def validate(name, email, twitter="", github=""):
    """Daftar pesan kesalahan (kosong kalau semua benar)."""
    errors = []
    name, email, twitter, github = (v.strip() for v in (name, email, twitter, github))
    if not name:
        errors.append("Nama wajib diisi.")
    elif len(name.split()) < 2:
        errors.append("Tulis nama depan dan nama belakang.")
    if not email:
        errors.append("Email wajib diisi.")
    elif not EMAIL_RE.match(email):
        errors.append(f"'{email}' bukan alamat email yang valid.")
    if twitter and not twitter.startswith("@"):
        errors.append("Akun Twitter harus diawali '@'.")
    elif twitter and not TWITTER_RE.match(twitter):
        errors.append("Akun Twitter hanya boleh berisi huruf, angka, dan _ (maksimal 15 karakter).")
    if github and not GITHUB_RE.match(github.lstrip("@")):
        errors.append(f"'{github}' bukan nama akun GitHub yang valid.")
    return errors


def _escape(value):
    return value.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")


def vcard(name, email, twitter="", github=""):
    """Teks vCard 3.0 untuk QR code."""
    parts = name.split()
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"N:{_escape(parts[-1])};{_escape(' '.join(parts[:-1]))};;;",
             f"FN:{_escape(name)}", f"EMAIL;TYPE=INTERNET:{email}"]
    if twitter:
        lines.append(f"URL;TYPE=Twitter:https://twitter.com/{twitter.lstrip('@')}")
    if github:
        lines.append(f"URL;TYPE=GitHub:https://github.com/{github.lstrip('@')}")
    lines.append("END:VCARD")
    return "\r\n".join(lines)


def qr_image(data, scale=8):
    """QR code sebagai PIL.Image (koreksi kesalahan M, sekitar 15% data bisa rusak)."""
    qr = segno.make(data, error="m", micro=False)
    buffer = io.BytesIO()
    qr.save(buffer, kind="png", scale=scale, border=2)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB"), qr


def _font(names, size):
    for name in names:
        for path in (os.path.join(FONT_DIR, name), name):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def _fit(draw, text, fonts, size, max_width):
    """Font terbesar (mulai dari size) yang membuat teks muat di max_width."""
    while size > 18:
        font = _font(fonts, size)
        if draw.textlength(text, font=font) <= max_width:
            return font
        size -= 4
    return _font(fonts, size)


def render_badge(name, email, twitter="", github="", event="Meetup", accent="#2e78c7"):
    """Badge nama siap cetak (PIL.Image, 1050 x 675 piksel = 3,5 x 2,25 inci pada 300 dpi)."""
    errors = validate(name, email, twitter, github)
    if errors:
        raise ValueError(" ".join(errors))
    name, email, twitter, github = (v.strip() for v in (name, email, twitter, github))
    image = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(image)
    bold, regular = ["segoeuib.ttf", "DejaVuSans-Bold.ttf"], ["segoeui.ttf", "DejaVuSans.ttf"]
    draw.rectangle((0, 0, WIDTH, 110), fill=accent)
    draw.text((48, 55), event, font=_fit(draw, event, bold, 52, WIDTH - 96), fill="white", anchor="lm")
    draw.text((WIDTH - 48, 55), "HALO, NAMA SAYA", font=_font(bold, 24), fill="#dbe8f7", anchor="rm")
    side = 380
    data = vcard(name, email, twitter, github)
    modules = segno.make(data, error="m", micro=False).symbol_size(border=2)[0]
    qr, _ = qr_image(data, scale=max(1, side // modules))  # skala bulat: setiap modul sama besar
    image.paste(qr, (WIDTH - side - 40 + (side - qr.width) // 2, 160 + (side - qr.height) // 2))
    text_width = WIDTH - side - 120
    first, *rest = name.split()
    draw.text((48, 170), first, font=_fit(draw, first, bold, 110, text_width), fill="#1d1d1b")
    draw.text((48, 300), " ".join(rest), font=_fit(draw, " ".join(rest), regular, 60, text_width), fill="#1d1d1b")
    y = 410
    for label, value in (("Email", email), ("Twitter", twitter), ("GitHub", github)):
        if value:
            draw.text((48, y), label.upper(), font=_font(bold, 20), fill="#7a7a75")
            draw.text((48, y + 24), value, font=_fit(draw, value, regular, 34, text_width), fill="#1d1d1b")
            y += 72
    draw.text((WIDTH - side / 2 - 40, 560), "Pindai untuk simpan kontak", font=_font(regular, 22), fill="#7a7a75",
              anchor="mm")
    draw.rectangle((0, HEIGHT - 16, WIDTH, HEIGHT), fill=accent)
    return image


def save_badge(image, path):
    lower = path.lower()
    if lower.endswith(".pdf"):
        image.save(path, "PDF", resolution=300)
    elif lower.endswith(".png"):
        image.save(path, "PNG", dpi=(300, 300))
    else:
        raise ValueError("Simpan sebagai .png atau .pdf.")
    return path


def print_file(path):
    """Kirim berkas ke printer bawaan Windows (lewat aplikasi pembuka gambar/PDF)."""
    if not hasattr(os, "startfile"):
        raise OSError("Mencetak langsung hanya didukung di Windows. Buka berkas PDF-nya lalu cetak.")
    os.startfile(path, "print")


# --- tampilan Tkinter ----------------------------------------------------------------

class BadgeApp:
    FIELDS = (("name", "Nama lengkap *"), ("email", "Email *"), ("twitter", "Twitter"), ("github", "GitHub"),
              ("event", "Nama acara"))

    def __init__(self, root, printer=print_file, ask_save=None):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.root = root
        self.printer = printer
        self.ask_save = ask_save or self._ask_save
        self.badge = None
        self.photo = None
        root.title("QR Code Badge Generator")
        root.resizable(False, False)
        form = ttk.LabelFrame(root, text="Data peserta", padding=12)
        form.pack(side="left", fill="y", padx=12, pady=12)
        self.vars = {}
        for row, (key, label) in enumerate(self.FIELDS):
            ttk.Label(form, text=label).grid(row=row * 2, column=0, sticky="w")
            var = tk.StringVar(value="Meetup Python Jogja" if key == "event" else "")
            entry = ttk.Entry(form, textvariable=var, width=32)
            entry.grid(row=row * 2 + 1, column=0, sticky="we", pady=(2, 8))
            self.vars[key] = var
            if key == "twitter":
                entry.bind("<FocusOut>", lambda _e: self.vars["twitter"].set(normalize_twitter(self.vars["twitter"].get())))
        buttons = ttk.Frame(form)
        buttons.grid(row=20, column=0, sticky="we", pady=(6, 0))
        ttk.Button(buttons, text="Cancel", command=self.cancel).pack(side="left")
        ttk.Button(buttons, text="Create", command=self.create).pack(side="right")
        self.errors = tk.StringVar()
        ttk.Label(form, textvariable=self.errors, foreground="#b3261e", wraplength=260, justify="left").grid(
            row=21, column=0, sticky="w", pady=(10, 0))

        panel = ttk.LabelFrame(root, text="Badge", padding=12)
        panel.pack(side="left", padx=(0, 12), pady=12)
        self.preview = ttk.Label(panel, text="Isi data lalu tekan Create.", width=60, anchor="center")
        self.preview.pack()
        actions = ttk.Frame(panel)
        actions.pack(fill="x", pady=(10, 0))
        self.print_button = ttk.Button(actions, text="Print", command=self.print_badge, state="disabled")
        self.print_button.pack(side="right")
        self.save_button = ttk.Button(actions, text="Simpan PNG/PDF…", command=self.save, state="disabled")
        self.save_button.pack(side="right", padx=6)
        self.status = tk.StringVar()
        ttk.Label(actions, textvariable=self.status, foreground="#555").pack(side="left")

    def values(self):
        return {key: var.get().strip() for key, var in self.vars.items()}

    def create(self):
        from PIL import ImageTk

        self.vars["twitter"].set(normalize_twitter(self.vars["twitter"].get()))
        v = self.values()
        errors = validate(v["name"], v["email"], v["twitter"], v["github"])
        if errors:
            self.errors.set("\n".join(errors))
            self.set_badge(None)
            return None
        self.errors.set("")
        badge = render_badge(v["name"], v["email"], v["twitter"], v["github"], v["event"] or "Meetup")
        self.set_badge(badge)
        preview = badge.resize((WIDTH * 2 // 5, HEIGHT * 2 // 5), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(preview, master=self.root)
        self.preview.configure(image=self.photo, text="")
        return badge

    def set_badge(self, badge):
        self.badge = badge
        state = "normal" if badge is not None else "disabled"
        self.print_button.configure(state=state)
        self.save_button.configure(state=state)
        if badge is None:
            self.preview.configure(image="", text="Isi data lalu tekan Create.")

    def cancel(self):
        for key, var in self.vars.items():
            if key != "event":
                var.set("")
        self.errors.set("")
        self.status.set("")
        self.set_badge(None)

    def print_badge(self):
        if self.badge is None:
            return
        path = os.path.join(tempfile.gettempdir(), "badge-cetak.pdf")
        save_badge(self.badge, path)
        try:
            self.printer(path)
            self.status.set("Dikirim ke printer.")
        except OSError as error:
            self.status.set(f"Gagal mencetak: {error}")

    def save(self):
        path = self.ask_save()
        if path and self.badge is not None:
            save_badge(self.badge, path)
            self.status.set(f"Tersimpan: {os.path.basename(path)}")
        return path

    def _ask_save(self):
        from tkinter import filedialog

        return filedialog.asksaveasfilename(parent=self.root, defaultextension=".png",
                                            filetypes=[("PNG", "*.png"), ("PDF", "*.pdf")])


def main(argv=None, gui=None):
    parser = argparse.ArgumentParser(description="Buat badge nama dengan QR code.")
    parser.add_argument("--name", help="nama lengkap (tanpa ini: buka jendela)")
    parser.add_argument("--email")
    parser.add_argument("--twitter", default="")
    parser.add_argument("--github", default="")
    parser.add_argument("--event", default="Meetup")
    parser.add_argument("-o", "--output", default="badge.png", help="berkas .png atau .pdf")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.name is None:
        (gui or run_gui)()
        return 0
    twitter = normalize_twitter(args.twitter)
    try:
        save_badge(render_badge(args.name, args.email or "", twitter, args.github, args.event), args.output)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"Badge disimpan ke {args.output}")
    return 0


def run_gui():
    import tkinter as tk

    root = tk.Tk()
    BadgeApp(root)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())
