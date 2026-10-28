import io
import json
import unittest
import urllib.error

from hello import FieldError, Session, format_geo, get_greeting, locate

GEO = {"status": "success", "country": "Germany", "city": "Berlin", "regionName": "Berlin",
       "zip": "10115", "lat": 52.52, "lon": 13.4, "timezone": "Europe/Berlin", "query": "1.2.3.4"}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fake_urlopen(geo=GEO, hello=None, requested=None):
    """Tiruan jaringan: ip-api menjawab `geo`, hellosalut menjawab `hello` (atau menurut query)."""
    def opener(url, timeout):
        if requested is not None:
            requested.append(url)
        if "ip-api.com" in url:
            if isinstance(geo, Exception):
                raise geo
            return FakeResponse(json.dumps(geo).encode())
        if isinstance(hello, Exception):
            raise hello
        return FakeResponse(json.dumps(hello or {"code": "de", "hello": "Gr&uuml;&szlig; Gott"}).encode())
    return opener


class GreetingTest(unittest.TestCase):
    def test_entitas_html_didekode(self):
        self.assertEqual(get_greeting("1.2.3.4", urlopen=fake_urlopen()), "Grüß Gott")

    def test_ip_dan_lang_masuk_ke_url(self):
        requested = []
        get_greeting("1.2.3.4", urlopen=fake_urlopen(requested=requested))
        get_greeting("1.2.3.4", lang="id", urlopen=fake_urlopen(requested=requested))
        self.assertTrue(requested[0].endswith("?ip=1.2.3.4"))
        self.assertTrue(requested[1].endswith("?lang=id"))  # lang menggantikan ip

    def test_jawaban_tanpa_salam(self):
        with self.assertRaises(ValueError):
            get_greeting("1.2.3.4", urlopen=fake_urlopen(hello={"code": "xx"}))


class LocateTest(unittest.TestCase):
    def test_berhasil(self):
        self.assertEqual(locate(fake_urlopen())["city"], "Berlin")

    def test_gagal_dari_layanan(self):
        with self.assertRaises(ValueError) as caught:
            locate(fake_urlopen(geo={"status": "fail", "message": "reserved range"}))
        self.assertIn("reserved range", str(caught.exception))


class SessionTest(unittest.TestCase):
    def test_login_dan_logout(self):
        session = Session(fake_urlopen())
        message, warnings = session.login("budi", "rahasia")
        self.assertEqual(message, "Grüß Gott budi you have successfully logged in!")
        self.assertEqual(warnings, [])
        self.assertEqual(session.geo["city"], "Berlin")
        self.assertEqual(session.logout(), "Have a great day budi!")
        self.assertIsNone(session.user)
        self.assertIsNone(session.geo)

    def test_kolom_kosong_ditandai(self):
        session = Session(fake_urlopen())
        for username, password, fields in (("", "x", ["username"]), ("u", "  ", ["password"]), ("", "", ["username", "password"])):
            with self.assertRaises(FieldError) as caught:
                session.login(username, password)
            self.assertEqual(caught.exception.fields, fields)
        self.assertIsNone(session.user)

    def test_logout_tanpa_login(self):
        with self.assertRaises(ValueError):
            Session(fake_urlopen()).logout()

    def test_override_bahasa_tanpa_geolokasi(self):
        offline = fake_urlopen(geo=urllib.error.URLError("offline"), hello={"code": "id", "hello": "Halo"})
        message, warnings = Session(offline).login("ani", "pw", lang="id")
        self.assertEqual(message, "Halo ani you have successfully logged in!")
        self.assertEqual(warnings, [])  # geolokasi gagal tapi tidak diperlukan

    def test_geolokasi_gagal_memakai_hello_biasa(self):
        offline = fake_urlopen(geo=urllib.error.URLError("offline"), hello=urllib.error.URLError("offline"))
        message, warnings = Session(offline).login("ani", "pw")
        self.assertTrue(message.startswith("Hello ani"))
        self.assertEqual(len(warnings), 2)

    def test_login_ulang_mengganti_pengguna(self):
        session = Session(fake_urlopen())
        session.login("a", "x")
        session.login("b", "y")
        self.assertEqual(session.logout(), "Have a great day b!")


class FormatTest(unittest.TestCase):
    def test_info_geolokasi_lengkap(self):
        text = format_geo(GEO)
        for expected in ("1.2.3.4", "Berlin", "Germany", "10115", "13.4", "52.52", "Europe/Berlin"):
            self.assertIn(expected, text)

    def test_kode_pos_kosong(self):
        self.assertIn("-", format_geo({**GEO, "zip": ""}))


if __name__ == "__main__":
    unittest.main()
