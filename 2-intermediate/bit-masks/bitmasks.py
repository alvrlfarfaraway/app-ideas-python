"""Bit Masks: cari kota berdasarkan offset GMT memakai operasi bitwise, bukan if/switch.

Setiap offset GMT dari -12 sampai +12 mendapat satu bit (25 bit):
    bit 0  = GMT -12
    bit 12 = GMT +0
    bit 24 = GMT +12

Tiap kota menyimpan pola bit zona waktunya. Pencarian membuat masker dari offset
yang dicari, lalu kota cocok kalau `pola_kota & masker` tidak nol. Beberapa offset
bisa digabung dengan OR (|) dalam satu masker, dan pencarian "bukan" cukup
membalik maskernya dengan XOR terhadap semua bit (^ ALL_ZONES).

Jalankan:
    python bitmasks.py 2            # kota di GMT +2
    python bitmasks.py -4 -5        # kota di GMT -4 atau -5
    python bitmasks.py 2 --not      # kota yang TIDAK di GMT +2
    python bitmasks.py 9 --bits     # tampilkan juga pola bitnya
    python bitmasks.py              # mode interaktif
"""

import argparse
import sys

MIN_OFFSET = -12
MAX_OFFSET = 12
ZONE_COUNT = MAX_OFFSET - MIN_OFFSET + 1  # 25 zona, -12..+12
ALL_ZONES = (1 << ZONE_COUNT) - 1  # 25 bit bernilai 1

# Offset sesuai spesifikasi (waktu musim panas untuk kota Eropa dan AS).
CITY_OFFSETS = (
    ("Moscow", 3),
    ("Paris", 2),
    ("Berlin", 2),
    ("Brussels", 2),
    ("Amsterdam", 2),
    ("Rome", 2),
    ("London", 1),
    ("Dublin", 1),
    ("New York", -4),
    ("Washington, DC", -4),
    ("St. Louis", -5),
    ("Los Angeles", -7),
    ("Tokyo", 9),
    ("Beijing", 8),
    ("Ho Chi Minh City", 7),
    ("Mumbai", 5),
)


def zone_bit(offset):
    """Bit untuk satu offset GMT. -12 -> 1 << 0, +12 -> 1 << 24."""
    if isinstance(offset, bool) or not isinstance(offset, int):
        raise TypeError("Offset GMT harus bilangan bulat.")
    if not MIN_OFFSET <= offset <= MAX_OFFSET:
        raise ValueError(f"Offset GMT harus antara {MIN_OFFSET} dan +{MAX_OFFSET}, bukan {offset}.")
    return 1 << (offset - MIN_OFFSET)


# Pola bit tiap kota dihitung sekali. Setelah ini offset aslinya tidak dipakai lagi untuk mencari.
CITY_BITS = tuple((name, zone_bit(offset)) for name, offset in CITY_OFFSETS)


def build_mask(offsets, invert=False):
    """Gabungkan bit beberapa offset dengan OR. invert=True membalik semua 25 bit."""
    mask = 0
    for offset in offsets:
        mask |= zone_bit(offset)
    if invert:
        mask ^= ALL_ZONES
    return mask


def find_cities(mask, cities=CITY_BITS):
    """Nama kota yang bitnya beririsan dengan masker. Satu operasi AND per kota, tanpa perbandingan offset."""
    return [name for name, bits in cities if bits & mask]


def format_bits(value):
    """Tampilkan 25 bit, offset +12 di kiri dan -12 di kanan (urutan biner biasa)."""
    return format(value, f"0{ZONE_COUNT}b")


def offset_label(offset):
    return f"GMT {offset:+d}" if offset else "GMT +0"


def parse_offset(text):
    cleaned = text.strip().upper().replace(" ", "")
    for prefix in ("GMT", "UTC"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):] or "0"
    try:
        value = int(cleaned)
    except ValueError:
        raise ValueError(f"'{text.strip()}' bukan offset GMT. Contoh: 2, -4, +9, GMT+3.") from None
    zone_bit(value)  # validasi rentang
    return value


def render(offsets, invert=False, show_bits=False):
    mask = build_mask(offsets, invert)
    found = set(find_cities(mask))
    labels = ", ".join(offset_label(o) for o in offsets)
    title = f"Kota yang TIDAK di {labels}" if invert else f"Kota di {labels}"
    lines = [title, ""]
    if show_bits:
        lines.append(f"{'masker':<18}  {format_bits(mask)}")
        lines.append("")
    for name, bits in CITY_BITS:
        box = "[x]" if name in found else "[ ]"
        if show_bits:
            hit = format_bits(bits & mask)
            lines.append(f"{box} {name:<16}  {format_bits(bits)}  & masker = {hit}")
        else:
            lines.append(f"{box} {name}")
    lines.append("")
    lines.append(f"{len(found)} dari {len(CITY_BITS)} kota cocok.")
    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(description="Cari kota berdasarkan offset GMT dengan bit mask.")
    parser.add_argument("offsets", nargs="*", help="offset GMT, misalnya 2 atau -4 (boleh lebih dari satu)")
    parser.add_argument("--not", dest="invert", action="store_true", help="cari kota yang TIDAK di offset itu")
    parser.add_argument("--bits", action="store_true", help="tampilkan pola bit tiap kota")
    return parser


def run_once(texts, invert, show_bits):
    if not texts:
        raise ValueError("Masukkan setidaknya satu offset GMT.")
    offsets = [parse_offset(t) for t in texts]
    return render(offsets, invert, show_bits)


def main(argv=None):
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    if args.offsets:
        try:
            print(run_once(args.offsets, args.invert, args.bits))
        except ValueError as error:
            print(f"Error: {error}")
            return 1
        return 0
    print("Bit Masks: ketik offset GMT (boleh beberapa, pisahkan spasi).")
    print("Awali dengan ! untuk mencari kebalikannya, misalnya !2. Kosongkan untuk keluar.")
    while True:
        text = input("GMT: ").strip()
        if not text:
            return 0
        invert = text.startswith("!")
        try:
            print(run_once(text.lstrip("!").split(), invert, args.bits))
        except ValueError as error:
            print(f"Error: {error}")
        print()


if __name__ == "__main__":
    raise SystemExit(main())
