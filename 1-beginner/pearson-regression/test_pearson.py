import math
import os
import random
import tempfile
import unittest

from pearson import (Observations, interpret, linear_regression, load_csv, main, mean, parse_number,
                     pearson_r, std_dev, summarize)

try:
    import numpy as np
except ImportError:  # pembanding opsional
    np = None

X = [10, 8, 13, 9, 11, 14, 6, 4, 12, 7, 5]
ANSCOMBE = [
    [8.04, 6.95, 7.58, 8.81, 8.33, 9.96, 7.24, 4.26, 10.84, 4.82, 5.68],
    [9.14, 8.14, 8.74, 8.77, 9.26, 8.10, 6.13, 3.10, 9.13, 7.26, 4.74],
    [7.46, 6.77, 12.74, 7.11, 7.81, 8.84, 6.08, 5.39, 8.15, 6.42, 5.73],
]
X4 = [8, 8, 8, 8, 8, 8, 8, 19, 8, 8, 8]
Y4 = [6.58, 5.76, 7.71, 8.84, 8.47, 7.04, 5.25, 12.50, 5.56, 7.91, 6.89]


class BasicStatsTest(unittest.TestCase):
    def test_mean(self):
        self.assertEqual(mean([1, 2, 3, 4]), 2.5)
        with self.assertRaises(ValueError):
            mean([])

    def test_std_dev(self):
        data = [2, 4, 4, 4, 5, 5, 7, 9]
        self.assertAlmostEqual(std_dev(data, sample=False), 2.0)
        self.assertAlmostEqual(std_dev(data), math.sqrt(32 / 7))
        with self.assertRaises(ValueError):
            std_dev([1])
        self.assertEqual(std_dev([5], sample=False), 0.0)


class PearsonTest(unittest.TestCase):
    def test_korelasi_sempurna(self):
        self.assertAlmostEqual(pearson_r([1, 2, 3, 4], [2, 4, 6, 8]), 1.0)
        self.assertAlmostEqual(pearson_r([1, 2, 3, 4], [8, 6, 4, 2]), -1.0)
        self.assertAlmostEqual(pearson_r([1, 2, 3], [5, 5.5, 6]), 1.0)

    def test_tanpa_korelasi(self):
        self.assertAlmostEqual(pearson_r([1, 2, 3, 4, 5], [2, 4, 5, 4, 2]), 0.0)

    def test_nilai_terkenal_kuartet_anscombe(self):
        for ys in ANSCOMBE:
            self.assertAlmostEqual(pearson_r(X, ys), 0.8165, places=3)
        self.assertAlmostEqual(pearson_r(X4, Y4), 0.8165, places=3)

    def test_simetris_dan_tak_berubah_oleh_skala(self):
        xs, ys = [1, 3, 4, 8], [2, 7, 5, 11]
        self.assertAlmostEqual(pearson_r(xs, ys), pearson_r(ys, xs))
        self.assertAlmostEqual(pearson_r(xs, ys), pearson_r([10 * x + 3 for x in xs], ys))
        self.assertAlmostEqual(pearson_r(xs, ys), -pearson_r([-x for x in xs], ys))

    def test_kasus_tak_terdefinisi(self):
        with self.assertRaises(ValueError):
            pearson_r([1, 1, 1], [1, 2, 3])
        with self.assertRaises(ValueError):
            pearson_r([1, 2, 3], [4, 4, 4])
        with self.assertRaises(ValueError):
            pearson_r([1], [1])
        with self.assertRaises(ValueError):
            pearson_r([1, 2], [1, 2, 3])

    @unittest.skipIf(np is None, "numpy tidak terpasang")
    def test_sama_dengan_numpy_pada_data_acak(self):
        rng = random.Random(3)
        for _ in range(100):
            n = rng.randint(3, 40)
            xs = [rng.uniform(-50, 50) for _ in range(n)]
            ys = [2 * x + rng.gauss(0, 30) for x in xs]
            self.assertAlmostEqual(pearson_r(xs, ys), float(np.corrcoef(xs, ys)[0, 1]), places=9)
            slope, intercept = linear_regression(xs, ys)
            np_slope, np_intercept = np.polyfit(xs, ys, 1)
            self.assertAlmostEqual(slope, float(np_slope), places=7)
            self.assertAlmostEqual(intercept, float(np_intercept), places=7)
            self.assertAlmostEqual(std_dev(xs), float(np.std(xs, ddof=1)), places=9)


class RegressionTest(unittest.TestCase):
    def test_garis_tepat(self):
        slope, intercept = linear_regression([0, 1, 2, 3], [1, 3, 5, 7])
        self.assertAlmostEqual(slope, 2.0)
        self.assertAlmostEqual(intercept, 1.0)

    def test_anscombe_garis_sama(self):
        slope, intercept = linear_regression(X, ANSCOMBE[0])
        self.assertAlmostEqual(slope, 0.5001, places=3)
        self.assertAlmostEqual(intercept, 3.0001, places=3)

    def test_x_sama_semua(self):
        with self.assertRaises(ValueError):
            linear_regression([2, 2, 2], [1, 2, 3])


class InterpretTest(unittest.TestCase):
    def test_tiga_tingkat(self):
        self.assertEqual(interpret(0.0), "No correlation")
        self.assertEqual(interpret(-0.29), "No correlation")
        self.assertEqual(interpret(0.3), "Neutral (positif)")
        self.assertEqual(interpret(-0.5), "Neutral (negatif)")
        self.assertEqual(interpret(0.7), "Some correlation (positif)")
        self.assertEqual(interpret(-0.95), "Some correlation (negatif)")


class ParseNumberTest(unittest.TestCase):
    def test_valid(self):
        for text, value in (("3", 3.0), (" -2.5 ", -2.5), ("1e3", 1000.0), (".5", 0.5)):
            self.assertEqual(parse_number(text), value)

    def test_tidak_valid(self):
        for text in ("", "  ", "abc", "3,5", "nan", "inf", "-inf", "1.2.3"):
            with self.assertRaises(ValueError, msg=text):
                parse_number(text)


class ObservationsTest(unittest.TestCase):
    def test_alur_normal(self):
        table = Observations()
        self.assertFalse(table.calculate_enabled)
        self.assertTrue(table.add("1", "2"))
        self.assertFalse(table.calculate_enabled)  # baru 1 pasang
        self.assertTrue(table.add("2", "4.1"))
        self.assertTrue(table.calculate_enabled)
        self.assertGreater(table.calculate()["r"], 0.99)

    def test_kesalahan_menonaktifkan_calculate_sampai_diperbaiki(self):
        table = Observations()
        table.add("1", "2")
        table.add("2", "3")
        self.assertFalse(table.add("abc", ""))
        self.assertIn("x:", table.error)
        self.assertIn("y: kosong", table.error)
        self.assertFalse(table.calculate_enabled)
        with self.assertRaises(ValueError):
            table.calculate()
        self.assertEqual(len(table.xs), 2)  # pasangan salah tidak masuk
        self.assertTrue(table.add("3", "5"))
        self.assertIsNone(table.error)
        self.assertTrue(table.calculate_enabled)


class CsvTest(unittest.TestCase):
    def write(self, text):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        path = os.path.join(self.dir.name, "d.csv")
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        return path

    def test_dengan_judul(self):
        self.assertEqual(load_csv(self.write("suhu,penjualan\n1,2\n3,4\n\n5,6\n")), ([1, 3, 5], [2, 4, 6]))

    def test_tanpa_judul(self):
        self.assertEqual(load_csv(self.write("1,2\n3,4\n")), ([1, 3], [2, 4]))

    def test_kesalahan(self):
        for text in ("", "x,y\n", "1,2,3\n", "1,2\na,4\n", "1\n"):
            with self.assertRaises(ValueError, msg=repr(text)):
                load_csv(self.write(text))
        with self.assertRaises(ValueError):
            load_csv("tidak-ada.csv")

    def test_cli(self):
        self.assertEqual(main([self.write("1,2\n2,4\n3,6.5\n")]), 0)
        self.assertEqual(main(["tidak-ada.csv"]), 1)
        self.assertEqual(main([]), 2)


class SummaryTest(unittest.TestCase):
    def test_semua_hasil_spesifikasi(self):
        result = summarize([1, 2, 3, 4, 5], [2, 4, 5, 4, 5])
        for key in ("mean_x", "mean_y", "std_x", "std_y", "r", "interpretation"):
            self.assertIn(key, result)
        self.assertAlmostEqual(result["r"], 0.7746, places=3)
        self.assertEqual(result["interpretation"], "Some correlation (positif)")


if __name__ == "__main__":
    unittest.main()
