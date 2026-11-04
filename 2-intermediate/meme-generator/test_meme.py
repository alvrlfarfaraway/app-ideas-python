import contextlib
import io
import os
import tempfile
import unittest

from PIL import Image, ImageDraw

import meme
from meme import Meme, Shape, TextItem, available_fonts, demo_image, load_font, main, wrap_text

WHITE, BLACK, GRAY = (255, 255, 255), (0, 0, 0), (120, 120, 120)


def plain(size=(400, 300)):
    m = Meme(Image.new("RGB", size, GRAY))
    m.texts = [TextItem("", 0.5, 0.1, size=40), TextItem("", 0.5, 0.9, size=40)]
    return m


def colors_in(image, box):
    return {color for _, color in image.crop(box).getcolors(1 << 24)}


class FontTest(unittest.TestCase):
    def test_font_tersedia(self):
        fonts = available_fonts()
        self.assertTrue(all(meme.find_font(name) for name in fonts))
        self.assertIsNotNone(load_font("Font yang tidak ada", 20))  # jatuh ke font bawaan Pillow

    def test_bungkus_teks(self):
        draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        font = load_font("Impact", 40)
        lines = wrap_text(draw, "SATU DUA TIGA EMPAT LIMA ENAM TUJUH DELAPAN", font, 200)
        self.assertGreater(len(lines), 1)
        self.assertTrue(all(draw.textlength(line, font=font) <= 200 for line in lines if " " in line))
        self.assertEqual(wrap_text(draw, "a\n\nb", font, 500), ["a", "", "b"])


class RenderTest(unittest.TestCase):
    def test_teks_atas_dan_bawah(self):
        m = plain()
        m.top.text, m.bottom.text = "atas", "bawah"
        image = m.render()
        self.assertIn(WHITE, colors_in(image, (0, 0, 400, 60)))
        self.assertIn(WHITE, colors_in(image, (0, 240, 400, 300)))
        self.assertNotIn(WHITE, colors_in(image, (0, 120, 400, 180)))
        self.assertEqual(m.image.getpixel((200, 20)), GRAY)  # gambar asli tidak berubah

    def test_warna_dan_garis_tepi(self):
        m = plain()
        m.top.text, m.top.color = "WARNA", "#ffd60a"
        image = m.render()
        self.assertIn((255, 214, 10), colors_in(image, (0, 0, 400, 80)))
        self.assertIn(BLACK, colors_in(image, (0, 0, 400, 80)))
        m.top.outline = False
        self.assertNotIn(BLACK, colors_in(m.render(), (0, 0, 400, 80)))

    def test_ukuran_teks(self):
        m = plain()
        m.top.text = "UKURAN"
        draw = ImageDraw.Draw(m.image.copy())
        small = m.text_layout(m.top, draw)[3]
        m.top.size = 80
        big = m.text_layout(m.top, draw)[3]
        self.assertGreater(big[2] - big[0], small[2] - small[0])

    def test_huruf_kapital(self):
        item = TextItem("halo", 0.5, 0.5)
        self.assertEqual(item.shown, "HALO")
        item.uppercase = False
        self.assertEqual(item.shown, "halo")

    def test_teks_panjang_tetap_di_dalam_gambar(self):
        m = plain()
        m.top.text = "teks yang sangat panjang sekali sehingga harus dibungkus menjadi dua baris"
        x0, y0, x1, y1 = m.text_layout(m.top, ImageDraw.Draw(m.image.copy()))[3]
        self.assertGreaterEqual(y0, 0)
        self.assertGreaterEqual(x0, 0)
        self.assertLessEqual(x1, 400)

    def test_bentuk(self):
        m = plain()
        m.shapes = [Shape("rect", [(10, 10), (100, 100)], "#ff0000", 4),
                    Shape("oval", [(300, 200), (200, 120)], "#00ff00", 4),
                    Shape("pen", [(150, 250), (250, 250)], "#0000ff", 6)]
        image = m.render()
        self.assertEqual(image.getpixel((11, 50)), (255, 0, 0))
        self.assertEqual(image.getpixel((50, 50)), GRAY)  # persegi tidak diisi
        self.assertIn((0, 255, 0), colors_in(image, (195, 115, 305, 205)))
        self.assertEqual(image.getpixel((200, 250)), (0, 0, 255))


class MoveTest(unittest.TestCase):
    def test_kena_dan_seret_teks(self):
        m = plain()
        m.top.text = "ATAS"
        self.assertEqual(m.hit_text(200, 30), 0)
        self.assertIsNone(m.hit_text(200, 150))
        self.assertIsNone(m.hit_text(200, 270))  # teks bawah kosong tidak bisa dipilih
        m.move_text(0, 100, 150)
        self.assertEqual((m.top.x, m.top.y), (0.25, 0.5))
        m.move_text(0, -50, 999)
        self.assertEqual((m.top.x, m.top.y), (0.0, 1.0))


class FileTest(unittest.TestCase):
    def test_buka_perkecil_dan_simpan(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "besar.png")
            Image.new("RGB", (2000, 1000), (10, 20, 30)).save(source)
            m = Meme.open(source)
            self.assertEqual(m.image.size, (900, 450))
            self.assertEqual(len(m.texts), 2)
            m.top.text = "x"
            for name, fmt in (("a.png", "PNG"), ("b.jpg", "JPEG")):
                with Image.open(m.save(os.path.join(tmp, name))) as saved:
                    self.assertEqual((saved.format, saved.size), (fmt, (900, 450)))
            with self.assertRaises(ValueError):
                m.save(os.path.join(tmp, "c.bmp"))

    def test_gambar_contoh(self):
        self.assertEqual(demo_image().size, (800, 600))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "m.png")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--top", "atas", "--bottom", "bawah", "--color", "#ff0000", "-o", out]), 0)
            with Image.open(out) as image:
                self.assertIn((255, 0, 0), colors_in(image, (0, 0, 800, 120)))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main([os.path.join(tmp, "hilang.png")]), 1)


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.tmp = tempfile.TemporaryDirectory()
        self.m = plain()
        self.app = meme.MemeApp(self.root, self.m, ask_save=lambda: os.path.join(self.tmp.name, "x.png"),
                                notify=lambda message: None)

    def tearDown(self):
        self.root.destroy()
        self.tmp.cleanup()

    def event(self, x, y):
        return type("E", (), {"x": x, "y": y})()

    def test_ketik_dan_gaya(self):
        self.app.top_var.set("halo")
        self.assertEqual(self.m.top.text, "halo")
        self.app.size_var.set(70)
        self.app.upper_var.set(False)
        self.app.on_style()
        self.assertEqual((self.m.top.size, self.m.bottom.size, self.m.top.uppercase), (70, 70, False))
        self.app.set_text_color("#00ff00")
        self.assertEqual(self.m.bottom.color, "#00ff00")

    def test_seret_teks_dan_gambar_bentuk(self):
        self.app.top_var.set("ATAS")
        self.app.on_press(self.event(200, 30))
        self.app.on_drag(self.event(200, 150))
        self.app.on_release(self.event(200, 150))
        self.assertEqual(self.m.top.y, 0.5)
        self.app.mode.set("rect")
        self.app.on_press(self.event(10, 10))
        self.app.on_release(self.event(10, 10))  # klik saja: tidak ada bentuk
        self.assertEqual(self.m.shapes, [])
        self.app.on_press(self.event(10, 10))
        self.app.on_drag(self.event(60, 80))
        self.app.on_release(self.event(60, 80))
        self.assertEqual(self.m.shapes[0].points, [(10, 10), (60, 80)])
        self.app.clear_shapes()
        self.assertEqual(self.m.shapes, [])

    def test_simpan(self):
        self.app.top_var.set("x")
        path = self.app.save()
        self.assertTrue(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
