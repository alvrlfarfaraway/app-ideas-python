import contextlib
import io
import unittest

import regex_helper
from regex_helper import RegexError, compile_pattern, main, run, to_python


class FunctionTest(unittest.TestCase):
    def test_test(self):
        self.assertIs(run(r"\d", "a1", "", "test").value, True)
        self.assertIs(run(r"\d", "ab", "", "test").value, False)

    def test_search(self):
        self.assertEqual(run("apel", "ada apel", "", "search").value, 4)
        self.assertEqual(run("jeruk", "ada apel", "", "search").value, -1)

    def test_match_tanpa_dan_dengan_g(self):
        self.assertEqual(run(r"(\d{4})-(\d{2})", "rilis 2023-10 lalu 2024-01", "", "match").value,
                         ["2023-10", "2023", "10"])
        self.assertEqual(run(r"(\d{4})-(\d{2})", "rilis 2023-10 lalu 2024-01", "g", "match").value,
                         ["2023-10", "2024-01"])
        self.assertIsNone(run("z", "abc", "", "match").value)
        self.assertIsNone(run("z", "abc", "g", "match").value)  # JavaScript: null, bukan []

    def test_grup_opsional_yang_tidak_cocok(self):
        self.assertEqual(run(r"a(b)?", "a", "", "match").value, ["a", None])


class FlagTest(unittest.TestCase):
    def test_i_m_s(self):
        self.assertTrue(run("APEL", "apel", "i", "test").value)
        self.assertFalse(run("APEL", "apel", "", "test").value)
        self.assertEqual(run("^b", "a\nb", "m", "search").value, 2)
        self.assertEqual(run("^b", "a\nb", "", "search").value, -1)
        self.assertTrue(run("a.b", "a\nb", "s", "test").value)
        self.assertFalse(run("a.b", "a\nb", "", "test").value)

    def test_sticky(self):
        self.assertFalse(run(r"\d", "a1", "y", "test").value)  # harus cocok dari posisi 0
        self.assertTrue(run(r"\d", "1a", "y", "test").value)
        self.assertEqual(run(r"\d", "12a3", "gy", "match").value, ["1", "2"])  # berhenti di 'a'
        self.assertEqual(run(r"\d", "12a3", "g", "match").value, ["1", "2", "3"])

    def test_kecocokan_kosong_tidak_berulang_tanpa_akhir(self):
        self.assertEqual(run("x*", "ab", "g", "match").value, ["", "", ""])
        self.assertEqual(run("x*", "ab", "gy", "match").value, ["", "", ""])


class SyntaxTest(unittest.TestCase):
    def test_grup_bernama_gaya_javascript(self):
        self.assertEqual(to_python(r"(?<tahun>\d{4})"), r"(?P<tahun>\d{4})")
        self.assertEqual(to_python(r"(?<=a)b(?<!c)"), r"(?<=a)b(?<!c)")  # lookbehind tidak diubah
        self.assertEqual(to_python(r"\(?<x>"), r"\(?<x>")  # kurung yang di-escape tidak diubah
        result = run(r"(?<th>\d{4})", "tahun 2026", "", "match")
        self.assertIn("grup bernama: {'th': '2026'}", result.message)

    def test_peringatan(self):
        for args, text in (((r"", "x"), "regular expression"), ((r"x", ""), "teks"), ((r"(", "x"), "tidak valid"),
                           ((r"x", "x", "q"), "Flag q")):
            with self.assertRaises(RegexError) as ctx:
                run(*args)
            self.assertIn(text, str(ctx.exception))
        with self.assertRaises(RegexError):
            run("x", "x", "", "replace")

    def test_compile(self):
        self.assertTrue(compile_pattern("a", "im").flags & regex_helper.re.IGNORECASE)


class SpanTest(unittest.TestCase):
    def test_sorotan(self):
        self.assertEqual(run(r"\d+", "a12b3", "g", "match").spans, [(1, 3), (4, 5)])
        self.assertEqual(run(r"\d+", "a12b3", "", "test").spans, [(1, 3)])  # tanpa g: yang pertama saja
        self.assertEqual(run(r"z", "abc", "g", "test").spans, [])

    def test_pesan(self):
        self.assertIn("tidak ada teks yang cocok", run("z", "abc", "", "test").message)
        self.assertIn("indeks 4", run("apel", "ada apel", "", "search").message)


class CliTest(unittest.TestCase):
    def test_terminal(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main([r"\d+", "a12b3", "--flags", "g", "--fn", "match"]), 0)
        self.assertEqual(out.getvalue().splitlines(), ["match(): 2 kecocokan: ['12', '3']", "a12b3", " ^^ ^"])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["(", "x"]), 1)


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.app = regex_helper.HelperApp(self.root)

    def tearDown(self):
        self.root.destroy()

    def test_sorotan_dan_pesan(self):
        self.assertEqual(len(self.app.text.tag_ranges("match0")) // 2, 2)  # 3 tahun, warna bergantian
        self.assertEqual(len(self.app.text.tag_ranges("match1")) // 2, 1)
        self.assertIn("3 kecocokan", self.app.message.get())

    def test_peringatan_dan_tidak_cocok(self):
        self.app.pattern.set("")
        self.assertIsNone(self.app.run())
        self.assertIn("Peringatan", self.app.message.get())
        self.app.pattern.set("zzz")
        self.app.run()
        self.assertIn("tidak ada teks yang cocok", self.app.message.get())
        self.assertEqual(self.app.text.tag_ranges("match0"), ())

    def test_flag_dan_fungsi(self):
        self.app.flags["g"].set(False)
        self.app.update_flags()
        self.app.function.set("search")
        self.app.pattern.set("versi")
        self.app.run()
        self.assertIn("indeks 23", self.app.message.get())
        self.assertEqual(self.app.flag_text.get(), "")


if __name__ == "__main__":
    unittest.main()
