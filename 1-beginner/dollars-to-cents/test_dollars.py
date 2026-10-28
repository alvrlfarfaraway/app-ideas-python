import unittest

from dollars import describe, dollars_to_cents, main, make_change


class DollarsToCentsTest(unittest.TestCase):
    def test_nilai_umum(self):
        self.assertEqual(dollars_to_cents("2.75"), 275)
        self.assertEqual(dollars_to_cents("0.58"), 58)
        self.assertEqual(dollars_to_cents("5"), 500)
        self.assertEqual(dollars_to_cents("0"), 0)
        self.assertEqual(dollars_to_cents(".5"), 50)

    def test_tanda_dolar_dan_spasi(self):
        self.assertEqual(dollars_to_cents("$2.75"), 275)
        self.assertEqual(dollars_to_cents("  $ 1.10 "), 110)

    def test_tidak_meleset_seperti_float(self):
        self.assertEqual(dollars_to_cents("1.15"), 115)  # float: 1.15*100 = 114.99999999999999
        self.assertEqual(dollars_to_cents("0.07"), 7)
        self.assertEqual(dollars_to_cents("4.35"), 435)

    def test_pembulatan_ke_sen_terdekat(self):
        self.assertEqual(dollars_to_cents("0.005"), 1)
        self.assertEqual(dollars_to_cents("0.004"), 0)
        self.assertEqual(dollars_to_cents("2.749"), 275)

    def test_input_salah(self):
        for text in ("", "   ", "$", "abc", "1,5", "-1", "nan", "inf", "1.2.3"):
            with self.assertRaises(ValueError, msg=text):
                dollars_to_cents(text)


class MakeChangeTest(unittest.TestCase):
    def test_contoh_spesifikasi(self):
        # 58 sen = 2 quarter + 1 nickel + 3 penny = 6 koin (spesifikasi menulis "4 koin", salah hitung)
        self.assertEqual(make_change(58), {"quarter": 2, "dime": 0, "nickel": 1, "penny": 3})

    def test_jumlah_koin_paling_sedikit(self):
        self.assertEqual(sum(make_change(30).values()), 2)  # quarter + nickel
        self.assertEqual(sum(make_change(99).values()), 9)  # 3q + 2d + 0n + 4p

    def test_nilai_koin_kembali_ke_total(self):
        values = {"quarter": 25, "dime": 10, "nickel": 5, "penny": 1}
        for cents in range(0, 500):
            change = make_change(cents)
            self.assertEqual(sum(values[name] * count for name, count in change.items()), cents)

    def test_nol(self):
        self.assertEqual(sum(make_change(0).values()), 0)


class CliTest(unittest.TestCase):
    def test_describe(self):
        self.assertEqual(describe("0.58"), "58 sen = 6 koin (2 quarter, 0 dime, 1 nickel, 3 penny)")

    def test_exit_code(self):
        self.assertEqual(main(["2.75"]), 0)
        self.assertEqual(main(["abc"]), 1)


if __name__ == "__main__":
    unittest.main()
