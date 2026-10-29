import json
import os
import random
import re
import tempfile
import unittest
import urllib.parse
from datetime import datetime

from quiz import (QUIZ_DIR, LETTERS, Quiz, QuizAborted, ScoreBoard, format_duration, format_history, format_result,
                  list_quizzes, load_quiz, main, parse_choice, run_quiz, share_text, share_url)


def make_quiz(n=4, pass_percent=70):
    questions = [{"question": f"Soal {i}", "answers": [f"{i}a", f"{i}b", f"{i}c", f"{i}d"], "correct": i % 4}
                 for i in range(n)]
    return Quiz("uji", "Kuis Uji", questions, pass_percent)


def scripted(answers):
    it = iter(answers)
    return lambda prompt="": next(it)


def always_right(quiz):
    """Penjawab yang tahu jawaban benar, apa pun urutan acaknya (mencocokkan teks yang ditampilkan)."""
    correct_texts = {i["question"]: i["answers"][i["correct"]] for i in quiz.questions}
    state = {"question": None, "options": {}}

    def show(text):
        if text.startswith("\nSoal "):
            state["question"] = text.split(": ", 1)[1]
            state["options"] = {}
        elif text.startswith("  ") and text[2:3] in LETTERS and text[3:4] == ".":
            state["options"][text[5:]] = text[2]

    def ask(prompt=""):
        return state["options"][correct_texts[state["question"]]]

    return show, ask


class BundledQuizzesTest(unittest.TestCase):
    def test_semua_berkas_kuis_valid(self):
        names = list_quizzes()
        self.assertGreaterEqual(len(names), 2)  # bonus: lebih dari satu kuis
        for name in names:
            quiz = load_quiz(os.path.join(QUIZ_DIR, name + ".json"))
            self.assertGreaterEqual(len(quiz.questions), 8)
            for item in quiz.questions:
                self.assertEqual(len(item["answers"]), 4)


class LoadQuizTest(unittest.TestCase):
    def load(self, data):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "q.json")
            with open(path, "w", encoding="utf-8") as file:
                file.write(data if isinstance(data, str) else json.dumps(data))
            return load_quiz(path)

    def good(self, **changes):
        item = {"question": "Q?", "answers": ["a", "b", "c", "d"], "correct": 0}
        item.update(changes)
        return {"title": "T", "questions": [item]}

    def test_valid(self):
        self.assertEqual(self.load(self.good()).pass_percent, 70)

    def test_tidak_valid(self):
        bad = [
            "{rusak", "[]", {"title": "T"}, {"title": "T", "questions": []},
            self.good(question=" "), self.good(answers=["a", "b", "c"]), self.good(answers=["a", "a", "c", "d"]),
            self.good(answers=["a", "b", "c", 4]), self.good(correct=4), self.good(correct=-1),
            self.good(correct="0"), self.good(correct=True),
            {**self.good(), "pass_percent": 0}, {**self.good(), "pass_percent": 101},
        ]
        for data in bad:
            with self.assertRaises(ValueError, msg=str(data)):
                self.load(data)

    def test_tidak_ditemukan(self):
        with self.assertRaises(ValueError):
            load_quiz("tidak-ada.json")


class ParseChoiceTest(unittest.TestCase):
    def test_pilihan(self):
        self.assertEqual([parse_choice(t) for t in ("a", "B", " c ", "D", "1", "4")], [0, 1, 2, 3, 0, 3])

    def test_tidak_valid(self):
        for text in ("", "e", "5", "ab", "0", "x"):
            self.assertIsNone(parse_choice(text), text)

    def test_keluar(self):
        with self.assertRaises(QuizAborted):
            parse_choice("Q")


class RunQuizTest(unittest.TestCase):
    def test_semua_benar_lulus(self):
        quiz = make_quiz()
        show, ask = always_right(quiz)
        result = run_quiz(quiz, ask=ask, show=show, rng=random.Random(1))
        self.assertEqual((result.correct, result.total, result.percent), (4, 4, 100))
        self.assertTrue(result.passed)
        self.assertEqual(result.wrong, [])

    def test_semua_salah_gagal(self):
        quiz = make_quiz()
        outputs = []
        correct_texts = {i["question"]: i["answers"][i["correct"]] for i in quiz.questions}
        state = {}

        def show(text):
            outputs.append(text)
            if text.startswith("\nSoal "):
                state["q"], state["opts"] = text.split(": ", 1)[1], {}
            elif text.startswith("  ") and text[3:4] == "." and text[2] in LETTERS:
                state["opts"][text[5:]] = text[2]

        def ask(prompt=""):
            wrong = next(letter for answer, letter in state["opts"].items() if answer != correct_texts[state["q"]])
            return wrong

        result = run_quiz(quiz, ask=ask, show=show, rng=random.Random(2))
        self.assertEqual((result.correct, result.passed), (0, False))
        self.assertEqual(len(result.wrong), 4)
        self.assertTrue(any("Salah. Jawaban yang benar" in line for line in outputs))

    def test_penjelasan_hanya_muncul_setelah_jawaban_salah(self):
        quiz = Quiz("u", "U", [{"question": "Q", "answers": ["a", "b", "c", "d"], "correct": 0,
                                 "explanation": "karena a"}])
        for answers, expect in (("abcd", 0), ("abcd", 1)):
            lines = []
            state = {}

            def show(text):
                lines.append(text)
                if re.match(r"^  [A-D]\. ", text):
                    state[text[5:]] = text[2]

            def ask(prompt=""):
                right = state["a"]
                return right if expect == 0 else next(l for t, l in state.items() if t != "a")

            run_quiz(quiz, ask=ask, show=show, rng=random.Random(4))
            self.assertEqual(any("Penjelasan: karena a" in l for l in lines), expect == 1)

    def test_setiap_soal_menampilkan_empat_jawaban(self):
        quiz = make_quiz(3)
        lines = []
        show, ask = always_right(quiz)
        run_quiz(quiz, ask=ask, show=lambda t: (lines.append(t), show(t)), rng=random.Random(3))
        self.assertEqual(sum(1 for l in lines if l.startswith("\nSoal ")), 3)
        self.assertEqual(sum(1 for l in lines if re.match(r"^  [A-D]\. ", l)), 12)

    def test_input_salah_diminta_ulang(self):
        quiz = make_quiz(1)
        lines = []
        run_quiz(quiz, ask=scripted(["z", "", "9", "a"]), show=lines.append, rng=random.Random(0))
        self.assertEqual(sum(1 for l in lines if "Ketik A, B, C, atau D" in l), 3)

    def test_urutan_diacak_tapi_benar_tetap_benar(self):
        quiz = make_quiz(8)
        orders = set()
        for seed in range(5):
            lines = []
            show, ask = always_right(quiz)
            result = run_quiz(quiz, ask=ask, show=lambda t: (lines.append(t), show(t)), rng=random.Random(seed))
            self.assertEqual(result.correct, 8)
            orders.add(tuple(l for l in lines if l.startswith("\nSoal ")))
        self.assertGreater(len(orders), 1)

    def test_waktu_dihitung(self):
        quiz = make_quiz(2)
        clock = iter([100.0, 187.0])
        show, ask = always_right(quiz)
        result = run_quiz(quiz, ask=ask, show=show, now=lambda: next(clock), rng=random.Random(1))
        self.assertEqual(result.seconds, 87.0)
        self.assertIn("1 menit 27 detik", format_result(result))

    def test_keluar_dan_input_habis(self):
        with self.assertRaises(QuizAborted):
            run_quiz(make_quiz(2), ask=scripted(["q"]), show=lambda t: None)
        def input_habis(prompt=""):
            raise EOFError

        with self.assertRaises(QuizAborted):
            run_quiz(make_quiz(2), ask=input_habis, show=lambda t: None)


class ResultTest(unittest.TestCase):
    def make(self, correct, total=10, pass_percent=70):
        from quiz import Result
        return Result(make_quiz(total, pass_percent), correct, total, 30, [])

    def test_batas_lulus(self):
        self.assertTrue(self.make(7).passed)
        self.assertFalse(self.make(6).passed)
        self.assertTrue(self.make(10).passed)
        self.assertTrue(self.make(5, pass_percent=50).passed)

    def test_format_dan_bagikan(self):
        result = self.make(8)
        text = format_result(result)
        self.assertIn("8 dari 10 (80%)", text)
        self.assertIn("LULUS", text)
        self.assertIn("lulus kuis Kuis Uji: 8/10", share_text(result))
        self.assertIn("belum lulus", share_text(self.make(2)))
        url = share_url(result)
        self.assertTrue(url.startswith("https://twitter.com/intent/tweet?text="))
        self.assertEqual(urllib.parse.unquote(url.split("text=")[1]), share_text(result))

    def test_durasi(self):
        self.assertEqual(format_duration(45), "45 detik")
        self.assertEqual(format_duration(125), "2 menit 5 detik")


class ScoreBoardTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "s.json")
        self.board = ScoreBoard(self.path, now=lambda: datetime(2026, 10, 29, 10, 0))

    def tearDown(self):
        self.dir.cleanup()

    def result(self, correct):
        from quiz import Result
        return Result(make_quiz(10), correct, 10, 20, [])

    def test_banyak_percobaan_per_pengguna(self):
        self.board.record("Ani", self.result(5))
        self.board.record("Ani", self.result(9))
        self.board.record("Budi", self.result(3))
        history = self.board.history("ani")  # tidak membedakan huruf besar kecil
        self.assertEqual([e["correct"] for e in history], [5, 9])
        self.assertEqual(len(self.board.history("Budi")), 1)
        self.assertEqual(self.board.history("Cici"), [])

    def test_persisten(self):
        self.board.record("Ani", self.result(7))
        self.assertEqual(len(ScoreBoard(self.path).history("Ani")), 1)

    def test_berkas_rusak_tidak_ditimpa(self):
        with open(self.path, "w", encoding="utf-8") as file:
            file.write("{rusak")
        with self.assertRaises(ValueError):
            self.board.record("Ani", self.result(7))
        with open(self.path, encoding="utf-8") as file:
            self.assertEqual(file.read(), "{rusak")

    def test_format_riwayat(self):
        self.assertIn("Belum ada skor", format_history([]))
        self.board.record("Ani", self.result(5))
        self.board.record("Ani", self.result(9))
        text = format_history(self.board.history("Ani"))
        self.assertIn("Terbaik: 9/10", text)
        self.assertIn("2 kali", text)


class MainTest(unittest.TestCase):
    def test_alur_penuh_dengan_kuis_asli(self):
        with tempfile.TemporaryDirectory() as folder:
            scores = os.path.join(folder, "s.json")
            code = main(["--quiz", "git-dasar", "--user", "Ani", "--score-file", scores, "--seed", "1"],
                        ask=scripted([""] + ["a"] * 10))
            self.assertEqual(code, 0)
            self.assertEqual(len(ScoreBoard(scores).history("Ani")), 1)
            self.assertEqual(main(["--scores", "--user", "Ani", "--score-file", scores]), 0)

    def test_keluar_tidak_menyimpan_skor(self):
        with tempfile.TemporaryDirectory() as folder:
            scores = os.path.join(folder, "s.json")
            code = main(["--quiz", "git-dasar", "--score-file", scores], ask=scripted(["", "q"]))
            self.assertEqual(code, 1)
            self.assertFalse(os.path.exists(scores))

    def test_kuis_tidak_ada_dan_pilihan_salah(self):
        self.assertEqual(main(["--quiz", "tidak-ada"], ask=scripted([""])), 1)
        self.assertEqual(main([], ask=scripted(["99"])), 1)

    def test_pilih_dari_daftar(self):
        with tempfile.TemporaryDirectory() as folder:
            scores = os.path.join(folder, "s.json")
            self.assertEqual(main(["--score-file", scores], ask=scripted(["1", ""] + ["b"] * 10)), 0)


if __name__ == "__main__":
    unittest.main()
