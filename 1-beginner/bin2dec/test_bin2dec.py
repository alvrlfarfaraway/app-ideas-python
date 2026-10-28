import unittest

from bin2dec import bin_to_dec, main


class BinToDecTest(unittest.TestCase):
    def test_nilai_dasar(self):
        self.assertEqual(bin_to_dec("0"), 0)
        self.assertEqual(bin_to_dec("1"), 1)
        self.assertEqual(bin_to_dec("10"), 2)
        self.assertEqual(bin_to_dec("1010"), 10)

    def test_delapan_digit(self):
        self.assertEqual(bin_to_dec("11111111"), 255)
        self.assertEqual(bin_to_dec("10000000"), 128)

    def test_nol_di_depan(self):
        self.assertEqual(bin_to_dec("00000101"), 5)

    def test_spasi_di_pinggir_diabaikan(self):
        self.assertEqual(bin_to_dec("  101 "), 5)

    def test_kosong_ditolak(self):
        for text in ("", "   "):
            with self.assertRaises(ValueError):
                bin_to_dec(text)

    def test_karakter_selain_0_dan_1_ditolak(self):
        for text in ("102", "abc", "1 0", "-1", "1.0"):
            with self.assertRaises(ValueError, msg=text):
                bin_to_dec(text)

    def test_lebih_dari_delapan_digit_ditolak(self):
        with self.assertRaises(ValueError):
            bin_to_dec("111111111")

    def test_bonus_digit_variabel(self):
        self.assertEqual(bin_to_dec("111111111", max_digits=16), 511)
        self.assertEqual(bin_to_dec("1" * 16, max_digits=16), 65535)
        with self.assertRaises(ValueError):
            bin_to_dec("1" * 17, max_digits=16)


class CliTest(unittest.TestCase):
    def test_exit_code(self):
        self.assertEqual(main(["101"]), 0)
        self.assertEqual(main(["12"]), 1)
        self.assertEqual(main(["111111111", "-m", "9"]), 0)


if __name__ == "__main__":
    unittest.main()
