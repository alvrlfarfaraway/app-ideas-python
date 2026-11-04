"""Password Generator: buat password acak yang aman, lengkap dengan ukuran kekuatannya.

Acak memakai modul secrets (sumber acak kriptografis sistem operasi), bukan
random. Setiap jenis karakter yang dipilih dijamin muncul minimal sekali.

Kekuatan dihitung sebagai entropi dalam bit: log2 dari banyaknya password yang
mungkin dihasilkan dengan pengaturan itu. Banyaknya dihitung tepat dengan
prinsip inklusi-eksklusi, karena syarat "minimal satu dari tiap jenis"
mengurangi kemungkinan dibanding N^panjang.

Jalankan:
    python password.py                       # jendela Tkinter
    python password.py -l 20                 # terminal: 20 karakter, semua jenis
    python password.py -l 12 --no-symbols -n 5
    python password.py -l 16 --no-ambiguous  # tanpa karakter mirip (O/0, l/1/I)
"""

import argparse
import math
import secrets
import string
import sys
from itertools import combinations

CLASSES = {
    "upper": ("Huruf besar (A-Z)", string.ascii_uppercase),
    "lower": ("Huruf kecil (a-z)", string.ascii_lowercase),
    "digits": ("Angka (0-9)", string.digits),
    "symbols": ("Simbol (!@#...)", "!#$%&*+-=?@^_~.,:;()[]{}"),
}
AMBIGUOUS = set("O0oIl1|S5B8")
MIN_LENGTH, MAX_LENGTH = 4, 128
LEVELS = ((128, "Sangat kuat"), (80, "Kuat"), (60, "Sedang"), (0, "Lemah"))


def pools(selected, no_ambiguous=False):
    """Daftar himpunan karakter untuk jenis yang dipilih."""
    if not selected:
        raise ValueError("Pilih minimal satu jenis karakter.")
    result = []
    for key in selected:
        chars = CLASSES[key][1]
        if no_ambiguous:
            chars = "".join(c for c in chars if c not in AMBIGUOUS)
        result.append(chars)
    return result


def generate(length, selected=tuple(CLASSES), no_ambiguous=False, rng=None):
    """Password sepanjang `length` dengan minimal satu karakter dari setiap jenis yang dipilih."""
    rng = rng or secrets.SystemRandom()
    groups = pools(selected, no_ambiguous)
    if not MIN_LENGTH <= length <= MAX_LENGTH:
        raise ValueError(f"Panjang password harus {MIN_LENGTH}-{MAX_LENGTH} karakter.")
    if length < len(groups):
        raise ValueError(f"Panjang minimal {len(groups)} supaya setiap jenis karakter muncul.")
    everything = "".join(groups)
    chars = [rng.choice(group) for group in groups]  # satu dari tiap jenis
    chars += [rng.choice(everything) for _ in range(length - len(groups))]
    rng.shuffle(chars)  # supaya karakter wajib tidak selalu di depan
    return "".join(chars)


def possible_count(length, group_sizes):
    """Banyaknya string sepanjang `length` yang memuat minimal satu karakter dari tiap kelompok.

    Inklusi-eksklusi: jumlahkan (-1)^|S| * (N - ukuran kelompok di S)^length untuk
    setiap himpunan bagian S dari kelompok.
    """
    total = sum(group_sizes)
    count = 0
    for k in range(len(group_sizes) + 1):
        for subset in combinations(group_sizes, k):
            count += (-1) ** k * (total - sum(subset)) ** length
    return count


def entropy_bits(length, selected=tuple(CLASSES), no_ambiguous=False):
    sizes = [len(group) for group in pools(selected, no_ambiguous)]
    return math.log2(possible_count(length, sizes))


def strength(bits):
    """Label kekuatan untuk entropi `bits`."""
    return next(label for limit, label in LEVELS if bits >= limit)


def crack_time(bits, guesses_per_second=1e12):
    """Perkiraan waktu rata-rata untuk menebak (separuh kemungkinan) dengan 10^12 tebakan per detik."""
    seconds = 2 ** (bits - 1) / guesses_per_second
    for unit, size in (("miliar tahun", 3.15576e16), ("juta tahun", 3.15576e13), ("tahun", 3.15576e7),
                       ("hari", 86400), ("jam", 3600), ("menit", 60)):
        if seconds >= size:
            value = seconds / size
            return f"sekitar {value:,.0f} {unit}".replace(",", ".") if value < 1e6 else f"lebih dari sejuta {unit}"
    return "kurang dari semenit"


def describe(length, selected, no_ambiguous=False):
    bits = entropy_bits(length, selected, no_ambiguous)
    return f"{strength(bits)} ({bits:.0f} bit, rata-rata ditebak dalam {crack_time(bits)})"


# --- tampilan Tkinter -------------------------------------------------------------

LEVEL_COLORS = {"Lemah": "#c0392b", "Sedang": "#d9900f", "Kuat": "#2a9d55", "Sangat kuat": "#1f7a44"}


class PasswordApp:
    def __init__(self, root, rng=None):
        import tkinter as tk
        from tkinter import ttk

        self.root = root
        self.rng = rng
        root.title("Password Generator")
        root.resizable(False, False)
        frame = ttk.Frame(root, padding=16)
        frame.pack(fill="both")
        self.password = tk.StringVar()
        ttk.Entry(frame, textvariable=self.password, font=("Consolas", 14), width=34, state="readonly").grid(
            row=0, column=0, columnspan=2, sticky="we")
        ttk.Button(frame, text="Copy to clipboard", command=self.copy).grid(row=0, column=2, padx=(8, 0))

        self.meter = tk.Canvas(frame, height=8, width=420, highlightthickness=0, background="#e6e6e6")
        self.meter.grid(row=1, column=0, columnspan=3, sticky="we", pady=(10, 2))
        self.strength = tk.StringVar()
        self.strength_label = ttk.Label(frame, textvariable=self.strength)
        self.strength_label.grid(row=2, column=0, columnspan=3, sticky="w")

        ttk.Label(frame, text="Panjang").grid(row=3, column=0, sticky="w", pady=(14, 0))
        self.length = tk.IntVar(value=16)
        ttk.Spinbox(frame, from_=MIN_LENGTH, to=MAX_LENGTH, textvariable=self.length, width=6,
                    command=self.generate).grid(row=3, column=1, sticky="w", pady=(14, 0))
        self.flags = {}
        for row, (key, (label, _)) in enumerate(CLASSES.items(), start=4):
            var = tk.BooleanVar(value=True)
            ttk.Checkbutton(frame, text=label, variable=var, command=self.generate).grid(
                row=row, column=0, columnspan=2, sticky="w")
            self.flags[key] = var
        self.no_ambiguous = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Tanpa karakter mirip (O/0, l/1/I)", variable=self.no_ambiguous,
                        command=self.generate).grid(row=8, column=0, columnspan=3, sticky="w")
        ttk.Button(frame, text="Generate password", command=self.generate).grid(
            row=9, column=0, columnspan=3, sticky="we", pady=(14, 0))
        self.status = tk.StringVar()
        ttk.Label(frame, textvariable=self.status, foreground="#555").grid(row=10, column=0, columnspan=3,
                                                                        sticky="w", pady=(8, 0))
        root.bind("<Return>", lambda _e: self.generate())
        self.generate()

    @property
    def selected(self):
        return [key for key, var in self.flags.items() if var.get()]

    def generate(self):
        try:
            length = int(self.length.get())
            value = generate(length, self.selected, self.no_ambiguous.get(), self.rng)
        except (ValueError, Exception) as error:  # TclError kalau kotak panjang berisi teks
            self.password.set("")
            self.strength.set(str(error) if isinstance(error, ValueError) else "Panjang harus angka.")
            self.draw_meter(0, "#c0392b")
            return None
        bits = entropy_bits(length, self.selected, self.no_ambiguous.get())
        label = strength(bits)
        self.password.set(value)
        self.strength.set(describe(length, self.selected, self.no_ambiguous.get()))
        self.draw_meter(min(1.0, bits / 128), LEVEL_COLORS[label])
        self.status.set("")
        return value

    def draw_meter(self, fraction, color):
        self.meter.delete("all")
        self.meter.update_idletasks()
        width = self.meter.winfo_width() or 420
        self.meter.create_rectangle(0, 0, width * fraction, 8, fill=color, outline="")
        self.strength_label.configure(foreground=color)

    def copy(self):
        if not self.password.get():
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.password.get())
        self.status.set("Password disalin ke clipboard.")


def main(argv=None, gui=None):
    parser = argparse.ArgumentParser(description="Buat password acak yang aman.")
    parser.add_argument("-l", "--length", type=int, help="panjang password (tanpa ini: buka jendela)")
    parser.add_argument("-n", "--count", type=int, default=1, help="jumlah password")
    for key, (label, _) in CLASSES.items():
        parser.add_argument(f"--no-{key}", action="store_true", help=f"tanpa {label.lower()}")
    parser.add_argument("--no-ambiguous", action="store_true", help="tanpa karakter yang mirip (O/0, l/1/I)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.length is None:
        (gui or run_gui)()
        return 0
    selected = [key for key in CLASSES if not getattr(args, f"no_{key}")]
    try:
        for _ in range(max(1, args.count)):
            print(generate(args.length, selected, args.no_ambiguous))
        print(f"Kekuatan: {describe(args.length, selected, args.no_ambiguous)}", file=sys.stderr)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


def run_gui():
    import tkinter as tk

    root = tk.Tk()
    PasswordApp(root)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())
