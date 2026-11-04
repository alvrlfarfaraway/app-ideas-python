import contextlib
import io
import unittest

import emoji_translator
from emoji_translator import EMOJI_TABLE, LEXICONS, Translator, build_lexicon, lookup, main, tokenize, translate


class LexiconTest(unittest.TestCase):
    def test_setiap_baris_punya_kata_di_dua_bahasa(self):
        for emoji, words_id, words_en in EMOJI_TABLE:
            self.assertTrue(words_id.strip(), emoji)
            self.assertTrue(words_en.strip(), emoji)

    def test_tidak_ada_kata_yang_menunjuk_dua_emoji(self):
        for column, language in ((1, "id"), (2, "en")):
            seen = {}
            for row in EMOJI_TABLE:
                for word in row[column].split(","):
                    key = " ".join(word.lower().split())
                    self.assertNotIn(key, seen, f"{language}: '{key}' dipakai {seen.get(key)} dan {row[0]}")
                    seen[key] = row[0]

    def test_ukuran_kamus(self):
        self.assertGreater(len(LEXICONS["id"]), 250)
        self.assertGreater(len(LEXICONS["en"]), 250)

    def test_bahasa_tidak_dikenal(self):
        with self.assertRaises(ValueError):
            build_lexicon("fr")
        with self.assertRaises(ValueError):
            translate("halo", "fr")


class TokenizeTest(unittest.TestCase):
    def test_kata_dan_bukan_kata_bergantian(self):
        self.assertEqual(tokenize("Halo, kupu-kupu!"), ["Halo", ", ", "kupu-kupu", "!"])
        self.assertEqual("".join(tokenize("a  b\n\tc...")), "a  b\n\tc...")
        self.assertEqual(tokenize("snake_case"), ["snake", "_", "case"])


class TranslateTest(unittest.TestCase):
    def test_kata_biasa_dan_tanda_baca_tetap(self):
        self.assertEqual(translate("Saya suka kucing dan kopi!"), "Saya ❤️ 🐱 dan ☕!")

    def test_huruf_besar_kecil(self):
        self.assertEqual(translate("KUCING Kucing kucing"), "🐱 🐱 🐱")

    def test_sinonim(self):
        for word in ("kucing", "meong", "kitten"):
            self.assertEqual(translate(word), "🐱")
        for word in ("ngakak", "tertawa", "ketawa"):
            self.assertEqual(translate(word), "😂")
        self.assertEqual(translate("kitty", "en"), "🐱")

    def test_frasa_lebih_dulu(self):
        self.assertEqual(translate("ke rumah sakit"), "ke 🏥")
        self.assertEqual(translate("ke rumah"), "ke 🏠")
        self.assertEqual(translate("naik kereta api"), "naik 🚆")
        self.assertEqual(translate("makan es krim"), "🍽️ 🍦")
        self.assertEqual(translate("anak laki-laki"), "👦")
        self.assertEqual(translate("terima kasih, guru!"), "🙏, 🧑‍🏫!")
        self.assertEqual(translate("hot dog", "en"), "🌭")
        self.assertEqual(translate("hot dogs", "en"), "🌭")
        self.assertEqual(translate("it is hot", "en"), "it is ☀️")

    def test_frasa_terpotong_tanda_baca_tidak_digabung(self):
        self.assertEqual(translate("rumah, sakit"), "🏠, 🤒")

    def test_jamak_dan_akhiran(self):
        self.assertEqual(translate("kucing-kucing"), "🐱🐱")
        self.assertEqual(translate("rumahnya bukuku"), "🏠nya 📚ku")
        self.assertEqual(translate("kamu"), "kamu")  # bukan 'ka' + 'mu'
        self.assertEqual(translate("cats and boxes", "en"), "🐱 and boxes")
        self.assertEqual(translate("bus yes", "en"), "🚌 👍")

    def test_angka(self):
        self.assertEqual(translate("jam 7"), "⏰ 7️⃣")
        self.assertEqual(translate("2026"), "2️⃣0️⃣2️⃣6️⃣")
        self.assertEqual(translate("abc123"), "abc123")
        self.assertEqual(translate("٣"), "٣")  # angka non-ASCII tidak diubah

    def test_kata_tanpa_emoji_tidak_berubah(self):
        text = "Pemrograman berorientasi objek."
        self.assertEqual(translate(text), text)
        self.assertEqual(translate(""), "")

    def test_bahasa_menentukan_kamus(self):
        self.assertEqual(translate("cat", "id"), "cat")
        self.assertEqual(translate("cat", "en"), "🐱")
        self.assertEqual(translate("kucing", "en"), "kucing")

    def test_lookup(self):
        self.assertEqual(lookup("Pizza", "id"), "🍕")
        self.assertIsNone(lookup("xyz", "en"))


class TranslatorLogicTest(unittest.TestCase):
    def test_peringatan_kosong_dan_tidak_berubah(self):
        t = Translator()
        self.assertEqual(t.translate("   ", "id"), (None, "Kotak teks masih kosong. Tulis kalimat dulu."))
        self.assertEqual(t.translate("kucing", "id"), ("🐱", None))
        result, warning = t.translate("kucing", "id")
        self.assertIsNone(result)
        self.assertIn("belum berubah", warning)
        self.assertEqual(t.translate("cat", "en")[0], "cat".replace("cat", "🐱"))
        self.assertEqual(t.translate("cat", "id"), ("cat", None))  # ganti bahasa dihitung perubahan

    def test_clear_mengizinkan_terjemahan_ulang(self):
        t = Translator()
        t.translate("kucing", "id")
        t.clear()
        self.assertEqual(t.translate("kucing", "id"), ("🐱", None))


class CliTest(unittest.TestCase):
    def test_terminal(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["i", "love", "pizza", "--lang", "en"]), 0)
        self.assertEqual(out.getvalue().strip(), "i ❤️ 🍕")

    def test_tanpa_teks_membuka_jendela(self):
        opened = []
        self.assertEqual(main([], gui=lambda: opened.append(True)), 0)
        self.assertEqual(opened, [True])


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.root.bell = lambda: None
        self.app = emoji_translator.TranslatorApp(self.root)

    def tearDown(self):
        self.root.destroy()

    def output(self):
        return self.app.output.get("1.0", "end-1c")

    def test_alur_tombol(self):
        self.app.on_translate()
        self.assertIn("kosong", self.app.warning.get())
        self.app.input.insert("1.0", "saya suka kopi")
        self.app.on_translate()
        self.assertEqual(self.output(), "saya ❤️ ☕")
        self.assertEqual(self.app.warning.get(), "")
        self.app.on_translate()
        self.assertIn("belum berubah", self.app.warning.get())
        self.assertEqual(self.output(), "saya ❤️ ☕")
        self.app.on_clear()
        self.assertEqual(self.app.input.get("1.0", "end-1c"), "")
        self.assertEqual(self.output(), "")
        self.assertEqual(self.app.warning.get(), "")

    def test_pilihan_bahasa(self):
        self.app.language.set("English")
        self.app.input.insert("1.0", "i love cats")
        self.app.on_translate()
        self.assertEqual(self.output(), "i ❤️ 🐱")


if __name__ == "__main__":
    unittest.main()
