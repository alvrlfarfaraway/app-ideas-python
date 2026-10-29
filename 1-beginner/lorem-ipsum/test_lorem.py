import re
import unittest

from lorem import MAX_PARAGRAPHS, OPENING, WORDS, generate, main, parse_count, sentence


class ParseCountTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(parse_count("3"), 3)
        self.assertEqual(parse_count(" 10 "), 10)
        self.assertEqual(parse_count(str(MAX_PARAGRAPHS)), MAX_PARAGRAPHS)

    def test_tidak_valid(self):
        for text in ("", "abc", "2.5", "0", "-1", str(MAX_PARAGRAPHS + 1)):
            with self.assertRaises(ValueError, msg=text):
                parse_count(text)


class GenerateTest(unittest.TestCase):
    def test_jumlah_paragraf(self):
        for count in (1, 2, 7):
            self.assertEqual(len(generate(count, seed=1)), count)

    def test_paragraf_pertama_diawali_kalimat_klasik(self):
        for seed in range(20):
            self.assertTrue(generate(3, seed)[0].startswith(OPENING + "."))
        # paragraf berikutnya tidak harus memakai kalimat pembuka
        self.assertFalse(any(p.startswith(OPENING) for p in generate(5, 3)[1:]))

    def test_deterministik_dengan_seed(self):
        self.assertEqual(generate(4, seed=42), generate(4, seed=42))
        self.assertNotEqual(generate(4, seed=42), generate(4, seed=43))

    def test_tanpa_seed_bervariasi(self):
        self.assertNotEqual(generate(3), generate(3))

    def test_bentuk_teks(self):
        for paragraph in generate(10, seed=5):
            sentences = re.findall(r"[^.]+\.", paragraph)
            self.assertTrue(4 <= len(sentences) <= 8)
            self.assertTrue(paragraph.endswith("."))
            self.assertTrue(paragraph[0].isupper())
            words = re.findall(r"[a-z]+", paragraph.lower())
            self.assertTrue(set(words) <= set(WORDS))

    def test_kalimat_biasa_tidak_diawali_pembuka(self):
        import random
        rng = random.Random(0)
        for _ in range(50):
            text = sentence(rng)
            self.assertTrue(6 <= len(text.rstrip(".").split()) <= 16)

    def test_jumlah_di_luar_batas(self):
        for bad in (0, -1, MAX_PARAGRAPHS + 1, "3", 2.0):
            with self.assertRaises(ValueError, msg=repr(bad)):
                generate(bad)


class CliTest(unittest.TestCase):
    def test_exit_code(self):
        self.assertEqual(main(["2", "--seed", "1"]), 0)
        self.assertEqual(main(["abc"]), 1)
        self.assertEqual(main(["0"]), 1)


if __name__ == "__main__":
    unittest.main()
