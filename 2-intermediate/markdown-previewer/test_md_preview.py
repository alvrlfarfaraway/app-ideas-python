import contextlib
import io
import os
import tempfile
import threading
import unittest
import unittest.mock
import urllib.error
import urllib.request

import md_preview
from md_preview import SAMPLE, document, editor_page, main, make_server, render


class RenderTest(unittest.TestCase):
    def test_markdown_dasar(self):
        out = render("# Judul\n\n*miring* **tebal** `kode`\n\n> kutip")
        self.assertIn("<h1>Judul</h1>", out)
        self.assertIn("<em>miring</em>", out)
        self.assertIn("<strong>tebal</strong>", out)
        self.assertIn("<code>kode</code>", out)
        self.assertIn("<blockquote>", out)

    def test_fitur_github(self):
        out = render("| a | b |\n| :- | -: |\n| 1 | 2 |\n\n~~coret~~\n\n- [ ] belum\n- [x] sudah\n\n"
                     "https://example.com\n\nCatatan[^1]\n\n[^1]: kaki")
        self.assertIn("<table>", out)
        self.assertIn('<td style="text-align:right">2</td>', out)
        self.assertIn("<del>coret</del>", out)
        self.assertIn('type="checkbox" disabled/>belum', out)
        self.assertIn("disabled checked/>sudah", out)
        self.assertIn('<a href="https://example.com">https://example.com</a>', out)
        self.assertIn('class="footnotes"', out)

    def test_blok_kode_di_escape(self):
        out = render("```python\nprint(1 < 2)\n```")
        self.assertIn('<code class="language-python">print(1 &lt; 2)', out)

    def test_html_mentah_dan_tautan_berbahaya(self):
        out = render("<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>\n\n[klik](javascript:alert(1))")
        self.assertNotIn("<script>", out)
        self.assertNotIn("<img", out)
        self.assertIn("&lt;script&gt;", out)
        self.assertNotIn("javascript:", out)

    def test_contoh_bawaan(self):
        out = render(SAMPLE)
        for tag in ("<h1>", "<table>", "<del>", "task-list-item", "footnotes", "<pre>"):
            self.assertIn(tag, out)


class PageTest(unittest.TestCase):
    def test_dokumen_utuh(self):
        page = document("# Hai", title="a<b>.md")
        self.assertTrue(page.startswith("<!DOCTYPE html>"))
        self.assertIn("<title>a&lt;b&gt;.md</title>", page)
        self.assertIn("<h1>Hai</h1>", page)
        self.assertIn("prefers-color-scheme: dark", page)

    def test_halaman_editor(self):
        page = editor_page()
        for placeholder in ("__THEME__", "__PREVIEW__", "__SAMPLE__"):
            self.assertNotIn(placeholder, page)
        self.assertIn('id="source"', page)
        self.assertIn("localStorage", page)
        self.assertIn("navigator.clipboard.writeText", page)
    def test_contoh_berisi_penutup_script_tidak_memutus_halaman(self):
        # Contoh disisipkan sebagai string JSON di dalam <script>; "</" harus di-escape.
        with unittest.mock.patch.object(md_preview, "SAMPLE", "a </script><script>alert(1)</script> b"):
            page = editor_page()
        script = page[page.index("<script>"):]
        self.assertEqual(script.count("</script>"), 1)
        self.assertIn("<\\/script>", script)


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def request(self, path, data=None, headers=None):
        req = urllib.request.Request(self.url + path, data=data, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status, response.headers, response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            return error.code, error.headers, error.read().decode("utf-8")

    def test_hanya_localhost(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_halaman(self):
        status, headers, body = self.request("/?contoh=1")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("Markdown Previewer", body)

    def test_render(self):
        status, headers, body = self.request("/render", "# Halo ✓\n\n<b>x</b>".encode("utf-8"),
                                             {"Content-Type": "text/plain; charset=utf-8"})
        self.assertEqual(status, 200)
        self.assertEqual(body.strip(), "<h1>Halo ✓</h1>\n<p>&lt;b&gt;x&lt;/b&gt;</p>")
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_teks_kosong(self):
        status, _, body = self.request("/render", b"")
        self.assertEqual((status, body), (200, ""))

    def test_tidak_ditemukan(self):
        self.assertEqual(self.request("/rahasia")[0], 404)
        self.assertEqual(self.request("/lain", b"x")[0], 404)

    def test_terlalu_besar(self):
        status, _, body = self.request("/render", b"x" * 1_000_001)
        self.assertEqual(status, 413)
        self.assertIn("1 MB", body)


class CliTest(unittest.TestCase):
    def test_render_berkas(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "a.md")
            target = os.path.join(tmp, "a.html")
            with open(source, "w", encoding="utf-8") as handle:
                handle.write("# Dari berkas\n\n- [x] ok")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main([source, "-o", target]), 0)
            with open(target, encoding="utf-8") as handle:
                self.assertIn("<h1>Dari berkas</h1>", handle.read())
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(main([os.path.join(tmp, "hilang.md"), "-o", target]), 1)

    def test_mode_berkas_butuh_dua_argumen(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["a.md"])


if __name__ == "__main__":
    unittest.main()
