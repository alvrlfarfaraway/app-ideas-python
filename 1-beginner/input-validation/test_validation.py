import itertools
import random
import unittest

from validation import (PASSWORD, submit, validate_email, validate_form, validate_password,
                        validate_username)

VALID_PASSWORD = "ABCDE!@#$%^--"  # 5 kapital, 6 simbol (!@#$%^), 2 tanda hubung


class PasswordTest(unittest.TestCase):
    def test_valid(self):
        self.assertIsNone(validate_password(VALID_PASSWORD))

    def test_urutan_bebas(self):
        rng = random.Random(7)
        chars = list(VALID_PASSWORD)
        for _ in range(200):
            rng.shuffle(chars)
            shuffled = "".join(chars)
            self.assertIsNone(validate_password(shuffled), shuffled)

    def test_jumlah_salah(self):
        cases = {
            "ABCD!@#$%^--": "4 huruf kapital",      # kurang 1 kapital (12 karakter)
            "ABCDEF!@#$%^--": "6 huruf kapital",     # kelebihan kapital
            "ABCDE!@#$%---": "3 tanda hubung",       # kelebihan hubung
            "ABCDE!@#$%^-": "1 tanda hubung",        # kurang hubung
            "ABCDE!@#$%--": "5 simbol (harus 6)",    # simbol kurang (12 karakter)
        }
        for text, expected in cases.items():
            message = validate_password(text)
            self.assertIsNotNone(message, text)
            self.assertIn(expected, message, text)

    def test_pesan_menyebut_hitungan(self):
        message = validate_password("ABCD!@#$%^--")
        self.assertIn("4 huruf kapital (harus 5)", message)
        self.assertNotIn("simbol (harus", message)  # simbol sudah pas, tidak disebut

    def test_karakter_terlarang(self):
        for text in (VALID_PASSWORD + "a", "abcde!@#$%^--" + "1", VALID_PASSWORD[:-1] + " "):
            self.assertIsNotNone(validate_password(text), text)
        self.assertIn("karakter lain", validate_password("ABCDE!@#$%^--a"))

    def test_kosong(self):
        self.assertIsNotNone(validate_password(""))

    def test_semua_posisi_hubung_diterima(self):
        base = "ABCDE!@#$%^"
        for i, j in itertools.combinations(range(13), 2):
            chars = list(base)
            chars.insert(i, "-")
            chars.insert(j, "-")
            self.assertIsNotNone(PASSWORD.fullmatch("".join(chars)), "".join(chars))

    def test_setiap_simbol_diterima_sebagai_simbol(self):
        for symbol in "!@#$%^&*()_+=[]{};:'\",.<>/?\\|`~":
            text = "ABCDE" + symbol * 6 + "--"
            self.assertIsNone(validate_password(text), text)
        for not_symbol in "abc123 ":
            self.assertIsNotNone(validate_password("ABCDE" + not_symbol * 6 + "--"), not_symbol)


class UsernameTest(unittest.TestCase):
    def test_valid(self):
        for text in ("budi", "BudiSantoso", "Zoë", "a"):
            self.assertIsNone(validate_username(text), text)

    def test_tidak_valid(self):
        for text in ("budi santoso", "budi1", "budi_s", "budi-s", "", " ", "budi\n"):
            self.assertIsNotNone(validate_username(text), repr(text))

    def test_pesan_spesifik(self):
        self.assertIn("spasi", validate_username("a b"))
        self.assertIn("huruf", validate_username("a1"))
        self.assertIn("kosong", validate_username(""))


class EmailTest(unittest.TestCase):
    def test_valid(self):
        for text in ("budi@gmail.com", "budi.santoso@gmail.com", "budi+tag@gmail.com", "B99@GMAIL.COM"):
            self.assertIsNone(validate_email(text), text)

    def test_bukan_gmail(self):
        for text in ("budi@yahoo.com", "budi@gmail.co", "budi@gmail.com.evil.com", "budi@notgmail.com", "budi@@gmail.com"):
            self.assertIsNotNone(validate_email(text), text)
        self.assertIn("Gmail", validate_email("budi@yahoo.com"))

    def test_bagian_lokal_tidak_valid(self):
        for text in ("@gmail.com", ".budi@gmail.com", "budi.@gmail.com", "bu..di@gmail.com", "bu di@gmail.com"):
            self.assertIsNotNone(validate_email(text), text)

    def test_kosong(self):
        self.assertIn("kosong", validate_email(""))


class FormTest(unittest.TestCase):
    GOOD = {"password": VALID_PASSWORD, "username": "budi", "email": "budi@gmail.com"}

    def test_formulir_valid(self):
        self.assertEqual(validate_form(self.GOOD), {})
        self.assertEqual(submit(self.GOOD), self.GOOD)

    def test_submit_ditolak_bila_satu_saja_salah(self):
        for field, bad in (("password", "x"), ("username", "b udi"), ("email", "b@yahoo.com")):
            values = {**self.GOOD, field: bad}
            with self.assertRaises(ValueError) as caught:
                submit(values)
            self.assertEqual(list(caught.exception.errors), [field])

    def test_semua_kesalahan_dilaporkan_sekaligus(self):
        with self.assertRaises(ValueError) as caught:
            submit({"password": "", "username": "", "email": ""})
        self.assertEqual(set(caught.exception.errors), {"password", "username", "email"})

    def test_isian_hilang_dianggap_kosong(self):
        self.assertEqual(set(validate_form({})), {"password", "username", "email"})


if __name__ == "__main__":
    unittest.main()
