import os
import tempfile
import unittest
from datetime import datetime

from notes import NoteStore, inline, main, markdown_to_html, note_page


class InlineTest(unittest.TestCase):
    def test_format_dasar(self):
        self.assertEqual(inline("**tebal**"), "<strong>tebal</strong>")
        self.assertEqual(inline("*miring*"), "<em>miring</em>")
        self.assertEqual(inline("_miring_"), "<em>miring</em>")
        self.assertEqual(inline("`kode`"), "<code>kode</code>")
        self.assertEqual(inline("a **b** dan *c*"), "a <strong>b</strong> dan <em>c</em>")

    def test_tautan(self):
        self.assertEqual(inline("[situs](https://a.com/x?y=1&z=2)"), '<a href="https://a.com/x?y=1&amp;z=2">situs</a>')
        self.assertEqual(inline("[lokal](halaman.html)"), '<a href="halaman.html">lokal</a>')

    def test_tautan_berbahaya_ditolak(self):
        for url in ("javascript:alert(1)", "JavaScript:alert(1)", "data:text/html,x", "vbscript:x"):
            result = inline(f"[klik]({url})")
            self.assertNotIn("<a", result, url)
            self.assertNotIn("href", result, url)
        # URL dengan kurung bersarang tidak didukung: sisa ")" tertinggal, tapi tidak ada tautan
        self.assertEqual(inline("[klik](javascript:alert)"), "klik")

    def test_html_mentah_di_escape(self):
        self.assertEqual(inline("<script>alert(1)</script>"), "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertEqual(inline('<img src=x onerror="a()">'), "&lt;img src=x onerror=&quot;a()&quot;&gt;")

    def test_isi_kode_tidak_diformat_ulang(self):
        self.assertEqual(inline("`**bukan tebal**`"), "<code>**bukan tebal**</code>")
        self.assertEqual(inline("`<b>`"), "<code>&lt;b&gt;</code>")

    def test_tanda_bintang_biasa_tidak_jadi_miring(self):
        self.assertEqual(inline("2 * 3 * 4"), "2 * 3 * 4")
        self.assertEqual(inline("snake_case_name"), "snake_case_name")


class MarkdownTest(unittest.TestCase):
    def test_judul_dan_paragraf(self):
        self.assertEqual(markdown_to_html("# Judul\n\nIsi satu\nlanjut.\n\n## Sub"),
                         "<h1>Judul</h1>\n<p>Isi satu lanjut.</p>\n<h2>Sub</h2>")

    def test_daftar(self):
        self.assertEqual(markdown_to_html("- a\n- b\n* c"), "<ul><li>a</li><li>b</li><li>c</li></ul>")
        self.assertEqual(markdown_to_html("1. satu\n2. dua"), "<ol><li>satu</li><li>dua</li></ol>")

    def test_daftar_diikuti_paragraf(self):
        self.assertEqual(markdown_to_html("- a\n- b\n\nteks"), "<ul><li>a</li><li>b</li></ul>\n<p>teks</p>")

    def test_blok_kode_di_escape(self):
        self.assertEqual(markdown_to_html("```\n<b>x</b>\n# bukan judul\n```"),
                         "<pre><code>&lt;b&gt;x&lt;/b&gt;\n# bukan judul</code></pre>")

    def test_kutipan_dan_garis(self):
        self.assertEqual(markdown_to_html("> kutip\n> dua"), "<blockquote><p>kutip dua</p></blockquote>")
        self.assertEqual(markdown_to_html("---"), "<hr>")

    def test_miring_di_awal_baris_bukan_daftar(self):
        self.assertEqual(markdown_to_html("*miring* teks"), "<p><em>miring</em> teks</p>")

    def test_kosong_dan_crlf(self):
        self.assertEqual(markdown_to_html(""), "")
        self.assertEqual(markdown_to_html("a\r\n\r\nb"), "<p>a</p>\n<p>b</p>")

    def test_blok_kode_tidak_ditutup(self):
        self.assertEqual(markdown_to_html("```\nx"), "<pre><code>x</code></pre>")


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "notes.json")
        self.times = iter(datetime(2026, 10, 29, 9, minute) for minute in range(0, 60))
        self.store = NoteStore(self.path, now=lambda: next(self.times))

    def tearDown(self):
        self.dir.cleanup()

    def test_buat_dan_tanggal(self):
        note = self.store.add("  Belanja  ", "telur")
        self.assertEqual((note["id"], note["title"], note["created"]), (1, "Belanja", "2026-10-29 09:00"))

    def test_persisten_antar_sesi(self):
        self.store.add("A", "isi a")
        again = NoteStore(self.path)
        self.assertEqual([n["title"] for n in again.all()], ["A"])

    def test_ubah_mengganti_tanggal_diubah_saja(self):
        self.store.add("A", "x")
        note = self.store.edit(1, body="y")
        self.assertEqual((note["title"], note["body"]), ("A", "y"))
        self.assertEqual((note["created"], note["updated"]), ("2026-10-29 09:00", "2026-10-29 09:01"))
        self.assertEqual(self.store.edit(1, title="B")["title"], "B")

    def test_hapus_dan_id_tidak_dipakai_ulang(self):
        self.store.add("A")
        self.store.add("B")
        self.store.delete(1)
        self.assertEqual([n["title"] for n in self.store.all()], ["B"])
        self.assertEqual(self.store.add("C")["id"], 3)

    def test_kesalahan(self):
        with self.assertRaises(ValueError):
            self.store.add("   ")
        for action in (lambda: self.store.get(9), lambda: self.store.edit(9, body="x"), lambda: self.store.delete(9)):
            with self.assertRaises(ValueError):
                action()
        self.store.add("A")
        with self.assertRaises(ValueError):
            self.store.edit(1, title=" ")
        self.assertEqual(self.store.get(1)["title"], "A")

    def test_berkas_rusak_tidak_ditimpa(self):
        with open(self.path, "w", encoding="utf-8") as file:
            file.write("{rusak")
        with self.assertRaises(ValueError):
            self.store.add("A")
        with open(self.path, encoding="utf-8") as file:
            self.assertEqual(file.read(), "{rusak")

    def test_tidak_ada_berkas_sementara_tertinggal(self):
        self.store.add("A")
        self.assertEqual(os.listdir(self.dir.name), ["notes.json"])

    def test_unicode_utuh(self):
        self.store.add("Rapat ☕", "Zoë dan 日本")
        self.assertEqual(NoteStore(self.path).get(1)["body"], "Zoë dan 日本")


class PageTest(unittest.TestCase):
    def test_halaman_html(self):
        note = {"title": "<b>T</b>", "body": "# Hai\n\n**x**", "created": "2026-10-29 09:00", "updated": "2026-10-29 09:00"}
        page = note_page(note)
        self.assertIn("<title>&lt;b&gt;T&lt;/b&gt;</title>", page)
        self.assertIn("<h1>Hai</h1>", page)
        self.assertIn("<strong>x</strong>", page)
        self.assertNotIn("diubah", page)


class CliTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = os.path.join(self.dir.name, "n.json")

    def tearDown(self):
        self.dir.cleanup()

    def run_main(self, *args):
        return main(["-f", self.store, *args])

    def test_alur_lengkap(self):
        self.assertEqual(self.run_main("add", "Belanja", "-b", "- telur\\n- susu"), 0)
        self.assertEqual(NoteStore(self.store).get(1)["body"], "- telur\n- susu")
        self.assertEqual(self.run_main("edit", "1", "-t", "Belanja 2"), 0)
        out = os.path.join(self.dir.name, "o.html")
        self.assertEqual(self.run_main("show", "1", "--html", "-o", out), 0)
        with open(out, encoding="utf-8") as file:
            self.assertIn("<ul><li>telur</li><li>susu</li></ul>", file.read())
        self.assertEqual(self.run_main("delete", "1"), 0)
        self.assertEqual(self.run_main("show", "1"), 1)

    def test_edit_tanpa_perubahan_ditolak(self):
        self.run_main("add", "A", "-b", "x")
        self.assertEqual(self.run_main("edit", "1"), 1)

    def test_berkas_isi_tidak_ada(self):
        self.assertEqual(self.run_main("add", "A", "--file", "tidak-ada.md"), 1)


if __name__ == "__main__":
    unittest.main()
