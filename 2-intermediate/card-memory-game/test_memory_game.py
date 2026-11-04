import json
import os
import random
import tempfile
import unittest

from memory_game import (
    COLORS,
    HIDDEN,
    LEVELS,
    MATCHED,
    SHAPES,
    VISIBLE,
    MemoryGame,
    Stats,
    blend,
    format_seconds,
    pick_symbols,
    shape_points,
)


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make_game(size=4, limit=60):
    clock = FakeClock()
    game = MemoryGame(size, limit, rng=random.Random(3), clock=clock)
    return game, clock


def pair_of(game, index):
    return next(j for j, card in enumerate(game.cards) if j != index and card == game.cards[index])


def non_pair(game, index):
    return next(j for j, card in enumerate(game.cards)
                if j != index and card != game.cards[index] and game.states[j] == HIDDEN)


class SymbolTest(unittest.TestCase):
    def test_simbol_unik(self):
        for pairs in (1, 8, 18, 32):
            symbols = pick_symbols(pairs, random.Random(pairs))
            self.assertEqual(len(symbols), pairs)
            self.assertEqual(len(set(symbols)), pairs)
            for shape, color in symbols:
                self.assertIn(shape, SHAPES)
                self.assertIn(color, COLORS)

    def test_level_mudah_tidak_bergantung_pada_warna(self):
        for seed in range(20):
            shapes = [shape for shape, _ in pick_symbols(8, random.Random(seed))]
            self.assertEqual(len(set(shapes)), 8)

    def test_batas(self):
        for bad in (0, 33):
            with self.assertRaises(ValueError):
                pick_symbols(bad)


class BoardTest(unittest.TestCase):
    def test_grid_n_kali_n_berpasangan(self):
        for size in (2, 4, 6, 8):
            game = MemoryGame(size, rng=random.Random(size))
            self.assertEqual(len(game.cards), size * size)
            self.assertTrue(all(game.cards.count(card) == 2 for card in game.cards))
            self.assertTrue(all(state == HIDDEN for state in game.states))

    def test_ukuran_ganjil_ditolak(self):
        for bad in (0, 1, 3, 5):
            with self.assertRaises(ValueError):
                MemoryGame(bad)

    def test_level(self):
        sizes = [level.size for level in LEVELS]
        limits = [level.time_limit for level in LEVELS]
        self.assertEqual(sizes, sorted(sizes))
        self.assertTrue(all(size % 2 == 0 for size in sizes))
        # Makin sulit, waktu per pasangan makin sedikit.
        per_pair = [limit / (size * size / 2) for size, limit in zip(sizes, limits)]
        self.assertEqual(per_pair, sorted(per_pair, reverse=True))


class PlayTest(unittest.TestCase):
    def test_tidak_bisa_klik_sebelum_mulai(self):
        game, _ = make_game()
        self.assertEqual(game.flip(0), "ignored")
        self.assertEqual(game.states[0], HIDDEN)

    def test_kartu_cocok(self):
        game, _ = make_game()
        game.start()
        self.assertEqual(game.flip(0), "first")
        self.assertEqual(game.states[0], VISIBLE)
        self.assertEqual(game.flip(pair_of(game, 0)), "match")
        self.assertEqual(game.states[0], MATCHED)
        self.assertEqual(game.moves, 1)

    def test_kartu_tidak_cocok_ditutup_lagi(self):
        game, _ = make_game()
        game.start()
        other = non_pair(game, 0)
        game.flip(0)
        self.assertEqual(game.flip(other), "mismatch")
        self.assertEqual((game.states[0], game.states[other]), (VISIBLE, VISIBLE))
        self.assertEqual(game.hide_pending(), (0, other))
        self.assertEqual((game.states[0], game.states[other]), (HIDDEN, HIDDEN))
        self.assertEqual(game.hide_pending(), ())

    def test_klik_berikutnya_langsung_menutup_pasangan_salah(self):
        game, _ = make_game()
        game.start()
        other = non_pair(game, 0)
        game.flip(0)
        game.flip(other)
        third = next(i for i in range(16) if i not in (0, other))
        self.assertEqual(game.flip(third), "first")
        self.assertEqual(game.states[0], HIDDEN)
        self.assertEqual(game.states[other], HIDDEN)
        self.assertEqual(game.states[third], VISIBLE)

    def test_klik_kartu_terbuka_atau_cocok_diabaikan(self):
        game, _ = make_game()
        game.start()
        game.flip(0)
        self.assertEqual(game.flip(0), "ignored")  # kartu yang sama dua kali
        self.assertEqual(game.states[0], VISIBLE)
        game.flip(pair_of(game, 0))
        self.assertEqual(game.flip(0), "ignored")
        self.assertEqual(game.flip(-1), "ignored")
        self.assertEqual(game.flip(16), "ignored")
        self.assertEqual(game.moves, 1)

    def test_menang_dengan_waktu(self):
        game, clock = make_game()
        game.start()
        done = set()
        results = []
        for i in range(16):
            if i in done:
                continue
            j = pair_of(game, i)
            clock.now += 2
            game.flip(i)
            results.append(game.flip(j))
            done |= {i, j}
        self.assertEqual(results[-1], "won")
        self.assertEqual(results[:-1], ["match"] * 7)
        self.assertEqual(game.result, "won")
        self.assertEqual(game.elapsed(), 16)
        clock.now += 100
        self.assertEqual(game.elapsed(), 16)  # waktu berhenti setelah menang
        self.assertFalse(game.check_timeout())
        self.assertEqual(game.flip(0), "ignored")

    def test_kalah_kalau_waktu_habis(self):
        game, clock = make_game(limit=60)
        game.start()
        clock.now += 30
        self.assertEqual(game.remaining(), 30)
        self.assertFalse(game.check_timeout())
        clock.now += 31
        self.assertEqual(game.flip(0), "lost")
        self.assertEqual(game.result, "lost")
        self.assertEqual(game.remaining(), 0)
        self.assertEqual(game.elapsed(), 60)
        self.assertEqual(game.flip(1), "ignored")

    def test_tanpa_batas_waktu(self):
        game = MemoryGame(2, None, rng=random.Random(1), clock=FakeClock())
        game.start()
        self.assertIsNone(game.remaining())
        self.assertFalse(game.check_timeout())


class StatsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "sub", "stats.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_catat_dan_simpan(self):
        stats = Stats(self.path)
        self.assertEqual(stats.summary("easy"), "Menang 0 | Kalah 0 | Terbaik -")
        self.assertTrue(stats.record("easy", True, 50.04))
        self.assertFalse(stats.record("easy", True, 61))
        self.assertTrue(stats.record("easy", True, 42.36))
        stats.record("easy", False)
        stats.record("hard", False)
        again = Stats(self.path)
        self.assertEqual(again.data["easy"], {"wins": 3, "losses": 1, "best": 42.4})
        self.assertEqual(again.data["hard"]["losses"], 1)
        self.assertEqual(again.summary("easy"), "Menang 3 | Kalah 1 | Terbaik 0:42,4")

    def test_berkas_rusak_tidak_membuat_crash(self):
        os.makedirs(os.path.dirname(self.path))
        for content in ("{rusak", "[]", json.dumps({"easy": {"wins": -5, "losses": "x", "best": -1}})):
            with open(self.path, "w", encoding="utf-8") as handle:
                handle.write(content)
            stats = Stats(self.path)
            self.assertEqual(stats.data["easy"], {"wins": 0, "losses": 0, "best": None})


class HelperTest(unittest.TestCase):
    def test_format_seconds(self):
        self.assertEqual(format_seconds(0), "0:00,0")
        self.assertEqual(format_seconds(9), "0:09,0")
        self.assertEqual(format_seconds(62.34), "1:02,3")
        self.assertEqual(format_seconds(59.96), "1:00,0")
        self.assertEqual(format_seconds(300), "5:00,0")

    def test_blend(self):
        self.assertEqual(blend("#000000", "#ffffff", 0), "#000000")
        self.assertEqual(blend("#000000", "#ffffff", 1), "#ffffff")
        self.assertEqual(blend("#000000", "#ffffff", 0.5), "#808080")

    def test_shape_points(self):
        self.assertIsNone(shape_points("circle", 0, 0, 10))
        self.assertEqual(len(shape_points("star", 0, 0, 10)), 20)
        self.assertEqual(len(shape_points("hexagon", 0, 0, 10)), 12)
        for shape in ("square", "triangle", "diamond", "cross"):
            points = shape_points(shape, 50, 50, 10)
            self.assertEqual(len(points) % 2, 0)
            self.assertTrue(all(39 <= v <= 61 for v in points), shape)


if __name__ == "__main__":
    unittest.main()
