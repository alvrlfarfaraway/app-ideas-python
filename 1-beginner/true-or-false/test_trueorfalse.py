import math
import unittest

from trueorfalse import JSValue, OPERATORS, compare, evaluate, main, make_value, string_to_number

S = lambda v: JSValue("string", v)
N = lambda v: JSValue("number", float(v))
B = lambda v: JSValue("boolean", v)
NULL = JSValue("null")
UNDEF = JSValue("undefined")


class StringToNumberTest(unittest.TestCase):
    def test_sama_dengan_number_di_javascript(self):
        cases = {"": 0, "  ": 0, "42": 42, " 42 ": 42, "-3.5": -3.5, "+7": 7, ".5": 0.5, "5.": 5, "1e3": 1000,
                 "0x1F": 31, "0b101": 5, "0o17": 15, "Infinity": math.inf, "-Infinity": -math.inf}
        for text, value in cases.items():
            self.assertEqual(string_to_number(text), value, repr(text))

    def test_bukan_angka_jadi_nan(self):
        for text in ("abc", "1,5", "1_000", "nan", "inf", "infinity", "0x", "0xZZ", "-0x10", "1 2", "--1", "1e"):
            self.assertTrue(math.isnan(string_to_number(text)), repr(text))


class StrictTest(unittest.TestCase):
    def test_tipe_harus_sama(self):
        self.assertFalse(compare(S("1"), "===", N(1)))
        self.assertTrue(compare(S("1"), "===", S("1")))
        self.assertTrue(compare(N(1), "===", N(1.0)))
        self.assertTrue(compare(S("1"), "!==", N(1)))

    def test_nan_tidak_sama_dengan_dirinya(self):
        nan = N(math.nan)
        self.assertFalse(compare(nan, "===", nan))
        self.assertTrue(compare(nan, "!==", nan))
        self.assertFalse(compare(nan, "==", nan))

    def test_null_dan_undefined(self):
        self.assertTrue(compare(NULL, "===", NULL))
        self.assertTrue(compare(UNDEF, "===", UNDEF))
        self.assertFalse(compare(NULL, "===", UNDEF))

    def test_nol_negatif_sama_dengan_nol(self):
        self.assertTrue(compare(N(-0.0), "===", N(0)))


class LooseTest(unittest.TestCase):
    def test_kasus_klasik_yang_true(self):
        true_cases = [(S("0"), B(False)), (S(""), N(0)), (S("1"), N(1)), (B(True), S("1")), (B(True), N(1)),
                      (NULL, UNDEF), (S("  12  "), N(12)), (S("0x10"), N(16)), (S(""), B(False)), (B(False), N(0)),
                      (S("1e3"), N(1000)), (S("Infinity"), N(math.inf))]
        for a, b in true_cases:
            self.assertTrue(compare(a, "==", b), f"{a} == {b}")
            self.assertTrue(compare(b, "==", a), f"{b} == {a} (simetris)")

    def test_kasus_klasik_yang_false(self):
        false_cases = [(NULL, N(0)), (UNDEF, N(0)), (NULL, B(False)), (NULL, S("")), (UNDEF, S("undefined")),
                       (S("abc"), N(math.nan)), (S("true"), B(True)), (S("2"), B(True)), (S("a"), S("b")),
                       (S("1"), S("01")), (N(math.nan), N(math.nan))]
        for a, b in false_cases:
            self.assertFalse(compare(a, "==", b), f"{a} == {b}")
            self.assertTrue(compare(a, "!=", b))

    def test_tidak_transitif(self):
        # contoh terkenal: "0" == 0 dan 0 == "" tetapi "0" != ""
        self.assertTrue(compare(S("0"), "==", N(0)))
        self.assertTrue(compare(N(0), "==", S("")))
        self.assertFalse(compare(S("0"), "==", S("")))


class RelationalTest(unittest.TestCase):
    def test_string_dibandingkan_urutan_kamus_bukan_angka(self):
        self.assertTrue(compare(S("10"), "<", S("9")))   # "1" < "9"
        self.assertFalse(compare(S("10"), "<", N(9)))    # string vs angka -> angka
        self.assertTrue(compare(S("apple"), "<", S("banana")))
        self.assertTrue(compare(S("Z"), "<", S("a")))    # huruf besar sebelum kecil
        self.assertTrue(compare(S("a"), "<", S("aa")))
        self.assertFalse(compare(S("a"), "<", S("a")))

    def test_nan_membuat_semua_perbandingan_false(self):
        for op in ("<", ">", "<=", ">="):
            self.assertFalse(compare(S("abc"), op, N(1)), op)
            self.assertFalse(compare(N(1), op, N(math.nan)), op)
            self.assertFalse(compare(UNDEF, op, N(0)), op)

    def test_null_menjadi_nol(self):
        self.assertTrue(compare(NULL, ">=", N(0)))   # terkenal: null >= 0 true, tapi null == 0 false
        self.assertFalse(compare(NULL, ">", N(0)))
        self.assertTrue(compare(NULL, "<=", N(0)))
        self.assertFalse(compare(NULL, "==", N(0)))

    def test_boolean_menjadi_angka(self):
        self.assertTrue(compare(B(True), ">", N(0)))
        self.assertTrue(compare(B(False), "<", B(True)))
        self.assertTrue(compare(B(True), ">=", S("1")))

    def test_batas_sama(self):
        self.assertTrue(compare(N(5), "<=", N(5)))
        self.assertTrue(compare(N(5), ">=", N(5)))
        self.assertFalse(compare(N(5), "<", N(5)))
        self.assertTrue(compare(N(math.inf), ">", N(1e308)))

    def test_urutan_unit_kode_utf16_bukan_titik_kode(self):
        # U+1F600 (😀) = surrogat D83D DE00, U+FF5E (～) = FF5E. Menurut JS, 😀 < ～ ; menurut Python (titik kode) sebaliknya.
        self.assertTrue(compare(S("\U0001F600"), "<", S("～")))
        self.assertFalse("\U0001F600" < "～")


class OperatorTest(unittest.TestCase):
    def test_operator_tidak_valid(self):
        for op in ("", "=", "=<", "<>", "===="," and ", "eval", "!!"):
            with self.assertRaises(ValueError, msg=repr(op)):
                evaluate("1", "2", op)

    def test_semua_operator_dikenal(self):
        for op in OPERATORS:
            evaluate("1", "2", op)

    def test_spasi_di_operator_diabaikan(self):
        self.assertEqual(evaluate("1", "1", " == ")[0], True)

    def test_tidak_memakai_eval(self):
        # input yang berbahaya hanyalah teks biasa
        result, _ = evaluate("__import__('os').system('echo x')", "1", "==")
        self.assertFalse(result)


class TypedValuesTest(unittest.TestCase):
    def test_tipe_ditentukan_pengguna(self):
        self.assertEqual(evaluate("1", "1", "===", "number", "string")[0], False)
        self.assertEqual(evaluate("1", "1", "==", "number", "string")[0], True)
        self.assertEqual(evaluate("true", "1", "==", "boolean", "number")[0], True)
        self.assertEqual(evaluate("", "", "==", "null", "undefined")[0], True)
        self.assertEqual(evaluate("", "", "===", "null", "undefined")[0], False)

    def test_nilai_tidak_cocok_dengan_tipenya(self):
        for text, type_ in (("abc", "number"), ("yes", "boolean"), ("True", "boolean"), ("1", "bukan-tipe")):
            with self.assertRaises(ValueError, msg=f"{text} {type_}"):
                make_value(text, type_)

    def test_nan_dan_infinity_sebagai_angka(self):
        self.assertTrue(math.isnan(make_value("NaN", "number").value))
        self.assertEqual(make_value("Infinity", "number").value, math.inf)

    def test_ungkapan_ditampilkan(self):
        self.assertEqual(evaluate("0", "false", "==", "string", "boolean")[1], '"0" == false')
        self.assertEqual(evaluate("5", "5.5", "<", "number", "number")[1], "5 < 5.5")
        self.assertEqual(evaluate("Infinity", "NaN", ">", "number", "number")[1], "Infinity > NaN")
        self.assertEqual(evaluate("", "", "==", "null", "undefined")[1], "null == undefined")


class CliTest(unittest.TestCase):
    def test_exit_code(self):
        self.assertEqual(main(["0", "false", "=="]), 0)
        self.assertEqual(main(["", "0", "=="]), 0)  # string kosong adalah masukan yang sah
        self.assertEqual(main(["1", "2", "=<"]), 1)
        self.assertEqual(main(["1", "2"]), 1)
        self.assertEqual(main(["abc", "1", "==", "--types", "number", "number"]), 1)


if __name__ == "__main__":
    unittest.main()
