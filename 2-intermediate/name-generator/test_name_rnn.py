import contextlib
import io
import os
import tempfile
import unittest

import numpy as np

import name_rnn as nr

TOY = ["ana", "ani", "anu", "ina", "ini", "inu", "una", "uni"]


class DataTest(unittest.TestCase):
    def test_dataset(self):
        names = nr.load_names()
        self.assertGreater(len(names), 700)
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(n.isalpha() and n.isascii() and n == n.lower() for n in names))

    def test_vocab(self):
        vocab = nr.Vocab.from_names(["ab", "ca"])
        self.assertEqual(vocab.chars, [".", "a", "b", "c"])
        self.assertEqual(vocab.encode("cab"), [3, 1, 2])
        with self.assertRaises(ValueError):
            vocab.encode("ax")

    def test_batch(self):
        vocab = nr.Vocab.from_names(["ab", "c"])
        x, y, mask = nr.make_batch(["ab", "c"], vocab)
        self.assertEqual(x.shape, (3, 2))
        self.assertEqual(x[:, 0].tolist(), [0, 1, 2])  # . a b
        self.assertEqual(y[:, 0].tolist(), [1, 2, 0])  # a b .
        self.assertEqual(mask[:, 1].tolist(), [1, 1, 0])  # "c" lebih pendek

    def test_pembagian_latih_validasi(self):
        names = nr.load_names()
        train, valid = nr.split_names(names)
        self.assertEqual(len(train) + len(valid), len(names))
        self.assertFalse(set(train) & set(valid))
        self.assertEqual(nr.split_names(names), (train, valid))  # selalu sama


class GradientTest(unittest.TestCase):
    def test_gradien_sama_dengan_gradien_numerik(self):
        names = ["ab", "ba", "abc", "c"]
        vocab = nr.Vocab.from_names(names)
        model = nr.GRU(len(vocab), hidden=4, seed=3)
        x, y, mask = nr.make_batch(names, vocab)
        _, grads = model.loss_and_grads(x, y, mask)
        rng = np.random.default_rng(0)
        for key in nr.PARAMS:
            P = model.p[key]
            for _ in range(6):  # beberapa elemen acak per parameter
                i = tuple(rng.integers(0, s) for s in P.shape)
                old = P[i]
                P[i] = old + 1e-5
                up = model.loss_and_grads(x, y, mask)[0]
                P[i] = old - 1e-5
                down = model.loss_and_grads(x, y, mask)[0]
                P[i] = old
                numeric = (up - down) / 2e-5
                self.assertAlmostEqual(grads[key][i], numeric, delta=1e-6 + 1e-4 * abs(numeric), msg=(key, i))


class TrainTest(unittest.TestCase):
    def test_loss_turun(self):
        vocab = nr.Vocab.from_names(TOY)
        model = nr.GRU(len(vocab), hidden=16, seed=0)
        batch = nr.make_batch(TOY, vocab)
        start = model.loss_and_grads(*batch)[0]
        for _ in range(150):
            model.adam(model.loss_and_grads(*batch)[1], lr=0.02)
        self.assertLess(model.loss_and_grads(*batch)[0], start * 0.6)

    def test_early_stopping_menyimpan_yang_terbaik(self):
        model, vocab, history = nr.train(nr.load_names()[:200], hidden=16, steps=600, eval_every=100)
        best = min(history, key=lambda row: row[2])
        self.assertEqual(model.best_step, best[0])
        self.assertEqual(len(history), 6)
        _, valid = nr.split_names(nr.load_names()[:200])
        self.assertAlmostEqual(nr.full_loss(model, vocab, valid), best[2], places=6)

    def test_gradien_dipotong(self):
        model = nr.GRU(3, hidden=2)
        huge = {k: np.full_like(v, 1e6) for k, v in model.p.items()}
        before = {k: v.copy() for k, v in model.p.items()}
        model.adam(huge, lr=0.01)
        self.assertTrue(all(np.isfinite(v).all() for v in model.p.values()))
        self.assertTrue(all(np.abs(model.p[k] - before[k]).max() <= 0.0101 for k in model.p))


class GenerateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model, cls.vocab = nr.load()

    def test_awalan_dipakai(self):
        rng = np.random.default_rng(0)
        for prefix in ("ar", "SRI", " wi "):
            name = nr.generate(self.model, self.vocab, prefix, 0.8, rng)
            self.assertTrue(name.startswith(prefix.strip().lower()), name)
            self.assertLessEqual(len(name), nr.MAX_LEN)

    def test_seed_bisa_diulang_dan_hasil_unik(self):
        a = nr.generate_many(self.model, self.vocab, "ra", 5, seed=7)
        b = nr.generate_many(self.model, self.vocab, "ra", 5, seed=7)
        self.assertEqual(a, b)
        self.assertEqual(len(set(a)), len(a))

    def test_hindari_nama_latih(self):
        names = set(nr.load_names())
        found = nr.generate_many(self.model, self.vocab, "ar", 5, seed=1, avoid=names)
        self.assertTrue(found)
        self.assertFalse(set(found) & names)

    def test_temperature_mengubah_keberanian(self):
        names = set(nr.load_names())

        def novelty(t):
            rng = np.random.default_rng(0)
            return np.mean([nr.generate(self.model, self.vocab, "", t, rng) not in names for _ in range(200)])
        self.assertLess(novelty(0.4), novelty(1.2))
        with self.assertRaises(ValueError):
            nr.generate(self.model, self.vocab, "a", 0)

    def test_simpan_dan_muat(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.npz")
            nr.save(self.model, self.vocab, path)
            model, vocab = nr.load(path)
            self.assertEqual(vocab.chars, self.vocab.chars)
            self.assertEqual(nr.generate_many(model, vocab, "di", 4, seed=2),
                             nr.generate_many(self.model, self.vocab, "di", 4, seed=2))


class CliTest(unittest.TestCase):
    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = nr.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_nama(self):
        code, out, _ = self.run_main("--prefix", "ar", "-n", "4", "--seed", "1")
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertTrue(all(line.startswith("Ar") for line in lines))

    def test_baru(self):
        code, out, _ = self.run_main("--prefix", "sri", "-n", "3", "--seed", "1", "--baru")
        self.assertEqual(code, 0)
        self.assertTrue(all("(baru)" in line for line in out.splitlines()))

    def test_awalan_tidak_valid(self):
        self.assertEqual(self.run_main("--prefix", "a1")[0], 1)
        code, _, err = self.run_main("--prefix", "xa")
        self.assertEqual(code, 1)
        self.assertIn("'x'", err)


try:
    import nbformat
    from nbclient import NotebookClient
except ImportError:
    nbformat = None


@unittest.skipIf(nbformat is None, "nbformat/nbclient tidak terpasang")
class NotebookTest(unittest.TestCase):
    def test_notebook_berjalan_tanpa_error(self):
        here = os.path.dirname(os.path.abspath(__file__))
        notebook = nbformat.read(os.path.join(here, "name_generator.ipynb"), as_version=4)
        NotebookClient(notebook, timeout=300, kernel_name="python3", resources={"metadata": {"path": here}}).execute()
        figures = sum(1 for cell in notebook.cells if cell.cell_type == "code"
                      for output in cell.outputs if output.output_type == "display_data")
        self.assertGreaterEqual(figures, 3)


if __name__ == "__main__":
    unittest.main()
