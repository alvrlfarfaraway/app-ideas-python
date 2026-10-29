"""Word Frequency: hitung kemunculan tiap kata dalam teks, urut dari yang paling sering.

Jalankan:
    python wordfreq.py catatan.txt              # dari berkas
    python wordfreq.py - < catatan.txt          # dari stdin
    python wordfreq.py --url https://example.com --top 10
    python wordfreq.py catatan.txt --stopwords id   # buang kata umum bahasa Indonesia (id) atau Inggris (en)
"""

import argparse
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser

MAX_CHARS = 2048  # batas isian teks pada spesifikasi
MAX_PAGE_BYTES = 2_000_000

# Kata = huruf (termasuk beraksen), boleh berisi apostrof atau tanda hubung di tengah: don't, e-mail, anak-anak.
WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*")

STOPWORDS = {
    "id": set("""yang dan di ke dari ini itu untuk dengan pada adalah dalam akan atau juga tidak sudah karena
        bisa oleh agar saya kita kami mereka ada jika lebih sebagai hanya saat setelah sebuah seperti
        tetapi tapi bila dapat para serta lagi telah masih belum dia ia nya""".split()),
    "en": set("""the a an and or of to in on at for with by is are was were be been it its this that these those
        as from but not no so if then than too very can will just i you he she we they my your his her our""".split()),
}


def tokenize(text):
    """Daftar kata huruf kecil, urut kemunculan. Angka dan tanda baca dilewati."""
    return [match.group(0).lower() for match in WORD.finditer(text)]


def count_words(text, max_chars=MAX_CHARS, stopwords=None):
    """Daftar (kata, jumlah) urut turun menurut jumlah, lalu abjad untuk jumlah yang sama.

    ValueError kalau teks kosong, melebihi `max_chars` (None = tanpa batas), atau tidak berisi kata sama sekali.
    """
    if not text or not text.strip():
        raise ValueError("Teks masih kosong. Ketik atau tempel teks dulu.")
    if max_chars is not None and len(text) > max_chars:
        raise ValueError(f"Teks terlalu panjang: {len(text)} karakter (maksimal {max_chars}).")
    words = tokenize(text)
    if stopwords:
        words = [w for w in words if w not in stopwords]
    if not words:
        raise ValueError("Tidak ada kata yang bisa dihitung di teks itu.")
    counts = {}
    for word in words:
        counts[word] = counts.get(word, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def format_table(frequencies, top=None, bars=True):
    """Tabel teks: peringkat, kata, jumlah, dan batang proporsional."""
    rows = frequencies[:top] if top else frequencies
    if not rows:
        return "(kosong)"
    width = max(len(word) for word, _ in rows)
    biggest = rows[0][1]
    lines = [f"{'#':>3}  {'Kata':<{width}}  {'Jumlah':>6}"]
    for rank, (word, count) in enumerate(rows, start=1):
        bar = "  " + "█" * max(1, round(24 * count / biggest)) if bars else ""
        lines.append(f"{rank:>3}  {word:<{width}}  {count:>6}{bar}")
    total = sum(count for _, count in frequencies)
    lines.append(f"\n{total} kata, {len(frequencies)} kata unik.")
    return "\n".join(lines)


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "template", "head", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth:
            self.parts.append(data)


def html_to_text(html_text):
    """Teks yang tampak di halaman: tanpa script, style, dan kepala dokumen; entitas HTML sudah didekode."""
    parser = _TextExtractor()
    parser.feed(html_text)
    parser.close()
    return " ".join(" ".join(parser.parts).split())


def fetch_text(url, urlopen=urllib.request.urlopen):
    """Unduh halaman web dan ambil teksnya. ValueError dengan pesan ramah kalau gagal."""
    if not re.match(r"https?://", url, re.IGNORECASE):
        raise ValueError("URL harus diawali http:// atau https://.")
    try:
        with urlopen(url, timeout=15) as response:
            content_type = response.headers.get("Content-Type", "") if hasattr(response, "headers") else ""
            if content_type and not re.match(r"text/|application/(xhtml|xml|json)", content_type, re.IGNORECASE):
                raise ValueError(f"Jenis konten '{content_type.split(';')[0]}' bukan teks atau halaman web.")
            raw = response.read(MAX_PAGE_BYTES + 1)
            charset = response.headers.get_content_charset() if hasattr(response, "headers") else None
    except urllib.error.HTTPError as error:
        raise ValueError(f"Server menjawab kode {error.code} untuk {url}.") from None
    except (urllib.error.URLError, TimeoutError):
        raise ValueError(f"Tidak bisa menjangkau {url}. Periksa alamat dan koneksi internet.") from None
    if len(raw) > MAX_PAGE_BYTES:
        raise ValueError("Halaman terlalu besar (lebih dari 2 MB).")
    html_text = raw.decode(charset or "utf-8", errors="replace")
    return html_to_text(html_text) if "<" in html_text else html_text


def main(argv=None):
    parser = argparse.ArgumentParser(description="Frekuensi kata.")
    parser.add_argument("source", nargs="?", help="berkas teks, atau - untuk stdin")
    parser.add_argument("--url", help="analisis isi halaman web (menggantikan berkas)")
    parser.add_argument("--top", type=int, help="tampilkan hanya N kata teratas")
    parser.add_argument("--stopwords", choices=sorted(STOPWORDS), help="buang kata umum: id atau en")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        if args.url:
            text, limit = fetch_text(args.url), None
        elif args.source == "-":
            text, limit = sys.stdin.read(), MAX_CHARS
        elif args.source:
            try:
                with open(args.source, encoding="utf-8-sig") as file:
                    text, limit = file.read(), MAX_CHARS
            except OSError as error:
                raise ValueError(f"Berkas '{args.source}' tidak bisa dibaca: {error.strerror}.") from None
        else:
            parser.error("beri berkas, - (stdin), atau --url")
        if args.top is not None and args.top < 1:
            raise ValueError("--top harus minimal 1.")
        result = count_words(text, limit, STOPWORDS.get(args.stopwords))
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    print(format_table(result, args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
