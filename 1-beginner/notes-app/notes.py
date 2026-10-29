"""Notes App: buat, ubah, hapus, dan simpan catatan (dengan Markdown -> HTML).

Catatan tersimpan di berkas JSON, jadi tetap ada saat program dijalankan lagi.

Jalankan:
    python notes.py add "Belanja" -b "- telur\n- susu"
    python notes.py list
    python notes.py show 1
    python notes.py show 1 --html -o belanja.html     # Markdown dikonversi ke HTML
    python notes.py edit 1 -t "Belanja Minggu Ini" -b "**Penting**: roti"
    python notes.py delete 1
"""

import argparse
import html
import json
import os
import re
import sys
import tempfile
from datetime import datetime

DEFAULT_FILE = os.path.join(os.path.expanduser("~"), ".app-ideas-python", "notes.json")
DATE_FORMAT = "%Y-%m-%d %H:%M"


# --- Markdown -> HTML --------------------------------------------------------

SAFE_LINK = re.compile(r"(https?://|mailto:)", re.IGNORECASE)


def inline(text):
    """Format di dalam baris: `kode`, [tautan](url), **tebal**, *miring*. Semua HTML mentah di-escape lebih dulu."""
    text = html.escape(text, quote=True)
    codes = []

    def stash(match):
        codes.append(match.group(1))
        return f"\x00{len(codes) - 1}\x00"

    def link(match):
        label, url = match.groups()
        if SAFE_LINK.match(url) or ":" not in url:  # tolak javascript:, data:, dst.
            return f'<a href="{url}">{label}</a>'
        return label

    text = re.sub(r"`([^`]+)`", stash, text)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?![\s*])(.+?)(?<![\s*])\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{codes[int(m.group(1))]}</code>", text)


def markdown_to_html(markdown):
    """Konversi subset Markdown: judul, paragraf, daftar, kutipan, blok kode, garis, dan format inline."""
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out, paragraph = [], []

    def flush():
        if paragraph:
            out.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            flush()
            code, i = [], i + 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
        elif re.match(r"^#{1,6}\s+\S", line):
            flush()
            level = len(line) - len(line.lstrip("#"))
            out.append(f"<h{level}>{inline(line[level:].strip().rstrip('#').strip())}</h{level}>")
        elif re.fullmatch(r"\s*([-*_])(\s*\1){2,}\s*", line):
            flush()
            out.append("<hr>")
        elif re.match(r"^\s*[-*+]\s+\S", line) or re.match(r"^\s*\d+[.)]\s+\S", line):
            flush()
            ordered = bool(re.match(r"^\s*\d+[.)]\s+", line))
            pattern = r"^\s*\d+[.)]\s+(.*)" if ordered else r"^\s*[-*+]\s+(.*)"
            items = []
            while i < len(lines) and re.match(pattern, lines[i]):
                items.append(re.match(pattern, lines[i]).group(1))
                i += 1
            i -= 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(item)}</li>" for item in items) + f"</{tag}>")
        elif line.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i][1:].strip())
                i += 1
            i -= 1
            out.append("<blockquote><p>" + inline(" ".join(quote)) + "</p></blockquote>")
        elif not line.strip():
            flush()
        else:
            paragraph.append(line.strip())
        i += 1
    flush()
    return "\n".join(out)


def note_page(note):
    """Halaman HTML utuh untuk satu catatan."""
    return (f'<!DOCTYPE html>\n<html lang="id">\n<head>\n<meta charset="utf-8">\n'
            f"<title>{html.escape(note['title'])}</title>\n</head>\n<body>\n"
            f"<h1>{html.escape(note['title'])}</h1>\n<p><small>Dibuat {note['created']}"
            f"{' · diubah ' + note['updated'] if note['updated'] != note['created'] else ''}</small></p>\n"
            f"{markdown_to_html(note['body'])}\n</body>\n</html>\n")


# --- Penyimpanan -------------------------------------------------------------

class NoteStore:
    def __init__(self, path, now=datetime.now):
        self.path = path
        self._now = now

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            return {"next_id": 1, "notes": []}
        except json.JSONDecodeError:
            raise ValueError(f"Berkas catatan '{self.path}' rusak dan tidak dibaca agar tidak tertimpa.") from None
        if not isinstance(data, dict) or "notes" not in data or "next_id" not in data:
            raise ValueError(f"Format berkas catatan '{self.path}' tidak dikenali.")
        return data

    def _save(self, data):
        folder = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(folder, exist_ok=True)
        # Tulis ke berkas sementara lalu ganti, supaya crash di tengah tidak merusak catatan lama.
        handle, temp = tempfile.mkstemp(dir=folder, suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
            os.replace(temp, self.path)
        except BaseException:
            if os.path.exists(temp):
                os.remove(temp)
            raise

    @staticmethod
    def _clean_title(title):
        title = title.strip()
        if not title:
            raise ValueError("Judul catatan tidak boleh kosong.")
        return title

    def all(self):
        return self._load()["notes"]

    def get(self, note_id):
        for note in self._load()["notes"]:
            if note["id"] == note_id:
                return note
        raise ValueError(f"Catatan nomor {note_id} tidak ditemukan.")

    def add(self, title, body=""):
        data = self._load()
        stamp = self._now().strftime(DATE_FORMAT)
        note = {"id": data["next_id"], "title": self._clean_title(title), "body": body,
                "created": stamp, "updated": stamp}
        data["next_id"] += 1
        data["notes"].append(note)
        self._save(data)
        return note

    def edit(self, note_id, title=None, body=None):
        data = self._load()
        for note in data["notes"]:
            if note["id"] == note_id:
                if title is not None:
                    note["title"] = self._clean_title(title)
                if body is not None:
                    note["body"] = body
                note["updated"] = self._now().strftime(DATE_FORMAT)
                self._save(data)
                return note
        raise ValueError(f"Catatan nomor {note_id} tidak ditemukan.")

    def delete(self, note_id):
        data = self._load()
        kept = [n for n in data["notes"] if n["id"] != note_id]
        if len(kept) == len(data["notes"]):
            raise ValueError(f"Catatan nomor {note_id} tidak ditemukan.")
        data["notes"] = kept
        self._save(data)


# --- CLI ---------------------------------------------------------------------

def read_body(args):
    """Isi catatan dari -b, -f, atau (kalau tidak ada) dari ketikan/stdin. None = tidak diberikan (untuk edit)."""
    if args.body is not None:
        return args.body.replace("\\n", "\n")
    if args.file:
        try:
            with open(args.file, encoding="utf-8") as file:
                return file.read()
        except OSError as error:
            raise ValueError(f"Berkas '{args.file}' tidak bisa dibaca: {error.strerror}.") from None
    return None


def prompt_body():
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Ketik isi catatan. Akhiri dengan baris yang hanya berisi satu titik (.)")
    lines = []
    while (line := input()) != ".":
        lines.append(line)
    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(description="Catatan sederhana.")
    parser.add_argument("-f", "--store", default=DEFAULT_FILE, help="berkas penyimpanan catatan")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add", help="buat catatan")
    add.add_argument("title")
    edit = sub.add_parser("edit", help="ubah catatan")
    edit.add_argument("id", type=int)
    edit.add_argument("-t", "--title")
    for p in (add, edit):
        p.add_argument("-b", "--body", help="isi (Markdown); \\n menjadi baris baru")
        p.add_argument("--file", help="ambil isi dari berkas")
    sub.add_parser("list", help="daftar catatan")
    show = sub.add_parser("show", help="tampilkan catatan")
    show.add_argument("id", type=int)
    show.add_argument("--html", action="store_true", help="tampilkan sebagai halaman HTML (Markdown dikonversi)")
    show.add_argument("-o", "--output", help="simpan hasil ke berkas")
    sub.add_parser("delete", help="hapus catatan").add_argument("id", type=int)
    return parser


def main(argv=None, now=datetime.now):
    args = build_parser().parse_args(argv)
    store = NoteStore(args.store, now)
    try:
        if args.command == "add":
            body = read_body(args)
            note = store.add(args.title, prompt_body() if body is None else body)
            print(f"Tersimpan sebagai catatan #{note['id']}.")
        elif args.command == "edit":
            if args.title is None and args.body is None and not args.file:
                raise ValueError("Tidak ada yang diubah: beri -t (judul), -b (isi), atau --file.")
            store.edit(args.id, args.title, read_body(args))
            print(f"Catatan #{args.id} diperbarui.")
        elif args.command == "list":
            notes = store.all()
            if not notes:
                print("Belum ada catatan.")
            for note in notes:
                print(f"#{note['id']:<3} {note['created']}  {note['title']}")
        elif args.command == "show":
            note = store.get(args.id)
            if args.html:
                text = note_page(note)
            else:
                text = f"#{note['id']} {note['title']}\nDibuat: {note['created']}  Diubah: {note['updated']}\n\n{note['body']}\n"
            if args.output:
                with open(args.output, "w", encoding="utf-8") as file:
                    file.write(text)
                print(f"Tersimpan: {args.output}")
            else:
                sys.stdout.reconfigure(errors="replace")
                print(text, end="")
        elif args.command == "delete":
            store.delete(args.id)
            print(f"Catatan #{args.id} dihapus.")
    except (ValueError, OSError) as error:
        print(f"Error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
