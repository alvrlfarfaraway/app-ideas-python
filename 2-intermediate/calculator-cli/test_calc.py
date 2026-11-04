import contextlib
import io
import unittest
from decimal import Decimal

from calc import (
    CalcError,
    add,
    div,
    format_result,
    main,
    mul,
    parse_number,
    power,
    square_root,
    sub,
)


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(list(argv))
        except SystemExit as exit_:
            code = exit_.code
    return code, out.getvalue().strip(), err.getvalue().strip()


def result(*argv):
    code, out, err = run(*argv)
    if code != 0:
        raise AssertionError(f"{argv} gagal: {err}")
    return out


class ParseTest(unittest.TestCase):
    def test_bulat_tanpa_f(self):
        self.assertEqual(parse_number("42", False), 42)
        self.assertEqual(parse_number("-7", False), -7)
        self.assertEqual(parse_number("1_000", False), 1000)
        self.assertIsInstance(parse_number("3", False), int)

    def test_pecahan_butuh_f(self):
        with self.assertRaises(CalcError) as ctx:
            parse_number("1.5", False)
        self.assertIn("-f", str(ctx.exception))
        self.assertEqual(parse_number("1.5", True), Decimal("1.5"))
        self.assertEqual(parse_number("1e3", True), Decimal("1E+3"))

    def test_bukan_angka(self):
        for text in ("abc", "", "1,5", "0x10"):
            for allow in (False, True):
                with self.assertRaises(CalcError, msg=(text, allow)):
                    parse_number(text, allow)
        for text in ("nan", "inf", "-Infinity"):
            with self.assertRaises(CalcError):
                parse_number(text, True)


class OperationTest(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add([1, 2, 3]), 6)
        self.assertEqual(add([5]), 5)
        self.assertEqual(add([Decimal("0.1"), Decimal("0.2")]), Decimal("0.3"))

    def test_add_even_odd(self):
        self.assertEqual(add([1, 2, 3, 4, 5, 6], "even"), 12)
        self.assertEqual(add([1, 2, 3, 4, 5, 6], "odd"), 9)
        self.assertEqual(add([-3, -2, 0], "even"), -2)
        self.assertEqual(add([-3, -2, 0], "odd"), -3)
        self.assertEqual(add([1, 3], "even"), 0)
        with self.assertRaises(CalcError):
            add([Decimal("2")], "even")

    def test_sub_mul_div(self):
        self.assertEqual(sub([10, 3, 2]), 5)
        self.assertEqual(sub([10]), 10)
        self.assertEqual(mul([2, 3, 4]), 24)
        self.assertEqual(mul([Decimal("1.5"), 2]), Decimal("3.0"))
        self.assertEqual(div([7, 2]), Decimal("3.5"))
        self.assertEqual(div([100, 4, 5]), 5)
        with self.assertRaises(CalcError):
            div([1, 0])
        with self.assertRaises(CalcError):
            div([1, Decimal("0.0")])

    def test_pecahan_desimal_eksak(self):
        self.assertEqual(add([Decimal("12345678901234567890123456789.1"), 1]),
                         Decimal("12345678901234567890123456790.1"))

    def test_power(self):
        self.assertEqual(power(2, 10), 1024)
        self.assertEqual(power(-2, 3), -8)
        self.assertEqual(power(5, 0), 1)
        self.assertEqual(power(2, -2), Decimal("0.25"))
        self.assertEqual(power(Decimal("2.25"), Decimal("0.5")), Decimal("1.5"))
        self.assertEqual(power(2, 100), 2 ** 100)  # eksak, bukan dibulatkan
        for base, exp in ((0, -1), (Decimal(-8), Decimal("0.5")), (10, 5000)):
            with self.assertRaises(CalcError, msg=(base, exp)):
                power(base, exp)

    def test_sqrt(self):
        self.assertEqual(square_root(144), 12)
        self.assertIsInstance(square_root(144), int)
        self.assertEqual(square_root(0), 0)
        self.assertEqual(str(square_root(2)), "1.414213562373095048801688724")
        self.assertEqual(square_root(Decimal("2.25")), Decimal("1.5"))
        self.assertEqual(square_root(10 ** 60), 10 ** 30)
        with self.assertRaises(CalcError):
            square_root(-4)

    def test_hasil_terlalu_besar(self):
        with self.assertRaises(CalcError):
            mul([10 ** 2000, 10 ** 2000])


class FormatTest(unittest.TestCase):
    def test_tanpa_nol_berlebih(self):
        self.assertEqual(format_result(5), "5")
        self.assertEqual(format_result(Decimal("5.000")), "5")
        self.assertEqual(format_result(Decimal("3.50")), "3.5")
        self.assertEqual(format_result(Decimal("1E+3")), "1000")
        self.assertEqual(format_result(Decimal("-0.0")), "0")
        self.assertEqual(format_result(Decimal("0.000125")), "0.000125")

    def test_notasi_ilmiah_untuk_angka_ekstrem(self):
        self.assertEqual(format_result(Decimal("1E+40")), "1E+40")
        self.assertEqual(format_result(Decimal("1E-40")), "1E-40")


class CliTest(unittest.TestCase):
    def test_user_stories(self):
        self.assertEqual(result("add", "1", "2", "3"), "6")
        self.assertEqual(result("add", "-f", "1.5", "2.25"), "3.75")
        self.assertEqual(result("add", "-f", "0.1", "0.2"), "0.3")
        self.assertEqual(result("add", "even", "1", "2", "3", "4"), "6")
        self.assertEqual(result("add", "odd", "1", "2", "3", "4"), "4")
        self.assertEqual(result("add", "EVEN", "2", "4"), "6")

    def test_bonus(self):
        self.assertEqual(result("sub", "10", "3", "2"), "5")
        self.assertEqual(result("sub", "10", "-3"), "13")
        self.assertEqual(result("mul", "2", "3", "4"), "24")
        self.assertEqual(result("div", "7", "2"), "3.5")
        self.assertEqual(result("div", "1", "3"), "0.3333333333333333333333333333")
        self.assertEqual(result("pow", "2", "10"), "1024")
        self.assertEqual(result("pow", "2", "-2"), "0.25")
        self.assertEqual(result("sqrt", "2"), "1.414213562373095048801688724")
        self.assertEqual(result("sqrt", "-f", "2.25"), "1.5")

    def test_pesan_error(self):
        cases = (
            (("add", "1.5", "2"), "-f"),
            (("add", "even"), "Tulis angka"),
            (("add", "-f", "even", "2"), "bilangan bulat"),
            (("div", "1", "0"), "nol"),
            (("sqrt", "-4"), "real"),
            (("pow", "10", "5000"), "terlalu besar"),
            (("mul", "-f", "1e999999", "1e999999"), "terlalu besar"),
        )
        for argv, text in cases:
            code, out, err = run(*argv)
            self.assertEqual(code, 1, argv)
            self.assertEqual(out, "", argv)
            self.assertIn(text, err, argv)

    def test_help(self):
        code, out, _ = run("-h")
        self.assertEqual(code, 0)
        for name in ("add", "sub", "mul", "div", "pow", "sqrt"):
            self.assertIn(name, out)
        code, out, _ = run("add", "--help")
        self.assertEqual(code, 0)
        self.assertIn("even|odd", out)
        self.assertIn("-f, --float", out)

    def test_tanpa_perintah(self):
        code, _, err = run()
        self.assertEqual(code, 2)
        self.assertIn("<perintah>", err)


if __name__ == "__main__":
    unittest.main()
