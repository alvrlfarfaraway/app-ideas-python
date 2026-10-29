import random
import unittest
from collections import Counter
from decimal import Decimal

from randomnum import MAX_COUNT, format_number, generate, main


class RangeTest(unittest.TestCase):
    def test_selalu_dalam_rentang_inklusif(self):
        numbers = generate(1, 6, count=1000, rng=random.Random(1))
        self.assertTrue(all(1 <= n <= 6 for n in numbers))
        self.assertEqual(set(numbers), {1, 2, 3, 4, 5, 6})  # kedua ujung ikut mungkin

    def test_seragam_kasar(self):
        counts = Counter(generate(1, 4, count=1000, rng=random.Random(5)))
        for value in (1, 2, 3, 4):
            self.assertTrue(180 < counts[value] < 320, counts)

    def test_min_sama_dengan_max(self):
        self.assertEqual(generate(7, 7, count=3), [7, 7, 7])

    def test_seed_membuat_hasil_tetap(self):
        self.assertEqual(generate(1, 100, 5, rng=random.Random(42)), generate(1, 100, 5, rng=random.Random(42)))

    def test_batas_berupa_teks_dan_desimal_dibulatkan_ke_dalam(self):
        numbers = generate("1.5", "4.2", count=200, rng=random.Random(2))  # bulat: hanya 2, 3, 4
        self.assertEqual(set(numbers), {2, 3, 4})
        self.assertEqual(generate(" 3 ", " 3 "), [3])


class NegativeTest(unittest.TestCase):
    def test_negatif_ditolak_kecuali_diizinkan(self):
        with self.assertRaises(ValueError):
            generate(-5, 5)
        numbers = generate(-5, 5, count=500, allow_negative=True, rng=random.Random(3))
        self.assertTrue(all(-5 <= n <= 5 for n in numbers))
        self.assertTrue(any(n < 0 for n in numbers))

    def test_semua_negatif(self):
        numbers = generate(-20, -10, count=200, allow_negative=True, rng=random.Random(4))
        self.assertTrue(all(-20 <= n <= -10 for n in numbers))


class DecimalTest(unittest.TestCase):
    def test_jumlah_desimal_dan_rentang(self):
        numbers = generate(0, 1, count=500, decimals=3, rng=random.Random(6))
        for n in numbers:
            self.assertTrue(Decimal(0) <= n <= Decimal(1))
            self.assertEqual(n, n.quantize(Decimal("0.001")))
        self.assertTrue(any(n != n.to_integral_value() for n in numbers))

    def test_tidak_pernah_keluar_rentang_akibat_pembulatan(self):
        numbers = generate("0.1", "0.2", count=500, decimals=2, rng=random.Random(7))
        self.assertTrue(all(Decimal("0.10") <= n <= Decimal("0.20") for n in numbers))
        self.assertEqual(set(numbers), {Decimal(k) / 100 for k in range(10, 21)})  # 0.10 sampai 0.20, kedua ujung muncul

    def test_negatif_dan_desimal(self):
        numbers = generate("-1.5", "-0.5", count=300, decimals=1, allow_negative=True, rng=random.Random(8))
        self.assertTrue(all(Decimal("-1.5") <= n <= Decimal("-0.5") for n in numbers))

    def test_tidak_ada_nilai_pada_presisi_itu(self):
        with self.assertRaises(ValueError):
            generate("0.11", "0.19", decimals=1)

    def test_format(self):
        self.assertEqual(format_number(Decimal("0.5"), 3), "0.500")
        self.assertEqual(format_number(7, 0), "7")


class UniqueTest(unittest.TestCase):
    def test_undian_tanpa_ulang(self):
        numbers = generate(1, 49, count=6, unique=True, rng=random.Random(9))
        self.assertEqual(len(set(numbers)), 6)

    def test_semua_nilai_tepat_sekali(self):
        self.assertEqual(sorted(generate(1, 10, count=10, unique=True)), list(range(1, 11)))

    def test_kurang_banyak_kemungkinan(self):
        with self.assertRaises(ValueError):
            generate(1, 5, count=6, unique=True)


class ValidationTest(unittest.TestCase):
    def test_masukan_salah(self):
        bad = [("a", 5), (1, "b"), ("", 5), (1, ""), ("nan", 5), (1, "inf"), (10, 1)]
        for lo, hi in bad:
            with self.assertRaises(ValueError, msg=f"{lo!r},{hi!r}"):
                generate(lo, hi)

    def test_parameter_salah(self):
        for kwargs in ({"count": 0}, {"count": MAX_COUNT + 1}, {"count": 1.5}, {"decimals": -1}, {"decimals": 11}):
            with self.assertRaises(ValueError, msg=str(kwargs)):
                generate(1, 10, **kwargs)


class CliTest(unittest.TestCase):
    def test_exit_code(self):
        self.assertEqual(main(["1", "6", "--seed", "1"]), 0)
        self.assertEqual(main(["6", "1"]), 1)
        self.assertEqual(main(["1", "x"]), 1)
        self.assertEqual(main(["-5", "5"]), 1)
        self.assertEqual(main(["-5", "5", "--negative"]), 0)


if __name__ == "__main__":
    unittest.main()
