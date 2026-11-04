import contextlib
import io
import json
import os
import tempfile
import unittest
import urllib.error
import urllib.parse

from game_poll import (
    PollError,
    connect,
    create_poll,
    format_results,
    game_details,
    get_poll,
    list_polls,
    main,
    results,
    search_games,
    vote,
)

# Data tiruan berbentuk sama dengan jawaban API Steam.
SEARCH = {
    "hollow": [(367520, "Hollow Knight"), (598190, "Hollow Knight - Official Soundtrack")],
    "stardew": [(413150, "Stardew Valley")],
    "elden": [(1245620, "ELDEN RING")],
    "kosong": [],
}
DETAILS = {
    367520: ("Hollow Knight", "game", ["Action", "Adventure", "Indie"]),
    598190: ("Hollow Knight - Official Soundtrack", "music", []),
    413150: ("Stardew Valley", "game", ["Indie", "RPG", "Simulation"]),
    1245620: ("ELDEN RING", "game", ["Action", "RPG"]),
}


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fake_steam(request, timeout=None):
    url = urllib.parse.urlsplit(request.full_url)
    query = dict(urllib.parse.parse_qsl(url.query))
    if url.path.endswith("storesearch/"):
        items = [{"type": "app", "id": i, "name": n} for i, n in SEARCH.get(query["term"].split()[0], [])]
        payload = {"total": len(items), "items": items}
    else:
        app_id = int(query["appids"])
        if app_id in DETAILS:
            name, kind, genres = DETAILS[app_id]
            payload = {str(app_id): {"success": True, "data": {
                "name": name, "type": kind, "genres": [{"id": "1", "description": g} for g in genres]}}}
        else:
            payload = {str(app_id): {"success": False}}
    return FakeResponse(json.dumps(payload).encode())


def offline(request, timeout=None):
    raise urllib.error.URLError("x")


class Clock:
    def __init__(self):
        self.n = 0

    def __call__(self):
        self.n += 1
        return f"2026-11-04T10:00:{self.n:02d}"


class SteamTest(unittest.TestCase):
    def test_cari(self):
        self.assertEqual(search_games("hollow knight", fake_steam)[0], (367520, "Hollow Knight"))
        self.assertEqual(search_games("kosong", fake_steam), [])
        with self.assertRaises(PollError):
            search_games("  ", fake_steam)

    def test_detail(self):
        self.assertEqual(game_details(413150, fake_steam), DETAILS[413150])
        with self.assertRaises(PollError):
            game_details(1, fake_steam)

    def test_jaringan(self):
        with self.assertRaises(PollError) as ctx:
            search_games("x", offline)
        self.assertIn("koneksi", str(ctx.exception))
        with self.assertRaises(PollError):
            search_games("x", lambda r, timeout=None: FakeResponse(b'{"items": null}'))


class PollTest(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")
        self.clock = Clock()
        self.poll = create_poll(self.db, "Main bareng Jumat", "budi", clock=self.clock)
        self.rpg = create_poll(self.db, "Malam RPG", "sari", genre="RPG", clock=self.clock)

    def tearDown(self):
        self.db.close()

    def cast(self, poll, app_id, voter):
        return vote(self.db, poll, app_id, voter, DETAILS[app_id], clock=self.clock)

    def test_buat_dan_daftar(self):
        self.assertEqual(get_poll(self.db, self.rpg)["genre"], "RPG")
        self.assertEqual([row["title"] for row in list_polls(self.db)], ["Malam RPG", "Main bareng Jumat"])
        self.assertEqual([row["title"] for row in list_polls(self.db, "BUDI")], ["Main bareng Jumat"])
        with self.assertRaises(PollError):
            create_poll(self.db, "  ", "budi")
        with self.assertRaises(PollError):
            create_poll(self.db, "x" * 81, "budi")
        with self.assertRaises(PollError):
            get_poll(self.db, 99)

    def test_suara_dan_peringkat(self):
        self.cast(self.poll, 413150, "rina")  # Stardew lebih dulu dapat suara
        self.cast(self.poll, 367520, "sari")
        self.cast(self.poll, 367520, "budi")
        self.cast(self.poll, 413150, "budi")
        self.cast(self.poll, 1245620, "dimas")
        self.cast(self.poll, 367520, "dimas")
        rows = results(self.db, self.poll)
        self.assertEqual([(r["name"], r["votes"]) for r in rows],
                         [("Hollow Knight", 3), ("Stardew Valley", 2), ("ELDEN RING", 1)])
        self.assertEqual(len(results(self.db, self.poll, top=2)), 2)

    def test_seri_yang_lebih_dulu_di_atas(self):
        self.cast(self.poll, 1245620, "a")
        self.cast(self.poll, 413150, "b")
        self.assertEqual([r["name"] for r in results(self.db, self.poll)], ["ELDEN RING", "Stardew Valley"])

    def test_suara_ganda_ditolak(self):
        self.cast(self.poll, 367520, "sari")
        with self.assertRaises(PollError) as ctx:
            self.cast(self.poll, 367520, "sari")
        self.assertIn("sudah memilih", str(ctx.exception))
        self.cast(self.rpg, 413150, "sari")  # polling lain boleh

    def test_bukan_game_ditolak(self):
        with self.assertRaises(PollError) as ctx:
            self.cast(self.poll, 598190, "sari")
        self.assertIn("bukan game", str(ctx.exception))

    def test_batas_genre(self):
        with self.assertRaises(PollError) as ctx:
            self.cast(self.rpg, 367520, "sari")
        self.assertIn("Action, Adventure, Indie", str(ctx.exception))
        self.cast(self.rpg, 1245620, "sari")
        self.assertEqual(results(self.db, self.rpg)[0]["name"], "ELDEN RING")

    def test_data_game_diperbarui_tanpa_menghapus_suara(self):
        self.cast(self.poll, 367520, "sari")
        vote(self.db, self.rpg, 1245620, "x", DETAILS[1245620])
        vote(self.db, self.poll, 367520, "budi", ("Hollow Knight (baru)", "game", ["Action"]))
        rows = results(self.db, self.poll)
        self.assertEqual((rows[0]["name"], rows[0]["votes"]), ("Hollow Knight (baru)", 2))

    def test_format(self):
        self.assertIn("Belum ada suara.", format_results(get_poll(self.db, self.poll), []))
        self.cast(self.poll, 367520, "a")
        self.cast(self.poll, 367520, "b")
        self.cast(self.poll, 413150, "a")
        text = format_results(get_poll(self.db, self.rpg), results(self.db, self.rpg))
        self.assertIn("genre RPG", text)
        text = format_results(get_poll(self.db, self.poll), results(self.db, self.poll))
        self.assertIn(" 1. Hollow Knight   " + "#" * 20 + " 2", text)
        self.assertIn(" 2. Stardew Valley  " + "#" * 10 + " 1", text)


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "polls.db")

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *argv, answers=()):
        out, err = io.StringIO(), io.StringIO()
        replies = iter(answers)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--db", self.db, *argv], urlopen=fake_steam, ask=lambda _p: next(replies))
        return code, out.getvalue(), err.getvalue()

    def test_alur_lengkap(self):
        self.assertEqual(self.run_main("create", "Main bareng", "--owner", "budi")[0], 0)
        self.assertEqual(self.run_main("vote", "1", "hollow knight", "--voter", "sari")[0], 0)
        self.assertEqual(self.run_main("vote", "1", "stardew", "--voter", "sari")[0], 0)
        self.assertEqual(self.run_main("vote", "1", "--id", "367520", "--voter", "budi")[0], 0)
        code, out, _ = self.run_main("results", "1", "--top", "5")
        self.assertEqual(code, 0)
        self.assertLess(out.index("Hollow Knight"), out.index("Stardew Valley"))
        code, out, _ = self.run_main("polls", "--owner", "budi")
        self.assertIn("3 suara", out)

    def test_pick_dan_interaktif(self):
        self.run_main("create", "Main", "--owner", "budi")
        code, _, err = self.run_main("vote", "1", "hollow", "--pick", "2", "--voter", "a")
        self.assertEqual(code, 1)
        self.assertIn("bukan game", err)
        self.assertEqual(self.run_main("vote", "1", "hollow", "--pick", "5", "--voter", "a")[0], 1)
        code, out, _ = self.run_main("vote", "1", "--voter", "a", answers=["kosong", "elden", "1"])
        self.assertEqual(code, 0)
        self.assertIn("Tidak ada yang cocok", out)
        self.assertIn("ELDEN RING", out)
        self.assertEqual(self.run_main("vote", "1", "--voter", "a", answers=[""])[0], 1)

    def test_error(self):
        code, _, err = self.run_main("vote", "7", "hollow", "--voter", "a")
        self.assertEqual(code, 1)
        self.assertIn("#7 tidak ada", err)
        self.assertEqual(self.run_main("results", "7")[0], 1)
        self.assertIn("Belum ada polling.", self.run_main("polls")[1])
        code, out, _ = self.run_main("search", "hollow")
        self.assertIn("(id 367520)", out)


if __name__ == "__main__":
    unittest.main()
