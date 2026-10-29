"""Random Number Generator: bilangan acak dalam rentang minimum-maksimum.

Jalankan:
    python randomnum.py 1 100                    # satu bilangan bulat 1..100
    python randomnum.py 1 49 --count 6 --unique  # 6 bilangan berbeda (seperti undian)
    python randomnum.py -- -10 10                # rentang negatif (perlu --negative)
    python randomnum.py 0 1 --decimals 3         # 3 angka di belakang koma, mis. 0.472
    python randomnum.py 1 6 --seed 42            # hasil tetap (untuk uji)
Tanpa argumen, program menanyakan minimum dan maksimum.
"""

import argparse
import random
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation

MAX_COUNT = 1000


def parse_bound(text, name):
    try:
        value = Decimal(str(text).strip())
    except InvalidOperation:
        raise ValueError(f"{name} '{str(text).strip()}' bukan angka.") from None
    if not value.is_finite():
        raise ValueError(f"{name} '{str(text).strip()}' bukan angka yang valid.")
    return value


def generate(minimum, maximum, count=1, decimals=0, allow_negative=False, unique=False, rng=None):
    """Daftar `count` bilangan acak dalam [minimum, maksimum], seragam dan selalu di dalam rentang.

    decimals=0 menghasilkan bilangan bulat; decimals=N menghasilkan bilangan dengan N angka di
    belakang koma. Cara kerjanya: rentang diskalakan ke bilangan bulat (x * 10^N), diundi sebagai
    bilangan bulat, lalu dikembalikan, jadi tidak ada kesalahan pembulatan yang bisa keluar rentang.
    """
    rng = rng or random.Random()
    lo, hi = parse_bound(minimum, "Minimum"), parse_bound(maximum, "Maksimum")
    if lo > hi:
        raise ValueError(f"Minimum ({lo}) tidak boleh lebih besar dari maksimum ({hi}).")
    if lo < 0 and not allow_negative:
        raise ValueError("Nilai negatif tidak diizinkan. Aktifkan opsi bilangan negatif untuk memakainya.")
    if not isinstance(decimals, int) or not 0 <= decimals <= 10:
        raise ValueError("Jumlah desimal harus bilangan bulat 0 sampai 10.")
    if not isinstance(count, int) or not 1 <= count <= MAX_COUNT:
        raise ValueError(f"Jumlah bilangan harus 1 sampai {MAX_COUNT}.")

    scale = Decimal(10) ** decimals
    low = int((lo * scale).to_integral_value(rounding=ROUND_CEILING))
    high = int((hi * scale).to_integral_value(rounding=ROUND_FLOOR))
    if low > high:
        raise ValueError("Tidak ada bilangan dengan jumlah desimal itu di dalam rentang tersebut.")
    size = high - low + 1
    if unique:
        if count > size:
            raise ValueError(f"Hanya ada {size} kemungkinan nilai, tidak cukup untuk {count} bilangan berbeda.")
        picks = [low + offset for offset in rng.sample(range(size), count)]
    else:
        picks = [rng.randint(low, high) for _ in range(count)]
    if decimals == 0:
        return picks
    return [Decimal(p) / scale for p in picks]


def format_number(value, decimals):
    return str(value) if decimals == 0 else f"{value:.{decimals}f}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generator bilangan acak.")
    parser.add_argument("minimum", nargs="?")
    parser.add_argument("maximum", nargs="?")
    parser.add_argument("-n", "--count", type=int, default=1, help="berapa bilangan yang dihasilkan")
    parser.add_argument("--unique", action="store_true", help="tanpa pengulangan (seperti undian)")
    parser.add_argument("--decimals", type=int, default=0, help="jumlah angka di belakang koma (bawaan 0 = bulat)")
    parser.add_argument("--negative", action="store_true", help="izinkan nilai negatif")
    parser.add_argument("--seed", type=int, help="angka acak tetap")
    args = parser.parse_args(argv)
    try:
        minimum, maximum = args.minimum, args.maximum
        if minimum is None:
            minimum = input("Minimum: ")
        if maximum is None:
            maximum = input("Maksimum: ")
        numbers = generate(minimum, maximum, args.count, args.decimals, args.negative, args.unique,
                           random.Random(args.seed))
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    print(", ".join(format_number(n, args.decimals) for n in numbers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
