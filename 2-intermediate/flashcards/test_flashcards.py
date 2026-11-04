import json
import os
import random
import tempfile
import unittest

import flashcards
from flashcards import DEFAULT_DECK, LETTERS, PROVINCES, FlashcardSession, load_deck

SMALL = [{"question": f"Soal {n}?", "answer": f"Jawab {n}", "info": f"Info {n}"} for n in range(6)]


def session(deck=SMALL, seed=1):
    return FlashcardSession(deck, rng=random.Random(seed))


def wrong_letter(s):
    return next(letter for letter, _ in s.choices if letter != s.correct_letter)


class DeckTest(unittest.TestCase):
    def test_deck_bawaan(self):
        self.assertEqual(len(PROVINCES), 37)  # 38 provinsi, tanpa DKI Jakarta
        self.assertEqual(len(DEFAULT_DECK), 37)
        answers = [card["answer"] for card in DEFAULT_DECK]
        self.assertEqual(len(set(answers)), len(answers))
        self.assertEqual(PROVINCES["Kalimantan Selatan"][0], "Banjarbaru")
        self.assertEqual(PROVINCES["Maluku Utara"][0], "Sofifi")
        for card in DEFAULT_DECK:
            self.assertTrue(card["question"].endswith("?"))
            self.assertTrue(card["info"])

    def test_muat_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "deck.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump([{"question": " Q? ", "answer": " A "}] + SMALL[:4], handle)
            deck = load_deck(path)
            self.assertEqual(deck[0], {"question": "Q?", "answer": "A", "info": ""})

    def test_json_tidak_valid(self):
        cases = ({"question": "x"}, [{"question": "x"}], [{"answer": "y"}], SMALL[:3],
                 [{"question": "q", "answer": "sama"}] * 5)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "deck.json")
            for data in cases:
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump(data, handle)
                with self.assertRaises(ValueError, msg=data):
                    load_deck(path)


class ChoicesTest(unittest.TestCase):
    def test_empat_pilihan_berhuruf_dari_kartu_lain(self):
        s = session()
        answers = {card["answer"] for card in SMALL}
        for _ in range(30):
            self.assertEqual([letter for letter, _ in s.choices], list(LETTERS))
            texts = [text for _, text in s.choices]
            self.assertEqual(len(set(texts)), 4)
            self.assertIn(s.card["answer"], texts)
            self.assertTrue(set(texts) <= answers)
            s.next_card()

    def test_posisi_jawaban_benar_acak(self):
        s = session(DEFAULT_DECK, seed=3)
        positions = set()
        for _ in range(40):
            positions.add(s.correct_letter)
            s.next_card()
        self.assertEqual(positions, set(LETTERS))

    def test_deck_terlalu_kecil(self):
        with self.assertRaises(ValueError):
            FlashcardSession(SMALL[:3])


class OrderTest(unittest.TestCase):
    def test_semua_kartu_muncul_sebelum_diulang(self):
        s = session()
        seen = [s.card["question"]]
        for _ in range(len(SMALL) - 1):
            seen.append(s.next_card()["question"])
        self.assertEqual(sorted(seen), sorted(card["question"] for card in SMALL))

    def test_tidak_ada_kartu_sama_berturut_turut(self):
        for seed in range(30):
            s = session(seed=seed)
            previous = s.card
            for _ in range(40):
                card = s.next_card()
                self.assertIsNot(card, previous, seed)
                previous = card

    def test_shuffle_mengacak_ulang(self):
        s = session()
        first = [s.card["question"]] + [s.next_card()["question"] for _ in range(5)]
        s.shuffle()
        second = [s.card["question"]] + [s.next_card()["question"] for _ in range(5)]
        self.assertEqual(sorted(first), sorted(second))
        self.assertNotEqual(first, second)


class AnswerTest(unittest.TestCase):
    def test_benar(self):
        s = session()
        self.assertTrue(s.answer(s.correct_letter))
        self.assertEqual((s.correct, s.incorrect), (1, 0))
        self.assertIsNone(s.answer(s.correct_letter))  # sudah selesai
        self.assertEqual((s.correct, s.incorrect), (1, 0))

    def test_salah_lalu_benar_dihitung_salah_sekali(self):
        s = session()
        self.assertFalse(s.answer(wrong_letter(s)))
        self.assertFalse(s.answer(wrong_letter(s)))
        self.assertTrue(s.answer(s.correct_letter))
        self.assertEqual((s.correct, s.incorrect), (0, 1))

    def test_hitungan_lintas_kartu_dan_reset(self):
        s = session()
        s.answer(s.correct_letter)
        s.next_card()
        s.answer(wrong_letter(s))
        s.next_card()
        s.answer(s.correct_letter)
        self.assertEqual(s.results(), "Benar 2 | Salah 1 (66% benar)")
        s.reset_tallies()
        self.assertEqual(s.results(), "Benar 0 | Salah 0")

    def test_huruf_tidak_ada(self):
        with self.assertRaises(ValueError):
            session().answer("E")


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.session = session(DEFAULT_DECK, seed=2)
        self.app = flashcards.FlashcardApp(self.root, self.session)

    def tearDown(self):
        self.root.destroy()

    def index_of(self, letter):
        return LETTERS.index(letter)

    def test_klik_salah_lalu_benar(self):
        s = self.session
        wrong = self.index_of(wrong_letter(s))
        self.app.choose(wrong)
        self.assertIn("Salah", self.app.feedback.cget("text"))
        self.assertEqual(str(self.app.choice_buttons[wrong].cget("state")), "disabled")
        self.app.choose(self.index_of(s.correct_letter))
        self.assertIn("Selamat", self.app.feedback.cget("text"))

    def test_more_info_dan_next(self):
        question = self.session.card["question"]
        self.app.flip()
        self.assertTrue(self.app.showing_info)
        self.assertEqual(self.app.info.cget("text"), self.session.card["info"])
        self.app.choose(0)  # tidak bisa menjawab saat kartu dibalik
        self.assertEqual(self.session.correct + self.session.incorrect, 0)
        self.app.flip()
        self.assertFalse(self.app.showing_info)
        self.app.next_question()
        self.assertNotEqual(self.session.card["question"], question)
        self.assertEqual(self.app.question.cget("text"), self.session.card["question"])
        self.assertEqual(self.app.feedback.cget("text"), "")

    def test_results_dan_reset(self):
        self.app.choose(self.index_of(self.session.correct_letter))
        self.app.show_results()
        self.assertEqual(self.app.results.get(), "Benar 1 | Salah 0 (100% benar)")
        self.app.reset()
        self.assertEqual(self.app.results.get(), "Benar 0 | Salah 0")


if __name__ == "__main__":
    unittest.main()
