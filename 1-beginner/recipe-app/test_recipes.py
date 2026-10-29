import copy
import io
import json
import os
import tempfile
import unittest
import urllib.error

from recipes import (DIFFICULTIES, MEAL_TYPES, SAMPLE_FILE, App, RecipeBook, format_card, interactive, list_text,
                     meal_to_recipe, search_meals, split_steps, validate_recipe)

RAW_MEAL = {
    "idMeal": "1", "strMeal": "Chicken Handi", "strCategory": "Chicken", "strArea": "Indian",
    "strInstructions": "Take a large pot.\r\n\r\nAdd the chicken. Stir well.\r\nServe hot.",
    "strMealThumb": "https://img.test/handi.jpg",
    "strIngredient1": "Chicken", "strMeasure1": "1.2 kg", "strIngredient2": "Onion", "strMeasure2": " 5 thinly sliced ",
    "strIngredient3": "Salt", "strMeasure3": "", "strIngredient4": "", "strIngredient5": None,
}
GOOD = {"title": "Tes Resep", "meal_type": "lunch", "serves": 2, "difficulty": "beginner",
        "ingredients": [{"item": "air", "amount": "1 gelas"}], "steps": ["Minum."]}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fake_api(meals=(RAW_MEAL,), error=None, payload=None):
    calls = []

    def opener(request, timeout):
        calls.append(request.full_url)
        if error:
            raise error
        return FakeResponse(json.dumps(payload if payload is not None else {"meals": list(meals) if meals else None}).encode())

    opener.calls = calls
    return opener


class SampleDataTest(unittest.TestCase):
    def setUp(self):
        with open(SAMPLE_FILE, encoding="utf-8") as file:
            self.recipes = json.load(file)

    def test_semua_resep_bawaan_valid_dan_lengkap(self):
        self.assertGreaterEqual(len(self.recipes), 6)
        for recipe in self.recipes:
            validate_recipe(recipe)
            self.assertIsNotNone(recipe["serves"])
            self.assertIsNotNone(recipe["difficulty"])

    def test_judul_unik_dan_mencakup_semua_jenis_dan_tingkat(self):
        titles = [r["title"].lower() for r in self.recipes]
        self.assertEqual(len(titles), len(set(titles)))
        self.assertEqual({r["meal_type"] for r in self.recipes}, set(MEAL_TYPES))
        self.assertEqual({r["difficulty"] for r in self.recipes}, set(DIFFICULTIES))


class ValidateTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_recipe(copy.deepcopy(GOOD)), GOOD)
        validate_recipe({**GOOD, "serves": None, "difficulty": None})  # dari API: boleh kosong

    def test_tidak_valid(self):
        bad = [None, [], {}, {**GOOD, "title": " "}, {**GOOD, "meal_type": "dinner"}, {**GOOD, "serves": 0},
               {**GOOD, "serves": "2"}, {**GOOD, "serves": True}, {**GOOD, "difficulty": "expert"},
               {**GOOD, "ingredients": []}, {**GOOD, "ingredients": ["air"]}, {**GOOD, "ingredients": [{"item": " "}]},
               {**GOOD, "steps": []}, {**GOOD, "steps": ["", "x"]}, {**GOOD, "photo": 5}]
        for recipe in bad:
            with self.assertRaises(ValueError, msg=str(recipe)):
                validate_recipe(recipe)


class CardTest(unittest.TestCase):
    def test_semua_bagian_ada(self):
        recipe = {**GOOD, "photo": "https://x/y.jpg", "ingredients": [{"item": "telur", "amount": "2 butir"}, {"item": "garam", "amount": ""}]}
        card = format_card(recipe)
        for expected in ("TES RESEP", "makan siang (lunch)", "2 orang", "pemula", "  - 2 butir telur", "  - garam",
                         "  1. Minum.", "https://x/y.jpg"):
            self.assertIn(expected, card)

    def test_porsi_dan_kesulitan_tidak_diketahui(self):
        card = format_card({**GOOD, "serves": None, "difficulty": None})
        self.assertEqual(card.count("tidak diketahui"), 2)


class BookTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "buku", "recipes.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_pertama_kali_disalin_dari_resep_bawaan(self):
        book = RecipeBook(self.path)
        self.assertTrue(os.path.exists(self.path))
        self.assertGreaterEqual(len(book.titles()), 6)

    def test_cari_menurut_nomor_judul_dan_potongan(self):
        book = RecipeBook(self.path)
        self.assertEqual(book.find("1")["title"], book.titles()[0])
        self.assertEqual(book.find("soto ayam")["title"], "Soto Ayam")
        self.assertEqual(book.find("rendang")["title"], "Rendang Daging")  # potongan yang unik

    def test_pencarian_gagal(self):
        book = RecipeBook(self.path)
        for query in ("0", "99", "", "tidak ada"):
            with self.assertRaises(ValueError, msg=query):
                book.find(query)

    def test_potongan_ambigu_ditolak(self):
        book = RecipeBook(self.path)
        with self.assertRaises(ValueError) as caught:
            book.find("a")  # cocok dengan banyak judul
        self.assertIn("cocok dengan", str(caught.exception))

    def test_tambah_dan_persisten(self):
        book = RecipeBook(self.path)
        count = len(book.titles())
        book.add(copy.deepcopy(GOOD))
        self.assertEqual(len(RecipeBook(self.path).titles()), count + 1)

    def test_judul_ganda_ditolak_tanpa_peduli_besar_kecil(self):
        book = RecipeBook(self.path)
        with self.assertRaises(ValueError):
            book.add({**GOOD, "title": "SOTO ayam"})

    def test_berkas_rusak_tidak_ditimpa(self):
        RecipeBook(self.path)
        with open(self.path, "w", encoding="utf-8") as file:
            file.write("{rusak")
        with self.assertRaises(ValueError):
            RecipeBook(self.path)
        with open(self.path, encoding="utf-8") as file:
            self.assertEqual(file.read(), "{rusak")

    def test_resep_tidak_valid_di_berkas_ditolak(self):
        RecipeBook(self.path)
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump([{"title": "Rusak"}], file)
        with self.assertRaises(ValueError):
            RecipeBook(self.path)


class ApiTest(unittest.TestCase):
    def test_split_steps(self):
        self.assertEqual(split_steps("Take a pot.\r\n\r\nAdd chicken. Stir well.\r\nServe hot."),
                         ["Take a pot.", "Add chicken. Stir well.", "Serve hot."])
        self.assertEqual(split_steps("1\r\nHeat oil.\r\n2\r\nAdd eggs."), ["Heat oil.", "Add eggs."])
        self.assertEqual(split_steps("STEP 1\nChop.\nSTEP 2\nFry."), ["Chop.", "Fry."])
        self.assertEqual(split_steps("1. Heat oil.\n2. Add eggs."), ["Heat oil.", "Add eggs."])
        self.assertEqual(split_steps("Heat the oil. Add the eggs. Serve."), ["Heat the oil.", "Add the eggs.", "Serve."])

    def test_meal_to_recipe(self):
        recipe = meal_to_recipe(RAW_MEAL)
        self.assertEqual(recipe["title"], "Chicken Handi")
        self.assertEqual(recipe["ingredients"], [{"item": "Chicken", "amount": "1.2 kg"},
                                                 {"item": "Onion", "amount": "5 thinly sliced"},
                                                 {"item": "Salt", "amount": ""}])
        self.assertEqual(recipe["meal_type"], "lunch")
        self.assertIsNone(recipe["serves"])
        self.assertIsNone(recipe["difficulty"])
        self.assertEqual(recipe["photo"], "https://img.test/handi.jpg")
        self.assertIn("Chicken", recipe["source"])

    def test_pemetaan_kategori_ke_jenis_hidangan(self):
        for category, expected in (("Breakfast", "breakfast"), ("Dessert", "snack"), ("Starter", "snack"),
                                   ("Side", "snack"), ("Beef", "lunch"), ("", "lunch")):
            self.assertEqual(meal_to_recipe({**RAW_MEAL, "strCategory": category})["meal_type"], expected)

    def test_data_tidak_lengkap(self):
        for raw in ({}, {"strMeal": "Tanpa bahan"}, {"strMeal": "X", "strIngredient1": "a"}, None):
            with self.assertRaises(ValueError, msg=str(raw)):
                meal_to_recipe(raw)

    def test_cari_berhasil_dan_nama_di_encode(self):
        api = fake_api()
        results = search_meals("chicken & rice", api)
        self.assertEqual(results[0]["title"], "Chicken Handi")
        self.assertIn("s=chicken+%26+rice", api.calls[0])

    def test_tidak_ada_yang_cocok_memberi_peringatan(self):
        for opener in (fake_api(meals=None), fake_api(payload={"meals": []}), fake_api(payload=[])):
            with self.assertRaises(ValueError) as caught:
                search_meals("zzzz", opener)
            self.assertIn("Tidak ada resep yang cocok", str(caught.exception))

    def test_data_rusak_dilewati_sisanya_tampil(self):
        results = search_meals("x", fake_api(meals=({"strMeal": "Rusak"}, RAW_MEAL)))
        self.assertEqual([r["title"] for r in results], ["Chicken Handi"])
        with self.assertRaises(ValueError):
            search_meals("x", fake_api(meals=({"strMeal": "Rusak"},)))

    def test_masukan_kosong_dan_jaringan(self):
        with self.assertRaises(ValueError):
            search_meals("   ", fake_api())
        with self.assertRaises(ValueError) as caught:
            search_meals("x", fake_api(error=urllib.error.URLError("offline")))
        self.assertIn("koneksi", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            search_meals("x", fake_api(error=urllib.error.HTTPError("u", 503, "x", {}, None)))
        self.assertIn("503", str(caught.exception))


class AppTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.book = RecipeBook(os.path.join(self.dir.name, "r.json"))
        self.opened = []
        self.app = App(self.book, fake_api(meals=(RAW_MEAL, {**RAW_MEAL, "strMeal": "Chicken Mandi"})), self.opened.append)

    def tearDown(self):
        self.dir.cleanup()

    def test_klik_judul_baru_mengganti_kartu(self):
        first = self.app.show("1")
        second = self.app.show("2")
        self.assertNotEqual(first, second)
        self.assertEqual(self.app.card["title"], self.book.titles()[1])
        self.assertIn(self.book.titles()[1].upper(), second)

    def test_alur_cari_buka_simpan(self):
        listing = self.app.search("chicken")
        self.assertIn("1. Chicken Handi", listing)
        self.assertIn("2. Chicken Mandi", listing)
        card = self.app.open_result("1")
        self.assertIn("CHICKEN HANDI", card)
        self.assertTrue(self.app.save_enabled)
        self.assertEqual(self.app.save(), "Tersimpan: Chicken Handi")
        self.assertIn("Chicken Handi", RecipeBook(self.book.path).titles())
        self.assertFalse(self.app.save_enabled)

    def test_save_hanya_untuk_resep_hasil_api(self):
        self.app.show("1")
        self.assertFalse(self.app.save_enabled)
        with self.assertRaises(ValueError):
            self.app.save()

    def test_simpan_dua_kali_ditolak(self):
        self.app.search("chicken")
        self.app.open_result("1")
        self.app.save()
        self.app.open_result("1")
        self.assertFalse(self.app.save_enabled)  # sudah ada di buku
        with self.assertRaises(ValueError):
            self.app.save()

    def test_open_tanpa_pencarian_atau_nomor_salah(self):
        with self.assertRaises(ValueError):
            self.app.open_result("1")
        self.app.search("chicken")
        for number in ("0", "3", "x", ""):
            with self.assertRaises(ValueError, msg=number):
                self.app.open_result(number)

    def test_foto(self):
        with self.assertRaises(ValueError):
            self.app.photo()  # belum ada kartu
        self.app.show("1")
        with self.assertRaises(ValueError):
            self.app.photo()  # resep bawaan tidak punya foto
        self.app.search("chicken")
        self.app.open_result("1")
        self.app.photo()
        self.assertEqual(self.opened, ["https://img.test/handi.jpg"])

    def test_tidak_ditemukan_menjaga_kartu_lama(self):
        self.app.show("1")
        with self.assertRaises(ValueError):
            self.app.show("tidak ada")
        self.assertEqual(self.app.card["title"], self.book.titles()[0])


class InteractiveTest(unittest.TestCase):
    def test_sesi_penuh(self):
        with tempfile.TemporaryDirectory() as folder:
            app = App(RecipeBook(os.path.join(folder, "r.json")), fake_api())
            commands = iter(["list", "show 1", "search chicken", "open 1", "save", "show nasi", "show zzz", "bogus", "quit"])
            import builtins
            import contextlib
            original = builtins.input
            builtins.input = lambda prompt="": next(commands)
            buffer = io.StringIO()
            try:
                with contextlib.redirect_stdout(buffer):
                    self.assertEqual(interactive(app), 0)
            finally:
                builtins.input = original
            output = buffer.getvalue()
            self.assertIn("Daftar resep:", output)
            self.assertIn("NASI GORENG SEDERHANA", output)
            self.assertIn("Tersimpan: Chicken Handi", output)
            self.assertIn("Peringatan: Resep 'zzz' tidak ada di daftar.", output)
            self.assertIn("Perintah tidak dikenal.", output)
            self.assertIn("Chicken Handi", list_text(app.book))


if __name__ == "__main__":
    unittest.main()
