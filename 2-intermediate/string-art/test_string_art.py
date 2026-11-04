import math
import random
import unittest

import string_art
from string_art import BACKGROUND, TRAIL, StringLine, faded, hsv_hex, segment_points


def inside(points, width, height, slack=1e-6):
    x1, y1, x2, y2 = points
    return all(-slack <= v <= width + slack for v in (x1, x2)) and all(-slack <= v <= height + slack for v in (y1, y2))


class LineTest(unittest.TestCase):
    def test_mulai_di_dalam_jendela(self):
        for seed in range(50):
            line = StringLine(400, 300, 150, 5, random.Random(seed))
            self.assertTrue(inside(line.endpoints(), 400, 300))

    def test_selalu_di_dalam_jendela_dan_panjang_tetap(self):
        for seed in range(10):
            line = StringLine(300, 200, 120, 9, random.Random(seed))
            for _ in range(2000):
                points = line.step()
                self.assertTrue(inside(points, 300, 200), (seed, points))
                x1, y1, x2, y2 = points
                self.assertAlmostEqual(math.hypot(x2 - x1, y2 - y1), 120)
            self.assertGreater(line.bounces, 5)

    def test_pantulan_mengubah_arah(self):
        line = StringLine(300, 200, 100, 10, random.Random(1))
        line.x, line.y, line.angle, line.spin, line.heading = 245, 100, 0.0, 0.0, 0.0  # menuju tepi kanan
        line.step()
        self.assertEqual(line.bounces, 1)
        self.assertLess(math.cos(line.heading), 0)  # sekarang bergerak ke kiri
        self.assertTrue(inside(line.endpoints(), 300, 200))

    def test_bergerak_sesuai_kecepatan(self):
        line = StringLine(1000, 1000, 50, 7, random.Random(2))
        line.x, line.y, line.heading, line.spin = 500, 500, 0.0, 0.0
        line.step()
        self.assertAlmostEqual(line.x, 507)

    def test_jejak_terbatas(self):
        line = StringLine(400, 300, 100, 4, random.Random(3))
        for _ in range(100):
            line.step()
        self.assertEqual(len(line.trail), TRAIL)
        self.assertEqual(line.trail[-1], line.endpoints())

    def test_panjang_dibatasi_ukuran_jendela(self):
        line = StringLine(200, 100, 500, 4, random.Random(4))
        self.assertAlmostEqual(line.length, 90)
        line.resize(80, 80)
        self.assertLessEqual(line.length, 72)


class ColorTest(unittest.TestCase):
    def test_memudar_ke_latar(self):
        self.assertEqual(faded("#ffffff", 1), "#ffffff")
        self.assertEqual(faded("#ffffff", 0), "#%02x%02x%02x" % BACKGROUND)
        bright = [int(faded("#ff0000", s)[1:3], 16) for s in (1.0, 0.6, 0.3, 0.0)]
        self.assertEqual(bright, sorted(bright, reverse=True))

    def test_hsv(self):
        self.assertEqual(hsv_hex(0, 1, 1), "#ff0000")
        self.assertEqual(hsv_hex(1 / 3, 1, 1), "#00ff00")
        self.assertEqual(hsv_hex(1.0, 1, 1), hsv_hex(0, 1, 1))

    def test_potongan_garis(self):
        parts = segment_points(0, 0, 60, 0, 6)
        self.assertEqual(len(parts), 6)
        self.assertEqual(parts[0], (0, 0, 10, 0))
        self.assertEqual(parts[-1][2:], (60, 0))


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.app = string_art.StringArtApp(self.root, 400, 300, rng=random.Random(1))

    def tearDown(self):
        if self.app.job:
            self.root.after_cancel(self.app.job)
        self.root.destroy()

    def test_jumlah_garis_dan_item(self):
        self.assertEqual(len(self.app.lines), 3)
        self.app.count.set(5)
        self.app.reset()
        self.assertEqual(len(self.app.lines), 5)
        self.assertEqual(len(self.app.canvas.find_all()), 5 * TRAIL * string_art.SEGMENTS)

    def test_jeda_lanjut_dan_pengaturan(self):
        self.app.toggle()
        self.assertIsNone(self.app.job)
        self.assertEqual(self.app.pause_button.cget("text"), "Lanjut")
        self.app.toggle()
        self.assertIsNotNone(self.app.job)
        self.app.speed.set(12)
        self.app.length.set(100)
        self.app.apply_settings()
        self.assertTrue(all(line.speed == 12 and line.length == 100 for line in self.app.lines))

    def test_tick_menggambar(self):
        self.app.root.after_cancel(self.app.job)
        self.app.tick()
        coords = self.app.canvas.coords(self.app.items[0][0][0])
        self.assertNotEqual(coords, [0, 0, 0, 0])


if __name__ == "__main__":
    unittest.main()
