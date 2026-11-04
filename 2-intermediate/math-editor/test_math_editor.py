import contextlib
import io
import json
import os
import tempfile
import unittest

from PIL import Image

import math_editor
from math_editor import (
    DocumentError,
    check_formulas,
    collect_images,
    export_html,
    formulas,
    load_document,
    main,
    parse,
    render_formula,
    save_document,
)


def make_png(path, color=(200, 30, 30)):
    Image.new("RGB", (20, 10), color).save(path)


class ParseTest(unittest.TestCase):
    def test_teks_rumus_dan_gaya(self):
        segments = parse(r"Ini **tebal $x^2$ dan *miring*** [warna=#c00]merah[/warna] $$\frac{1}{2}$$ akhir")
        self.assertEqual(segments, [
            ("text", "Ini ", frozenset()),
            ("text", "tebal ", frozenset({"bold"})),
            ("math", "x^2", frozenset({"bold"})),
            ("text", " dan ", frozenset({"bold"})),
            ("text", "miring", frozenset({"bold", "italic"})),
            ("text", " ", frozenset()),
            ("text", "merah", frozenset({"color:#cc0000"})),
            ("text", " ", frozenset()),
            ("display", r"\frac{1}{2}", frozenset()),
            ("text", " akhir", frozenset()),
        ])

    def test_dolar_biasa_dan_bintang_di_tengah_angka(self):
        self.assertEqual(parse(r"harga \$5 dan \$7, hasil 2*3*4"),
                         [("text", "harga $5 dan $7, hasil 2*3*4", frozenset())])

    def test_gambar(self):
        self.assertEqual(parse("![grafik](a.png)"), [("image", "a.png", frozenset({"alt:grafik"}))])

    def test_daftar_rumus(self):
        self.assertEqual(formulas(r"$a$ dan $$b$$ serta $c$"), ["a", "b", "c"])
        self.assertEqual(len(formulas(math_editor.SAMPLE)), 8)


class RenderTest(unittest.TestCase):
    def test_png_dan_svg(self):
        png = render_formula(r"\frac{-b \pm \sqrt{b^2-4ac}}{2a}")
        self.assertTrue(png.startswith(b"\x89PNG"))
        self.assertIn(b"<svg", render_formula(r"\int_0^1 x^2\,dx", fmt="svg"))

    def test_rumus_lebih_besar_gambar_lebih_besar(self):
        small = Image.open(io.BytesIO(render_formula("x^2", size=10)))
        big = Image.open(io.BytesIO(render_formula("x^2", size=30)))
        self.assertGreater(big.width, small.width)

    def test_rumus_salah(self):
        with self.assertRaises(ValueError) as ctx:
            render_formula(r"\frac{1}{")
        self.assertIn(r"\frac{1}{", str(ctx.exception))
        self.assertEqual(len(check_formulas(r"$\frac{1}{$ dan $x^2$")), 1)
        self.assertEqual(check_formulas(math_editor.SAMPLE), [])


class DocumentTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_simpan_dan_buka_rumus_utuh(self):
        path = os.path.join(self.dir, "a.mathdoc")
        save_document(path, math_editor.SAMPLE, font_size=16)
        doc = load_document(path)
        self.assertEqual(doc["text"], math_editor.SAMPLE)
        self.assertEqual(doc["font_size"], 16)
        self.assertEqual(formulas(doc["text"]), formulas(math_editor.SAMPLE))

    def test_gambar_ikut_tersimpan(self):
        make_png(os.path.join(self.dir, "grafik.png"))
        path = os.path.join(self.dir, "a.mathdoc")
        save_document(path, "Lihat ![g](grafik.png)")
        os.remove(os.path.join(self.dir, "grafik.png"))  # dokumen tidak bergantung pada berkas asli
        doc = load_document(path)
        data = math_editor.image_bytes("grafik.png", doc["images"])
        self.assertEqual(Image.open(io.BytesIO(data)).getpixel((0, 0)), (200, 30, 30))

    def test_gambar_yang_tidak_ada_dilewati(self):
        self.assertEqual(collect_images("![x](hilang.png)", self.dir), {})

    def test_berkas_tidak_valid(self):
        bad = os.path.join(self.dir, "b.mathdoc")
        for content in ("{rusak", json.dumps({"text": "x"}), json.dumps({"format": "mathdoc", "text": 5}),
                        json.dumps({"format": "mathdoc", "version": 99, "text": "x"})):
            with open(bad, "w", encoding="utf-8") as handle:
                handle.write(content)
            with self.assertRaises(DocumentError, msg=content):
                load_document(bad)
        with self.assertRaises(DocumentError):
            load_document(os.path.join(self.dir, "hilang.mathdoc"))
        with self.assertRaises(DocumentError):
            save_document(bad, "x", font_size=99)

    def test_ukuran_huruf_aneh_kembali_ke_bawaan(self):
        path = os.path.join(self.dir, "c.mathdoc")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"format": "mathdoc", "version": 1, "text": "x", "font_size": "besar"}, handle)
        self.assertEqual(load_document(path)["font_size"], 12)


class HtmlTest(unittest.TestCase):
    def test_ekspor(self):
        page = export_html(r"**Tebal** <b>mentah</b> [warna=#2a7d46]hijau[/warna] $x^2$ $$\frac{1}{2}$$ $\frac{$")
        self.assertIn("<strong>Tebal</strong>", page)
        self.assertIn("&lt;b&gt;mentah&lt;/b&gt;", page)
        self.assertIn('<span style="color:#2a7d46">hijau</span>', page)
        self.assertEqual(page.count("<svg"), 2)
        self.assertIn('class="math display"', page)
        self.assertIn('class="error"', page)  # rumus salah ditandai, tidak membuat ekspor gagal
        self.assertNotIn("<?xml", page)

    def test_gambar_sebagai_data_uri(self):
        page = export_html("![g](a.png)", images={"a.png": "data:image/png;base64,AAAA"})
        self.assertIn('<img src="data:image/png;base64,AAAA" alt="g">', page)
        self.assertIn("tidak ditemukan", export_html("![g](b.png)"))


class CliTest(unittest.TestCase):
    def test_ekspor_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = os.path.join(tmp, "a.mathdoc")
            out = os.path.join(tmp, "a.html")
            save_document(doc, r"$x^2$ dan $\frac{$")
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(main([doc, "--html", out]), 0)
            self.assertIn("2 rumus", stdout.getvalue())
            self.assertIn("Peringatan", stderr.getvalue())
            self.assertTrue(os.path.getsize(out) > 0)


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.tmp = tempfile.TemporaryDirectory()
        self.doc = os.path.join(self.tmp.name, "a.mathdoc")
        self.notes = []
        self.formula = r"\sqrt{2}"
        self.app = math_editor.MathEditorApp(self.root, ask_save=lambda *_: self.doc, ask_open=lambda: self.doc,
                                             ask_formula=lambda: self.formula, notify=self.notes.append)

    def tearDown(self):
        self.root.destroy()
        self.tmp.cleanup()

    def test_contoh_dirender(self):
        self.assertEqual(len(self.app.photos), 8)  # 8 rumus di contoh
        self.assertIn("8 rumus", self.app.status.get())

    def test_sisip_rumus_dan_format(self):
        self.app.set_text("")
        self.app.insert_formula()
        self.assertEqual(self.app.text, r"$\sqrt{2}$")
        self.formula = r"\frac{1}{"
        self.app.insert_formula()
        self.assertEqual(self.app.text, r"$\sqrt{2}$")  # rumus salah tidak disisipkan
        self.assertEqual(len(self.notes), 1)
        self.app.set_text("halo")
        self.app.source.tag_add("sel", "1.0", "1.4")
        self.app.wrap("**", "**")
        self.assertEqual(self.app.text, "**halo**")

    def test_simpan_buka_dan_gambar(self):
        os.mkdir(os.path.join(self.tmp.name, "unduhan"))  # gambar di folder lain, bukan di samping dokumen
        image = os.path.join(self.tmp.name, "unduhan", "g.png")
        make_png(image, (10, 200, 10))
        self.app.add_image(image)
        self.app.font_size.set(18)
        self.assertEqual(self.app.save(), self.doc)
        os.remove(image)
        self.app.new()
        self.assertEqual(self.app.text, "")
        self.app.open()
        self.assertEqual(self.app.font_size.get(), 18)
        self.assertIn("![g](g.png)", self.app.text)
        self.assertEqual(len(self.app.photos), 9)  # 8 rumus + 1 gambar


if __name__ == "__main__":
    unittest.main()
