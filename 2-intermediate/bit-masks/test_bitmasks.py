import contextlib
import io
import unittest
from unittest import mock

import bitmasks
from bitmasks import (
    ALL_ZONES,
    CITY_BITS,
    CITY_OFFSETS,
    ZONE_COUNT,
    build_mask,
    find_cities,
    format_bits,
    main,
    parse_offset,
    render,
    zone_bit,
)


def naive(offsets, invert=False):
    """Cara biasa dengan perbandingan, hanya dipakai di tes sebagai pembanding."""
    wanted = set(offsets)
    return [name for name, off in CITY_OFFSETS if (off in wanted) != invert]


class ZoneBitTest(unittest.TestCase):
    def test_ujung_dan_tengah(self):
        self.assertEqual(ZONE_COUNT, 25)
        self.assertEqual(zone_bit(-12), 1)
        self.assertEqual(zone_bit(0), 1 << 12)
        self.assertEqual(zone_bit(12), 1 << 24)

    def test_tiap_offset_satu_bit_unik(self):
        bits = [zone_bit(o) for o in range(-12, 13)]
        self.assertEqual(len(set(bits)), 25)
        for b in bits:
            self.assertEqual(bin(b).count("1"), 1)
        combined = 0
        for b in bits:
            combined |= b
        self.assertEqual(combined, ALL_ZONES)

    def test_di_luar_rentang(self):
        for bad in (-13, 13, 100):
            with self.assertRaises(ValueError):
                zone_bit(bad)
        for bad in (2.0, "2", True):
            with self.assertRaises(TypeError):
                zone_bit(bad)


class FindTest(unittest.TestCase):
    def test_contoh_spesifikasi(self):
        self.assertEqual(find_cities(build_mask([2])), ["Paris", "Berlin", "Brussels", "Amsterdam", "Rome"])
        self.assertEqual(find_cities(build_mask([-4])), ["New York", "Washington, DC"])
        self.assertEqual(find_cities(build_mask([9])), ["Tokyo"])
        self.assertEqual(find_cities(build_mask([0])), [])

    def test_sama_dengan_cara_biasa_untuk_semua_offset(self):
        for offset in range(-12, 13):
            for invert in (False, True):
                self.assertEqual(find_cities(build_mask([offset], invert)), naive([offset], invert), (offset, invert))

    def test_gabungan_beberapa_offset(self):
        self.assertEqual(find_cities(build_mask([-4, -5])), ["New York", "Washington, DC", "St. Louis"])
        self.assertEqual(find_cities(build_mask([1, 3, 5])), naive([1, 3, 5]))
        self.assertEqual(find_cities(build_mask([1, 3, 5], invert=True)), naive([1, 3, 5], invert=True))

    def test_kebalikan_melengkapi(self):
        for offset in (2, -7, 11):
            yes = find_cities(build_mask([offset]))
            no = find_cities(build_mask([offset], invert=True))
            self.assertEqual(len(yes) + len(no), len(CITY_BITS))
            self.assertFalse(set(yes) & set(no))

    def test_masker_kebalikan_tetap_25_bit(self):
        mask = build_mask([2], invert=True)
        self.assertEqual(mask, ALL_ZONES ^ zone_bit(2))
        self.assertTrue(0 <= mask <= ALL_ZONES)
        self.assertEqual(format_bits(mask).count("1"), 24)
        self.assertEqual(build_mask([], invert=True), ALL_ZONES)

    def test_masker_kosong_dan_penuh(self):
        self.assertEqual(find_cities(0), [])
        self.assertEqual(len(find_cities(ALL_ZONES)), 16)

    def test_tidak_membandingkan_offset(self):
        # Data kota hanya berupa pola bit; tidak ada offset yang bisa dibandingkan.
        cities = (("A", 0b101), ("B", 0b010), ("C", 0))
        self.assertEqual(find_cities(0b001, cities), ["A"])
        self.assertEqual(find_cities(0b110, cities), ["A", "B"])


class ParseTest(unittest.TestCase):
    def test_bentuk_yang_diterima(self):
        self.assertEqual(parse_offset("2"), 2)
        self.assertEqual(parse_offset("+9"), 9)
        self.assertEqual(parse_offset(" -4 "), -4)
        self.assertEqual(parse_offset("GMT+3"), 3)
        self.assertEqual(parse_offset("gmt -5"), -5)
        self.assertEqual(parse_offset("UTC"), 0)

    def test_ditolak(self):
        for bad in ("", "abc", "2.5", "+13", "-13", "GMT+x"):
            with self.assertRaises(ValueError, msg=bad):
                parse_offset(bad)


class RenderTest(unittest.TestCase):
    def test_daftar_centang_dan_ringkasan(self):
        out = render([-4])
        self.assertIn("[x] New York", out)
        self.assertIn("[x] Washington, DC", out)
        self.assertIn("[ ] Tokyo", out)
        self.assertEqual(out.count("[x]"), 2)
        self.assertEqual(out.count("[ ]"), 14)
        self.assertIn("2 dari 16 kota cocok.", out)

    def test_kebalikan(self):
        out = render([2], invert=True)
        self.assertIn("TIDAK di GMT +2", out)
        self.assertIn("11 dari 16 kota cocok.", out)
        self.assertIn("[ ] Paris", out)

    def test_pola_bit(self):
        out = render([9], show_bits=True)
        self.assertIn(format_bits(zone_bit(9)), out)
        self.assertEqual(len(format_bits(zone_bit(9))), 25)
        self.assertIn("& masker = " + format_bits(zone_bit(9)), out)


class MainTest(unittest.TestCase):
    def run_main(self, argv, inputs=None):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            if inputs is None:
                code = main(argv)
            else:
                with mock.patch("builtins.input", side_effect=inputs):
                    code = main(argv)
        return code, buf.getvalue()

    def test_offset_negatif_sebagai_argumen(self):
        code, out = self.run_main(["-4", "-5"])
        self.assertEqual(code, 0)
        self.assertIn("3 dari 16 kota cocok.", out)

    def test_not(self):
        code, out = self.run_main(["2", "--not"])
        self.assertEqual(code, 0)
        self.assertIn("11 dari 16", out)

    def test_error(self):
        code, out = self.run_main(["20"])
        self.assertEqual(code, 1)
        self.assertIn("Error", out)

    def test_interaktif(self):
        code, out = self.run_main([], ["9", "!2", "!", "xx", ""])
        self.assertEqual(code, 0)
        self.assertIn("1 dari 16", out)
        self.assertIn("11 dari 16", out)
        self.assertIn("setidaknya satu offset", out)
        self.assertIn("bukan offset GMT", out)


if __name__ == "__main__":
    unittest.main()
