"""Podcast Directory: tabel episode dari podcast favorit, dengan ikon yang bisa diklik.

Podcast dicari lewat iTunes Search API (gratis, tanpa kunci). Episode diambil
dari feed RSS masing-masing podcast. Spesifikasi menyebut Podbean, tetapi API
Podbean butuh kredensial OAuth. RSS adalah sumber yang sama yang dipakai semua
aplikasi podcast, termasuk podcast yang di-hosting di Podbean.

Jalankan:
    python podcasts.py                        # jendela Tkinter
    python podcasts.py search "python"        # cari podcast
    python podcasts.py add 1501905538         # tambah favorit (id iTunes dari hasil cari)
    python podcasts.py list                   # daftar favorit
    python podcasts.py episodes -n 15         # episode terbaru dari semua favorit
    python podcasts.py remove 1501905538
"""

import argparse
import io
import json
import os
import queue
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

USER_AGENT = "app-ideas-python-podcast-directory/1.0"
SEARCH_URL = "https://itunes.apple.com/search"
LOOKUP_URL = "https://itunes.apple.com/lookup"
FAVORITES = os.path.join(os.path.expanduser("~"), ".app-ideas-python", "podcasts.json")
ITUNES_NS = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
MAX_FEED_BYTES = 30_000_000


class PodcastError(Exception):
    """Kesalahan yang ditampilkan ke pengguna sebagai pesan biasa."""


# --- jaringan -----------------------------------------------------------------

def fetch(url, urlopen=urllib.request.urlopen, limit=MAX_FEED_BYTES):
    if not url.lower().startswith(("https://", "http://")):
        raise PodcastError(f"Alamat feed tidak didukung: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=20) as response:
            data = response.read(limit + 1)
    except urllib.error.HTTPError as error:
        raise PodcastError(f"Server menjawab kode {error.code} untuk {urllib.parse.urlsplit(url).netloc}.") from None
    except (urllib.error.URLError, TimeoutError):
        raise PodcastError("Tidak bisa terhubung. Periksa koneksi internet.") from None
    if len(data) > limit:
        raise PodcastError("Feed terlalu besar.")
    return data


def _podcast_from_itunes(item):
    return {"id": item["collectionId"], "name": item.get("collectionName") or "Tanpa nama",
            "author": item.get("artistName") or "", "feed": item.get("feedUrl") or "",
            "artwork": item.get("artworkUrl100") or item.get("artworkUrl60") or ""}


def search(term, urlopen=urllib.request.urlopen, limit=10):
    term = term.strip()
    if not term:
        raise PodcastError("Tulis nama podcast yang dicari.")
    query = urllib.parse.urlencode({"media": "podcast", "entity": "podcast", "term": term, "limit": limit})
    try:
        data = json.loads(fetch(f"{SEARCH_URL}?{query}", urlopen))
        return [_podcast_from_itunes(item) for item in data["results"] if item.get("feedUrl")]
    except (ValueError, KeyError, TypeError):
        raise PodcastError("Format hasil pencarian iTunes tidak dikenali.") from None


def lookup(podcast_id, urlopen=urllib.request.urlopen):
    query = urllib.parse.urlencode({"id": podcast_id, "entity": "podcast"})
    try:
        results = json.loads(fetch(f"{LOOKUP_URL}?{query}", urlopen))["results"]
    except (ValueError, KeyError, TypeError):
        raise PodcastError("Format data iTunes tidak dikenali.") from None
    found = [_podcast_from_itunes(r) for r in results if r.get("collectionId") == int(podcast_id) and r.get("feedUrl")]
    if not found:
        raise PodcastError(f"Podcast dengan id {podcast_id} tidak ditemukan (atau tidak punya feed RSS).")
    return found[0]


# --- RSS ----------------------------------------------------------------------------

def _text(element, path):
    found = element.find(path)
    return (found.text or "").strip() if found is not None and found.text else ""


def parse_date(text):
    try:
        moment = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def parse_feed(data, podcast_name=None):
    """Feed RSS (bytes) -> (info podcast, daftar episode terbaru dulu).

    ElementTree tidak memuat entitas eksternal, dan expat bawaan Python 3.12 membatasi
    ledakan entitas ("billion laughs"), jadi feed dari internet aman diurai.
    """
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise PodcastError(f"Feed RSS tidak valid ({error}).") from None
    channel = root.find("channel")
    if channel is None:
        raise PodcastError("Berkas itu bukan feed RSS podcast.")
    name = podcast_name or _text(channel, "title") or "Tanpa nama"
    image = channel.find(f"{ITUNES_NS}image")
    artwork = image.get("href", "") if image is not None else _text(channel, "image/url")
    episodes = []
    for item in channel.findall("item"):
        title = _text(item, "title")
        if not title:
            continue
        link = _text(item, "link")
        guid = _text(item, "guid")
        if not link.startswith(("http://", "https://")):
            link = guid if guid.startswith(("http://", "https://")) else ""
        item_image = item.find(f"{ITUNES_NS}image")
        episodes.append({
            "podcast": name,
            "title": title,
            "date": parse_date(_text(item, "pubDate")),
            "link": link,
            "image": item_image.get("href", "") if item_image is not None else artwork,
            "duration": _text(item, f"{ITUNES_NS}duration"),
        })
    oldest = datetime.min.replace(tzinfo=timezone.utc)
    episodes.sort(key=lambda e: e["date"] or oldest, reverse=True)
    return {"name": name, "artwork": artwork, "link": _text(channel, "link")}, episodes


def format_date(moment):
    months = "Jan Feb Mar Apr Mei Jun Jul Agu Sep Okt Nov Des".split()
    return f"{moment.day} {months[moment.month - 1]} {moment.year}" if moment else "-"


def merge(episodes_by_podcast, selected=None):
    """Gabungkan episode dari podcast yang dipilih, terbaru dulu."""
    oldest = datetime.min.replace(tzinfo=timezone.utc)
    rows = [e for name, episodes in episodes_by_podcast.items() if selected is None or name in selected
            for e in episodes]
    return sorted(rows, key=lambda e: e["date"] or oldest, reverse=True)


# --- favorit -----------------------------------------------------------------------

class Favorites:
    def __init__(self, path=FAVORITES):
        self.path = path
        try:
            with open(path, encoding="utf-8") as handle:
                data = json.load(handle)
            self.items = [p for p in data if isinstance(p, dict) and "id" in p and "feed" in p]
        except FileNotFoundError:
            self.items = []
        except (OSError, ValueError):
            raise PodcastError(f"Berkas favorit {path} rusak; tidak ditimpa supaya datanya tidak hilang.") from None

    def _save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        temp = self.path + ".tmp"
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(self.items, handle, ensure_ascii=False, indent=1)
        os.replace(temp, self.path)

    def add(self, podcast):
        if any(p["id"] == podcast["id"] for p in self.items):
            raise PodcastError(f"'{podcast['name']}' sudah ada di favorit.")
        self.items.append(podcast)
        self._save()

    def remove(self, podcast_id):
        before = len(self.items)
        self.items = [p for p in self.items if p["id"] != podcast_id]
        if len(self.items) == before:
            raise PodcastError(f"Podcast {podcast_id} tidak ada di favorit.")
        self._save()


def load_all(favorites, urlopen=urllib.request.urlopen):
    """{nama: episode} untuk semua favorit, dan daftar pesan error untuk feed yang gagal."""
    episodes, errors = {}, []
    for podcast in favorites:
        try:
            _, items = parse_feed(fetch(podcast["feed"], urlopen), podcast["name"])
            episodes[podcast["name"]] = items
        except PodcastError as error:
            errors.append(f"{podcast['name']}: {error}")
    return episodes, errors


# --- tampilan Tkinter -------------------------------------------------------------------

class PodcastApp:
    def __init__(self, root, favorites, urlopen=urllib.request.urlopen, open_url=webbrowser.open, notify=None):
        import tkinter as tk
        from tkinter import ttk

        self.tk, self.ttk = tk, ttk
        self.root = root
        self.favorites = favorites
        self.urlopen = urlopen
        self.open_url = open_url
        self.notify = notify or self._notify
        self.episodes = {}
        self.icons = {}
        self.rows = {}
        self.show = {}
        self.jobs = queue.Queue()

        root.title("Podcast Directory")
        top = ttk.Frame(root, padding=(12, 10))
        top.pack(fill="x")
        self.term = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.term, width=30)
        entry.pack(side="left")
        entry.bind("<Return>", lambda _e: self.search())
        ttk.Button(top, text="Cari podcast", command=self.search).pack(side="left", padx=6)
        ttk.Button(top, text="Muat ulang", command=self.reload).pack(side="right")
        self.status = tk.StringVar()
        ttk.Label(top, textvariable=self.status, foreground="#555").pack(side="left", padx=8)

        self.summary = ttk.LabelFrame(root, text="Ringkasan", padding=8)
        self.summary.pack(fill="x", padx=12)

        style = ttk.Style(root)
        style.configure("Podcast.Treeview", rowheight=40)
        table = ttk.Frame(root, padding=12)
        table.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table, columns=("title", "podcast", "date"), style="Podcast.Treeview", height=12)
        self.tree.heading("#0", text="")
        self.tree.column("#0", width=56, stretch=False)
        for column, label, width in (("title", "Judul episode", 460), ("podcast", "Podcast", 190),
                                     ("date", "Tanggal siar", 110)):
            self.tree.heading(column, text=label)
            self.tree.column(column, width=width, anchor="w")
        self.tree.tag_configure("odd", background="#f3f5f8")
        self.tree.tag_configure("even", background="#ffffff")
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<Button-1>", self.on_click)
        self.tree.bind("<Double-1>", lambda e: self.open_row(self.tree.identify_row(e.y)))
        self.root.after(100, self.poll)
        self.reload()

    # --- latar belakang --------------------------------------------------------
    def run_background(self, work, done):
        def runner():
            try:
                result = work()
            except Exception as error:  # dikirim ke thread Tk
                result = error
            self.jobs.put((done, result))
        threading.Thread(target=runner, daemon=True).start()

    def poll(self):
        while not self.jobs.empty():
            done, result = self.jobs.get()
            done(result)
        self.root.after(100, self.poll)

    # --- data --------------------------------------------------------------------
    def reload(self):
        if not self.favorites.items:
            self.status.set("Belum ada favorit. Cari podcast lalu tambahkan.")
            self.episodes = {}
            self.render()
            return
        self.status.set("Memuat feed…")
        self.run_background(lambda: (load_all(self.favorites.items, self.urlopen), self.load_icons()),
                            self.on_loaded)

    def load_icons(self):
        from PIL import Image

        icons = {}
        for podcast in self.favorites.items:
            try:
                with Image.open(io.BytesIO(fetch(podcast["artwork"], self.urlopen, 2_000_000))) as image:
                    icons[podcast["name"]] = image.convert("RGB").resize((36, 36))
            except (PodcastError, OSError, ValueError):
                continue
        return icons

    def on_loaded(self, result):
        from PIL import ImageTk

        if isinstance(result, Exception):
            self.status.set(f"Gagal: {result}")
            return
        (episodes, errors), images = result
        self.episodes = episodes
        self.icons = {name: ImageTk.PhotoImage(image, master=self.root) for name, image in images.items()}
        self.render()
        total = sum(len(v) for v in episodes.values())
        self.status.set(f"{total} episode dari {len(episodes)} podcast" + (f" | {len(errors)} feed gagal" if errors else ""))
        if errors:
            self.notify("\n".join(errors))

    def render(self):
        ttk = self.ttk
        for child in self.summary.winfo_children():
            child.destroy()
        for podcast in self.favorites.items:
            name = podcast["name"]
            var = self.show.setdefault(name, self.tk.BooleanVar(value=True))
            row = ttk.Frame(self.summary)
            row.pack(fill="x")
            count = len(self.episodes.get(name, []))
            ttk.Checkbutton(row, text=f"{name}: {count} episode", variable=var, command=self.fill_table).pack(side="left")
            ttk.Button(row, text="Hapus", width=7, command=lambda p=podcast: self.remove(p)).pack(side="right")
        if not self.favorites.items:
            ttk.Label(self.summary, text="Belum ada podcast favorit.", foreground="#777").pack(anchor="w")
        self.fill_table()

    def fill_table(self):
        self.tree.delete(*self.tree.get_children())
        self.rows = {}
        selected = {name for name, var in self.show.items() if var.get()}
        for index, episode in enumerate(merge(self.episodes, selected)):
            icon = self.icons.get(episode["podcast"], "")
            item = self.tree.insert("", "end", image=icon, values=(episode["title"], episode["podcast"],
                                                                   format_date(episode["date"])),
                                    tags=("odd" if index % 2 else "even",))
            self.rows[item] = episode

    # --- interaksi --------------------------------------------------------------
    def on_click(self, event):
        if self.tree.identify_column(event.x) == "#0":  # klik ikon episode
            self.open_row(self.tree.identify_row(event.y))

    def open_row(self, item):
        episode = self.rows.get(item)
        if episode and episode["link"]:
            self.open_url(episode["link"])
            self.status.set(f"Membuka: {episode['title'][:60]}")
        elif episode:
            self.status.set("Episode ini tidak punya halaman web.")

    def search(self):
        term = self.term.get()
        self.status.set("Mencari…")
        self.run_background(lambda: search(term, self.urlopen), self.on_search)

    def on_search(self, result):
        if isinstance(result, Exception):
            self.status.set(str(result))
            return
        self.status.set(f"{len(result)} podcast ditemukan.")
        self.choose_dialog(result)

    def choose_dialog(self, results):
        tk, ttk = self.tk, self.ttk
        dialog = tk.Toplevel(self.root)
        dialog.title("Tambah podcast")
        dialog.transient(self.root)
        listbox = tk.Listbox(dialog, width=70, height=min(10, max(3, len(results))))
        listbox.pack(padx=12, pady=12)
        for podcast in results:
            listbox.insert("end", f"{podcast['name']}  ({podcast['author']})")

        def add():
            if listbox.curselection():
                self.add(results[listbox.curselection()[0]])
            dialog.destroy()
        ttk.Button(dialog, text="Tambah ke favorit", command=add).pack(pady=(0, 12))
        listbox.bind("<Double-1>", lambda _e: add())
        self.dialog = dialog
        return dialog

    def add(self, podcast):
        try:
            self.favorites.add(podcast)
        except PodcastError as error:
            self.notify(str(error))
            return
        self.reload()

    def remove(self, podcast):
        self.favorites.remove(podcast["id"])
        self.episodes.pop(podcast["name"], None)
        self.show.pop(podcast["name"], None)
        self.render()

    def _notify(self, message):
        from tkinter import messagebox

        messagebox.showwarning("Podcast Directory", message, parent=self.root)


# --- baris perintah ------------------------------------------------------------------------

def main(argv=None, urlopen=urllib.request.urlopen, favorites_path=FAVORITES, gui=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="podcasts", description="Direktori podcast favorit.")
    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser("search", help="cari podcast di iTunes")
    p.add_argument("term")
    p = sub.add_parser("add", help="tambah favorit dengan id iTunes")
    p.add_argument("id", type=int)
    p = sub.add_parser("remove", help="hapus favorit")
    p.add_argument("id", type=int)
    sub.add_parser("list", help="daftar favorit")
    p = sub.add_parser("episodes", help="episode terbaru dari semua favorit")
    p.add_argument("-n", "--limit", type=int, default=20)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        favorites = Favorites(favorites_path)
        if args.command is None:
            (gui or run_gui)(favorites)
        elif args.command == "search":
            for podcast in search(args.term, urlopen):
                print(f"{podcast['id']:>11}  {podcast['name']}  ({podcast['author']})")
        elif args.command == "add":
            podcast = lookup(args.id, urlopen)
            favorites.add(podcast)
            print(f"Ditambahkan: {podcast['name']}")
        elif args.command == "remove":
            favorites.remove(args.id)
            print("Dihapus dari favorit.")
        elif args.command == "list":
            if not favorites.items:
                print("Belum ada favorit. Cari dulu: python podcasts.py search \"kata kunci\"")
            for podcast in favorites.items:
                print(f"{podcast['id']:>11}  {podcast['name']}  ({podcast['author']})")
        elif args.command == "episodes":
            episodes, errors = load_all(favorites.items, urlopen)
            for name, items in episodes.items():
                print(f"{name}: {len(items)} episode")
            print()
            for episode in merge(episodes)[:args.limit]:
                print(f"{format_date(episode['date']):>12}  {episode['podcast'][:24]:<24}  {episode['title']}")
            for message in errors:
                print(f"Peringatan: {message}", file=sys.stderr)
    except PodcastError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


def run_gui(favorites):
    import tkinter as tk

    root = tk.Tk()
    PodcastApp(root, favorites)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())
