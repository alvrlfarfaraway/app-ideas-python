"""Lorem Ipsum Generator: buat paragraf teks pengisi (placeholder).

Jalankan:
    python lorem.py 3              # 3 paragraf
    python lorem.py 5 --copy       # tampilkan dan salin ke clipboard
    python lorem.py 2 --seed 42    # hasil yang sama setiap kali (berguna untuk uji)
    python lorem.py                # tanya jumlah paragraf
"""

import argparse
import random
import subprocess
import sys

MAX_PARAGRAPHS = 100

OPENING = "Lorem ipsum dolor sit amet, consectetur adipiscing elit"

WORDS = """lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut
labore et dolore magna aliqua enim ad minim veniam quis nostrud exercitation ullamco laboris nisi
aliquip ex ea commodo consequat duis aute irure in reprehenderit voluptate velit esse cillum
fugiat nulla pariatur excepteur sint occaecat cupidatat non proident sunt culpa qui officia
deserunt mollit anim id est laborum curabitur pretium tincidunt lacus nunc gravida justo
vestibulum ante primis faucibus orci luctus ultrices posuere cubilia curae donec sagittis
euismod purus integer nec odio praesent libero suspendisse potenti pellentesque habitant morbi
tristique senectus netus malesuada fames turpis egestas aenean lectus mauris ornare vulputate
mattis fringilla cras vel""".split()


def parse_count(text):
    """Ubah teks jumlah paragraf menjadi bilangan bulat 1..MAX_PARAGRAPHS, atau ValueError."""
    text = text.strip()
    try:
        count = int(text)
    except ValueError:
        raise ValueError(f"'{text}' bukan bilangan bulat.") from None
    if not 1 <= count <= MAX_PARAGRAPHS:
        raise ValueError(f"Jumlah paragraf harus antara 1 dan {MAX_PARAGRAPHS}.")
    return count


def sentence(rng, first=False):
    if first:
        return OPENING + "."
    length = rng.randint(6, 16)
    words = [rng.choice(WORDS) for _ in range(length)]
    if length >= 10:  # sisipkan koma di tengah kalimat panjang
        words[rng.randint(3, length - 4)] += ","
    return " ".join(words).capitalize() + "."


def paragraph(rng, first=False):
    count = rng.randint(4, 8)
    return " ".join(sentence(rng, first and i == 0) for i in range(count))


def generate(count, seed=None):
    """Daftar `count` paragraf. Paragraf pertama selalu diawali kalimat klasik "Lorem ipsum dolor sit amet..."."""
    if not isinstance(count, int) or not 1 <= count <= MAX_PARAGRAPHS:
        raise ValueError(f"Jumlah paragraf harus bilangan bulat antara 1 dan {MAX_PARAGRAPHS}.")
    rng = random.Random(seed)
    return [paragraph(rng, first=(i == 0)) for i in range(count)]


def copy_to_clipboard(text):
    """Salin teks ke clipboard dengan perintah bawaan OS. Mengembalikan True kalau berhasil."""
    command = {"win32": ["clip"], "darwin": ["pbcopy"]}.get(sys.platform, ["xclip", "-selection", "clipboard"])
    try:
        # Teks lorem hanya berisi ASCII, jadi tidak ada masalah pengodean di clip.exe.
        subprocess.run(command, input=text.encode("ascii"), check=True, timeout=15, capture_output=True)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generator lorem ipsum.")
    parser.add_argument("paragraphs", nargs="?", help=f"jumlah paragraf (1-{MAX_PARAGRAPHS}); kosong = ditanya")
    parser.add_argument("--copy", action="store_true", help="salin hasilnya ke clipboard")
    parser.add_argument("--seed", type=int, help="angka acak tetap supaya hasilnya selalu sama")
    args = parser.parse_args(argv)
    try:
        text = args.paragraphs if args.paragraphs is not None else input("Jumlah paragraf: ")
        output = "\n\n".join(generate(parse_count(text), args.seed))
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    print(output)
    if args.copy:
        print("\n(Disalin ke clipboard.)" if copy_to_clipboard(output) else "\n(Gagal menyalin ke clipboard; salin manual dari atas.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
