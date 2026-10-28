import io
import json
import unittest
import urllib.error

from github_status import RED, RESET, fetch_status, format_status, parse_components

SAMPLE = {
    "components": [
        {"name": "Git Operations", "status": "operational", "group": False},
        {"name": "API Requests", "status": "degraded_performance", "group": False},
        {"name": "Visible components", "status": "operational", "group": True},
        {"name": "Pages", "status": "major_outage"},
        {"name": "Visit www.githubstatus.com for more information", "status": "operational"},
    ]
}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def opener_returning(body):
    return lambda url, timeout: FakeResponse(body)


def opener_raising(error):
    def opener(url, timeout):
        raise error
    return opener


class ParseTest(unittest.TestCase):
    def test_lewati_grup_dan_baris_tautan(self):
        names = [name for name, _ in parse_components(SAMPLE)]
        self.assertEqual(names, ["Git Operations", "API Requests", "Pages"])

    def test_format_tidak_dikenali(self):
        for data in ({}, {"components": [{"name": "X"}]}, [], None):
            with self.assertRaises(ValueError, msg=repr(data)):
                parse_components(data)


class FormatTest(unittest.TestCase):
    def test_semua_operasional(self):
        text = format_status([("Git Operations", "operational"), ("API Requests", "operational")], color=False)
        self.assertIn("Semua komponen operasional.", text)
        self.assertNotIn("▲", text)

    def test_komponen_bermasalah_mencolok(self):
        text = format_status(parse_components(SAMPLE), color=False)
        lines = text.splitlines()
        self.assertTrue(lines[0].startswith("✔"))
        self.assertTrue(lines[1].startswith("▲") and "Degraded performance" in lines[1])
        self.assertTrue(lines[2].startswith("▲") and "Major outage" in lines[2])
        self.assertIn("2 komponen bermasalah.", text)

    def test_warna_hanya_bila_diminta(self):
        components = [("Pages", "major_outage")]
        self.assertIn(RED, format_status(components, color=True))
        self.assertNotIn(RESET, format_status(components, color=False))

    def test_status_tidak_dikenal_tetap_ditampilkan(self):
        self.assertIn("Some new state", format_status([("X", "some_new_state")], color=False))

    def test_daftar_kosong(self):
        self.assertIn("Semua komponen operasional.", format_status([], color=False))


class FetchTest(unittest.TestCase):
    def test_berhasil(self):
        self.assertEqual(fetch_status(urlopen=opener_returning(json.dumps(SAMPLE).encode())), SAMPLE)

    def test_tanpa_internet(self):
        with self.assertRaises(ValueError) as caught:
            fetch_status(urlopen=opener_raising(urllib.error.URLError("offline")))
        self.assertIn("koneksi internet", str(caught.exception))

    def test_kode_http_salah(self):
        error = urllib.error.HTTPError("u", 503, "x", {}, None)
        with self.assertRaises(ValueError) as caught:
            fetch_status(urlopen=opener_raising(error))
        self.assertIn("503", str(caught.exception))

    def test_bukan_json(self):
        with self.assertRaises(ValueError):
            fetch_status(urlopen=opener_returning(b"<html>maintenance</html>"))


if __name__ == "__main__":
    unittest.main()
