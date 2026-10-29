"""Vigenere Cipher: sandi klasik dengan kunci berulang, ditulis tanpa pustaka.

Setiap huruf teks digeser sebanyak nilai huruf kunci pada posisi yang sama (A=0 ... Z=25).
Kunci diulang; huruf besar/kecil dipertahankan; karakter selain huruf A-Z (spasi, angka, tanda
baca, dan huruf beraksen) tidak diubah dan TIDAK memajukan kunci.

Jalankan:
    python vigenere.py encrypt "Attack at dawn" LEMON
    python vigenere.py decrypt "Lxfopv ef rnhr" LEMON
    python vigenere.py crack berkas_sandi.txt     # coba patahkan (teks Inggris, panjang >= ~200 huruf)
    python vigenere.py                            # panel interaktif
"""

import argparse
import string
import sys

ALPHABET = string.ascii_uppercase

# Frekuensi huruf bahasa Inggris (persen), dipakai untuk mematahkan sandi.
ENGLISH_FREQ = [8.167, 1.492, 2.782, 4.253, 12.702, 2.228, 2.015, 6.094, 6.966, 0.153, 0.772, 4.025, 2.406,
                6.749, 7.507, 1.929, 0.095, 5.987, 6.327, 9.056, 2.758, 0.978, 2.360, 0.150, 1.974, 0.074]


def validate_key(key):
    key = key.strip()
    if not key:
        raise ValueError("Kunci tidak boleh kosong.")
    bad = [c for c in key if c.upper() not in ALPHABET]
    if bad:
        raise ValueError(f"Kunci hanya boleh berisi huruf A-Z (ditemukan '{bad[0]}').")
    return key.upper()


def _shift(text, key, direction):
    key = validate_key(key)
    out, index = [], 0
    for char in text:
        upper = char.upper()
        if char.isascii() and upper in ALPHABET:
            shift = ALPHABET.index(key[index % len(key)]) * direction
            shifted = ALPHABET[(ALPHABET.index(upper) + shift) % 26]
            out.append(shifted if char.isupper() else shifted.lower())
            index += 1
        else:
            out.append(char)
    return "".join(out)


def encrypt(plaintext, key):
    return _shift(plaintext, key, +1)


def decrypt(ciphertext, key):
    return _shift(ciphertext, key, -1)


# --- Analisis: menjawab "bagaimana mendeteksi dan mematahkannya?" -----------

def letters_only(text):
    return "".join(c.upper() for c in text if c.isascii() and c.upper() in ALPHABET)


def index_of_coincidence(text):
    """Peluang dua huruf acak dari teks sama. Bahasa Inggris ~0.066, teks acak merata ~0.038."""
    letters = letters_only(text)
    n = len(letters)
    if n < 2:
        raise ValueError("Butuh minimal 2 huruf.")
    counts = [letters.count(c) for c in ALPHABET]
    return sum(c * (c - 1) for c in counts) / (n * (n - 1))


def guess_key_length(ciphertext, max_length=20):
    """Panjang kunci: yang membuat tiap 'kolom' (huruf-huruf yang memakai huruf kunci sama) mirip bahasa asli.

    Kelipatan panjang kunci yang benar (5 -> 10, 15) juga bagus, dan selisihnya hanya derau acak, jadi diambil
    panjang TERKECIL yang skornya mendekati skor terbaik (>= 80% darinya)."""
    letters = letters_only(ciphertext)
    scores = {}
    for length in range(1, min(max_length, len(letters) // 4) + 1):
        columns = [letters[i::length] for i in range(length)]
        scores[length] = sum(index_of_coincidence(c) for c in columns) / length
    best = max(scores.values())
    return min(length for length, score in scores.items() if score >= 0.8 * best)


def crack(ciphertext, max_length=20):
    """Patahkan sandi teks Inggris: tebak panjang kunci, lalu tiap huruf kunci dengan uji frekuensi huruf."""
    letters = letters_only(ciphertext)
    if len(letters) < 50:
        raise ValueError("Teks terlalu pendek untuk dipatahkan (minimal sekitar 50 huruf, idealnya 200+).")
    length = guess_key_length(ciphertext, max_length)
    key = []
    for column in (letters[i::length] for i in range(length)):
        best_shift, best_score = 0, float("inf")
        for shift in range(26):
            counts = [0] * 26
            for c in column:
                counts[(ALPHABET.index(c) - shift) % 26] += 1
            expected = [f / 100 * len(column) for f in ENGLISH_FREQ]
            score = sum((counts[i] - expected[i]) ** 2 / expected[i] for i in range(26))  # chi-kuadrat
            if score < best_score:
                best_shift, best_score = shift, score
        key.append(ALPHABET[best_shift])
    return "".join(key), decrypt(ciphertext, "".join(key))


# --- Panel: tombol Encrypt / Decrypt / Compare -------------------------------

class Panel:
    def __init__(self):
        self.plaintext = ""
        self.key = ""
        self.encrypted = None
        self.result = ""

    @property
    def decrypt_enabled(self):
        return self.encrypted is not None  # nonaktif sampai ada pesan terenkripsi

    @property
    def compare_enabled(self):
        return self.decrypt_enabled and self.result != "" and self.result != self.encrypted

    def encrypt(self, plaintext, key):
        if not plaintext.strip():
            raise ValueError("Pesan tidak boleh kosong.")
        self.encrypted = encrypt(plaintext, key)
        self.plaintext, self.key, self.result = plaintext, key, self.encrypted
        return self.encrypted

    def decrypt(self):
        if not self.decrypt_enabled:
            raise ValueError("Tombol Decrypt nonaktif: enkripsi sebuah pesan dulu.")
        self.result = decrypt(self.encrypted, self.key)
        return self.result

    def compare(self):
        """Bandingkan pesan asli dengan hasil dekripsi; ValueError kalau berbeda."""
        if not self.compare_enabled:
            raise ValueError("Tombol Compare nonaktif: dekripsi pesannya dulu.")
        if self.result != self.plaintext:
            raise ValueError(f"Berbeda! Asli: {self.plaintext!r}, hasil dekripsi: {self.result!r}")
        return True


def run_panel():
    panel = Panel()
    print("Panel Vigenere. Perintah: encrypt, decrypt, compare, quit")
    while True:
        state = f"[ENCRYPT] [DECRYPT{'' if panel.decrypt_enabled else ' (nonaktif)'}] [COMPARE{'' if panel.compare_enabled else ' (nonaktif)'}]"
        try:
            command = input(f"{state}\n> ").strip().lower()
            if command in ("quit", "q"):
                return 0
            if command == "encrypt":
                print("Hasil:", panel.encrypt(input("Pesan: "), input("Kunci: ")))
            elif command == "decrypt":
                print("Hasil:", panel.decrypt())
            elif command == "compare":
                panel.compare()
                print("Sama: pesan asli dan hasil dekripsi identik.")
            else:
                print("Perintah tidak dikenal.")
        except ValueError as error:
            print(f"Error: {error}")
        except EOFError:
            return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Vigenere Cipher.")
    sub = parser.add_subparsers(dest="command")
    for name in ("encrypt", "decrypt"):
        p = sub.add_parser(name)
        p.add_argument("text")
        p.add_argument("key")
    sub.add_parser("crack").add_argument("file", help="berkas teks sandi")
    args = parser.parse_args(argv)
    try:
        if args.command is None:
            return run_panel()
        if args.command == "encrypt":
            print(encrypt(args.text, args.key))
        elif args.command == "decrypt":
            print(decrypt(args.text, args.key))
        else:
            try:
                with open(args.file, encoding="utf-8") as file:
                    text = file.read()
            except OSError as error:
                raise ValueError(f"Berkas '{args.file}' tidak bisa dibaca: {error.strerror}.") from None
            key, plain = crack(text)
            print(f"Tebakan kunci: {key}\n{plain}")
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
