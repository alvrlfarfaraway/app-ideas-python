import unittest

from windchill import Calculator, describe, main, parse_value, wind_chill


class KnownValuesTest(unittest.TestCase):
    """Nilai acuan dari tabel resmi NWS / Environment Canada (dibulatkan ke bilangan bulat)."""

    def test_metrik(self):
        self.assertEqual(round(wind_chill(-20, 30, "metric")), -33)
        self.assertEqual(round(wind_chill(0, 20, "metric")), -5)

    def test_inggris(self):
        self.assertEqual(round(wind_chill(0, 15, "english")), -19)
        self.assertEqual(round(wind_chill(20, 40, "english")), -1)

    def test_dua_sistem_konsisten(self):
        # -10 °C = 14 °F dan 20 km/jam = 12.4274 mph; kedua rumus harus memberi suhu terasa yang sama (dalam 0.1 °C)
        celsius = wind_chill(-10, 20, "metric")
        fahrenheit = wind_chill(14, 20 / 1.609344, "english")
        self.assertAlmostEqual(celsius, (fahrenheit - 32) * 5 / 9, delta=0.1)

    def test_lebih_kencang_lebih_dingin(self):
        values = [wind_chill(-5, v, "metric") for v in (5, 10, 20, 40, 80)]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_lebih_dingin_lebih_dingin(self):
        values = [wind_chill(t, 25, "metric") for t in (10, 0, -10, -30)]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_hasil_selalu_lebih_rendah_dari_suhu_udara_di_seluruh_rentang_berlaku(self):
        for t in range(-60, 11):
            for v in (4.8, 5, 10, 30, 60, 120):
                self.assertLess(wind_chill(t, v, "metric"), t, (t, v))
        for t in range(-70, 51):
            for v in (3, 4, 10, 30, 60, 100):
                self.assertLess(wind_chill(t, v, "english"), t, (t, v))


class ValidityTest(unittest.TestCase):
    def test_di_luar_rentang_ditolak(self):
        with self.assertRaises(ValueError) as caught:
            wind_chill(15, 30, "metric")
        self.assertIn("suhu <= 10", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            wind_chill(-5, 3, "metric")
        self.assertIn("kecepatan angin >= 4.8", str(caught.exception))
        with self.assertRaises(ValueError):
            wind_chill(60, 20, "english")
        with self.assertRaises(ValueError):
            wind_chill(30, 2, "english")

    def test_batas_tepat_diterima(self):
        self.assertLess(wind_chill(10, 4.8, "metric"), 10)
        self.assertLess(wind_chill(50, 3, "english"), 50)

    def test_sistem_tidak_dikenal(self):
        with self.assertRaises(ValueError):
            wind_chill(0, 10, "kelvin")


class ParseTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(parse_value(" -12.5 ", "Suhu"), -12.5)

    def test_tidak_valid(self):
        for text in ("", "  ", "abc", "nan", "inf", "1,5"):
            with self.assertRaises(ValueError, msg=text):
                parse_value(text, "Suhu")

    def test_pesan_menyebut_isian(self):
        with self.assertRaises(ValueError) as caught:
            parse_value("", "Kecepatan angin")
        self.assertIn("Kecepatan angin belum diisi", str(caught.exception))


class CalculatorTest(unittest.TestCase):
    def test_hitung_ulang_tanpa_perubahan_diminta_nilai_baru(self):
        calc = Calculator()
        first = calc.calculate("-20", "30")
        with self.assertRaises(ValueError) as caught:
            calc.calculate("-20", "30")
        self.assertIn("sama dengan perhitungan sebelumnya", str(caught.exception))
        self.assertNotEqual(calc.calculate("-20", "31"), first)

    def test_data_belum_diisi(self):
        calc = Calculator()
        for temperature, speed in (("", "10"), ("-5", ""), ("", "")):
            with self.assertRaises(ValueError):
                calc.calculate(temperature, speed)

    def test_masukan_gagal_tidak_dianggap_perhitungan_sebelumnya(self):
        calc = Calculator()
        with self.assertRaises(ValueError):
            calc.calculate("30", "10")  # di luar rentang
        with self.assertRaises(ValueError) as caught:
            calc.calculate("30", "10")
        self.assertNotIn("sama dengan perhitungan sebelumnya", str(caught.exception))  # tetap pesan rentang

    def test_ganti_sistem_dihitung_baru(self):
        calc = Calculator()
        calc.calculate("0", "15", "metric")
        calc.calculate("0", "15", "english")  # angka sama, sistem berbeda -> bukan duplikat


class OutputTest(unittest.TestCase):
    def test_describe(self):
        text = describe(-20, 30, "metric", wind_chill(-20, 30, "metric"))
        self.assertEqual(text, "Suhu udara -20 °C, angin 30 km/jam  ->  terasa seperti -32.6 °C")

    def test_cli(self):
        self.assertEqual(main(["-20", "30"]), 0)
        self.assertEqual(main(["0", "15", "--system", "english"]), 0)
        self.assertEqual(main(["20", "30"]), 1)
        self.assertEqual(main(["abc", "30"]), 1)
        self.assertEqual(main(["-20"]), 1)  # kecepatan belum diisi


if __name__ == "__main__":
    unittest.main()
