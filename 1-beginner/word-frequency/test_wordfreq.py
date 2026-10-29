import email.message
import io
import os
import tempfile
import unittest
import urllib.error

from wordfreq import (MAX_CHARS, STOPWORDS, count_words, fetch_text, format_table, html_to_text, main,
                      tokenize)


class TokenizeTest(unittest.TestCase):
    def test_huruf_kecil_dan_tanda_baca_dibuang(self):
        self.assertEqual(tokenize("Halo, Dunia! HALO?"), ["halo", "dunia", "halo"])

    def test_angka_dilewati(self):
        self.assertEqual(tokenize("abc 123 def4 5ghi"), ["abc", "def", "ghi"])

    def test_apostrof_dan_tanda_hubung_di_tengah_kata(self):
        self.assertEqual(tokenize("Don't e-mail anak-anak 'quote'"), ["don't", "e-mail", "anak-anak", "quote"])
        self.assertEqual(tokenize("it’s"), ["it’s"])  # apostrof lengkung

    def test_huruf_beraksen_dan_non_latin(self):
        self.assertEqual(tokenize("Café Zoë naïve 日本語"), ["café", "zoë", "naïve", "日本語"])

    def test_garis_bawah_bukan_bagian_kata(self):
        self.assertEqual(tokenize("snake_case"), ["snake", "case"])

    def test_tanda_hubung_di_ujung_tidak_ikut(self):
        self.assertEqual(tokenize("- kata- -kata --"), ["kata", "kata"])


class CountWordsTest(unittest.TestCase):
    def test_urut_turun_menurut_jumlah(self):
        result = count_words("a b b c c c")
        self.assertEqual(result, [("c", 3), ("b", 2), ("a", 1)])

    def test_jumlah_sama_diurut_abjad(self):
        self.assertEqual(count_words("zebra apel mangga"), [("apel", 1), ("mangga", 1), ("zebra", 1)])

    def test_tidak_membedakan_huruf_besar_kecil(self):
        self.assertEqual(count_words("Aku aku AKU"), [("aku", 3)])

    def test_total_sama_dengan_jumlah_kata(self):
        text = "the quick brown fox jumps over the lazy dog the end"
        result = count_words(text)
        self.assertEqual(sum(c for _, c in result), len(text.split()))
        self.assertEqual(result[0], ("the", 3))

    def test_kosong(self):
        for text in ("", "   ", "\n\t "):
            with self.assertRaises(ValueError, msg=repr(text)):
                count_words(text)

    def test_batas_2048_karakter(self):
        count_words("a" * MAX_CHARS)  # tepat di batas: boleh
        with self.assertRaises(ValueError) as caught:
            count_words("a" * (MAX_CHARS + 1))
        self.assertIn("maksimal 2048", str(caught.exception))

    def test_tanpa_batas(self):
        self.assertEqual(count_words("a " * 5000, max_chars=None), [("a", 5000)])

    def test_tanpa_kata_sama_sekali(self):
        for text in ("12345", "!!! ???", "--"):
            with self.assertRaises(ValueError, msg=text):
                count_words(text)

    def test_stopwords(self):
        result = count_words("yang yang dan kucing dan kucing kucing", stopwords=STOPWORDS["id"])
        self.assertEqual(result, [("kucing", 3)])
        with self.assertRaises(ValueError):
            count_words("yang dan di", stopwords=STOPWORDS["id"])


class FormatTest(unittest.TestCase):
    def test_tabel(self):
        text = format_table(count_words("a b b c c c"))
        lines = text.splitlines()
        self.assertTrue(lines[0].lstrip().startswith("#"))
        self.assertIn("c", lines[1])
        self.assertIn("█", lines[1])
        self.assertIn("6 kata, 3 kata unik.", text)

    def test_top(self):
        text = format_table(count_words("a b b c c c"), top=2)
        self.assertNotIn(" a ", text.split("\n\n")[0])
        self.assertIn("6 kata, 3 kata unik.", text)  # total tetap dari seluruh teks

    def test_batang_proporsional(self):
        lines = format_table(count_words("a " * 10 + "b " * 5)).splitlines()
        self.assertEqual(lines[1].count("█"), 24)
        self.assertEqual(lines[2].count("█"), 12)


class HtmlTest(unittest.TestCase):
    def test_script_style_dan_head_dibuang(self):
        page = ("<html><head><title>Judul</title><style>p{color:red}</style></head><body>"
                "<h1>Halo Dunia</h1><script>var rahasia = 'jangan';</script><p>Isi &amp; <b>tebal</b></p>"
                "<noscript>aktifkan js</noscript></body></html>")
        text = html_to_text(page)
        self.assertEqual(text, "Halo Dunia Isi & tebal")

    def test_entitas_didekode(self):
        self.assertEqual(html_to_text("<p>caf&eacute; &lt;b&gt;</p>"), "café <b>")


class FakeResponse(io.BytesIO):
    def __init__(self, body, content_type="text/html; charset=utf-8"):
        super().__init__(body)
        self.headers = email.message.Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FetchTest(unittest.TestCase):
    def test_halaman_html(self):
        opener = lambda url, timeout: FakeResponse(b"<html><body><p>kucing kucing anjing</p></body></html>")
        self.assertEqual(count_words(fetch_text("https://x.test", opener), None), [("kucing", 2), ("anjing", 1)])

    def test_teks_biasa(self):
        opener = lambda url, timeout: FakeResponse("a < b dan b > a".encode(), "text/plain; charset=utf-8")
        self.assertIn("dan", fetch_text("http://x.test", opener))

    def test_charset_dihormati(self):
        opener = lambda url, timeout: FakeResponse("<p>café</p>".encode("latin-1"), "text/html; charset=iso-8859-1")
        self.assertEqual(fetch_text("http://x.test", opener), "café")

    def test_url_tidak_valid(self):
        for url in ("example.com", "ftp://x", "file:///etc/passwd", "javascript:alert(1)"):
            with self.assertRaises(ValueError, msg=url):
                fetch_text(url, lambda u, timeout: None)

    def test_jenis_konten_bukan_teks(self):
        opener = lambda url, timeout: FakeResponse(b"\x89PNG", "image/png")
        with self.assertRaises(ValueError) as caught:
            fetch_text("https://x.test/a.png", opener)
        self.assertIn("image/png", str(caught.exception))

    def test_kesalahan_jaringan(self):
        def offline(url, timeout):
            raise urllib.error.URLError("offline")

        def http_error(url, timeout):
            raise urllib.error.HTTPError(url, 404, "nf", {}, None)

        with self.assertRaises(ValueError) as caught:
            fetch_text("https://x.test", offline)
        self.assertIn("koneksi", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            fetch_text("https://x.test", http_error)
        self.assertIn("404", str(caught.exception))

    def test_halaman_terlalu_besar(self):
        opener = lambda url, timeout: FakeResponse(b"a" * 2_000_001, "text/plain")
        with self.assertRaises(ValueError):
            fetch_text("https://x.test", opener)


class CliTest(unittest.TestCase):
    def test_berkas(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "t.txt")
            with open(path, "w", encoding="utf-8") as file:
                file.write("a b b")
            self.assertEqual(main([path]), 0)
            self.assertEqual(main([path, "--top", "1"]), 0)
            self.assertEqual(main([path, "--top", "0"]), 1)
            long_path = os.path.join(folder, "long.txt")
            with open(long_path, "w", encoding="utf-8") as file:
                file.write("kata " * 500)  # 2500 karakter: melebihi batas isian
            self.assertEqual(main([long_path]), 1)
            self.assertEqual(main([os.path.join(folder, "tidak-ada.txt")]), 1)


if __name__ == "__main__":
    unittest.main()
