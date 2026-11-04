import contextlib
import io
import json
import os
import tempfile
import unittest
import urllib.error
from decimal import Decimal

import currency
from currency import (
    RatesError,
    code_of,
    convert,
    currency_choices,
    format_money,
    load_rates,
    main,
    parse_amount,
    parse_rates,
    read_cache,
)

LATEST = {"amount": 1.0, "base": "EUR", "date": "2026-11-03",
          "rates": {"USD": 1.1179, "IDR": 20275.02, "JPY": 176.95, "GBP": 0.83358}}
NAMES = {"EUR": "Euro", "USD": "United States Dollar", "IDR": "Indonesian Rupiah",
         "JPY": "Japanese Yen", "GBP": "British Pound"}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fake_api(latest=LATEST, names=NAMES):
    def opener(request, timeout=None):
        url = request.full_url
        payload = latest if url.endswith("/latest") else names
        return FakeResponse(json.dumps(payload).encode())
    return opener


def offline(request, timeout=None):
    raise urllib.error.URLError("no network")


class AmountTest(unittest.TestCase):
    def test_bentuk_yang_diterima(self):
        self.assertEqual(parse_amount("100"), Decimal("100"))
        self.assertEqual(parse_amount(" 12,5 "), Decimal("12.5"))
        self.assertEqual(parse_amount("12.50"), Decimal("12.50"))
        self.assertEqual(parse_amount("7,"), Decimal("7"))
        self.assertEqual(parse_amount("0"), Decimal("0"))

    def test_maksimal_sembilan_digit(self):
        self.assertEqual(parse_amount("999999999"), Decimal("999999999"))
        self.assertEqual(parse_amount("9999999,99"), Decimal("9999999.99"))
        self.assertEqual(parse_amount("000000000123"), Decimal("123"))  # nol di depan tidak dihitung
        for bad in ("1000000000", "99999999,99"):
            with self.assertRaises(ValueError) as ctx:
                parse_amount(bad)
            self.assertIn("9 digit", str(ctx.exception))

    def test_bukan_angka(self):
        for bad in ("", "  ", "abc", "12,5x", "-5", "1e5", "1.000.000", "1,000", ",5", "1 000", "١٢"):
            with self.assertRaises(ValueError, msg=bad):
                parse_amount(bad)


class ConvertTest(unittest.TestCase):
    def setUp(self):
        _, self.rates = parse_rates(LATEST)

    def test_kurs_silang_lewat_eur(self):
        self.assertEqual(convert(Decimal(100), "USD", "IDR", self.rates), Decimal("1813670.27"))
        self.assertEqual(convert(Decimal(1), "EUR", "USD", self.rates), Decimal("1.12"))
        self.assertEqual(convert(Decimal(100), "IDR", "IDR", self.rates), Decimal("100.00"))

    def test_dibulatkan_dua_desimal_setengah_ke_atas(self):
        rates = {"EUR": Decimal(1), "AAA": Decimal(1), "BBB": Decimal("0.125")}
        self.assertEqual(convert(Decimal(1), "AAA", "BBB", rates), Decimal("0.13"))

    def test_bolak_balik_mendekati_semula(self):
        there = convert(Decimal(250000), "IDR", "USD", self.rates)
        back = convert(there, "USD", "IDR", self.rates)
        self.assertLess(abs(back - 250000), 100)

    def test_kode_tidak_dikenal(self):
        with self.assertRaises(ValueError):
            convert(Decimal(1), "USD", "XXX", self.rates)

    def test_format_indonesia(self):
        self.assertEqual(format_money(Decimal("1813670.27")), "1.813.670,27")
        self.assertEqual(format_money(Decimal("0.5")), "0,50")
        self.assertEqual(format_money(Decimal("999")), "999,00")
        self.assertEqual(format_money(Decimal("1000")), "1.000,00")


class RatesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = os.path.join(self.tmp.name, "rates.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_parse_menambah_eur(self):
        date, rates = parse_rates(LATEST)
        self.assertEqual(date, "2026-11-03")
        self.assertEqual(rates["EUR"], 1)
        self.assertEqual(rates["IDR"], Decimal("20275.02"))  # lewat str, bukan float mentah

    def test_parse_menolak_data_aneh(self):
        for bad in ({}, {"base": "USD", "date": "x", "rates": {"A": 1}}, {"base": "EUR", "date": "x", "rates": {}},
                    {"base": "EUR", "date": "x", "rates": {"A": 0}}, {"base": "EUR", "date": "x", "rates": []}):
            with self.assertRaises(RatesError, msg=bad):
                parse_rates(bad)

    def test_online_lalu_offline_memakai_cache(self):
        data = load_rates(fake_api(), self.cache)
        self.assertFalse(data["offline"])
        self.assertEqual(data["names"]["IDR"], "Indonesian Rupiah")
        cached = load_rates(offline, self.cache)
        self.assertTrue(cached["offline"])
        self.assertEqual(cached["date"], "2026-11-03")
        self.assertEqual(cached["rates"], data["rates"])

    def test_offline_tanpa_cache(self):
        with self.assertRaises(RatesError) as ctx:
            load_rates(offline, self.cache)
        self.assertIn("koneksi", str(ctx.exception))

    def test_data_server_rusak_memakai_cache(self):
        load_rates(fake_api(), self.cache)
        data = load_rates(fake_api(latest={"error": "x"}), self.cache)
        self.assertTrue(data["offline"])

    def test_cache_rusak(self):
        for content in ("{", "[]", json.dumps({"date": "x", "rates": {"USD": "abc"}}),
                        json.dumps({"date": "x", "rates": {"USD": "-1"}})):
            with open(self.cache, "w", encoding="utf-8") as handle:
                handle.write(content)
            self.assertIsNone(read_cache(self.cache), content)

    def test_daftar_terurut(self):
        _, rates = parse_rates(LATEST)
        choices = currency_choices(rates, NAMES)
        self.assertEqual([code_of(c) for c in choices], ["EUR", "GBP", "IDR", "JPY", "USD"])
        self.assertIn("IDR - Indonesian Rupiah", choices)
        self.assertEqual(currency_choices({"XYZ": 1}, {}), ["XYZ - XYZ"])


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = os.path.join(self.tmp.name, "rates.json")

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, argv, opener=None, gui=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv, urlopen=opener or fake_api(), cache_path=self.cache, gui=gui)
        return code, out.getvalue(), err.getvalue()

    def test_konversi(self):
        code, out, _ = self.run_main(["100", "usd", "idr"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "100,00 USD = 1.813.670,27 IDR (kurs ECB 2026-11-03)")

    def test_offline_ditandai(self):
        self.run_main(["1", "EUR", "USD"])
        code, out, _ = self.run_main(["1", "EUR", "USD"], opener=offline)
        self.assertEqual(code, 0)
        self.assertIn("offline", out)

    def test_error(self):
        self.assertEqual(self.run_main(["abc", "USD", "IDR"])[0], 1)
        self.assertEqual(self.run_main(["1", "USD", "XXX"])[0], 1)
        self.assertEqual(self.run_main(["100"])[0], 2)
        self.cache = os.path.join(self.tmp.name, "kosong.json")  # belum pernah online
        code, _, err = self.run_main(["1", "USD", "IDR"], opener=offline)
        self.assertEqual(code, 1)
        self.assertIn("belum ada cache", err)

    def test_list_dan_gui(self):
        code, out, _ = self.run_main(["--list"])
        self.assertEqual(out.splitlines()[0], "EUR - Euro")
        opened = []
        self.assertEqual(self.run_main([], gui=opened.append)[0], 0)
        self.assertEqual(opened[0]["date"], "2026-11-03")


class GuiTest(unittest.TestCase):
    """Logika jendela: hasil berubah langsung, error, dan tombol tukar."""

    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:  # tanpa layar
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.root.bell = lambda: None
        date, rates = parse_rates(LATEST)
        self.app = currency.ConverterApp(self.root, {"date": date, "rates": rates, "names": NAMES})

    def tearDown(self):
        self.root.destroy()

    def test_hasil_langsung_berubah(self):
        self.assertEqual(self.app.result.get(), "1.813.670,27 IDR")
        self.app.amount.set("1")
        self.assertEqual(self.app.result.get(), "18.136,70 IDR")

    def test_peringatan_bukan_angka(self):
        self.app.amount.set("12x")
        self.assertIn("bukan angka", self.app.error.get())
        self.assertEqual(self.app.result.get(), "")
        self.app.amount.set("")
        self.assertEqual(self.app.error.get(), "")
        self.app.amount.set("5")
        self.assertEqual(self.app.error.get(), "")

    def test_tukar(self):
        self.app.amount.set("250000")
        self.app.swap()
        self.assertEqual(code_of(self.app.source.get()), "IDR")
        self.assertEqual(code_of(self.app.target.get()), "USD")
        self.assertEqual(self.app.result.get(), "13,78 USD")


if __name__ == "__main__":
    unittest.main()
