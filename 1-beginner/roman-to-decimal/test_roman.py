import unittest

from roman import MAX_VALUE, convert, decimal_to_roman, main, roman_to_decimal


class RomanToDecimalTest(unittest.TestCase):
    def test_contoh_umum(self):
        cases = {"I": 1, "IV": 4, "IX": 9, "XIV": 14, "XL": 40, "XC": 90, "CD": 400, "CM": 900,
                 "MCMXCIV": 1994, "MMXXVI": 2026, "MMMCMXCIX": 3999, "MDCLXVI": 1666, "III": 3, "VIII": 8}
        for text, value in cases.items():
            self.assertEqual(roman_to_decimal(text), value, text)

    def test_huruf_kecil_dan_spasi(self):
        self.assertEqual(roman_to_decimal("  xiv "), 14)

    def test_simbol_salah_menyebut_posisi(self):
        with self.assertRaises(ValueError) as caught:
            roman_to_decimal("XIA")
        self.assertIn("'A' di posisi 3", str(caught.exception))
        for text in ("Z", "12", "X I", "X-V", "IV!"):
            with self.assertRaises(ValueError, msg=text):
                roman_to_decimal(text)

    def test_kosong(self):
        for text in ("", "   "):
            with self.assertRaises(ValueError):
                roman_to_decimal(text)

    def test_susunan_tidak_baku_ditolak_dengan_saran(self):
        suggestions = {"IIII": "IV", "VX": "V", "IC": "XCIX", "XXXX": "XL", "VV": "X", "IXI": "X", "MMMM": ""}
        for text, suggestion in suggestions.items():
            with self.assertRaises(ValueError, msg=text) as caught:
                roman_to_decimal(text)
            self.assertIn("baku", str(caught.exception))
        for text, hint in (("IIII", "Maksudmu IV?"), ("IC", "Maksudmu XCIX?"), ("XXXX", "Maksudmu XL?")):
            with self.assertRaises(ValueError) as caught:
                roman_to_decimal(text)
            self.assertIn(hint, str(caught.exception))
        for text in ("VX", "LC", "DM", "MMMM"):  # tidak ada saran yang masuk akal
            with self.assertRaises(ValueError) as caught:
                roman_to_decimal(text)
            self.assertNotIn("Maksudmu", str(caught.exception), text)

    def test_lebih_dari_3999_ditolak(self):
        with self.assertRaises(ValueError):
            roman_to_decimal("MMMMM")


class DecimalToRomanTest(unittest.TestCase):
    def test_contoh(self):
        for value, text in {1: "I", 4: "IV", 9: "IX", 14: "XIV", 49: "XLIX", 1994: "MCMXCIV", 2026: "MMXXVI",
                            3999: "MMMCMXCIX", 444: "CDXLIV"}.items():
            self.assertEqual(decimal_to_roman(value), text)

    def test_di_luar_rentang(self):
        for value in (0, -1, MAX_VALUE + 1):
            with self.assertRaises(ValueError, msg=str(value)):
                decimal_to_roman(value)

    def test_bukan_bilangan_bulat(self):
        for value in (1.5, "5", None, True):
            with self.assertRaises(ValueError, msg=repr(value)):
                decimal_to_roman(value)

    def test_bolak_balik_untuk_semua_nilai(self):
        for value in range(1, MAX_VALUE + 1):
            self.assertEqual(roman_to_decimal(decimal_to_roman(value)), value)


class ConvertTest(unittest.TestCase):
    def test_arah_dikenali_otomatis(self):
        self.assertEqual(convert("XIV"), "14")
        self.assertEqual(convert("14"), "XIV")
        self.assertEqual(convert(" mcmxciv "), "1994")

    def test_kesalahan(self):
        for text in ("0", "4000", "-5", "+5", "abc", ""):
            with self.assertRaises(ValueError, msg=text):
                convert(text)

    def test_cli(self):
        self.assertEqual(main(["XIV"]), 0)
        self.assertEqual(main(["IIII"]), 1)
        self.assertEqual(main(["5000"]), 1)


if __name__ == "__main__":
    unittest.main()
