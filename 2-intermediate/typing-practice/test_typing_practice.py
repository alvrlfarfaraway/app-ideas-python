import os
import random
import tempfile
import time
import unittest
import wave

import typing_practice as tp
from typing_practice import MIN_INTERVAL, START_INTERVAL, STEP, Session, pick_word


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def session():
    clock = Clock()
    return Session(random.Random(1), clock), clock


class SessionTest(unittest.TestCase):
    def test_belum_mulai(self):
        s, _ = session()
        self.assertEqual(s.type("a"), "idle")
        self.assertEqual(s.remaining(), 0)

    def test_kata_benar(self):
        s, _ = session()
        word = s.start()
        for i in range(1, len(word)):
            self.assertEqual(s.type(word[:i]), "typing")
        self.assertEqual(s.type(word.upper()), "correct")  # huruf besar tetap dianggap benar
        self.assertEqual((s.successes, s.attempts), (1, 1))
        self.assertEqual(s.interval, START_INTERVAL - STEP)
        self.assertNotEqual(s.word, word)  # kata baru

    def test_huruf_salah(self):
        s, _ = session()
        word = s.start()
        self.assertEqual(s.type(word[0] + "#"), "wrong")
        self.assertEqual((s.successes, s.attempts), (0, 1))
        self.assertEqual(s.word, word)  # tetap kata yang sama
        self.assertEqual(s.interval, START_INTERVAL)

    def test_waktu_habis(self):
        s, clock = session()
        word = s.start()
        clock.now += START_INTERVAL - 0.01
        self.assertIsNone(s.check_time())
        clock.now += 0.02
        self.assertEqual(s.check_time(), "timeout")
        self.assertEqual((s.successes, s.attempts), (0, 1))
        self.assertNotEqual(s.word, word)
        self.assertAlmostEqual(s.remaining(), START_INTERVAL)
        clock.now += START_INTERVAL + 1
        self.assertEqual(s.type(s.word), "timeout")  # mengetik setelah waktu habis tidak dihitung benar

    def test_waktu_makin_singkat_sampai_batas(self):
        s, _ = session()
        s.start()
        for _ in range(40):
            s.type(s.word)
        self.assertEqual(s.interval, MIN_INTERVAL)
        self.assertEqual(s.successes, 40)

    def test_mulai_lagi_mereset_skor(self):
        s, _ = session()
        s.start()
        s.type(s.word)
        s.stop()
        self.assertEqual(s.type("a"), "idle")
        s.start()
        self.assertEqual((s.successes, s.attempts, s.interval), (0, 0, START_INTERVAL))

    def test_kata_tidak_berulang(self):
        rng = random.Random(2)
        previous = None
        for _ in range(300):
            word = pick_word(rng, previous)
            self.assertNotEqual(word, previous)
            previous = word
        self.assertTrue(all(w.isalpha() and w.islower() for w in tp.WORDS))


class SoundTest(unittest.TestCase):
    def test_tiga_bunyi_berbeda(self):
        with tempfile.TemporaryDirectory() as tmp:
            contents = set()
            for name, spec in tp.SOUNDS.items():
                path = tp.write_wav(os.path.join(tmp, f"{name}.wav"), tp.tone(*spec))
                with wave.open(path, "rb") as handle:
                    self.assertEqual(handle.getframerate(), tp.RATE)
                    frames = handle.readframes(handle.getnframes())
                self.assertGreater(max(frames), 0)
                contents.add(frames)
            self.assertEqual(len(contents), 3)


class FakeSound:
    def __init__(self):
        self.played = []

    def play(self, name):
        self.played.append(name)


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.clock = Clock()
        self.sound = FakeSound()
        self.app = tp.TypingApp(self.root, Session(random.Random(3), self.clock), sound=self.sound)

    def tearDown(self):
        self.app.stop()
        self.root.destroy()

    def type_text(self, text):
        for ch in text:
            self.app.typed.set(self.app.typed.get() + ch)

    def test_alur_benar_dan_salah(self):
        self.assertEqual(str(self.app.entry.cget("state")), "disabled")
        self.app.start()
        self.assertEqual(self.app.prompt_var.get(), self.app.session.word)
        word = self.app.session.word
        self.type_text(word)
        self.assertIn("Selamat", self.app.message.get())
        self.assertEqual(self.app.score_text.get(), "1 berhasil / 1 percobaan")
        self.assertEqual(self.app.typed.get(), "")
        self.assertIn("5,75", self.app.interval_text.get())
        current = self.app.session.word
        self.type_text(current[0] + "#")
        self.assertIn("coba lagi", self.app.message.get())
        self.assertEqual(self.app.score_text.get(), "1 berhasil / 2 percobaan")
        deadline = time.monotonic() + 2
        while self.app.flash_job and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.02)
        self.assertEqual(self.app.typed.get(), "")  # dikosongkan setelah berkedip
        self.assertEqual(self.app.session.word, current)
        self.assertEqual(self.sound.played, ["new", "correct", "new", "wrong"])

    def test_waktu_habis_dan_stop(self):
        self.app.start()
        self.clock.now += 10
        self.app.root.after_cancel(self.app.timer_job)
        self.app.tick()
        self.assertIn("Waktu habis", self.app.message.get())
        self.assertEqual(self.app.score_text.get(), "0 berhasil / 1 percobaan")
        self.app.stop()
        self.assertEqual(str(self.app.start_button.cget("state")), "normal")
        self.assertEqual(str(self.app.stop_button.cget("state")), "disabled")
        self.assertIn("0% benar", self.app.message.get())


if __name__ == "__main__":
    unittest.main()
