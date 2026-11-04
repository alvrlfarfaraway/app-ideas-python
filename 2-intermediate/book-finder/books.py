"""Book Finder: cari buku berdasarkan judul, penulis, subjek, penerbit, bahasa, atau tahun.

Memakai Open Library Search API (gratis, tanpa kunci). Google Books yang disarankan
spesifikasi sekarang menolak permintaan tanpa kunci API (kuota 0).

Jalankan:
    python books.py "laskar pelangi"                 # pencarian bebas
    python books.py -t "bumi manusia" -a pramoedya   # gabungan kriteria
    python books.py -s astronomy --lang ind -n 5
    python books.py dune --html hasil.html           # halaman HTML berisi sampul dan tautan
    python books.py                                  # mode interaktif
"""

import argparse
import html
import itertools
import json
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request

SEARCH_URL = "https://openlibrary.org/search.json"
WORK_URL = "https://openlibrary.org{key}"
COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-{size}.jpg"
USER_AGENT = "app-ideas-python-book-finder/1.0"
FIELDS = "key,title,author_name,first_publish_year,cover_i,publisher,language,number_of_pages_median,edition_count"

# Kriteria yang diteruskan langsung sebagai parameter Open Library.
CRITERIA = ("q", "title", "author", "subject", "publisher", "language")
LABELS = {"q": "kata kunci", "title": "judul", "author": "penulis", "subject": "subjek",
          "publisher": "penerbit", "language": "bahasa", "year": "tahun"}


def build_url(criteria, limit=10, page=1):
    """URL pencarian dari kamus kriteria. Tahun terbit pertama ditambahkan sebagai filter di q."""
    params = {}
    for name in CRITERIA:
        value = (criteria.get(name) or "").strip()
        if value:
            params[name] = value
    year = criteria.get("year")
    if year:
        start, _, end = str(year).partition("-")
        if not start.strip().isdigit() or (end and not end.strip().isdigit()):
            raise ValueError("Tahun harus angka, misalnya 2005 atau 2000-2010.")
        span = f"[{start.strip()} TO {end.strip()}]" if end else start.strip()
        params["q"] = f"{params.get('q', '')} first_publish_year:{span}".strip()
    if not params:
        raise ValueError("Isi setidaknya satu kriteria pencarian (kata kunci, judul, penulis, ...).")
    if not 1 <= limit <= 100:
        raise ValueError("Jumlah hasil harus antara 1 dan 100.")
    if page < 1:
        raise ValueError("Halaman dimulai dari 1.")
    params.update(fields=FIELDS, limit=limit, page=page)
    return f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"


def fetch_json(url, urlopen=urllib.request.urlopen):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise ValueError(f"Open Library menjawab kode {error.code}. Coba lagi sebentar lagi.") from None
    except (urllib.error.URLError, TimeoutError):
        raise ValueError("Tidak bisa menjangkau openlibrary.org. Periksa koneksi internet.") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("Jawaban Open Library bukan JSON yang valid.") from None


def parse_books(data):
    """Ubah JSON Open Library menjadi (jumlah_total, daftar buku). Kolom yang hilang menjadi None."""
    if not isinstance(data, dict) or not isinstance(data.get("docs"), list):
        raise ValueError("Format data Open Library tidak dikenali.")
    books = []
    for doc in data["docs"]:
        if not isinstance(doc, dict) or not doc.get("title"):
            continue
        cover_id = doc.get("cover_i")
        key = doc.get("key") or ""
        books.append({
            "title": doc["title"],
            "authors": list(doc.get("author_name") or []),
            "year": doc.get("first_publish_year"),
            "publisher": (doc.get("publisher") or [None])[0],
            "languages": list(doc.get("language") or []),
            "pages": doc.get("number_of_pages_median"),
            "editions": doc.get("edition_count"),
            "cover": COVER_URL.format(cover_id=cover_id, size="M") if isinstance(cover_id, int) else None,
            "link": WORK_URL.format(key=key) if key.startswith("/works/") else None,
        })
    total = data.get("numFound", data.get("num_found", len(books)))
    return total, books


def search(criteria, limit=10, page=1, urlopen=urllib.request.urlopen):
    return parse_books(fetch_json(build_url(criteria, limit, page), urlopen))


def describe_book(book):
    authors = ", ".join(book["authors"]) or "penulis tidak diketahui"
    year = book["year"] or "tahun tidak diketahui"
    lines = [f"{book['title']}", f"   {authors} ({year})"]
    extra = []
    if book["publisher"]:
        extra.append(book["publisher"])
    if book["pages"]:
        extra.append(f"{book['pages']} halaman")
    if book["languages"]:
        extra.append("bahasa: " + ", ".join(book["languages"][:3]))
    if extra:
        lines.append("   " + " | ".join(extra))
    lines.append(f"   Sampul: {book['cover'] or '-'}")
    lines.append(f"   Info  : {book['link'] or '-'}")
    return "\n".join(lines)


def format_results(total, books, page=1, limit=10):
    if not books:
        return "Tidak ada buku yang cocok."
    first = (page - 1) * limit + 1
    lines = [f"Menampilkan {first}-{first + len(books) - 1} dari {total} buku.", ""]
    for number, book in enumerate(books, start=first):
        lines.append(f"{number:>3}. {describe_book(book)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _safe_url(url):
    return url if url and url.startswith("https://") else None


def render_html(books, title="Hasil pencarian buku"):
    """Halaman HTML responsif: kartu buku dengan sampul, data, dan tautan ke Open Library."""
    cards = []
    for book in books:
        esc = html.escape
        cover = _safe_url(book["cover"])
        link = _safe_url(book["link"])
        image = (f'<img src="{esc(cover)}" alt="Sampul {esc(book["title"])}" loading="lazy">'
                 if cover else '<div class="nocover">Tanpa sampul</div>')
        name = esc(book["title"])
        if link:
            name = f'<a href="{esc(link)}" target="_blank" rel="noopener noreferrer">{name}</a>'
        meta = esc(", ".join(book["authors"]) or "Penulis tidak diketahui")
        year = esc(str(book["year"])) if book["year"] else "?"
        cards.append(f'<article>{image}<div><h2>{name}</h2><p>{meta}</p><p class="year">{year}</p></div></article>')
    body = "\n".join(cards) or "<p>Tidak ada buku yang cocok.</p>"
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  :root {{ color-scheme: light dark; --bg: #f6f6f3; --card: #fff; --text: #1d1d1b; --muted: #66665f; --line: #deded8; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg: #171716; --card: #222220; --text: #ececea; --muted: #a3a39c; --line: #343431; }} }}
  body {{ margin: 0; font: 16px/1.45 system-ui, sans-serif; background: var(--bg); color: var(--text); }}
  header {{ padding: 24px 20px 8px; max-width: 1100px; margin: auto; }}
  h1 {{ font-size: 1.4rem; margin: 0; }}
  main {{ display: grid; gap: 16px; padding: 16px 20px 40px; max-width: 1100px; margin: auto;
          grid-template-columns: repeat(auto-fill, minmax(min(100%, 230px), 1fr)); }}
  article {{ background: var(--card); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; display: flex; flex-direction: column; }}
  img, .nocover {{ width: 100%; aspect-ratio: 2 / 3; object-fit: cover; background: var(--line); }}
  .nocover {{ display: grid; place-items: center; color: var(--muted); }}
  article div {{ padding: 12px 14px 14px; }}
  h2 {{ font-size: 1rem; margin: 0 0 4px; }}
  a {{ color: inherit; }}
  p {{ margin: 0; color: var(--muted); }}
  .year {{ font-variant-numeric: tabular-nums; }}
</style>
</head>
<body>
<header><h1>{html.escape(title)}</h1></header>
<main>
{body}
</main>
</body>
</html>
"""


class Spinner:
    """Animasi 'memuat' di terminal selama permintaan berjalan. Diam kalau keluaran bukan terminal."""

    def __init__(self, text="Mencari", stream=None, interval=0.1):
        self.text = text
        self.stream = stream if stream is not None else sys.stderr
        self.interval = interval
        self._stop = threading.Event()
        self._thread = None

    def _run(self):
        for frame in itertools.cycle("|/-\\"):
            self.stream.write(f"\r{self.text} {frame}")
            self.stream.flush()
            if self._stop.wait(self.interval):
                break
        self.stream.write("\r" + " " * (len(self.text) + 2) + "\r")
        self.stream.flush()

    def __enter__(self):
        if getattr(self.stream, "isatty", lambda: False)():
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread:
            self._thread.join()
        return False


def build_parser():
    parser = argparse.ArgumentParser(description="Cari buku di Open Library.")
    parser.add_argument("q", nargs="?", help="kata kunci bebas")
    parser.add_argument("-t", "--title", help="judul")
    parser.add_argument("-a", "--author", help="penulis")
    parser.add_argument("-s", "--subject", help="subjek, misalnya history")
    parser.add_argument("-p", "--publisher", help="penerbit")
    parser.add_argument("--lang", dest="language", help="kode bahasa ISO 639-2, misalnya ind atau eng")
    parser.add_argument("-y", "--year", help="tahun terbit pertama, misalnya 2005 atau 2000-2010")
    parser.add_argument("-n", "--limit", type=int, default=10, help="jumlah hasil (1-100, bawaan 10)")
    parser.add_argument("--page", type=int, default=1, help="halaman hasil (bawaan 1)")
    parser.add_argument("--html", metavar="BERKAS", help="tulis juga halaman HTML berisi sampul")
    return parser


def run_search(criteria, limit, page, html_path=None, urlopen=urllib.request.urlopen, spinner_stream=None):
    with Spinner(stream=spinner_stream):
        total, books = search(criteria, limit, page, urlopen)
    print(format_results(total, books, page, limit))
    if html_path:
        label = ", ".join(f"{LABELS[k]} {v}" for k, v in criteria.items() if v)
        with open(html_path, "w", encoding="utf-8") as handle:
            handle.write(render_html(books, f"Buku untuk {label}"))
        print(f"\nHalaman HTML ditulis ke {html_path}")


def main(argv=None, urlopen=urllib.request.urlopen, spinner_stream=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # judul berhuruf non-Latin tidak membuat program berhenti
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    criteria = {name: getattr(args, name) for name in CRITERIA}
    criteria["year"] = args.year
    if any(criteria.values()):
        try:
            run_search(criteria, args.limit, args.page, args.html, urlopen, spinner_stream)
        except (ValueError, OSError) as error:
            print(f"Error: {error}")
            return 1
        return 0
    print("Book Finder: ketik kata kunci. Kosongkan untuk keluar.")
    print("Kriteria khusus bisa ditulis seperti: title:dune author:herbert")
    while True:
        text = input("Cari: ").strip()
        if not text:
            return 0
        try:
            run_search(parse_query(text), args.limit, 1, None, urlopen, spinner_stream)
        except ValueError as error:
            print(f"Error: {error}")
        print()


def parse_query(text):
    """'dune author:herbert year:1965' -> {'q': 'dune', 'author': 'herbert', 'year': '1965'}."""
    criteria = {}
    free = []
    current = None
    for word in text.split():
        name, sep, value = word.partition(":")
        name = {"lang": "language"}.get(name.lower(), name.lower())
        if sep and (name in CRITERIA or name == "year") and name != "q":
            current = name
            criteria[name] = value
        elif current:
            criteria[current] = f"{criteria[current]} {word}".strip()
        else:
            free.append(word)
    if free:
        criteria["q"] = " ".join(free)
    return criteria


if __name__ == "__main__":
    raise SystemExit(main())
