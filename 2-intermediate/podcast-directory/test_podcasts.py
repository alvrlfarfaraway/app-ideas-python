import contextlib
import io
import json
import os
import tempfile
import time
import unittest
import urllib.error
import urllib.parse
from datetime import datetime, timezone

from PIL import Image

import podcasts
from podcasts import Favorites, PodcastError, format_date, lookup, main, merge, parse_date, parse_feed, search

FEED_A = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
<channel>
  <title>Ngoding Santai</title>
  <link>https://example.com/ngoding</link>
  <itunes:image href="https://example.com/art-a.png"/>
  <item><title>Episode 2: Python &amp; Data</title><link>https://example.com/ep2</link>
        <pubDate>Tue, 03 Nov 2026 07:00:00 +0700</pubDate></item>
  <item><title>Episode 1: Halo</title><guid>https://example.com/ep1</guid>
        <pubDate>Mon, 05 Oct 2026 10:00:00 GMT</pubDate><itunes:image href="https://example.com/ep1.png"/></item>
  <item><title>Tanpa tanggal</title><link>javascript:alert(1)</link></item>
  <item><title></title><link>https://example.com/kosong</link></item>
</channel></rss>"""
FEED_B = b"""<rss version="2.0"><channel><title>Kopi Pagi</title><image><url>https://example.com/art-b.png</url></image>
  <item><title>Kopi 1</title><link>https://example.com/k1</link><pubDate>Sun, 01 Nov 2026 06:00:00 +0700</pubDate></item>
</channel></rss>"""
ITUNES = {"resultCount": 2, "results": [
    {"collectionId": 11, "collectionName": "Ngoding Santai", "artistName": "Budi", "feedUrl": "https://example.com/a.xml",
     "artworkUrl100": "https://example.com/art-a.png"},
    {"collectionId": 12, "collectionName": "Tanpa Feed", "artistName": "X"},
]}


def png():
    buffer = io.BytesIO()
    Image.new("RGB", (100, 100), (200, 0, 0)).save(buffer, "PNG")
    return buffer.getvalue()


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fake_net(request, timeout=None):
    url = request.full_url
    path = urllib.parse.urlsplit(url).path
    routes = {"/search": json.dumps(ITUNES).encode(), "/lookup": json.dumps(ITUNES).encode(),
              "/a.xml": FEED_A, "/b.xml": FEED_B, "/art-a.png": png(), "/art-b.png": png()}
    if path in routes:
        return FakeResponse(routes[path])
    raise urllib.error.HTTPError(url, 404, "x", {}, None)


PODCAST_A = {"id": 11, "name": "Ngoding Santai", "author": "Budi", "feed": "https://example.com/a.xml",
             "artwork": "https://example.com/art-a.png"}
PODCAST_B = {"id": 13, "name": "Kopi Pagi", "author": "Sari", "feed": "https://example.com/b.xml",
             "artwork": "https://example.com/art-b.png"}


class FeedTest(unittest.TestCase):
    def test_episode_terurut_dan_lengkap(self):
        info, episodes = parse_feed(FEED_A)
        self.assertEqual(info["name"], "Ngoding Santai")
        self.assertEqual(info["artwork"], "https://example.com/art-a.png")
        self.assertEqual([e["title"] for e in episodes], ["Episode 2: Python & Data", "Episode 1: Halo", "Tanpa tanggal"])
        self.assertEqual(episodes[0]["link"], "https://example.com/ep2")
        self.assertEqual(episodes[1]["link"], "https://example.com/ep1")  # dari guid
        self.assertEqual(episodes[2]["link"], "")  # javascript: dibuang
        self.assertEqual(episodes[1]["image"], "https://example.com/ep1.png")
        self.assertEqual(episodes[0]["image"], "https://example.com/art-a.png")  # gambar podcast

    def test_feed_rusak(self):
        for data in (b"<rss><channel>", b"<html></html>", b"bukan xml"):
            with self.assertRaises(PodcastError):
                parse_feed(data)

    def test_entitas_eksternal_tidak_dimuat(self):
        evil = b"""<?xml version="1.0"?><!DOCTYPE rss [<!ENTITY x SYSTEM "file:///c:/windows/win.ini">]>
<rss><channel><title>&x;</title></channel></rss>"""
        try:
            info, _ = parse_feed(evil)
        except PodcastError:
            return  # ditolak juga aman
        self.assertNotIn("fonts", info["name"].lower())

    def test_tanggal(self):
        moment = parse_date("Tue, 03 Nov 2026 07:00:00 +0700")
        self.assertEqual(moment.astimezone(timezone.utc).hour, 0)
        self.assertEqual(format_date(moment), "3 Nov 2026")
        self.assertIsNone(parse_date("bukan tanggal"))
        self.assertEqual(format_date(None), "-")

    def test_gabung_dan_saring(self):
        _, a = parse_feed(FEED_A, "A")
        _, b = parse_feed(FEED_B, "B")
        rows = merge({"A": a, "B": b})
        self.assertEqual([r["title"] for r in rows][:3], ["Episode 2: Python & Data", "Kopi 1", "Episode 1: Halo"])
        self.assertEqual({r["podcast"] for r in merge({"A": a, "B": b}, {"B"})}, {"B"})


class ItunesTest(unittest.TestCase):
    def test_cari_dan_lookup(self):
        results = search("ngoding", fake_net)
        self.assertEqual([p["id"] for p in results], [11])  # yang tanpa feed dibuang
        self.assertEqual(lookup(11, fake_net)["feed"], "https://example.com/a.xml")
        with self.assertRaises(PodcastError):
            lookup(12, fake_net)
        with self.assertRaises(PodcastError):
            search("  ", fake_net)

    def test_alamat_aneh_ditolak(self):
        with self.assertRaises(PodcastError):
            podcasts.fetch("file:///c:/rahasia.txt", fake_net)


class FavoritesTest(unittest.TestCase):
    def test_tambah_hapus_dan_simpan(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sub", "fav.json")
            fav = Favorites(path)
            fav.add(PODCAST_A)
            with self.assertRaises(PodcastError):
                fav.add(PODCAST_A)
            self.assertEqual([p["id"] for p in Favorites(path).items], [11])
            fav.remove(11)
            self.assertEqual(Favorites(path).items, [])
            with self.assertRaises(PodcastError):
                fav.remove(11)
            with open(path, "w") as handle:
                handle.write("{rusak")
            with self.assertRaises(PodcastError):
                Favorites(path)


class CliTest(unittest.TestCase):
    def test_alur(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "fav.json")

            def run(*argv):
                out = io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                    code = main(list(argv), urlopen=fake_net, favorites_path=path)
                return code, out.getvalue()
            self.assertIn("Ngoding Santai", run("search", "ngoding")[1])
            self.assertEqual(run("add", "11")[0], 0)
            code, out = run("episodes", "-n", "2")
            self.assertIn("Ngoding Santai: 3 episode", out)
            self.assertIn("3 Nov 2026", out)
            self.assertEqual(run("add", "12")[0], 1)
            self.assertEqual(run("remove", "11")[0], 0)
            self.assertIn("Belum ada favorit", run("list")[1])


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.tmp = tempfile.TemporaryDirectory()
        fav = Favorites(os.path.join(self.tmp.name, "f.json"))
        fav.add(PODCAST_A)
        fav.add(PODCAST_B)
        self.opened, self.notes = [], []
        self.app = podcasts.PodcastApp(self.root, fav, urlopen=fake_net, open_url=self.opened.append,
                                       notify=self.notes.append)
        deadline = time.monotonic() + 5
        while not self.app.rows and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.02)

    def tearDown(self):
        self.root.destroy()
        self.tmp.cleanup()

    def test_tabel_dan_ringkasan(self):
        self.assertEqual(len(self.app.rows), 4)
        items = self.app.tree.get_children()
        self.assertEqual(self.app.tree.item(items[0], "values")[0], "Episode 2: Python & Data")
        self.assertEqual([self.app.tree.item(i, "tags")[0] for i in items], ["even", "odd", "even", "odd"])
        labels = [w.winfo_children()[0].cget("text") for w in self.app.summary.winfo_children()]
        self.assertEqual(labels, ["Ngoding Santai: 3 episode", "Kopi Pagi: 1 episode"])
        self.assertEqual(set(self.app.icons), {"Ngoding Santai", "Kopi Pagi"})

    def test_saring_dan_buka(self):
        self.app.show["Ngoding Santai"].set(False)
        self.app.fill_table()
        self.assertEqual(len(self.app.rows), 1)
        self.app.open_row(self.app.tree.get_children()[0])
        self.assertEqual(self.opened, ["https://example.com/k1"])

    def test_hapus(self):
        self.app.remove(PODCAST_B)
        self.assertEqual(len(self.app.rows), 3)
        self.assertEqual([p["id"] for p in self.app.favorites.items], [11])


if __name__ == "__main__":
    unittest.main()
