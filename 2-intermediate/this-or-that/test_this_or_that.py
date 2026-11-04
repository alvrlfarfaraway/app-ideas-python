import contextlib
import io
import os
import random
import sqlite3
import tempfile
import unittest
from collections import Counter

from PIL import Image

import this_or_that
from this_or_that import (
    BUILTIN,
    CARD,
    Matchmaker,
    connect,
    emoji_card,
    format_leaderboard,
    leaderboard,
    load_items,
    main,
    photo_card,
    vote,
)


class ItemsTest(unittest.TestCase):
    def test_kartu_bawaan(self):
        items = load_items()
        self.assertEqual(len(items), 16)
        image = items[0][1]()
        self.assertEqual(image.size, CARD)

    def test_emoji_berwarna(self):
        card = emoji_card("Bakso", "🍲", "#ffffff")
        colors = {color for _, color in card.crop((80, 40, 240, 220)).getcolors(1 << 20)}
        self.assertGreater(len(colors), 10)  # lebih dari sekadar hitam-putih

    def test_folder_sendiri(self):
        with tempfile.TemporaryDirectory() as tmp:
            Image.new("RGB", (600, 300), "red").save(os.path.join(tmp, "kucing_oren.jpg"))
            Image.new("RGB", (200, 400), "blue").save(os.path.join(tmp, "kucing-hitam.png"))
            open(os.path.join(tmp, "catatan.txt"), "w").close()
            items = load_items(tmp)
            self.assertEqual([name for name, _ in items], ["kucing-hitam", "kucing_oren"])
            self.assertEqual(items[1][1]().size, CARD)
            os.remove(os.path.join(tmp, "kucing-hitam.png"))
            with self.assertRaises(ValueError):
                load_items(tmp)  # tinggal satu gambar

    def test_foto_dipotong_persegi(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.png")
            image = Image.new("RGB", (300, 100), "red")
            image.paste((0, 0, 255), (0, 0, 100, 100))  # sepertiga kiri biru, akan terpotong
            image.save(path)
            card = photo_card(path)
            self.assertEqual(card.getpixel((10, 10)), (255, 0, 0))


class MatchmakerTest(unittest.TestCase):
    def test_tidak_pernah_melawan_diri_sendiri(self):
        m = Matchmaker(list("abcde"), random.Random(1))
        for _ in range(500):
            a, b = m.next_pair()
            self.assertNotEqual(a, b)

    def test_pasangan_sama_tidak_berturut_turut(self):
        m = Matchmaker(["a", "b", "c"], random.Random(2))
        previous = None
        for _ in range(300):
            pair = set(m.next_pair())
            self.assertNotEqual(pair, previous)
            previous = pair

    def test_semua_item_tampil_merata(self):
        names = [n for n, *_ in BUILTIN]
        m = Matchmaker(names, random.Random(3))
        counts = Counter(name for _ in range(400) for name in m.next_pair())
        self.assertEqual(set(counts), set(names))
        self.assertLessEqual(max(counts.values()) - min(counts.values()), 4)

    def test_dua_item(self):
        m = Matchmaker(["a", "b"], random.Random(4))
        self.assertEqual({frozenset(m.next_pair()) for _ in range(5)}, {frozenset("ab")})
        with self.assertRaises(ValueError):
            Matchmaker(["a"])


class VoteTest(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")

    def tearDown(self):
        self.db.close()

    def test_papan_peringkat(self):
        for winner, loser in (("Bakso", "Sate"), ("Bakso", "Kopi"), ("Sate", "Kopi"), ("Kopi", "Donat"),
                              ("Donat", "Sate")):
            vote(self.db, winner, loser)
        rows = leaderboard(self.db)
        self.assertEqual(rows[0], ("Bakso", 2, 2, 100.0))
        self.assertEqual([r[0] for r in rows], ["Bakso", "Donat", "Kopi", "Sate"])  # seri 1 menang: % lalu nama
        self.assertIn(" 1. Bakso", format_leaderboard(rows))

    def test_maksimal_sepuluh(self):
        for i in range(15):
            vote(self.db, f"item{i:02d}", "lain")
        self.assertEqual(len(leaderboard(self.db)), 10)
        self.assertEqual(format_leaderboard([]), "Belum ada suara.")

    def test_tidak_bisa_memilih_diri_sendiri(self):
        with self.assertRaises(sqlite3.IntegrityError):
            vote(self.db, "Bakso", "Bakso")

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "v.db")
            db = connect(path)
            vote(db, "Bakso", "Sate")
            db.close()
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(["--db", path, "--top"]), 0)
            self.assertIn("Bakso", out.getvalue())


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.db = connect(":memory:")
        self.app = this_or_that.ThisOrThatApp(self.root, load_items(), self.db, random.Random(5), animate=False)

    def tearDown(self):
        self.root.destroy()
        self.db.close()

    def test_pilih_menyimpan_suara_dan_ganti_pasangan(self):
        first = self.app.pair
        winner = self.app.choose(1)
        self.assertEqual(winner, first[1])
        self.assertEqual(self.db.execute("SELECT winner, loser FROM votes").fetchall(), [(first[1], first[0])])
        self.assertNotEqual(set(self.app.pair), set(first))
        self.assertIn(winner, self.app.board.get("1.0", "end"))

    def test_lewati_tidak_menyimpan(self):
        self.app.show_next()
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM votes").fetchone()[0], 0)

    def test_animasi_tidak_bisa_diklik_saat_bergerak(self):
        self.app.animate = True
        self.app.show_next()
        self.assertTrue(self.app.busy)
        self.assertIsNone(self.app.choose(0))
        for _ in range(this_or_that.ANIMATION_FRAMES + 5):
            self.root.update()
            self.root.after(this_or_that.FRAME_MS + 2)
        self.assertFalse(self.app.busy)
        self.assertEqual(self.app.canvas.coords(self.app.cards[0])[0], self.app.x_for(0))


if __name__ == "__main__":
    unittest.main()
