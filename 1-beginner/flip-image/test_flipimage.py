import os
import tempfile
import unittest

from PIL import Image, ImageChops, ImageOps

from flipimage import TILE, FlipBoard, load_image, main, run_gui, sample_image


def same(a, b):
    return ImageChops.difference(a.convert("RGB"), b.convert("RGB")).getbbox() is None


class FlipBoardTest(unittest.TestCase):
    def setUp(self):
        self.image = sample_image()
        self.board = FlipBoard(self.image)

    def test_awal_semua_sama_dengan_aslinya(self):
        for index in range(4):
            self.assertTrue(same(self.board.tile(index), self.image))

    def test_sampel_tidak_simetris(self):
        self.assertFalse(same(self.image, ImageOps.mirror(self.image)))
        self.assertFalse(same(self.image, ImageOps.flip(self.image)))

    def test_balik_horizontal_dan_vertikal(self):
        self.board.flip(0, "left")
        self.board.flip(1, "up")
        self.assertTrue(same(self.board.tile(0), ImageOps.mirror(self.image)))
        self.assertTrue(same(self.board.tile(1), ImageOps.flip(self.image)))

    def test_hanya_gambar_yang_dipilih_berubah(self):
        self.board.flip(2, "right")
        for index in (0, 1, 3):
            self.assertTrue(same(self.board.tile(index), self.image))

    def test_dua_kali_kembali_ke_awal(self):
        self.board.flip(3, "left")
        self.board.flip(3, "right")
        self.assertTrue(same(self.board.tile(3), self.image))

    def test_horizontal_dan_vertikal_bersama_jadi_rotasi_180(self):
        self.board.flip(0, "left")
        self.board.flip(0, "down")
        self.assertTrue(same(self.board.tile(0), self.image.rotate(180)))

    def test_arah_dan_nomor_salah(self):
        with self.assertRaises(ValueError):
            self.board.flip(4, "up")
        with self.assertRaises(ValueError):
            self.board.flip(-1, "up")
        with self.assertRaises(ValueError):
            self.board.flip(0, "diagonal")

    def test_render_2x2(self):
        self.board.flip(1, "left")
        canvas = self.board.render(gap=6)
        self.assertEqual(canvas.size, (TILE * 2 + 6, TILE * 2 + 6))
        self.assertTrue(same(canvas.crop((0, 0, TILE, TILE)), self.image))
        self.assertTrue(same(canvas.crop((TILE + 6, 0, TILE * 2 + 6, TILE)), ImageOps.mirror(self.image)))


class LoadImageTest(unittest.TestCase):
    def test_berkas_valid_dijadikan_persegi(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "lebar.png")
            Image.new("RGB", (400, 100), "red").save(path)
            self.assertEqual(load_image(path).size, (TILE, TILE))

    def test_tidak_ditemukan(self):
        with self.assertRaises(ValueError) as caught:
            load_image("tidak-ada.png")
        self.assertIn("tidak ditemukan", str(caught.exception))

    def test_bukan_gambar(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "teks.png")
            with open(path, "w") as file:
                file.write("bukan gambar")
            with self.assertRaises(ValueError) as caught:
                load_image(path)
            self.assertIn("bukan berkas gambar", str(caught.exception))

    def test_url_tidak_bisa_dijangkau(self):
        with self.assertRaises(ValueError):
            load_image("http://127.0.0.1:9/tidak-ada.png")


class CliTest(unittest.TestCase):
    def test_simpan_hasil(self):
        with tempfile.TemporaryDirectory() as folder:
            out = os.path.join(folder, "hasil.png")
            self.assertEqual(main(["--flip", "1:left", "--flip", "4:up", "-o", out]), 0)
            self.assertEqual(Image.open(out).size, (TILE * 2 + 6, TILE * 2 + 6))

    def test_argumen_salah(self):
        self.assertEqual(main(["--flip", "9:up", "-o", "x.png"]), 1)
        self.assertEqual(main(["--flip", "1:miring", "-o", "x.png"]), 1)
        self.assertEqual(main(["--flip", "salah", "-o", "x.png"]), 1)
        self.assertEqual(main(["--image", "tidak-ada.png", "-o", "x.png"]), 1)


class GuiTest(unittest.TestCase):
    def test_tombol_panah_membalik_gambar(self):
        import tkinter as tk
        board = FlipBoard(sample_image())
        try:
            root = run_gui(board)
        except tk.TclError:
            self.skipTest("tidak ada layar untuk Tkinter")
        try:
            buttons = [w for cell in root.winfo_children() for w in cell.winfo_children() if isinstance(w, tk.Button)]
            self.assertEqual(len(buttons), 16)  # 4 gambar x 4 panah
            buttons[2].invoke()  # gambar 1, panah kiri
            self.assertEqual(board.state[0], {"h": True, "v": False})
            buttons[4 * 3 + 0].invoke()  # gambar 4, panah atas
            self.assertEqual(board.state[3], {"h": False, "v": True})
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
