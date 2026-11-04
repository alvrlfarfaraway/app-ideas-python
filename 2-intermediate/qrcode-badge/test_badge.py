import contextlib
import io
import os
import tempfile
import unittest

from PIL import Image

import badge
from badge import HEIGHT, WIDTH, main, normalize_twitter, qr_image, render_badge, save_badge, validate, vcard

try:
    import zxingcpp
except ImportError:  # pembaca QR hanya untuk tes: pip install zxing-cpp
    zxingcpp = None

GOOD = ("Rina Kartika", "rina.kartika@example.com", "@rinakartika", "rinakartika")


class ValidateTest(unittest.TestCase):
    def test_data_benar(self):
        self.assertEqual(validate(*GOOD), [])
        self.assertEqual(validate("Rina Kartika", "rina@example.co.id"), [])  # Twitter & GitHub opsional

    def test_kesalahan(self):
        cases = {
            ("", "a@b.co"): "Nama wajib",
            ("Rina", "a@b.co"): "nama depan dan nama belakang",
            ("Rina K", ""): "Email wajib",
            ("Rina K", "rina@"): "bukan alamat email",
            ("Rina K", "a@b.co", "rina"): "diawali '@'",
            ("Rina K", "a@b.co", "@nama panjang"): "huruf, angka",
            ("Rina K", "a@b.co", "", "-salah-"): "GitHub",
        }
        for args, text in cases.items():
            errors = validate(*args)
            self.assertTrue(any(text in e for e in errors), (args, errors))

    def test_tanda_at_otomatis(self):
        self.assertEqual(normalize_twitter("rina"), "@rina")
        self.assertEqual(normalize_twitter(" @rina "), "@rina")
        self.assertEqual(normalize_twitter(""), "")


class VcardTest(unittest.TestCase):
    def test_isi(self):
        text = vcard(*GOOD)
        self.assertIn("N:Kartika;Rina;;;", text)
        self.assertIn("FN:Rina Kartika", text)
        self.assertIn("EMAIL;TYPE=INTERNET:rina.kartika@example.com", text)
        self.assertIn("URL;TYPE=Twitter:https://twitter.com/rinakartika", text)
        self.assertIn("URL;TYPE=GitHub:https://github.com/rinakartika", text)
        self.assertNotIn("Twitter", vcard("Rina Kartika", "r@x.co"))

    def test_escape(self):
        self.assertIn("FN:Toko\\, Kopi\\; Senja", vcard("Toko, Kopi; Senja", "a@b.co"))


class BadgeTest(unittest.TestCase):
    def test_ukuran_dan_error(self):
        image = render_badge(*GOOD, event="PyCon")
        self.assertEqual(image.size, (WIDTH, HEIGHT))
        with self.assertRaises(ValueError):
            render_badge("Rina", "bukan email")

    @unittest.skipIf(zxingcpp is None, "zxing-cpp tidak terpasang")
    def test_qr_di_badge_bisa_dipindai(self):
        results = zxingcpp.read_barcodes(render_badge(*GOOD))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].text, vcard(*GOOD))

    @unittest.skipIf(zxingcpp is None, "zxing-cpp tidak terpasang")
    def test_qr_tetap_terbaca_saat_dicetak_kecil(self):
        small = render_badge(*GOOD).resize((WIDTH // 3, HEIGHT // 3), Image.Resampling.LANCZOS)
        self.assertEqual(zxingcpp.read_barcodes(small)[0].text, vcard(*GOOD))

    @unittest.skipIf(zxingcpp is None, "zxing-cpp tidak terpasang")
    def test_qr_teks_unicode(self):
        image, _ = qr_image("Halo, Café ☕")
        self.assertEqual(zxingcpp.read_barcodes(image)[0].text, "Halo, Café ☕")

    def test_simpan(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = render_badge(*GOOD)
            with Image.open(save_badge(image, os.path.join(tmp, "a.png"))) as png:
                self.assertEqual(round(png.info["dpi"][0]), 300)
            with open(save_badge(image, os.path.join(tmp, "a.pdf")), "rb") as handle:
                self.assertTrue(handle.read(4) == b"%PDF")
            with self.assertRaises(ValueError):
                save_badge(image, os.path.join(tmp, "a.jpg"))

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "b.png")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--name", "Rina Kartika", "--email", "r@x.co", "--twitter", "rina", "-o", out]), 0)
            self.assertTrue(os.path.exists(out))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["--name", "Rina", "--email", "r@x.co"]), 1)


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.printed = []
        self.app = badge.BadgeApp(self.root, printer=self.printed.append)

    def tearDown(self):
        self.root.destroy()

    def fill(self, name="Rina Kartika", email="rina@example.com", twitter="rina", github=""):
        for key, value in (("name", name), ("email", email), ("twitter", twitter), ("github", github)):
            self.app.vars[key].set(value)

    def state(self):
        return str(self.app.print_button.cget("state"))

    def test_print_hanya_setelah_valid(self):
        self.assertEqual(self.state(), "disabled")
        self.fill(name="Rina")
        self.assertIsNone(self.app.create())
        self.assertIn("nama depan", self.app.errors.get())
        self.assertEqual(self.state(), "disabled")
        self.fill()
        self.assertIsNotNone(self.app.create())
        self.assertEqual(self.app.vars["twitter"].get(), "@rina")  # @ ditambahkan otomatis
        self.assertEqual(self.state(), "normal")
        self.app.print_badge()
        self.assertTrue(self.printed[0].endswith(".pdf"))

    def test_koreksi_lalu_create_lagi(self):
        self.fill()
        first = self.app.create()
        self.app.vars["name"].set("Sari Dewi")
        second = self.app.create()
        self.assertNotEqual(first.tobytes(), second.tobytes())

    def test_cancel(self):
        self.fill()
        self.app.create()
        self.app.cancel()
        self.assertEqual(self.app.values()["name"], "")
        self.assertIsNone(self.app.badge)
        self.assertEqual(self.state(), "disabled")


if __name__ == "__main__":
    unittest.main()
