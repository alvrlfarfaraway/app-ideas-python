import io
import json
import os
import tempfile
import unittest
import urllib.error
import urllib.parse

from weather import (CONDITIONS, CityMemory, clean_city, current_weather, describe_condition, find_places,
                     format_weather, main, place_label, run)

SEMARANG = {"name": "Kota Semarang", "admin1": "Jawa Tengah", "country": "Indonesia",
            "latitude": -6.99306, "longitude": 110.42083}
KOTA2 = {"name": "Semarang", "admin1": "Semarang", "country": "Indonesia", "latitude": -7.0, "longitude": 110.4}
CURRENT = {"time": "2026-10-29T07:15", "temperature_2m": 28.3, "apparent_temperature": 33.3,
           "relative_humidity_2m": 73, "weather_code": 1, "wind_speed_10m": 3.0, "is_day": 1}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fake_api(places=(SEMARANG,), current=CURRENT, error=None, geo_payload=None):
    calls = []

    def opener(url, timeout):
        calls.append(url)
        if error:
            raise error
        if "geocoding-api" in url:
            payload = geo_payload if geo_payload is not None else ({"results": list(places)} if places else {"generationtime_ms": 0.5})
        else:
            payload = {"current": current}
        return FakeResponse(json.dumps(payload).encode())

    opener.calls = calls
    return opener


class ConditionTest(unittest.TestCase):
    def test_semua_kode_wmo_yang_dikenal_punya_deskripsi_dan_ikon(self):
        wmo = [0, 1, 2, 3, 45, 48, 51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99]
        self.assertEqual(sorted(CONDITIONS), sorted(wmo))
        for code in wmo:
            text, icon = describe_condition(code, True)
            self.assertTrue(text and icon, code)

    def test_ikon_siang_dan_malam_berbeda_untuk_langit_cerah(self):
        self.assertNotEqual(describe_condition(0, True)[1], describe_condition(0, False)[1])
        self.assertEqual(describe_condition(0, True)[0], "Cerah")

    def test_kode_tidak_dikenal(self):
        text, icon = describe_condition(1234, True)
        self.assertIn("1234", text)
        self.assertEqual(icon, "❔")


class CityTest(unittest.TestCase):
    def test_dirapikan(self):
        self.assertEqual(clean_city("  Kota   Semarang "), "Kota Semarang")

    def test_tidak_valid(self):
        for text in ("", "   ", "a" * 101, "Jakarta\x00", "Bandung\n\x1b[31m"):
            with self.assertRaises(ValueError, msg=repr(text)):
                clean_city(text)


class GeocodeTest(unittest.TestCase):
    def test_nama_di_url_di_encode(self):
        api = fake_api()
        find_places("São Paulo & co", urlopen=api)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(api.calls[0]).query)
        self.assertEqual(query["name"], ["São Paulo & co"])
        self.assertEqual(query["language"], ["id"])

    def test_kota_tidak_ditemukan(self):
        for opener in (fake_api(places=None), fake_api(geo_payload={"results": []}), fake_api(geo_payload=[])):
            with self.assertRaises(ValueError) as caught:
                find_places("Zzzxyq", urlopen=opener)
            self.assertIn("tidak ditemukan", str(caught.exception))

    def test_label(self):
        self.assertEqual(place_label(SEMARANG), "Kota Semarang, Jawa Tengah, Indonesia")
        self.assertEqual(place_label({"name": "Singapore", "admin1": "Singapore", "country": "Singapore"}), "Singapore")


class WeatherTest(unittest.TestCase):
    def test_parse(self):
        weather = current_weather(SEMARANG, fake_api())
        self.assertEqual(weather["temperature"], 28.3)
        self.assertEqual(weather["feels_like"], 33.3)
        self.assertEqual((weather["humidity"], weather["code"], weather["is_day"]), (73, 1, True))
        self.assertEqual(weather["time"], "2026-10-29 07:15")

    def test_data_tidak_lengkap(self):
        for current in ({}, {**CURRENT, "weather_code": None}, {k: v for k, v in CURRENT.items() if k != "temperature_2m"}):
            with self.assertRaises(ValueError, msg=str(current)):
                current_weather(SEMARANG, fake_api(current=current))

    def test_kesalahan_jaringan(self):
        with self.assertRaises(ValueError) as caught:
            find_places("Semarang", urlopen=fake_api(error=urllib.error.URLError("offline")))
        self.assertIn("koneksi", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            find_places("Semarang", urlopen=fake_api(error=urllib.error.HTTPError("u", 429, "x", {}, None)))
        self.assertIn("429", str(caught.exception))

    def test_format_siang_dan_malam(self):
        day = format_weather(current_weather(SEMARANG, fake_api()))
        self.assertIn("Hampir cerah", day)
        self.assertIn("Siang", day)
        self.assertIn("28.3 °C", day)
        self.assertIn("terasa 33.3", day)
        night = format_weather(current_weather(SEMARANG, fake_api(current={**CURRENT, "is_day": 0, "weather_code": 0})))
        self.assertIn("Malam", night)
        self.assertIn("🌙", night)


class MemoryTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "state", "city.json")
        self.memory = CityMemory(self.path)

    def tearDown(self):
        self.dir.cleanup()

    def test_simpan_dan_baca_antar_sesi(self):
        self.assertIsNone(self.memory.load())
        self.memory.save("Kota Semarang")
        self.assertEqual(CityMemory(self.path).load(), "Kota Semarang")

    def test_berkas_rusak_diabaikan(self):
        os.makedirs(os.path.dirname(self.path))
        for content in ("{rusak", "[]", '{"city": 5}', '{"city": "  "}'):
            with open(self.path, "w", encoding="utf-8") as file:
                file.write(content)
            self.assertIsNone(self.memory.load(), content)


class RunTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.memory = CityMemory(os.path.join(self.dir.name, "c.json"))

    def tearDown(self):
        self.dir.cleanup()

    def test_menyimpan_kota_setelah_berhasil(self):
        lines = []
        run("Semarang", memory=self.memory, urlopen=fake_api(), out=lines.append)
        self.assertEqual(self.memory.load(), "Semarang")
        self.assertIn("Hampir cerah", lines[0])

    def test_kota_gagal_tidak_disimpan(self):
        with self.assertRaises(ValueError):
            run("Zzzxyq", memory=self.memory, urlopen=fake_api(places=None), out=lambda t: None)
        self.assertIsNone(self.memory.load())

    def test_beberapa_kota_cocok_dan_pilihan(self):
        api = fake_api(places=(SEMARANG, KOTA2))
        text = run("Semarang", urlopen=api, out=lambda t: None)
        self.assertIn("--list", text)
        listing = run("Semarang", list_only=True, urlopen=api, out=lambda t: None)
        self.assertIn("1. Kota Semarang", listing)
        self.assertIn("2. Semarang", listing)
        self.assertNotIn("°C", listing)
        run("Semarang", pick=2, urlopen=api, out=lambda t: None)
        self.assertIn("latitude=-7.0", api.calls[-1])

    def test_pilihan_di_luar_daftar(self):
        for pick in (0, 3, -1):
            with self.assertRaises(ValueError):
                run("Semarang", pick=pick, urlopen=fake_api(places=(SEMARANG, KOTA2)), out=lambda t: None)


class CliTest(unittest.TestCase):
    def test_alur_kota_terakhir(self):
        with tempfile.TemporaryDirectory() as folder:
            state = os.path.join(folder, "c.json")
            self.assertEqual(main(["Semarang", "--state-file", state], fake_api()), 0)
            self.assertEqual(main(["--state-file", state], fake_api()), 0)  # memakai kota tersimpan
            self.assertEqual(CityMemory(state).load(), "Semarang")

    def test_nama_kota_beberapa_kata(self):
        with tempfile.TemporaryDirectory() as folder:
            api = fake_api()
            self.assertEqual(main(["Kota", "Semarang", "--state-file", os.path.join(folder, "c.json")], api), 0)
            self.assertIn("name=Kota+Semarang", api.calls[0])

    def test_kesalahan(self):
        with tempfile.TemporaryDirectory() as folder:
            state = os.path.join(folder, "c.json")
            self.assertEqual(main(["Zzzxyq", "--state-file", state], fake_api(places=None)), 1)
            self.assertEqual(main(["Semarang", "--state-file", state], fake_api(error=urllib.error.URLError("x"))), 1)
            self.assertEqual(main(["Semarang", "--pick", "9", "--state-file", state], fake_api()), 1)


if __name__ == "__main__":
    unittest.main()
