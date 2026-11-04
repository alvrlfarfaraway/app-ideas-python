"""Image Scanner: baca teks dari foto, lalu temukan nomor telepon, email, dan tautan.

OCR memakai mesin bawaan Windows 10/11 (Windows.Media.Ocr) lewat skrip PowerShell
windows_ocr.ps1, jadi tidak perlu memasang Tesseract. Hasil bisa disimpan sebagai
kontak (.vcf), dan setiap pemindaian masuk ke riwayat yang bisa diberi tag.

Jalankan:
    python scanner.py                                  # jendela Tkinter
    python scanner.py kartu.jpg                        # terminal
    python scanner.py kartu.jpg --vcf rina.vcf --tag kerja
    python scanner.py --history --tag kerja
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OCR_SCRIPT = os.path.join(HERE, "windows_ocr.ps1")
HISTORY = os.path.join(os.path.expanduser("~"), ".app-ideas-python", "scanner-history.json")
IMAGE_TYPES = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff")


class ScanError(Exception):
    """Kesalahan yang ditampilkan ke pengguna sebagai pesan biasa."""


# --- OCR -------------------------------------------------------------------------

def ocr(path, runner=subprocess.run):
    """Baris-baris teks dari gambar. Memanggil windows_ocr.ps1 lewat PowerShell."""
    if not os.path.isfile(path):
        raise ScanError(f"Berkas '{path}' tidak ada.")
    if not path.lower().endswith(IMAGE_TYPES):
        raise ScanError("Pilih berkas gambar (.jpg, .png, .bmp, .gif, atau .tif).")
    command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", OCR_SCRIPT,
               "-Path", os.path.abspath(path)]
    try:
        done = runner(command, capture_output=True, timeout=60,
                      creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except FileNotFoundError:
        raise ScanError("PowerShell tidak ditemukan. OCR ini butuh Windows 10/11.") from None
    except subprocess.TimeoutExpired:
        raise ScanError("OCR terlalu lama (lebih dari 60 detik).") from None
    stdout = done.stdout.decode("utf-8", "replace") if isinstance(done.stdout, bytes) else done.stdout
    stderr = done.stderr.decode("utf-8", "replace") if isinstance(done.stderr, bytes) else done.stderr
    if done.returncode != 0:
        reason = next((line.strip() for line in (stderr or "").splitlines() if line.strip()), "tidak diketahui")
        raise ScanError(f"OCR gagal: {reason}")
    try:
        data = json.loads(stdout.strip().lstrip("\ufeff"))
        lines = data["lines"]
    except (ValueError, KeyError, TypeError):
        raise ScanError("Keluaran OCR tidak bisa dibaca.") from None
    if isinstance(lines, str):  # ConvertTo-Json kadang meratakan daftar satu elemen
        lines = [lines]
    return [str(line) for line in lines or []]


# --- ekstraksi -------------------------------------------------------------------

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
URL_RE = re.compile(r"\b(?:https?://|www\.)[^\s<>\"']+", re.IGNORECASE)
# Domain tanpa http/www (misalnya bit.ly/abc atau tokoku.id) diterima kalau akhirannya dikenal
# atau diikuti path "/...". Dengan begitu "foto.jpg" atau "09.00" tidak dianggap tautan.
BARE_DOMAIN_RE = re.compile(r"(?<![@\w.-])((?:[a-z0-9-]{2,}\.)+([a-z]{2,6}))(/[^\s<>\"']*)?(?![\w@-])",
                            re.IGNORECASE)
KNOWN_TLDS = {"com", "net", "org", "id", "io", "co", "dev", "app", "edu", "gov", "info", "me", "ai", "ly", "xyz",
              "site", "online", "store", "tech", "tv", "gg", "link", "uk", "us", "sg", "my", "au", "jp"}
# Nomor telepon diawali +, 0, atau tanda kurung; boleh berisi spasi, titik, tanda hubung, dan kurung.
PHONE_RE = re.compile(r"(?<![\w+])(?:\+|\(0|0)[\d\s().-]{6,}\d")
DATE_RE = re.compile(r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}$")
TRAILING = ".,;:!?)]}'\""


def _strip(text):
    while text and text[-1] in TRAILING:
        if text[-1] == ")" and text.count("(") >= text.count(")"):
            break
        text = text[:-1]
    return text


def normalize_phone(text):
    """'+62 812-3456-7890' -> '+6281234567890'; '(021) 555-0123' -> '0215550123'."""
    digits = re.sub(r"\D", "", text)
    return ("+" if text.strip().startswith("+") else "") + digits


def _unique(items, key=lambda x: x):
    seen = set()
    out = []
    for item in items:
        k = key(item)
        if k not in seen:
            seen.add(k)
            out.append(item)
    return out


def extract(lines):
    """Kelompokkan temuan: {'phones': [...], 'emails': [...], 'links': [...]} (urutan sesuai gambar)."""
    text = "\n".join(lines)
    emails = _unique((m.group(0).rstrip(".") for m in EMAIL_RE.finditer(text)), key=str.lower)
    without_emails = EMAIL_RE.sub(" ", text)
    links = [_strip(m.group(0)) for m in URL_RE.finditer(without_emails)]
    rest = URL_RE.sub(" ", without_emails)
    links += [_strip(m.group(0)) for m in BARE_DOMAIN_RE.finditer(rest)
              if m.group(2).lower() in KNOWN_TLDS or m.group(3)]
    links = _unique(links, key=lambda u: re.sub(r"^https?://", "", u.lower()).rstrip("/"))
    phones = []
    for line in lines:
        cleaned = EMAIL_RE.sub(" ", URL_RE.sub(" ", line))
        for match in PHONE_RE.finditer(cleaned):
            candidate = match.group(0).strip()
            digits = re.sub(r"\D", "", candidate)
            if DATE_RE.match(candidate) or not 8 <= len(digits) <= 15:
                continue
            phones.append(candidate)
    phones = _unique(phones, key=normalize_phone)
    return {"phones": phones, "emails": emails, "links": links}


def guess_name(lines):
    """Tebakan nama kontak: baris pertama yang tampak seperti nama orang/usaha."""
    for line in lines:
        words = line.split()
        if 1 <= len(words) <= 5 and not re.search(r"[\d@/:]", line) and any(w[:1].isupper() for w in words):
            return line.strip()
    return "Kontak baru"


# --- vCard -------------------------------------------------------------------------

def _vcard_escape(text):
    return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def vcard(name, phones=(), emails=(), links=()):
    """Teks vCard 3.0 (baris diakhiri CRLF) yang bisa diimpor ke kontak ponsel atau Outlook."""
    name = " ".join(name.split()) or "Kontak baru"
    parts = name.split(" ")
    family, given = (parts[-1], " ".join(parts[:-1])) if len(parts) > 1 else (name, "")
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"FN:{_vcard_escape(name)}",
             f"N:{_vcard_escape(family)};{_vcard_escape(given)};;;"]
    lines += [f"TEL;TYPE=CELL:{normalize_phone(p)}" for p in phones]
    lines += [f"EMAIL;TYPE=INTERNET:{e}" for e in emails]
    lines += [f"URL:{u if u.lower().startswith('http') else 'https://' + u}" for u in links]
    lines.append("END:VCARD")
    return "\r\n".join(lines) + "\r\n"


def save_vcard(path, *args, **kwargs):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(vcard(*args, **kwargs))
    return path


# --- riwayat -------------------------------------------------------------------------

def parse_tags(text):
    """'kerja, Kopi  kerja' -> ['kerja', 'kopi'] (huruf kecil, tanpa duplikat)."""
    return _unique(tag.strip().lower() for tag in re.split(r"[,\s]+", text or "") if tag.strip())


class History:
    def __init__(self, path=HISTORY, clock=lambda: datetime.now().isoformat(timespec="seconds")):
        self.path = path
        self.clock = clock
        self.entries = self._load()

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as handle:
                data = json.load(handle)
            return [e for e in data if isinstance(e, dict) and "id" in e] if isinstance(data, list) else []
        except FileNotFoundError:
            return []
        except (OSError, ValueError):
            raise ScanError(f"Berkas riwayat {self.path} rusak; tidak ditimpa supaya datanya tidak hilang.") from None

    def _save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        temp = self.path + ".tmp"
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(self.entries, handle, ensure_ascii=False, indent=1)
        os.replace(temp, self.path)

    def add(self, source, lines, found, tags=()):
        entry = {"id": max((e["id"] for e in self.entries), default=0) + 1, "source": source,
                 "scanned_at": self.clock(), "lines": list(lines), "tags": list(tags), **found}
        self.entries.append(entry)
        self._save()
        return entry

    def set_tags(self, entry_id, tags):
        for entry in self.entries:
            if entry["id"] == entry_id:
                entry["tags"] = list(tags)
                self._save()
                return entry
        raise ScanError(f"Riwayat #{entry_id} tidak ada.")

    def search(self, tag=None):
        """Terbaru dulu. Dengan tag: hanya entri yang punya tag itu (tanpa membedakan huruf besar kecil)."""
        wanted = (tag or "").strip().lower()
        rows = [e for e in self.entries if not wanted or wanted in e.get("tags", [])]
        return sorted(rows, key=lambda e: e["id"], reverse=True)


def format_found(found):
    lines = []
    for key, title in (("phones", "Telepon"), ("emails", "Email"), ("links", "Tautan")):
        lines.append(f"{title}:")
        lines += [f"  - {item}" for item in found[key]] or ["  (tidak ada)"]
    return "\n".join(lines)


# --- tampilan Tkinter -----------------------------------------------------------------

class ScannerApp:
    def __init__(self, root, history=None, ocr_func=ocr, ask_save=None, notify=None):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = root
        self.history = history or History()
        self.ocr = ocr_func
        self.ask_save = ask_save or self._ask_save
        self.notify = notify or self._notify
        self.current = None
        self.preview_photo = None

        root.title("Image Scanner")
        bar = ttk.Frame(root, padding=(12, 10))
        bar.pack(fill="x")
        ttk.Button(bar, text="Buka gambar…", command=self.open_image).pack(side="left")
        ttk.Button(bar, text="Tempel (Ctrl+V)", command=self.paste_image).pack(side="left", padx=6)
        self.status = tk.StringVar(value="Buka foto kartu nama, poster, atau tangkapan layar.")
        ttk.Label(bar, textvariable=self.status, foreground="#555").pack(side="left", padx=10)

        body = ttk.Frame(root, padding=(12, 0, 12, 12))
        body.pack(fill="both", expand=True)
        self.preview = ttk.Label(body, text="(belum ada gambar)", anchor="center", width=40)
        self.preview.grid(row=0, column=0, rowspan=2, sticky="n")

        self.cards = ttk.Frame(body, padding=(14, 0))
        self.cards.grid(row=0, column=1, sticky="nsew")
        tag_row = ttk.Frame(body, padding=(14, 8, 14, 0))
        tag_row.grid(row=1, column=1, sticky="we")
        ttk.Label(tag_row, text="Tag:").pack(side="left")
        self.tags = tk.StringVar()
        ttk.Entry(tag_row, textvariable=self.tags, width=24).pack(side="left", padx=4)
        ttk.Button(tag_row, text="Simpan tag", command=self.save_tags).pack(side="left")
        ttk.Button(tag_row, text="Simpan semua sebagai kontak…", command=lambda: self.save_contact()).pack(side="right")

        side = ttk.LabelFrame(body, text="Riwayat", padding=8)
        side.grid(row=0, column=2, rowspan=2, sticky="ns")
        search = ttk.Frame(side)
        search.pack(fill="x")
        ttk.Label(search, text="Cari tag:").pack(side="left")
        self.tag_filter = tk.StringVar()
        ttk.Entry(search, textvariable=self.tag_filter, width=12).pack(side="left", padx=4)
        self.tag_filter.trace_add("write", lambda *_: self.refresh_history())
        self.history_list = tk.Listbox(side, width=34, height=18, activestyle="none")
        self.history_list.pack(fill="both", expand=True, pady=(6, 0))
        self.history_list.bind("<<ListboxSelect>>", self.on_history_select)
        body.columnconfigure(1, weight=1)
        root.bind("<Control-v>", lambda _e: self.paste_image())
        self.history_rows = []
        self.refresh_history()
        self.render_cards(None)

    # --- memindai --------------------------------------------------------------
    def open_image(self):
        from tkinter import filedialog

        path = filedialog.askopenfilename(parent=self.root, title="Pilih gambar", filetypes=[
            ("Gambar", "*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff")])
        if path:
            self.scan(path)

    def paste_image(self):
        from PIL import ImageGrab

        image = ImageGrab.grabclipboard()
        if image is None or isinstance(image, list):
            files = [f for f in image or [] if f.lower().endswith(IMAGE_TYPES)]
            if files:
                return self.scan(files[0])
            self.notify("Clipboard tidak berisi gambar.")
            return None
        path = os.path.join(tempfile.gettempdir(), f"scan-tempel-{datetime.now():%Y%m%d-%H%M%S}.png")
        image.save(path)
        return self.scan(path, source="clipboard")

    def scan(self, path, source=None):
        self.status.set("Memindai…")
        self.root.update_idletasks()
        try:
            lines = self.ocr(path)
        except ScanError as error:
            self.status.set("Gagal memindai.")
            self.notify(str(error))
            return None
        found = extract(lines)
        entry = self.history.add(source or os.path.basename(path), lines, found, parse_tags(self.tags.get()))
        self.show_preview(path)
        self.show_entry(entry)
        self.refresh_history()
        total = sum(len(found[k]) for k in found)
        self.status.set(f"{len(lines)} baris teks, {total} temuan.")
        return entry

    def show_preview(self, path):
        from PIL import Image, ImageTk

        try:
            with Image.open(path) as image:
                image.thumbnail((320, 320))
                self.preview_photo = ImageTk.PhotoImage(image.convert("RGB"), master=self.root)
            self.preview.configure(image=self.preview_photo, text="")
        except OSError:
            self.preview.configure(image="", text="(pratinjau tidak tersedia)")

    # --- kartu hasil -------------------------------------------------------------
    def show_entry(self, entry):
        self.current = entry
        self.tags.set(", ".join(entry.get("tags", [])))
        self.render_cards(entry)

    def render_cards(self, entry):
        ttk = self.ttk
        for child in self.cards.winfo_children():
            child.destroy()
        if entry is None:
            ttk.Label(self.cards, text="Hasil pindaian akan muncul di sini.", foreground="#777").pack(anchor="w")
            return
        ttk.Label(self.cards, text=f"#{entry['id']}  {entry['source']}  ({entry['scanned_at'].replace('T', ' ')})",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
        for key, title in (("phones", "Telepon"), ("emails", "Email"), ("links", "Tautan")):
            card = ttk.LabelFrame(self.cards, text=f"{title} ({len(entry[key])})", padding=8)
            card.pack(fill="x", pady=4)
            if not entry[key]:
                ttk.Label(card, text="Tidak ditemukan.", foreground="#777").pack(anchor="w")
            for item in entry[key]:
                row = ttk.Frame(card)
                row.pack(fill="x", pady=1)
                ttk.Label(row, text=item, font=("Segoe UI", 11)).pack(side="left")
                ttk.Button(row, text="Simpan kontak", command=lambda k=key, v=item: self.save_contact(k, v)
                           ).pack(side="right")
                ttk.Button(row, text="Salin", command=lambda v=item: self.copy(v)).pack(side="right", padx=4)

    def copy(self, value):
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.status.set(f"Disalin: {value}")

    def save_contact(self, key=None, value=None):
        """Simpan satu temuan (atau semuanya) sebagai berkas .vcf."""
        if not self.current:
            self.notify("Pindai gambar dulu.")
            return None
        entry = self.current
        if key is None:
            phones, emails, links = entry["phones"], entry["emails"], entry["links"]
        else:
            phones = [value] if key == "phones" else []
            emails = [value] if key == "emails" else []
            links = [value] if key == "links" else []
        name = guess_name(entry["lines"])
        path = self.ask_save(f"{re.sub(r'[^A-Za-z0-9]+', '-', name).strip('-') or 'kontak'}.vcf")
        if not path:
            return None
        save_vcard(path, name, phones, emails, links)
        self.status.set(f"Kontak '{name}' disimpan ke {os.path.basename(path)}")
        return path

    def _ask_save(self, suggested):
        from tkinter import filedialog

        return filedialog.asksaveasfilename(parent=self.root, title="Simpan kontak", initialfile=suggested,
                                            defaultextension=".vcf", filetypes=[("vCard", "*.vcf")])

    def _notify(self, message):
        from tkinter import messagebox

        messagebox.showwarning("Image Scanner", message, parent=self.root)

    # --- riwayat -------------------------------------------------------------------
    def refresh_history(self):
        self.history_rows = self.history.search(self.tag_filter.get())
        self.history_list.delete(0, "end")
        for entry in self.history_rows:
            count = len(entry["phones"]) + len(entry["emails"]) + len(entry["links"])
            tags = f" [{', '.join(entry['tags'])}]" if entry.get("tags") else ""
            self.history_list.insert("end", f"#{entry['id']} {entry['source'][:18]} · {count} temuan{tags}")

    def on_history_select(self, _event=None):
        selection = self.history_list.curselection()
        if selection:
            self.show_entry(self.history_rows[selection[0]])
            self.preview.configure(image="", text="(gambar dari riwayat tidak disimpan)")

    def save_tags(self):
        if not self.current:
            return
        self.current = self.history.set_tags(self.current["id"], parse_tags(self.tags.get()))
        self.refresh_history()
        self.status.set("Tag disimpan.")


# --- baris perintah ---------------------------------------------------------------------

def main(argv=None, ocr_func=ocr, history_path=HISTORY, gui=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Cari telepon, email, dan tautan di dalam gambar.")
    parser.add_argument("image", nargs="?", help="gambar yang dipindai (kosong: buka jendela)")
    parser.add_argument("--vcf", help="simpan temuan sebagai kontak vCard")
    parser.add_argument("--name", help="nama kontak (bawaan: ditebak dari teks)")
    parser.add_argument("--tag", help="tag untuk riwayat, pisahkan dengan koma; dengan --history: saring")
    parser.add_argument("--history", action="store_true", help="tampilkan riwayat pemindaian")
    parser.add_argument("--no-history", action="store_true", help="jangan catat pemindaian ini di riwayat")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        history = History(history_path)
        if args.history:
            rows = history.search(args.tag)
            if not rows:
                print("Riwayat kosong.")
            for e in rows:
                tags = f" [{', '.join(e['tags'])}]" if e.get("tags") else ""
                print(f"#{e['id']} {e['scanned_at'].replace('T', ' ')} {e['source']}{tags}: "
                      f"{len(e['phones'])} telepon, {len(e['emails'])} email, {len(e['links'])} tautan")
            return 0
        if not args.image:
            (gui or run_gui)()
            return 0
        lines = ocr_func(args.image)
        found = extract(lines)
        print(format_found(found))
        if not args.no_history:
            entry = history.add(os.path.basename(args.image), lines, found, parse_tags(args.tag))
            print(f"\nDicatat di riwayat sebagai #{entry['id']}.")
        if args.vcf:
            name = args.name or guess_name(lines)
            save_vcard(args.vcf, name, found["phones"], found["emails"], found["links"])
            print(f"Kontak '{name}' disimpan ke {args.vcf}")
    except ScanError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


def run_gui():
    import tkinter as tk

    root = tk.Tk()
    ScannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())
