import contextlib
import io
import json
import os
import tempfile
import time
import unittest
import unittest.mock
import urllib.error
import urllib.parse

from books import (
    Spinner,
    build_url,
    describe_book,
    fetch_json,
    format_results,
    main,
    parse_books,
    parse_query,
    render_html,
    search,
)

SAMPLE = {
    "numFound": 2,
    "docs": [
        {"key": "/works/OL15302003W", "title": "Laskar Pelangi", "author_name": ["Andrea Hirata"],
         "first_publish_year": 2005, "cover_i": 7079796, "publisher": ["Bentang", "Mizan"],
         "language": ["ind"], "number_of_pages_median": 534, "edition_count": 1},
        {"key": "/works/OL1W", "title": "Tanpa Data"},
        {"title": ""},  # tanpa judul: dilewati
    ],
}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fake_urlopen(payload, seen=None):
    def opener(request, timeout=None):
        if seen is not None:
            seen.append(request)
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        return FakeResponse(raw)
    return opener


def raising(error):
    def opener(request, timeout=None):
        raise error
    return opener


def query_of(url):
    return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))


class BuildUrlTest(unittest.TestCase):
    def test_gabungan_kriteria(self):
        q = query_of(build_url({"title": "bumi manusia", "author": "pramoedya", "language": "ind"}, limit=5, page=2))
        self.assertEqual(q["title"], "bumi manusia")
        self.assertEqual(q["author"], "pramoedya")
        self.assertEqual(q["language"], "ind")
        self.assertEqual(q["limit"], "5")
        self.assertEqual(q["page"], "2")
        self.assertIn("cover_i", q["fields"])
        self.assertNotIn("q", q)

    def test_tahun_dan_rentang(self):
        self.assertEqual(query_of(build_url({"q": "dune", "year": "1965"}))["q"], "dune first_publish_year:1965")
        self.assertEqual(query_of(build_url({"author": "hirata", "year": "2005-2008"}))["q"],
                         "first_publish_year:[2005 TO 2008]")

    def test_kriteria_kosong_diabaikan(self):
        q = query_of(build_url({"q": "  ", "title": "dune", "author": None}))
        self.assertEqual(set(q) - {"fields", "limit", "page"}, {"title"})

    def test_input_salah(self):
        for criteria, kwargs in (({}, {}), ({"q": " "}, {}), ({"q": "x", "year": "dua ribu"}, {}),
                                 ({"q": "x", "year": "2000-x"}, {}), ({"q": "x"}, {"limit": 0}),
                                 ({"q": "x"}, {"limit": 101}), ({"q": "x"}, {"page": 0})):
            with self.assertRaises(ValueError, msg=(criteria, kwargs)):
                build_url(criteria, **kwargs)


class FetchTest(unittest.TestCase):
    def test_mengirim_user_agent(self):
        seen = []
        fetch_json("https://example.test", fake_urlopen({"ok": 1}, seen))
        self.assertIn("app-ideas-python", seen[0].get_header("User-agent"))

    def test_kesalahan_jaringan_jadi_pesan_ramah(self):
        http = urllib.error.HTTPError("u", 503, "x", {}, None)
        cases = ((raising(http), "503"), (raising(urllib.error.URLError("x")), "koneksi"),
                 (raising(TimeoutError()), "koneksi"), (fake_urlopen(b"<html>"), "JSON"))
        for opener, text in cases:
            with self.assertRaises(ValueError) as ctx:
                fetch_json("https://example.test", opener)
            self.assertIn(text, str(ctx.exception))


class ParseTest(unittest.TestCase):
    def test_buku_lengkap(self):
        total, books = parse_books(SAMPLE)
        self.assertEqual(total, 2)
        self.assertEqual(len(books), 2)
        book = books[0]
        self.assertEqual(book["title"], "Laskar Pelangi")
        self.assertEqual(book["authors"], ["Andrea Hirata"])
        self.assertEqual(book["year"], 2005)
        self.assertEqual(book["publisher"], "Bentang")
        self.assertEqual(book["pages"], 534)
        self.assertEqual(book["cover"], "https://covers.openlibrary.org/b/id/7079796-M.jpg")
        self.assertEqual(book["link"], "https://openlibrary.org/works/OL15302003W")

    def test_kolom_hilang(self):
        book = parse_books(SAMPLE)[1][1]
        self.assertEqual(book["authors"], [])
        self.assertIsNone(book["year"])
        self.assertIsNone(book["cover"])
        self.assertIsNone(book["publisher"])

    def test_kunci_aneh_tidak_jadi_tautan(self):
        book = parse_books({"docs": [{"title": "X", "key": "//evil.test", "cover_i": "1"}]})[1][0]
        self.assertIsNone(book["link"])
        self.assertIsNone(book["cover"])

    def test_format_tidak_dikenal(self):
        for bad in (None, [], {"docs": None}, {"error": "x"}):
            with self.assertRaises(ValueError):
                parse_books(bad)


class FormatTest(unittest.TestCase):
    def test_teks(self):
        total, books = parse_books(SAMPLE)
        out = format_results(total, books)
        self.assertIn("Menampilkan 1-2 dari 2 buku.", out)
        self.assertIn("  1. Laskar Pelangi", out)
        self.assertIn("Andrea Hirata (2005)", out)
        self.assertIn("Bentang | 534 halaman | bahasa: ind", out)
        self.assertIn("penulis tidak diketahui (tahun tidak diketahui)", describe_book(books[1]))
        self.assertEqual(format_results(0, []), "Tidak ada buku yang cocok.")

    def test_nomor_halaman_kedua(self):
        _, books = parse_books(SAMPLE)
        self.assertIn(" 11. Laskar Pelangi", format_results(30, books, page=2, limit=10))

    def test_html_di_escape(self):
        book = {"title": "<script>alert(1)</script>", "authors": ["A & B"], "year": 2000,
                "cover": "javascript:alert(1)", "link": "https://openlibrary.org/works/OL1W"}
        page = render_html([book], "Judul <b>")
        self.assertNotIn("<script>alert", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("A &amp; B", page)
        self.assertNotIn("javascript:", page)
        self.assertIn("Tanpa sampul", page)
        self.assertIn('rel="noopener noreferrer"', page)
        self.assertIn("Judul &lt;b&gt;", page)

    def test_html_responsif(self):
        page = render_html(parse_books(SAMPLE)[1])
        self.assertIn('name="viewport"', page)
        self.assertIn("auto-fill", page)
        self.assertIn('loading="lazy"', page)
        self.assertIn("prefers-color-scheme: dark", page)


class ParseQueryTest(unittest.TestCase):
    def test_kata_bebas_dan_kriteria(self):
        self.assertEqual(parse_query("dune"), {"q": "dune"})
        self.assertEqual(parse_query("dune author:frank herbert year:1965"),
                         {"q": "dune", "author": "frank herbert", "year": "1965"})
        self.assertEqual(parse_query("title:bumi manusia lang:ind"), {"title": "bumi manusia", "language": "ind"})

    def test_titik_dua_lain_tetap_kata_bebas(self):
        self.assertEqual(parse_query("c++ http://x"), {"q": "c++ http://x"})


class SpinnerTest(unittest.TestCase):
    def test_diam_kalau_bukan_terminal(self):
        stream = io.StringIO()
        with Spinner(stream=stream):
            pass
        self.assertEqual(stream.getvalue(), "")

    def test_beranimasi_di_terminal(self):
        class Tty(io.StringIO):
            def isatty(self):
                return True

        stream = Tty()
        with Spinner(stream=stream, interval=0.01):
            time.sleep(0.05)
        self.assertIn("Mencari", stream.getvalue())
        self.assertTrue(stream.getvalue().endswith("\r"))  # baris spinner dibersihkan


class MainTest(unittest.TestCase):
    def run_main(self, argv, opener):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(argv, urlopen=opener, spinner_stream=io.StringIO())
        return code, buf.getvalue()

    def test_cari_dan_tulis_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "hasil.html")
            seen = []
            code, out = self.run_main(["-a", "hirata", "-n", "3", "--html", path], fake_urlopen(SAMPLE, seen))
            self.assertEqual(code, 0)
            self.assertIn("Laskar Pelangi", out)
            self.assertEqual(query_of(seen[0].full_url)["author"], "hirata")
            self.assertEqual(query_of(seen[0].full_url)["limit"], "3")
            with open(path, encoding="utf-8") as handle:
                page = handle.read()
            self.assertIn("Buku untuk penulis hirata", page)
            self.assertIn("covers.openlibrary.org", page)

    def test_error_jaringan(self):
        code, out = self.run_main(["dune"], raising(urllib.error.URLError("x")))
        self.assertEqual(code, 1)
        self.assertIn("Error", out)

    def test_interaktif(self):
        seen = []
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), unittest.mock.patch("builtins.input", side_effect=["dune author:herbert", ""]):
            code = main([], urlopen=fake_urlopen(SAMPLE, seen), spinner_stream=io.StringIO())
        self.assertEqual(code, 0)
        self.assertEqual(query_of(seen[0].full_url)["author"], "herbert")
        self.assertIn("Laskar Pelangi", buf.getvalue())

    def test_search(self):
        total, books = search({"q": "x"}, urlopen=fake_urlopen(SAMPLE))
        self.assertEqual((total, len(books)), (2, 2))


if __name__ == "__main__":
    unittest.main()
