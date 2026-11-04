import pathlib
import random
import time
import statistics
import tempfile
import unittest
import wave

import highstriker
from highstriker import (
    MAX_STRENGTH,
    MIN_STRENGTH,
    RATE,
    Scoreboard,
    make_sounds,
    peak_fraction,
    points_for,
    puck_path,
    strike_strength,
)


class PointsTest(unittest.TestCase):
    def test_skala_spesifikasi(self):
        cases = ((0.0, 0), (0.1249, 0), (0.125, 1), (0.2499, 1), (0.25, 2), (0.4999, 2), (0.5, 3),
                 (0.7499, 3), (0.75, 4), (0.9999, 4), (1.0, 5))
        for fraction, points in cases:
            self.assertEqual(points_for(fraction), points, fraction)

    def test_tinggi_kuadrat_kekuatan_dibatasi_bel(self):
        self.assertAlmostEqual(peak_fraction(0.5), 0.25)
        self.assertAlmostEqual(peak_fraction(0.9), 0.81)
        self.assertEqual(peak_fraction(1.0), 1.0)
        self.assertEqual(peak_fraction(1.3), 1.0)


class StrengthTest(unittest.TestCase):
    def test_distribusi(self):
        rng = random.Random(0)
        values = [strike_strength(rng) for _ in range(20000)]
        self.assertTrue(all(MIN_STRENGTH <= v <= MAX_STRENGTH for v in values))
        self.assertAlmostEqual(statistics.mean(values), 0.82, delta=0.01)
        bell = sum(peak_fraction(v) >= 1 for v in values) / len(values)
        self.assertGreater(bell, 0.14)  # bel bisa dicapai, tapi tidak setiap kali
        self.assertLess(bell, 0.23)

    def test_dapat_diulang_dengan_seed(self):
        a = [strike_strength(random.Random(7)) for _ in range(3)]
        b = [strike_strength(random.Random(7)) for _ in range(3)]
        self.assertEqual(a, b)


class PathTest(unittest.TestCase):
    def test_naik_lalu_turun(self):
        for strength in (0.3, 0.7, 0.95):
            path = puck_path(strength)
            peak = path.index(max(path))
            self.assertEqual(path[0], 0.0)
            self.assertEqual(path[-1], 0.0)
            self.assertAlmostEqual(max(path), strength ** 2)
            self.assertEqual(path[:peak + 1], sorted(path[:peak + 1]))  # naik terus
            self.assertEqual(path[peak:], sorted(path[peak:], reverse=True))  # lalu turun terus

    def test_melambat_saat_naik(self):
        path = puck_path(0.8)
        peak = path.index(max(path))
        steps = [b - a for a, b in zip(path[:peak], path[1:peak])]
        self.assertGreater(steps[0], steps[-1])

    def test_kena_bel(self):
        path = puck_path(1.2)
        self.assertEqual(max(path), 1.0)
        self.assertTrue(all(0 <= p <= 1 for p in path))
        # Pukulan lebih kuat menyentuh bel lebih cepat.
        self.assertLess(path.index(1.0), puck_path(1.0).index(1.0))


class ScoreboardTest(unittest.TestCase):
    def test_hitungan_dan_ucapan_sekali(self):
        board = Scoreboard()
        self.assertEqual(board.record(0.6), (3, False, False))
        self.assertEqual(board.record(1.0), (5, True, False))
        self.assertEqual(board.record(0.3), (2, False, True))  # 10 poin tercapai
        self.assertEqual(board.record(1.0), (5, True, False))  # ucapan tidak diulang
        self.assertEqual(board.summary(), "Bel berbunyi 2 kali dari 4 pukulan | Poin 15")
        board.clear()
        self.assertEqual(board.summary(), "Bel berbunyi 0 kali dari 0 pukulan | Poin 0")
        board.record(1.0)
        board.record(1.0)
        self.assertTrue(board.congratulated)  # setelah clear, ucapan bisa muncul lagi


class SoundTest(unittest.TestCase):
    def test_berkas_wav_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_sounds(tmp)
            self.assertEqual(set(paths), {"rail", "bell", "points-0", "points-1", "points-2", "points-3", "points-4"})
            durations = {}
            for name, path in paths.items():
                with wave.open(path, "rb") as handle:
                    self.assertEqual(handle.getframerate(), RATE)
                    self.assertEqual(handle.getnchannels(), 1)
                    self.assertEqual(handle.getsampwidth(), 2)
                    durations[name] = handle.getnframes() / RATE
                    frames = handle.readframes(handle.getnframes())
                self.assertGreater(max(frames), 0, name)  # tidak senyap
            self.assertAlmostEqual(durations["bell"], 1.6, places=2)
            self.assertLess(durations["rail"], 1)
            self.assertEqual(len({pathlib.Path(p).read_bytes() for p in paths.values()}), len(paths))  # semuanya beda


class FakeSound:
    def __init__(self):
        self.played = []

    def play(self, name):
        self.played.append(name)


class FixedRandom(random.Random):
    """Kekuatan pukulan ditentukan tes."""

    def __init__(self, strengths):
        super().__init__(0)
        self.strengths = list(strengths)

    def gauss(self, mu=0.0, sigma=1.0):
        return self.strengths.pop(0)


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.sound = FakeSound()
        self.alerts = []

    def tearDown(self):
        self.root.destroy()

    def make(self, strengths):
        return highstriker.HighStrikerApp(self.root, rng=FixedRandom(strengths), sound=self.sound,
                                          alert=self.alerts.append)

    def run_strike(self, app):
        app.strike()
        while app.animating:
            if app.job:
                self.root.after_cancel(app.job)
            app.animate()

    def test_pukulan_lemah_dan_kena_bel(self):
        app = self.make([0.6, 1.1])
        self.run_strike(app)
        self.assertEqual(app.board.attempts, 1)
        self.assertEqual(app.board.points, 2)  # 0,6² = 0,36 -> 2 poin
        self.assertEqual(self.sound.played, ["rail", "points-2"])
        self.assertIn("36%", app.message.get())
        self.run_strike(app)
        self.assertEqual(app.board.bells, 1)
        self.assertEqual(self.sound.played[-1], "bell")
        self.assertIn("Bel berbunyi 1 kali dari 2 pukulan | Poin 7", app.score.get())
        self.assertEqual(str(app.strike_button.cget("state")), "normal")

    def test_ucapan_selamat_dan_clear(self):
        app = self.make([1.1, 1.1, 1.1])
        for _ in range(2):
            self.run_strike(app)
        deadline = time.monotonic() + 3
        while not self.alerts and time.monotonic() < deadline:  # tunggu after(400) yang menampilkan ucapan
            self.root.update()
            time.sleep(0.02)
        self.assertEqual(len(self.alerts), 1)
        self.assertIn("10 poin", self.alerts[0])
        app.clear()
        self.assertIn("0 kali dari 0 pukulan", app.score.get())

    def test_tidak_bisa_memukul_saat_puck_bergerak(self):
        app = self.make([0.9, 0.9])
        app.strike()
        app.strike()  # diabaikan
        self.assertEqual(self.sound.played, ["rail"])


if __name__ == "__main__":
    unittest.main()
