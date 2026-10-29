"""Roman to Decimal: konversi angka Romawi <-> desimal (1 sampai 3999).

Jalankan:
    python roman.py XIV          # -> 14
    python roman.py 1994         # -> MCMXCIV   (angka dikenali otomatis, jadi dua arah)
    python roman.py              # mode interaktif
"""

import re
import sys

VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
MAX_VALUE = 3999  # tanpa garis atas (vinculum), M paling banyak tiga kali

# Bentuk baku: ribuan, ratusan, puluhan, satuan, masing-masing dengan pola sendiri.
CANONICAL = re.compile(r"M{0,3}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})")

NUMERALS = (("M", 1000), ("CM", 900), ("D", 500), ("CD", 400), ("C", 100), ("XC", 90),
            ("L", 50), ("XL", 40), ("X", 10), ("IX", 9), ("V", 5), ("IV", 4), ("I", 1))


def decimal_to_roman(number):
    if isinstance(number, bool) or not isinstance(number, int):
        raise ValueError("Angka desimal harus bilangan bulat.")
    if not 1 <= number <= MAX_VALUE:
        raise ValueError(f"Angka Romawi hanya bisa menyatakan 1 sampai {MAX_VALUE} (diterima {number}).")
    parts = []
    for symbol, value in NUMERALS:
        count, number = divmod(number, value)
        parts.append(symbol * count)
    return "".join(parts)


def _loose_value(text):
    """Nilai menurut aturan kurang-di-depan, tanpa memeriksa kebakuan (hanya untuk saran perbaikan)."""
    total = 0
    for i, char in enumerate(text):
        value = VALUES[char]
        total += -value if i + 1 < len(text) and VALUES[text[i + 1]] > value else value
    return total


def roman_to_decimal(text):
    """Ubah angka Romawi baku (huruf besar/kecil) ke desimal. ValueError dengan alasan yang jelas."""
    original = text
    text = text.strip().upper()
    if not text:
        raise ValueError("Masukkan satu angka Romawi.")
    for position, char in enumerate(text, start=1):
        if char not in VALUES:
            raise ValueError(f"Simbol '{char}' di posisi {position} bukan angka Romawi. "
                             f"Simbol yang sah: {', '.join(VALUES)}.")
    if not CANONICAL.fullmatch(text):
        guess = _loose_value(text)
        # V, L, dan D tidak pernah boleh dikurangkan (VX, LC, DM), jadi tebakan semacam itu tidak disarankan.
        bad_subtraction = any(a in "VLD" and VALUES[a] < VALUES[b] for a, b in zip(text, text[1:]))
        hint = f" Maksudmu {decimal_to_roman(guess)}?" if 1 <= guess <= MAX_VALUE and not bad_subtraction else ""
        raise ValueError(f"'{original.strip()}' bukan penulisan angka Romawi yang baku.{hint}")
    return _loose_value(text)  # untuk bentuk baku, aturan kurang-di-depan memberi nilai yang tepat


def convert(text):
    """Dua arah otomatis: digit -> Romawi, huruf -> desimal. Mengembalikan teks hasil."""
    text = text.strip()
    if text.isdigit():
        return decimal_to_roman(int(text))
    if text.lstrip("+-").isdigit():
        raise ValueError(f"Angka Romawi hanya bisa menyatakan 1 sampai {MAX_VALUE} (diterima {text}).")
    return str(roman_to_decimal(text))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        try:
            print(convert(argv[0]))
        except ValueError as error:
            print(f"Error: {error}")
            return 1
        return 0
    print("Ketik angka Romawi (XIV) atau desimal (14); kosongkan untuk keluar.")
    while True:
        try:
            text = input("> ")
        except EOFError:
            return 0
        if not text.strip():
            return 0
        try:
            print(convert(text))
        except ValueError as error:
            print(f"Error: {error}")


if __name__ == "__main__":
    raise SystemExit(main())
