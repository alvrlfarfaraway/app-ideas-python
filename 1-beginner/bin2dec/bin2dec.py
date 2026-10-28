"""Bin2Dec: ubah bilangan biner (maksimal 8 digit) menjadi desimal.

Batasan dari spesifikasi app-ideas:
- Digit biner tidak disimpan dalam array/list.
- Nilai desimal tiap digit dihitung dengan satu fungsi matematika, yaitu pangkat 2**n.

Jalankan:
    python bin2dec.py            # mode interaktif
    python bin2dec.py 1010       # satu kali konversi
    python bin2dec.py 1010 -m 16 # izinkan sampai 16 digit (fitur bonus)
"""

import argparse

MAX_DIGITS = 8


def bin_to_dec(text, max_digits=MAX_DIGITS):
    """Kembalikan nilai desimal dari string biner.

    Melempar ValueError dengan pesan yang bisa langsung ditampilkan ke pengguna
    kalau input kosong, terlalu panjang, atau berisi selain 0 dan 1.
    """
    text = text.strip()
    if not text:
        raise ValueError("Masukkan minimal 1 digit biner.")
    if len(text) > max_digits:
        raise ValueError(f"Maksimal {max_digits} digit, kamu memasukkan {len(text)}.")

    total = 0
    last = len(text) - 1
    for position, char in enumerate(text):
        if char not in "01":
            raise ValueError(f"Hanya boleh 0 dan 1, ditemukan '{char}' di posisi {position + 1}.")
        if char == "1":
            total += 2 ** (last - position)
    return total


def run_interactive(max_digits):
    print(f"Bin2Dec: ketik bilangan biner (maks {max_digits} digit), kosongkan untuk keluar.")
    while True:
        text = input("Biner  : ")
        if not text.strip():
            break
        try:
            print(f"Desimal: {bin_to_dec(text, max_digits)}")
        except ValueError as error:
            print(f"Error  : {error}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Konversi biner ke desimal.")
    parser.add_argument("binary", nargs="?", help="bilangan biner; kosongkan untuk mode interaktif")
    parser.add_argument("-m", "--max-digits", type=int, default=MAX_DIGITS,
                        help=f"jumlah digit maksimum (bawaan {MAX_DIGITS})")
    args = parser.parse_args(argv)

    if args.binary is None:
        run_interactive(args.max_digits)
        return 0
    try:
        print(bin_to_dec(args.binary, args.max_digits))
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
