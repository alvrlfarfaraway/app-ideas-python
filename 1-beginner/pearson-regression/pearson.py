"""Pearson Regression: koefisien korelasi Pearson dan garis regresi linear, dihitung tanpa paket.

Semua perhitungan (rata-rata, simpangan baku, korelasi, regresi) ditulis dengan Python murni
sesuai batasan spesifikasi. Pustaka seperti numpy hanya dipakai di notebook/tes untuk
MEMBANDINGKAN hasil, bukan untuk menghitung.

Jalankan dari terminal:
    python pearson.py data.csv     # CSV dua kolom (x,y); baris judul boleh ada
"""

import csv
import math
import sys

STRONG = 0.7  # |r| >= 0.7  -> "Some correlation"
WEAK = 0.3    # |r| <  0.3  -> "No correlation"; di antaranya "Neutral"


def parse_number(text):
    """Ubah teks menjadi bilangan real, atau ValueError dengan pesan yang jelas."""
    text = str(text).strip()
    if not text:
        raise ValueError("kosong")
    try:
        value = float(text)
    except ValueError:
        raise ValueError(f"'{text}' bukan bilangan real (gunakan titik untuk desimal, misalnya 3.5)") from None
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"'{text}' bukan bilangan real yang terhingga")
    return value


def mean(values):
    if not values:
        raise ValueError("Data kosong.")
    return sum(values) / len(values)


def std_dev(values, sample=True):
    """Simpangan baku. sample=True memakai pembagi n-1 (sampel), False memakai n (populasi)."""
    n = len(values)
    if n < (2 if sample else 1):
        raise ValueError("Simpangan baku sampel butuh minimal 2 data.")
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1 if sample else n))


def _check_pairs(xs, ys):
    if len(xs) != len(ys):
        raise ValueError(f"Jumlah x ({len(xs)}) dan y ({len(ys)}) harus sama.")
    if len(xs) < 2:
        raise ValueError("Butuh minimal 2 pasang pengamatan.")


def pearson_r(xs, ys):
    """r = sum((x-mx)(y-my)) / sqrt(sum((x-mx)^2) * sum((y-my)^2)), selalu dalam [-1, 1]."""
    _check_pairs(xs, ys)
    mx, my = mean(xs), mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        raise ValueError("Korelasi tidak terdefinisi: semua nilai x (atau semua y) sama.")
    return max(-1.0, min(1.0, sxy / math.sqrt(sxx * syy)))  # jepit kesalahan pembulatan kecil


def linear_regression(xs, ys):
    """Garis kuadrat terkecil y = slope * x + intercept."""
    _check_pairs(xs, ys)
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        raise ValueError("Garis regresi tidak terdefinisi: semua nilai x sama.")
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return slope, my - slope * mx


def interpret(r):
    """Tafsiran tiga tingkat dari spesifikasi, ditambah arah hubungannya."""
    strength = abs(r)
    if strength < WEAK:
        return "No correlation"
    direction = "positif" if r > 0 else "negatif"
    return f"Neutral ({direction})" if strength < STRONG else f"Some correlation ({direction})"


def summarize(xs, ys):
    """Semua hasil yang diminta spesifikasi dalam satu dict."""
    r = pearson_r(xs, ys)
    slope, intercept = linear_regression(xs, ys)
    return {"n": len(xs), "mean_x": mean(xs), "mean_y": mean(ys),
            "std_x": std_dev(xs), "std_y": std_dev(ys),
            "r": r, "interpretation": interpret(r), "slope": slope, "intercept": intercept}


class Observations:
    """Tabel pasangan (x, y) seperti panel input: 'Add' memvalidasi, 'Calculate' dinonaktifkan saat ada kesalahan."""

    def __init__(self):
        self.xs, self.ys = [], []
        self.error = None

    def add(self, x_text, y_text):
        """Tambahkan satu pasang. Kembalikan True kalau berhasil; kalau tidak, self.error berisi pesannya."""
        problems = []
        values = {}
        for name, text in (("x", x_text), ("y", y_text)):
            try:
                values[name] = parse_number(text)
            except ValueError as error:
                problems.append(f"{name}: {error}")
        if problems:
            self.error = "; ".join(problems)
            return False
        self.xs.append(values["x"])
        self.ys.append(values["y"])
        self.error = None
        return True

    @property
    def calculate_enabled(self):
        return self.error is None and len(self.xs) >= 2

    def calculate(self):
        if not self.calculate_enabled:
            raise ValueError(self.error or "Tambahkan minimal 2 pasang pengamatan dulu.")
        return summarize(self.xs, self.ys)


def load_csv(path):
    """Baca berkas CSV dua kolom. Baris judul non-numerik di paling atas dilewati; baris lain yang salah ditolak."""
    xs, ys = [], []
    try:
        with open(path, newline="", encoding="utf-8-sig") as file:
            for number, row in enumerate(csv.reader(file), start=1):
                if not row or not any(cell.strip() for cell in row):
                    continue
                if len(row) != 2:
                    raise ValueError(f"Baris {number}: harus tepat 2 kolom (x,y), ada {len(row)}.")
                try:
                    x, y = parse_number(row[0]), parse_number(row[1])
                except ValueError as error:
                    if number == 1:
                        continue  # anggap sebagai baris judul
                    raise ValueError(f"Baris {number}: {error}.") from None
                xs.append(x)
                ys.append(y)
    except FileNotFoundError:
        raise ValueError(f"Berkas '{path}' tidak ditemukan.") from None
    except OSError as error:
        raise ValueError(f"Berkas '{path}' tidak bisa dibaca: {error.strerror}.") from None
    if not xs:
        raise ValueError("Berkas tidak berisi data.")
    return xs, ys


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("Pemakaian: python pearson.py data.csv")
        return 2
    try:
        result = summarize(*load_csv(argv[0]))
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    print(f"Jumlah pasangan : {result['n']}")
    print(f"Rata-rata x, y  : {result['mean_x']:.4f}, {result['mean_y']:.4f}")
    print(f"Simpangan baku  : {result['std_x']:.4f}, {result['std_y']:.4f}  (sampel, n-1)")
    print(f"Korelasi Pearson: {result['r']:.4f}  ->  {result['interpretation']}")
    sign = "+" if result["intercept"] >= 0 else "-"
    print(f"Garis regresi   : y = {result['slope']:.4f} x {sign} {abs(result['intercept']):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
