import os
import tempfile
import unittest

from PIL import Image

import drawing_app
from drawing_app import BACKGROUND, Drawing, Item, normalized_box, star_points

WHITE = (255, 255, 255)
RED = (209, 73, 91)  # #d1495b


class StarTest(unittest.TestCase):
    def test_sepuluh_titik_di_dalam_kotak(self):
        points = star_points(100, 50, 300, 250)
        self.assertEqual(len(points), 10)
        for x, y in points:
            self.assertTrue(100 - 1e-9 <= x <= 300 + 1e-9)
            self.assertTrue(50 - 1e-9 <= y <= 250 + 1e-9)
        self.assertAlmostEqual(points[0][0], 200)  # ujung atas di tengah
        self.assertAlmostEqual(points[0][1], 50)

    def test_kotak_dinormalkan(self):
        self.assertEqual(normalized_box([(300, 250), (100, 50)]), (100, 50, 300, 250))


class ModelTest(unittest.TestCase):
    def test_tambah_urungkan_bersihkan(self):
        d = Drawing()
        a = Item("stroke", [(1, 1), (5, 5)], "#000000", 3)
        b = Item("rect", [(10, 10), (20, 20)], "#000000", 2)
        d.add(a)
        d.add(b)
        self.assertEqual(d.items, [a, b])
        self.assertTrue(d.undo())
        self.assertEqual(d.items, [a])
        d.add(b)
        d.clear()
        self.assertEqual(d.items, [])
        self.assertTrue(d.undo())  # bersihkan juga bisa diurungkan
        self.assertEqual(d.items, [a, b])
        self.assertTrue(d.undo())
        self.assertTrue(d.undo())
        self.assertEqual(d.items, [])
        self.assertFalse(d.undo())

    def test_bersihkan_kanvas_kosong_tidak_menambah_riwayat(self):
        d = Drawing()
        d.clear()
        self.assertEqual(d.history, [])

    def test_item_tidak_valid(self):
        d = Drawing()
        with self.assertRaises(ValueError):
            d.add(Item("stroke", [], "#000000", 3))
        with self.assertRaises(ValueError):
            d.add(Item("rect", [(1, 1)], "#000000", 3))


class RenderTest(unittest.TestCase):
    def test_goresan_dan_ujung_bulat(self):
        d = Drawing(200, 100)
        d.add(Item("stroke", [(20, 50), (180, 50)], "#d1495b", 10))
        img = d.render()
        self.assertEqual(img.size, (200, 100))
        self.assertEqual(img.getpixel((100, 50)), RED)
        self.assertEqual(img.getpixel((16, 50)), RED)  # ujung bulat melewati titik awal
        self.assertEqual(img.getpixel((100, 20)), WHITE)

    def test_satu_titik_jadi_bulatan(self):
        d = Drawing(50, 50)
        d.add(Item("stroke", [(25, 25)], "#d1495b", 12))
        img = d.render()
        self.assertEqual(img.getpixel((25, 25)), RED)
        self.assertEqual(img.getpixel((25, 34)), WHITE)

    def test_bentuk_kosong_dan_terisi(self):
        d = Drawing(300, 100)
        d.add(Item("rect", [(10, 10), (90, 90)], "#d1495b", 4))
        d.add(Item("oval", [(110, 10), (190, 90)], "#d1495b", 4, fill=True))
        d.add(Item("star", [(210, 10), (290, 90)], "#d1495b", 2, fill=True))
        img = d.render()
        self.assertEqual(img.getpixel((11, 50)), RED)  # garis tepi persegi
        self.assertEqual(img.getpixel((50, 50)), WHITE)  # tengah persegi kosong
        self.assertEqual(img.getpixel((150, 50)), RED)  # elips terisi
        self.assertEqual(img.getpixel((250, 50)), RED)  # tengah bintang terisi
        self.assertEqual(img.getpixel((212, 88)), WHITE)  # sudut kotak di luar bintang

    def test_bentuk_terbalik_arah(self):
        d = Drawing(100, 100)
        d.add(Item("rect", [(90, 90), (10, 10)], "#d1495b", 1, fill=True))  # diseret dari kanan bawah
        self.assertEqual(d.render().getpixel((50, 50)), RED)

    def test_garis(self):
        d = Drawing(100, 100)
        d.add(Item("line", [(0, 0), (99, 99)], "#d1495b", 3))
        img = d.render()
        self.assertEqual(img.getpixel((50, 50)), RED)
        self.assertEqual(img.getpixel((90, 10)), WHITE)

    def test_penghapus_memakai_warna_latar(self):
        d = Drawing(100, 100)
        d.add(Item("rect", [(0, 0), (99, 99)], "#d1495b", 1, fill=True))
        d.add(Item("stroke", [(0, 50), (99, 50)], BACKGROUND, 10))
        img = d.render()
        self.assertEqual(img.getpixel((50, 50)), WHITE)
        self.assertEqual(img.getpixel((50, 20)), RED)


class SaveTest(unittest.TestCase):
    def test_png_dan_jpg(self):
        d = Drawing(120, 80)
        d.add(Item("oval", [(10, 10), (110, 70)], "#2e78c7", 3, fill=True))
        with tempfile.TemporaryDirectory() as tmp:
            for name, fmt in (("a.png", "PNG"), ("b.JPG", "JPEG"), ("c.jpeg", "JPEG")):
                path = os.path.join(tmp, name)
                d.save(path)
                with Image.open(path) as img:
                    self.assertEqual(img.format, fmt)
                    self.assertEqual(img.size, (120, 80))
            with Image.open(os.path.join(tmp, "a.png")) as img:
                self.assertEqual(img.getpixel((60, 40)), (46, 120, 199))
            with self.assertRaises(ValueError):
                d.save(os.path.join(tmp, "x.gif"))


class FakeEvent:
    def __init__(self, x, y):
        self.x, self.y = x, y


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.app = drawing_app.DrawingApp(self.root)

    def tearDown(self):
        self.root.destroy()

    def drag(self, *points):
        self.app.on_press(FakeEvent(*points[0]))
        for point in points[1:]:
            self.app.on_drag(FakeEvent(*point))
        self.app.on_release(FakeEvent(*points[-1]))

    def test_menggambar_dengan_mouse(self):
        self.app.set_color("#d1495b")
        self.app.size.set(9)
        self.drag((10, 10), (50, 20), (90, 40))
        item = self.app.drawing.items[-1]
        self.assertEqual(item.kind, "stroke")
        self.assertEqual(item.points, [(10, 10), (50, 20), (90, 40)])
        self.assertEqual((item.color, item.width), ("#d1495b", 9))
        self.assertEqual(len(self.app.canvas.find_withtag("item")), 1)
        self.assertEqual(self.app.canvas.find_withtag("preview"), ())

    def test_bentuk_dan_klik_tanpa_seret(self):
        self.app.tool.set("star")
        self.app.fill.set(True)
        self.drag((100, 100), (200, 180))
        self.assertEqual(self.app.drawing.items[-1].points, [(100, 100), (200, 180)])
        self.assertTrue(self.app.drawing.items[-1].fill)
        before = len(self.app.drawing.items)
        self.drag((300, 300))
        self.assertEqual(len(self.app.drawing.items), before)

    def test_penghapus_dan_ganti_warna(self):
        self.app.tool.set("eraser")
        self.drag((10, 10), (20, 20))
        self.assertEqual(self.app.drawing.items[-1].color, BACKGROUND)
        self.app.set_color("#2a9d55")
        self.assertEqual(self.app.tool.get(), "pen")  # memilih warna kembali ke pena

    def test_bersihkan_dan_urungkan(self):
        self.drag((10, 10), (20, 20))
        self.drag((30, 30), (40, 40))
        self.app.clear()
        self.assertEqual(self.app.canvas.find_all(), ())
        self.app.undo()
        self.assertEqual(len(self.app.canvas.find_all()), 2)

    def test_simpan(self):
        self.drag((10, 10), (200, 200))
        with tempfile.TemporaryDirectory() as tmp:
            path = self.app.save(os.path.join(tmp, "gambar.png"))
            self.assertTrue(os.path.exists(path))
            self.assertIn("Tersimpan", self.app.status.get())


if __name__ == "__main__":
    unittest.main()
