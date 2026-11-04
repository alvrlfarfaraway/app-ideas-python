import contextlib
import io
import json
import os
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import tz_bot
from tz_bot import (
    LocalDirectory,
    SlackDirectory,
    build_rows,
    handle_command,
    main,
    make_handler,
    parse_targets,
    sign,
    slack_response,
    text_table,
    verify,
)

HERE = os.path.dirname(os.path.abspath(__file__))
TEAM = LocalDirectory.load(os.path.join(HERE, "contoh", "tim.json"))
NOW = datetime(2026, 11, 4, 15, 17, tzinfo=timezone.utc)
SECRET = "rahasia-tanda-tangan"


class ParseTest(unittest.TestCase):
    def test_nama_dan_mention(self):
        self.assertEqual(parse_targets("<@U01RINA|rina> budi, @wayan <@U02BUDI>"),
                         [("id", "U01RINA", "rina"), ("id", "U02BUDI", "U02BUDI"), ("name", "budi", "budi"),
                          ("name", "wayan", "wayan")])

    def test_duplikat_dibuang(self):
        self.assertEqual(len(parse_targets("rina Rina @rina")), 1)
        self.assertEqual(parse_targets("   "), [])


class RowsTest(unittest.TestCase):
    def test_jam_dan_zona(self):
        rows, missing = build_rows("rina budi yohanes priya sam", TEAM, NOW)
        table = {name: (f"{local:%H:%M}", abbr) for name, local, abbr, _, _ in rows}
        self.assertEqual(table["Rina"], ("22:17", "WIB"))
        self.assertEqual(table["Budi"], ("23:17", "WITA"))
        self.assertEqual(table["Yohanes"], ("00:17", "WIT"))
        self.assertEqual(table["Priya"], ("20:47", "IST"))
        self.assertEqual(table["Sam"], ("10:17", "EST"))
        self.assertEqual(missing, [])

    def test_urut_dari_barat_ke_timur(self):
        rows, _ = build_rows("kenji sam rina lena", TEAM, NOW)
        self.assertEqual([r[0] for r in rows], ["Sam", "Lena", "Rina", "Kenji"])

    def test_waktu_musim_panas(self):
        summer = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
        rows, _ = build_rows("sam lena", TEAM, summer)
        self.assertEqual({r[0]: r[2] for r in rows}, {"Sam": "EDT", "Lena": "CEST"})

    def test_tidak_ditemukan_dan_kosong(self):
        rows, missing = build_rows("rina tono", TEAM, NOW)
        self.assertEqual(missing, ["tono"])
        self.assertIn("Tidak ditemukan: tono", text_table(rows, missing))
        with self.assertRaises(tz_bot.BotError):
            build_rows("", TEAM, NOW)

    def test_cari_dengan_nama_tampilan_atau_lengkap(self):
        self.assertEqual(TEAM.by_name("Rina Kartika")["id"], "U01RINA")
        self.assertEqual(TEAM.by_name("@WAYAN")["id"], "U03WAYAN")


class ResponseTest(unittest.TestCase):
    def test_warna_baris_selang_seling(self):
        rows, missing = build_rows("sam lena rina kenji tono", TEAM, NOW)
        reply = slack_response(rows, missing)
        colors = [a["color"] for a in reply["attachments"]]
        self.assertEqual(colors[:4], ["#2e78c7", "#9cc3ef", "#2e78c7", "#9cc3ef"])
        self.assertEqual(colors[4], "#c0392b")  # baris "tidak ditemukan"
        self.assertEqual(reply["response_type"], "in_channel")
        self.assertIn("*Rina*  22:17 *WIB*", reply["attachments"][2]["text"])
        self.assertIn("Kam 5 Nov", reply["attachments"][3]["text"])  # Tokyo sudah besok

    def test_perintah_lain_dan_teks_kosong(self):
        self.assertEqual(handle_command({"command": "/lain", "text": "x"}, TEAM)["response_type"], "ephemeral")
        self.assertIn("Tulis nama", handle_command({"command": "/tz", "text": ""}, TEAM)["text"])


class SignatureTest(unittest.TestCase):
    def test_tanda_tangan(self):
        body = b"command=%2Ftz&text=rina"
        signature = sign(SECRET, "1700000000", body)
        self.assertTrue(verify(SECRET, "1700000000", body, signature, now=lambda: 1700000100))
        self.assertFalse(verify(SECRET, "1700000000", body + b"x", signature, now=lambda: 1700000100))
        self.assertFalse(verify("salah", "1700000000", body, signature, now=lambda: 1700000100))
        self.assertFalse(verify(SECRET, "1700000000", body, signature, now=lambda: 1700001000))  # kedaluwarsa
        self.assertFalse(verify(SECRET, "bukan-angka", body, signature))
        self.assertFalse(verify(SECRET, None, body, signature))

    def test_contoh_resmi_slack(self):
        # Contoh dari dokumentasi Slack "Verifying requests from Slack".
        secret = "8f742231b10e8888abcd99yyyzzz85a5"
        body = (b"token=xyzz0WbapA4vBCDEFasx0q6G&team_id=T1DC2JH3J&team_domain=testteamnow&channel_id=G8PSS9T3V"
                b"&channel_name=foobar&user_id=U2CERLKJA&user_name=roadrunner&command=%2Fwebhook-collect&text="
                b"&response_url=https%3A%2F%2Fhooks.slack.com%2Fcommands%2FT1DC2JH3J%2F397700885554%2F96rGlfmibIGlgcZRskXaIFfN"
                b"&trigger_id=398738663015.47445629121.803a0bc887a14d10d2c447fce8b6703c")
        self.assertEqual(sign(secret, "1531420618", body),
                         "v0=a2114d57b48eac39b9ad189dd8316235a7b4a8d21a10bd27519666489c69b503")


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fake_slack_api(request, timeout=None):
    url = urllib.parse.urlsplit(request.full_url)
    assert request.get_header("Authorization") == "Bearer xoxb-tes"
    if url.path.endswith("users.list"):
        payload = {"ok": True, "members": TEAM.members}
    else:
        user = dict(urllib.parse.parse_qsl(url.query))["user"]
        member = TEAM.by_id(user)
        payload = {"ok": True, "user": member} if member else {"ok": False, "error": "user_not_found"}
    return FakeResponse(json.dumps(payload).encode())


class SlackDirectoryTest(unittest.TestCase):
    def test_api(self):
        directory = SlackDirectory("xoxb-tes", fake_slack_api)
        self.assertEqual(directory.by_id("U02BUDI")["name"], "budi")
        self.assertIsNone(directory.by_id("UXXXX"))
        self.assertEqual(directory.by_name("lena")["tz"], "Europe/Berlin")


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from http.server import ThreadingHTTPServer
        handler = make_handler(SECRET, SlackDirectory("xoxb-tes", fake_slack_api))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}/slack/tz"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def post(self, text, secret=SECRET, path=None):
        body = urllib.parse.urlencode({"command": "/tz", "text": text, "user_id": "U01RINA"}).encode()
        stamp = str(int(time.time()))
        request = urllib.request.Request(path or self.url, data=body, headers={
            "X-Slack-Request-Timestamp": stamp, "X-Slack-Signature": sign(secret, stamp, body),
            "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_permintaan_bertanda_tangan(self):
        status, reply = self.post("<@U01RINA|rina> <@U06SAM|sam> lena")
        self.assertEqual(status, 200)
        self.assertEqual(len(reply["attachments"]), 3)
        self.assertIn("*Sam*", reply["attachments"][0]["text"])

    def test_tanda_tangan_salah_ditolak(self):
        status, reply = self.post("rina", secret="bukan-rahasia")
        self.assertEqual((status, reply["error"]), (401, "invalid_signature"))

    def test_alamat_lain(self):
        self.assertEqual(self.post("rina", path=self.url.replace("/slack/tz", "/lain"))[0], 404)


class CliTest(unittest.TestCase):
    def test_simulate(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["simulate", "rina", "kenji"]), 0)
        self.assertIn("WIB", out.getvalue())
        self.assertIn("JST", out.getvalue())

    def test_serve_butuh_rahasia(self):
        env = {k: os.environ.pop(k) for k in ("SLACK_SIGNING_SECRET", "SLACK_BOT_TOKEN") if k in os.environ}
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["serve"]), 1)
        finally:
            os.environ.update(env)


if __name__ == "__main__":
    unittest.main()
