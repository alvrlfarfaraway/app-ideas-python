import email.message
import io
import json
import os
import tempfile
import unittest
import urllib.error

from PIL import Image

from randommeal import MealWindow, fetch_image, format_meal, main, parse_meal, random_meal, save_picture

RAW = {
    "idMeal": "53225", "strMeal": "Yemeni Lahsa", "strCategory": "Breakfast", "strArea": "Saudi Arabian",
    "strInstructions": "1\r\nHeat the oil.\r\n2\r\nAdd the eggs.", "strMealThumb": "https://img.test/meal.jpg",
    "strYoutube": "https://www.youtube.com/watch?v=abc",
    "strIngredient1": "Egg", "strMeasure1": "5", "strIngredient2": "Olive Oil", "strMeasure2": " 2 tablespoons ",
    "strIngredient3": "Salt", "strMeasure3": " ", "strIngredient4": "", "strMeasure4": "", "strIngredient5": None,
}


def png_bytes():
    buffer = io.BytesIO()
    Image.new("RGB", (40, 30), "red").save(buffer, "PNG")
    return buffer.getvalue()


class FakeResponse(io.BytesIO):
    def __init__(self, body, content_type="application/json"):
        super().__init__(body)
        self.headers = email.message.Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def api(payload=None, image=None, content_type="image/png", error=None):
    requested = []

    def opener(request, timeout):
        url = request.full_url if hasattr(request, "full_url") else request
        requested.append(url)
        if error:
            raise error
        if "random.php" in url:
            return FakeResponse(json.dumps(payload if payload is not None else {"meals": [RAW]}).encode())
        return FakeResponse(image if image is not None else png_bytes(), content_type)

    opener.requested = requested
    return opener


class ParseTest(unittest.TestCase):
    def test_bahan_dan_takaran(self):
        meal = parse_meal(RAW)
        self.assertEqual(meal.ingredients, [("Egg", "5"), ("Olive Oil", "2 tablespoons"), ("Salt", "")])
        self.assertEqual((meal.name, meal.category, meal.area), ("Yemeni Lahsa", "Breakfast", "Saudi Arabian"))

    def test_baris_baru_dirapikan(self):
        self.assertEqual(parse_meal(RAW).instructions, "1\nHeat the oil.\n2\nAdd the eggs.")

    def test_dua_puluh_bahan(self):
        raw = {"strMeal": "Banyak", **{f"strIngredient{i}": f"b{i}" for i in range(1, 21)}}
        self.assertEqual(len(parse_meal(raw).ingredients), 20)

    def test_tanpa_bidang_opsional(self):
        meal = parse_meal({"strMeal": "Polos"})
        self.assertEqual((meal.ingredients, meal.instructions, meal.thumbnail, meal.youtube), ([], "", "", ""))

    def test_data_tidak_lengkap(self):
        for raw in ({}, {"strMeal": None}, None, "teks", []):
            with self.assertRaises(ValueError, msg=repr(raw)):
                parse_meal(raw)


class FormatTest(unittest.TestCase):
    def test_semua_bagian_tampil(self):
        text = format_meal(parse_meal(RAW))
        for expected in ("Yemeni Lahsa", "Breakfast · Saudi Arabian", "  - 5 Egg", "  - 2 tablespoons Olive Oil",
                         "  - Salt", "Instruksi:", "Heat the oil.", "https://img.test/meal.jpg", "watch?v=abc"):
            self.assertIn(expected, text)

    def test_tanpa_video(self):
        raw = {**RAW, "strYoutube": ""}
        self.assertNotIn("Video", format_meal(parse_meal(raw)))


class RandomMealTest(unittest.TestCase):
    def test_berhasil_dan_memanggil_endpoint_acak(self):
        opener = api()
        self.assertEqual(random_meal(opener).name, "Yemeni Lahsa")
        self.assertTrue(opener.requested[0].endswith("/random.php"))

    def test_jawaban_kosong(self):
        for payload in ({"meals": None}, {"meals": []}, {}, []):
            with self.assertRaises(ValueError, msg=str(payload)):
                random_meal(api(payload))

    def test_kesalahan_jaringan(self):
        with self.assertRaises(ValueError) as caught:
            random_meal(api(error=urllib.error.URLError("offline")))
        self.assertIn("koneksi", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            random_meal(api(error=urllib.error.HTTPError("u", 503, "x", {}, None)))
        self.assertIn("503", str(caught.exception))

    def test_bukan_json(self):
        def opener(request, timeout):
            return FakeResponse(b"<html>maaf</html>")
        with self.assertRaises(ValueError):
            random_meal(opener)


class ImageTest(unittest.TestCase):
    def test_unduh_dan_simpan(self):
        meal = parse_meal(RAW)
        with tempfile.TemporaryDirectory() as folder:
            path = save_picture(meal, folder, api())
            self.assertEqual(os.path.basename(path), "meal.jpg")
            with open(path, "rb") as file:
                self.assertEqual(file.read(), png_bytes())

    def test_bukan_gambar_ditolak(self):
        with self.assertRaises(ValueError) as caught:
            fetch_image("https://img.test/x", api(image=b"<html>", content_type="text/html"))
        self.assertIn("bukan gambar", str(caught.exception))

    def test_alamat_tidak_valid(self):
        for url in ("", "file:///etc/passwd", "ftp://x", "javascript:alert(1)"):
            with self.assertRaises(ValueError, msg=url):
                fetch_image(url, api())

    def test_terlalu_besar_dan_kosong(self):
        with self.assertRaises(ValueError):
            fetch_image("https://img.test/x", api(image=b"x" * 5_000_001))
        with self.assertRaises(ValueError):
            fetch_image("https://img.test/x", api(image=b""))

    def test_tidak_ditemukan(self):
        with self.assertRaises(ValueError) as caught:
            fetch_image("https://img.test/x", api(error=urllib.error.HTTPError("u", 404, "nf", {}, None)))
        self.assertIn("404", str(caught.exception))


class WindowTest(unittest.TestCase):
    def make_window(self, **kwargs):
        import tkinter as tk
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("tidak ada layar untuk Tkinter")
        self.addCleanup(root.destroy)
        return MealWindow(root, threaded=False, **kwargs)

    def test_tombol_menampilkan_resep_dan_klik_lagi_menggantinya(self):
        meals = iter([parse_meal(RAW), parse_meal({**RAW, "strMeal": "Resep Kedua", "strYoutube": ""})])
        window = self.make_window(get_meal=lambda: next(meals), get_image=lambda url: png_bytes())
        window.button.invoke()
        self.assertEqual(window.title_label.cget("text"), "Yemeni Lahsa")
        self.assertIn("5 Egg", window.text.get("1.0", "end"))
        self.assertIsNotNone(window.photo)
        self.assertTrue(window.video_button.winfo_manager())  # tombol video muncul
        window.button.invoke()
        self.assertEqual(window.title_label.cget("text"), "Resep Kedua")
        self.assertFalse(window.video_button.winfo_manager())  # tanpa video: tombol hilang

    def test_gagal_menampilkan_pesan_dan_tombol_aktif_lagi(self):
        def gagal():
            raise ValueError("offline")
        window = self.make_window(get_meal=gagal)
        window.button.invoke()
        self.assertIn("offline", window.status.cget("text"))
        self.assertEqual(str(window.button.cget("state")), "normal")

    def test_gambar_gagal_resep_tetap_tampil(self):
        def tanpa_gambar(url):
            raise ValueError("tidak ada")
        window = self.make_window(get_meal=lambda: parse_meal(RAW), get_image=tanpa_gambar)
        window.button.invoke()
        self.assertEqual(window.title_label.cget("text"), "Yemeni Lahsa")
        self.assertIsNone(window.photo)

    def test_tombol_video_membuka_url(self):
        opened = []
        window = self.make_window(get_meal=lambda: parse_meal(RAW), get_image=lambda u: png_bytes(), open_url=opened.append)
        window.button.invoke()
        window.video_button.invoke()
        self.assertEqual(opened, ["https://www.youtube.com/watch?v=abc"])


class CliTest(unittest.TestCase):
    def test_exit_code(self):
        self.assertEqual(main([], api()), 0)
        self.assertEqual(main([], api({"meals": None})), 1)
        self.assertEqual(main([], api(error=urllib.error.URLError("x"))), 1)


if __name__ == "__main__":
    unittest.main()
