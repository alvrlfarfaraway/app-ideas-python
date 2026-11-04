import contextlib
import io
import math
import random
import string
import unittest
from itertools import product

import password
from password import (
    AMBIGUOUS,
    CLASSES,
    crack_time,
    entropy_bits,
    generate,
    main,
    possible_count,
    strength,
)

ALL = tuple(CLASSES)


class GenerateTest(unittest.TestCase):
    def test_panjang_dan_jenis_karakter(self):
        for length in (4, 8, 16, 64, 128):
            value = generate(length)
            self.assertEqual(len(value), length)
            self.assertTrue(any(c in string.ascii_uppercase for c in value))
            self.assertTrue(any(c in string.ascii_lowercase for c in value))
            self.assertTrue(any(c in string.digits for c in value))
            self.assertTrue(any(c in CLASSES["symbols"][1] for c in value))

    def test_hanya_jenis_yang_dipilih(self):
        for _ in range(50):
            self.assertTrue(set(generate(12, ["digits"])) <= set(string.digits))
            value = generate(10, ["lower", "symbols"])
            self.assertFalse(set(value) & set(string.ascii_uppercase + string.digits))

    def test_setiap_jenis_selalu_muncul_walau_pendek(self):
        rng = random.Random(1)
        for _ in range(500):
            value = generate(4, ALL, rng=rng)
            for _, chars in CLASSES.values():
                self.assertTrue(set(value) & set(chars), value)

    def test_karakter_wajib_tidak_selalu_di_depan(self):
        rng = random.Random(2)
        firsts = {generate(8, ALL, rng=rng)[0] in string.ascii_uppercase for _ in range(200)}
        self.assertEqual(firsts, {True, False})

    def test_tanpa_karakter_mirip(self):
        for _ in range(50):
            self.assertFalse(set(generate(40, ALL, no_ambiguous=True)) & AMBIGUOUS)

    def test_input_salah(self):
        for args in ((3,), (129,), (8, [])):
            with self.assertRaises(ValueError, msg=args):
                generate(*args)

    def test_memakai_secrets(self):
        self.assertIsInstance(password.secrets.SystemRandom(), random.SystemRandom)


class StrengthTest(unittest.TestCase):
    def test_inklusi_eksklusi_sama_dengan_hitung_manual(self):
        groups = ["ab", "c", "de"]  # 5 karakter, 3 kelompok
        for length in (3, 4, 5):
            brute = sum(1 for s in product("abcde", repeat=length) if all(set(s) & set(g) for g in groups))
            self.assertEqual(possible_count(length, [2, 1, 2]), brute)

    def test_satu_jenis_sama_dengan_n_pangkat_panjang(self):
        self.assertAlmostEqual(entropy_bits(10, ["digits"]), 10 * math.log2(10))

    def test_syarat_mengurangi_sedikit_dari_maksimum(self):
        bits = entropy_bits(16, ALL)
        maximum = 16 * math.log2(26 + 26 + 10 + len(CLASSES["symbols"][1]))
        self.assertLess(bits, maximum)
        self.assertGreater(bits, maximum - 1)

    def test_label(self):
        self.assertEqual(strength(40), "Lemah")
        self.assertEqual(strength(60), "Sedang")
        self.assertEqual(strength(100), "Kuat")
        self.assertEqual(strength(128), "Sangat kuat")
        self.assertEqual(strength(entropy_bits(8, ["lower"])), "Lemah")
        self.assertEqual(strength(entropy_bits(20, ALL)), "Sangat kuat")

    def test_waktu_tebak(self):
        self.assertEqual(crack_time(20), "kurang dari semenit")
        self.assertIn("tahun", crack_time(80))
        self.assertEqual(crack_time(300), "lebih dari sejuta miliar tahun")


class CliTest(unittest.TestCase):
    def test_terminal(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main(["-l", "12", "-n", "3", "--no-symbols"]), 0)
        lines = out.getvalue().split()
        self.assertEqual(len(lines), 3)
        self.assertTrue(all(len(p) == 12 and p.isalnum() for p in lines))
        self.assertIn("Kekuatan:", err.getvalue())
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["-l", "8", "--no-upper", "--no-lower", "--no-digits", "--no-symbols"]), 1)


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.app = password.PasswordApp(self.root, rng=random.Random(3))

    def tearDown(self):
        self.root.destroy()

    def test_generate_dan_salin(self):
        self.assertEqual(len(self.app.password.get()), 16)
        self.app.length.set(24)
        value = self.app.generate()
        self.assertEqual(len(value), 24)
        self.assertIn("Sangat kuat", self.app.strength.get())
        self.app.copy()
        self.assertEqual(self.root.clipboard_get(), value)

    def test_pilihan_jenis(self):
        for key in ("upper", "lower", "symbols"):
            self.app.flags[key].set(False)
        self.app.length.set(8)
        self.assertTrue(self.app.generate().isdigit())
        self.assertIn("Lemah", self.app.strength.get())
        self.app.flags["digits"].set(False)
        self.assertIsNone(self.app.generate())
        self.assertIn("minimal satu jenis", self.app.strength.get())


if __name__ == "__main__":
    unittest.main()
