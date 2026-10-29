"""TrueOrFalse: hasil operator pembanding JavaScript untuk dua nilai, tanpa eval().

Aturannya mengikuti spesifikasi ECMAScript:
- ===, !==   : sama tipe dan sama nilai (NaN tidak pernah sama dengan apa pun, termasuk dirinya sendiri)
- ==, !=     : "abstract equality", nilai dikonversi dulu bila tipenya berbeda
- <, >, <=, >= : dua string dibandingkan menurut urutan kode UTF-16; selain itu keduanya diubah ke angka

Tipe yang didukung: string, number, boolean, null, undefined.

Jalankan:
    python trueorfalse.py 0 false ==                      # kedua nilai string "0" dan "false"
    python trueorfalse.py 0 false == --types number boolean
    python trueorfalse.py                                 # mode interaktif
"""

import argparse
import math
import re

OPERATORS = ("===", "!==", "==", "!=", "<=", ">=", "<", ">")
TYPES = ("string", "number", "boolean", "null", "undefined")

NaN = float("nan")
_DECIMAL = re.compile(r"[+-]?(?:\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)")
_RADIX = {"0x": 16, "0b": 2, "0o": 8}


class JSValue:
    """Nilai JavaScript dengan tipenya: type adalah salah satu dari TYPES."""

    def __init__(self, type_, value=None):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"JSValue({self.type}, {self.value!r})"


def string_to_number(text):
    """Number("...") pada JavaScript: spasi di pinggir dibuang, "" -> 0, tidak valid -> NaN."""
    text = text.strip()
    if text == "":
        return 0.0
    if _DECIMAL.fullmatch(text):
        return float(text)
    sign, body = (text[0], text[1:]) if text[0] in "+-" else ("", text)
    if body == "Infinity":
        return -math.inf if sign == "-" else math.inf
    if not sign and body[:2].lower() in _RADIX and len(body) > 2:
        try:
            return float(int(body[2:], _RADIX[body[:2].lower()]))
        except ValueError:
            return NaN
    return NaN  # "nan", "inf", "1_000", "1,5", ... bukan angka di JavaScript


def to_number(value):
    if value.type == "number":
        return value.value
    if value.type == "string":
        return string_to_number(value.value)
    if value.type == "boolean":
        return 1.0 if value.value else 0.0
    if value.type == "null":
        return 0.0
    return NaN  # undefined


def strict_equals(a, b):
    if a.type != b.type:
        return False
    if a.type in ("null", "undefined"):
        return True
    return a.value == b.value  # NaN == NaN adalah False di Python juga


def loose_equals(a, b):
    if a.type == b.type:
        return strict_equals(a, b)
    if {a.type, b.type} == {"null", "undefined"}:
        return True
    if a.type in ("null", "undefined") or b.type in ("null", "undefined"):
        return False
    if a.type == "boolean":
        return loose_equals(JSValue("number", to_number(a)), b)
    if b.type == "boolean":
        return loose_equals(a, JSValue("number", to_number(b)))
    # sisa: number dan string -> string diubah ke angka
    return to_number(a) == to_number(b)


def _utf16(text):
    return text.encode("utf-16-be")  # urutan byte big-endian = urutan unit kode UTF-16 (aturan JS)


def less_than(a, b):
    """a < b. Mengembalikan None bila 'undefined' (ada NaN), yang diperlakukan False oleh pemanggil."""
    if a.type == "string" and b.type == "string":
        return _utf16(a.value) < _utf16(b.value)
    x, y = to_number(a), to_number(b)
    if math.isnan(x) or math.isnan(y):
        return None
    return x < y


def compare(a, operator, b):
    """Hasil `a <operator> b` di JavaScript sebagai bool."""
    if operator == "===":
        return strict_equals(a, b)
    if operator == "!==":
        return not strict_equals(a, b)
    if operator == "==":
        return loose_equals(a, b)
    if operator == "!=":
        return not loose_equals(a, b)
    if operator == "<":
        return less_than(a, b) is True
    if operator == ">":
        return less_than(b, a) is True
    if operator == "<=":
        result = less_than(b, a)  # a <= b  setara  !(b < a), tetapi False bila tidak terdefinisi
        return result is False
    if operator == ">=":
        result = less_than(a, b)
        return result is False
    raise ValueError(f"Operator '{operator}' tidak valid. Pilih salah satu: {' '.join(OPERATORS)}")


def make_value(text, type_="string"):
    """Bentuk nilai bertipe dari teks isian. ValueError kalau tidak cocok dengan tipenya."""
    if type_ not in TYPES:
        raise ValueError(f"Tipe '{type_}' tidak dikenal. Pilih salah satu: {', '.join(TYPES)}.")
    if type_ == "string":
        return JSValue("string", text)
    if type_ == "number":
        number = string_to_number(text)
        if math.isnan(number) and text.strip() != "NaN":
            raise ValueError(f"'{text}' bukan angka JavaScript yang valid (boleh juga NaN atau Infinity).")
        return JSValue("number", number)
    if type_ == "boolean":
        if text.strip() not in ("true", "false"):
            raise ValueError(f"'{text}' bukan boolean; tulis true atau false.")
        return JSValue("boolean", text.strip() == "true")
    return JSValue(type_)


def show(value):
    if value.type == "string":
        return f'"{value.value}"'
    if value.type == "number":
        v = value.value
        if math.isnan(v):
            return "NaN"
        if math.isinf(v):
            return "Infinity" if v > 0 else "-Infinity"
        return str(int(v)) if v.is_integer() else repr(v)
    if value.type == "boolean":
        return "true" if value.value else "false"
    return value.type


def evaluate(left_text, right_text, operator, left_type="string", right_type="string"):
    """Satu pembandingan lengkap. Mengembalikan (hasil bool, ungkapan JavaScript untuk ditampilkan)."""
    operator = operator.strip()
    if operator not in OPERATORS:
        raise ValueError(f"Operator '{operator}' tidak valid. Pilih salah satu: {' '.join(OPERATORS)}")
    a, b = make_value(left_text, left_type), make_value(right_text, right_type)
    return compare(a, operator, b), f"{show(a)} {operator} {show(b)}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Hasil pembandingan JavaScript tanpa eval().")
    parser.add_argument("left", nargs="?")
    parser.add_argument("right", nargs="?")
    parser.add_argument("operator", nargs="?")
    parser.add_argument("--types", nargs=2, metavar=("TIPE_KIRI", "TIPE_KANAN"), default=["string", "string"],
                        help=f"tipe tiap nilai: {', '.join(TYPES)} (bawaan: string string)")
    args = parser.parse_args(argv)
    try:
        if args.left is None:
            return interactive()
        if args.right is None or args.operator is None:
            raise ValueError("Beri tiga argumen: nilai kiri, nilai kanan, operator.")
        result, expression = evaluate(args.left, args.right, args.operator, *args.types)
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    print(f"{expression}  ->  {'TRUE' if result else 'FALSE'}")
    return 0


def interactive():
    print(f"Operator: {' '.join(OPERATORS)}. Ketik :q sebagai nilai kiri untuk keluar.")
    print(f"Tipe (opsional): {', '.join(TYPES)}; kosong = string. Nilai kosong (\"\") boleh dibandingkan.")
    while True:
        try:
            left = input("Nilai kiri : ")
            if left == ":q":
                return 0
            left_type = input("  tipe     : ").strip() or "string"
            right = input("Nilai kanan: ")
            right_type = input("  tipe     : ").strip() or "string"
            operator = input("Operator   : ")
            result, expression = evaluate(left, right, operator, left_type, right_type)
            print(f"{expression}  ->  {'TRUE' if result else 'FALSE'}")
        except ValueError as error:
            print(f"Peringatan: {error}")
        except EOFError:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
