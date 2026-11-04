"""Calculator CLI: kalkulator baris perintah dengan sub-command.

Tanpa -f hanya bilangan bulat yang diterima (seperti bahasa bertipe statis di
catatan spesifikasi). Dengan -f angka pecahan dihitung memakai Decimal, jadi
0.1 + 0.2 menghasilkan 0.3, bukan 0.30000000000000004.

Jalankan:
    python calc.py add 1 2 3            # 6
    python calc.py add -f 0.1 0.2       # 0.3
    python calc.py add even 1 2 3 4     # 6  (hanya bilangan genap)
    python calc.py add odd 1 2 3 4      # 4  (hanya bilangan ganjil)
    python calc.py sub 10 3 2           # 5
    python calc.py mul 2 3 4            # 24
    python calc.py div 7 2              # 3.5
    python calc.py pow 2 10             # 1024
    python calc.py sqrt 2               # 1.414213562373095048801688724
    python calc.py -h                   # semua perintah
    python calc.py add -h               # bantuan satu perintah
"""

import argparse
import math
import sys
from decimal import Decimal, DivisionByZero, InvalidOperation, Overflow, localcontext

PRECISION = 28  # digit penting untuk hasil yang tidak bisa eksak: pembagian, akar, pangkat pecahan
MAX_DIGITS = 4000  # batas panjang hasil; Python 3.12 menolak mencetak int lebih dari 4300 digit
SCIENTIFIC_FROM = 30  # Decimal dengan eksponen lebih dari ini ditampilkan dalam notasi ilmiah
TOO_BIG = f"Hasil terlalu besar (lebih dari {MAX_DIGITS} digit)."


class CalcError(ValueError):
    """Kesalahan yang ditampilkan ke pengguna sebagai pesan biasa."""


def parse_number(text, allow_float):
    """Ubah teks menjadi int (tanpa -f) atau Decimal (dengan -f)."""
    cleaned = text.strip().replace("_", "")
    if not allow_float:
        try:
            return int(cleaned)
        except ValueError:
            pass
        try:
            Decimal(cleaned)
        except InvalidOperation:
            raise CalcError(f"'{text}' bukan angka.") from None
        raise CalcError(f"'{text}' bukan bilangan bulat. Pakai -f untuk angka pecahan.")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise CalcError(f"'{text}' bukan angka.") from None
    if not value.is_finite():
        raise CalcError(f"'{text}' bukan angka yang terhingga.")
    return value


def parse_numbers(texts, allow_float):
    return [parse_number(t, allow_float) for t in texts]


def _check_size(value):
    if isinstance(value, int) and value and math.log10(abs(value)) >= MAX_DIGITS:
        raise CalcError(TOO_BIG)
    return value


def add(numbers, only=None):
    """Jumlahkan angka. only='even' atau 'odd' menyaring bilangan genap/ganjil lebih dulu."""
    if only is not None:
        if any(not isinstance(n, int) for n in numbers):
            raise CalcError(f"'{only}' hanya untuk bilangan bulat, jadi tidak bisa dipakai bersama -f.")
        numbers = [n for n in numbers if (n % 2 == 0) == (only == "even")]
    with localcontext() as ctx:
        ctx.prec = MAX_DIGITS  # penjumlahan desimal tetap eksak
        return _check_size(sum(numbers, 0))


def sub(numbers):
    with localcontext() as ctx:
        ctx.prec = MAX_DIGITS
        result = numbers[0]
        for n in numbers[1:]:
            result -= n
        return _check_size(result)


def mul(numbers):
    with localcontext() as ctx:
        ctx.prec = MAX_DIGITS
        result = 1
        for n in numbers:
            result = _check_size(result * n)
        return result


def div(numbers):
    """Bagi dari kiri ke kanan. Hasil selalu Decimal supaya 7 / 2 = 3.5."""
    with localcontext() as ctx:
        ctx.prec = PRECISION
        ctx.traps[DivisionByZero] = True
        result = Decimal(numbers[0])
        for n in numbers[1:]:
            if n == 0:
                raise CalcError("Tidak bisa membagi dengan nol.")
            result /= Decimal(n)
        return +result


def power(base, exponent):
    if base == 0 and exponent < 0:
        raise CalcError("Nol tidak bisa dipangkatkan dengan bilangan negatif.")
    if isinstance(base, int) and isinstance(exponent, int) and exponent >= 0:
        if abs(base) > 1 and exponent * math.log10(abs(base)) >= MAX_DIGITS:
            raise CalcError(TOO_BIG)
        return base ** exponent  # eksak
    with localcontext() as ctx:
        ctx.prec = PRECISION
        try:
            return Decimal(base) ** Decimal(exponent)
        except InvalidOperation:
            raise CalcError("Pangkat pecahan dari bilangan negatif tidak menghasilkan bilangan real.") from None


def square_root(value):
    if value < 0:
        raise CalcError("Akar kuadrat bilangan negatif bukan bilangan real.")
    if isinstance(value, int):
        root = math.isqrt(value)
        if root * root == value:
            return root
    with localcontext() as ctx:
        ctx.prec = PRECISION
        return Decimal(value).sqrt()


def format_result(value):
    """Tampilkan tanpa notasi ilmiah dan tanpa nol berlebih: 5.000 -> 5, 1E+3 -> 1000."""
    if isinstance(value, int):
        return str(value)
    value = value.normalize()
    if value.is_zero():
        return "0"
    if abs(value.adjusted()) > SCIENTIFIC_FROM:
        return str(value)  # misalnya 1E+500 atau 1.5E-40
    return format(value, "f")


OPERATIONS = {
    "add": "jumlahkan semua angka (bisa disaring: even/odd)",
    "sub": "kurangi angka pertama dengan angka-angka berikutnya",
    "mul": "kalikan semua angka",
    "div": "bagi angka pertama dengan angka-angka berikutnya",
    "pow": "pangkatkan: BASIS PANGKAT",
    "sqrt": "akar kuadrat satu angka",
}


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-f", "--float", action="store_true", help="terima angka pecahan (desimal)")

    parser = argparse.ArgumentParser(
        prog="calc",
        description="Kalkulator baris perintah.",
        epilog="Ketik 'calc <perintah> -h' untuk bantuan tiap perintah.",
    )
    commands = parser.add_subparsers(dest="command", metavar="<perintah>", required=True)

    add_parser = commands.add_parser(
        "add", parents=[common], help=OPERATIONS["add"],
        usage="calc add [-h] [-f] [even|odd] ANGKA [ANGKA ...]",
        description="Jumlahkan angka. Tulis 'even' atau 'odd' sebelum angka untuk hanya menjumlahkan "
                    "bilangan genap atau ganjil.",
        epilog="contoh: calc add 1 2 3 | calc add -f 1.5 2.25 | calc add even 1 2 3 4",
    )
    add_parser.add_argument("numbers", nargs="+", metavar="ANGKA", help="angka; boleh diawali even atau odd")

    for name in ("sub", "mul", "div"):
        p = commands.add_parser(name, parents=[common], help=OPERATIONS[name], description=OPERATIONS[name].capitalize() + ".")
        p.add_argument("numbers", nargs="+", metavar="ANGKA")

    pow_parser = commands.add_parser("pow", parents=[common], help=OPERATIONS["pow"],
                                     description="Pangkatkan BASIS dengan PANGKAT.")
    pow_parser.add_argument("base", metavar="BASIS")
    pow_parser.add_argument("exponent", metavar="PANGKAT")

    sqrt_parser = commands.add_parser("sqrt", parents=[common], help=OPERATIONS["sqrt"],
                                      description="Akar kuadrat satu angka.")
    sqrt_parser.add_argument("value", metavar="ANGKA")
    return parser


def calculate(args):
    if args.command == "add":
        texts = list(args.numbers)
        only = None
        if texts[0].lower() in ("even", "odd"):
            only = texts.pop(0).lower()
            if not texts:
                raise CalcError(f"Tulis angka setelah '{only}'.")
        return add(parse_numbers(texts, args.float), only)
    if args.command in ("sub", "mul", "div"):
        numbers = parse_numbers(args.numbers, args.float)
        return {"sub": sub, "mul": mul, "div": div}[args.command](numbers)
    if args.command == "pow":
        return power(parse_number(args.base, args.float), parse_number(args.exponent, args.float))
    return square_root(parse_number(args.value, args.float))


def main(argv=None):
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    try:
        print(format_result(calculate(args)))
    except CalcError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except Overflow:
        print("Error: Hasil terlalu besar.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
