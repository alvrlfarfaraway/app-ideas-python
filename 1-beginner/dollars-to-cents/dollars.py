"""Dollars to Cents: ubah nilai dolar menjadi sen, lalu pecah menjadi koin paling sedikit.

Memakai Decimal (bukan float) supaya 0.07 atau 1.15 tidak meleset akibat
pembulatan bilangan pecahan biner.

Jalankan:
    python dollars.py 2.75        # -> 275 sen: 11 quarter
    python dollars.py '$0.58'
    python dollars.py             # mode interaktif
"""

import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

COINS = (("quarter", 25), ("dime", 10), ("nickel", 5), ("penny", 1))


def dollars_to_cents(text):
    """Ubah teks seperti '2.75' atau '$2.75' menjadi bilangan bulat sen (dibulatkan ke sen terdekat)."""
    cleaned = text.strip()
    if cleaned.startswith("$"):
        cleaned = cleaned[1:].strip()
    if not cleaned:
        raise ValueError("Masukkan nilai dolar, misalnya 2.75.")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"'{text.strip()}' bukan angka yang valid.") from None
    if not amount.is_finite():
        raise ValueError(f"'{text.strip()}' bukan angka yang valid.")
    if amount < 0:
        raise ValueError("Nilai dolar tidak boleh negatif.")
    return int((amount * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def make_change(cents):
    """Pecah sen menjadi koin paling sedikit dengan algoritma greedy (koin terbesar dulu)."""
    result = {}
    left = cents
    for name, value in COINS:
        result[name], left = divmod(left, value)
    return result


def describe(text):
    cents = dollars_to_cents(text)
    change = make_change(cents)
    total = sum(change.values())
    parts = ", ".join(f"{count} {name}" for name, count in change.items())
    return f"{cents} sen = {total} koin ({parts})"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        try:
            print(describe(argv[0]))
        except ValueError as error:
            print(f"Error: {error}")
            return 1
        return 0
    print("Dollars to Cents: ketik nilai dolar, kosongkan untuk keluar.")
    while True:
        text = input("Dolar: ")
        if not text.strip():
            return 0
        try:
            print(describe(text))
        except ValueError as error:
            print(f"Error: {error}")


if __name__ == "__main__":
    raise SystemExit(main())
