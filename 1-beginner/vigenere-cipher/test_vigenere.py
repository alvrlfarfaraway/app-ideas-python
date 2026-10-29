import os
import tempfile
import unittest

from vigenere import (Panel, crack, decrypt, encrypt, guess_key_length, index_of_coincidence, main,
                      validate_key)

ENGLISH = (
    "It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of foolishness, "
    "it was the epoch of belief, it was the epoch of incredulity, it was the season of Light, it was the season of "
    "Darkness, it was the spring of hope, it was the winter of despair, we had everything before us, we had nothing "
    "before us, we were all going direct to Heaven, we were all going direct the other way. In short, the period was "
    "so far like the present period, that some of its noisiest authorities insisted on its being received, for good "
    "or for evil, in the superlative degree of comparison only. There were a king with a large jaw and a queen with "
    "a plain face, on the throne of England; there were a king with a large jaw and a queen with a fair face, on the "
    "throne of France. In both countries it was clearer than crystal to the lords of the State preserves of loaves "
    "and fishes, that things in general were settled for ever."
)


class KnownVectorsTest(unittest.TestCase):
    def test_contoh_wikipedia(self):
        self.assertEqual(encrypt("ATTACKATDAWN", "LEMON"), "LXFOPVEFRNHR")
        self.assertEqual(decrypt("LXFOPVEFRNHR", "LEMON"), "ATTACKATDAWN")

    def test_kunci_a_tidak_mengubah_apa_pun(self):
        self.assertEqual(encrypt("Halo Dunia", "A"), "Halo Dunia")

    def test_kunci_satu_huruf_adalah_sandi_caesar(self):
        self.assertEqual(encrypt("abc xyz", "B"), "bcd yza")


class FormattingTest(unittest.TestCase):
    def test_huruf_besar_kecil_dipertahankan(self):
        self.assertEqual(encrypt("Attack at Dawn", "LEMON"), "Lxfopv ef Rnhr")

    def test_bukan_huruf_tidak_berubah_dan_tidak_memajukan_kunci(self):
        # spasi/angka/tanda baca dilewati; kunci hanya maju pada huruf, jadi hasilnya sama dengan teks tanpa itu
        plain = "Attack, at dawn! 2026"
        letters_only = "Attackatdawn"
        enc = encrypt(plain, "LEMON")
        self.assertEqual("".join(c for c in enc if c.isalpha()), encrypt(letters_only, "LEMON"))
        self.assertEqual(enc[-5:], " 2026")

    def test_huruf_beraksen_dan_non_latin_dilewati(self):
        self.assertEqual(encrypt("é日本", "KEY"), "é日本")
        self.assertEqual(decrypt(encrypt("Café au lait", "KEY"), "KEY"), "Café au lait")

    def test_kunci_tidak_membedakan_besar_kecil(self):
        self.assertEqual(encrypt("hello", "lemon"), encrypt("hello", "LEMON"))


class RoundTripTest(unittest.TestCase):
    def test_bolak_balik(self):
        for key in ("A", "KEY", "LEMON", "ThisIsALongerKeyThanTheText"):
            self.assertEqual(decrypt(encrypt(ENGLISH, key), key), ENGLISH)

    def test_kunci_salah_tidak_mengembalikan_pesan(self):
        self.assertNotEqual(decrypt(encrypt("Attack at dawn", "LEMON"), "LEMOO"), "Attack at dawn")


class KeyTest(unittest.TestCase):
    def test_kunci_tidak_valid(self):
        for key in ("", "   ", "AB1", "A B", "KÉY", "key!"):
            with self.assertRaises(ValueError, msg=repr(key)):
                encrypt("teks", key)

    def test_kunci_valid_dirapikan(self):
        self.assertEqual(validate_key(" lemon "), "LEMON")


class AnalysisTest(unittest.TestCase):
    def test_ic_membedakan_bahasa_dari_acak(self):
        self.assertGreater(index_of_coincidence(ENGLISH), 0.06)  # teks Inggris biasa
        self.assertLess(index_of_coincidence(encrypt(ENGLISH, "LEMONADE")), 0.05)  # sandi: mendekati acak

    def test_ic_butuh_dua_huruf(self):
        with self.assertRaises(ValueError):
            index_of_coincidence("a")

    def test_menebak_panjang_kunci(self):
        for key in ("KEY", "LEMON", "CRYPTO"):
            self.assertEqual(guess_key_length(encrypt(ENGLISH, key)), len(key), key)

    def test_mematahkan_sandi(self):
        for key in ("KEY", "LEMON", "CRYPTO"):
            found, plain = crack(encrypt(ENGLISH, key))
            self.assertEqual(found, key)
            self.assertEqual(plain, ENGLISH)

    def test_teks_terlalu_pendek(self):
        with self.assertRaises(ValueError):
            crack(encrypt("Attack at dawn", "LEMON"))


class PanelTest(unittest.TestCase):
    def test_decrypt_nonaktif_sampai_ada_enkripsi(self):
        panel = Panel()
        self.assertFalse(panel.decrypt_enabled)
        with self.assertRaises(ValueError):
            panel.decrypt()
        panel.encrypt("Attack at dawn", "LEMON")
        self.assertTrue(panel.decrypt_enabled)

    def test_alur_enkripsi_dekripsi_bandingkan(self):
        panel = Panel()
        self.assertEqual(panel.encrypt("Attack at dawn", "LEMON"), "Lxfopv ef rnhr")
        self.assertEqual(panel.result, "Lxfopv ef rnhr")  # kolom hasil menampilkan teks sandi
        self.assertEqual(panel.decrypt(), "Attack at dawn")
        self.assertTrue(panel.compare())

    def test_compare_nonaktif_sebelum_dekripsi(self):
        panel = Panel()
        panel.encrypt("halo", "KEY")
        with self.assertRaises(ValueError):
            panel.compare()

    def test_compare_melaporkan_perbedaan(self):
        panel = Panel()
        panel.encrypt("halo", "KEY")
        panel.decrypt()
        panel.plaintext = "halo!"  # simulasi pesan asli berubah / rusak
        with self.assertRaises(ValueError) as caught:
            panel.compare()
        self.assertIn("Berbeda", str(caught.exception))

    def test_pesan_atau_kunci_salah(self):
        panel = Panel()
        with self.assertRaises(ValueError):
            panel.encrypt("   ", "KEY")
        with self.assertRaises(ValueError):
            panel.encrypt("halo", "")
        self.assertFalse(panel.decrypt_enabled)


class CliTest(unittest.TestCase):
    def test_perintah(self):
        self.assertEqual(main(["encrypt", "halo", "KEY"]), 0)
        self.assertEqual(main(["decrypt", "rewy", "KEY"]), 0)
        self.assertEqual(main(["encrypt", "halo", "K3Y"]), 1)

    def test_crack_dari_berkas(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "sandi.txt")
            with open(path, "w", encoding="utf-8") as file:
                file.write(encrypt(ENGLISH, "LEMON"))
            self.assertEqual(main(["crack", path]), 0)
            self.assertEqual(main(["crack", os.path.join(folder, "tidak-ada.txt")]), 1)


if __name__ == "__main__":
    unittest.main()
