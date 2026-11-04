"""Currency Converter: konversi mata uang dengan kurs referensi ECB (lewat Frankfurter API).

Kurs diambil sekali (berbasis EUR) lalu kurs silang dihitung sendiri dengan
Decimal. Kurs terakhir disimpan ke berkas, jadi program tetap bisa dipakai
saat offline (dengan tanggal kurs yang lama).

Jalankan:
    python currency.py                  # jendela Tkinter
    python currency.py 100 USD IDR      # sekali hitung di terminal
    python currency.py --list           # daftar mata uang
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from decimal import ROUND_HALF_UP, Decimal

API = "https://api.frankfurter.dev/v1"
USER_AGENT = "app-ideas-python-currency/1.0"
CACHE = os.path.join(os.path.expanduser("~"), ".app-ideas-python", "rates.json")
MAX_DIGITS = 9
CENT = Decimal("0.01")
AMOUNT_RE = re.compile(r"^([0-9]+)(?:[.,]([0-9]*))?$")  # [0-9], bukan \d: \d juga cocok dengan angka Arab dll.


class RatesError(Exception):
    """Kurs tidak bisa diambil dari internet maupun cache."""


def parse_amount(text):
    """Teks -> Decimal. Maksimal 9 digit, pemisah desimal titik atau koma, maksimal 2 desimal."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Masukkan jumlah uang.")
    match = AMOUNT_RE.match(cleaned)
    if not match:
        raise ValueError(f"'{cleaned}' bukan angka. Pakai angka saja, misalnya 1500 atau 12,50.")
    whole, fraction = match.group(1), match.group(2) or ""
    if len(fraction) > 2:
        raise ValueError("Maksimal 2 angka di belakang koma (pemisah ribuan tidak dipakai).")
    if len(whole.lstrip("0")) + len(fraction) > MAX_DIGITS:
        raise ValueError(f"Maksimal {MAX_DIGITS} digit.")
    return Decimal(f"{whole}.{fraction or '0'}")


def convert(amount, source, target, rates):
    """Konversi lewat EUR: amount / kurs[sumber] * kurs[tujuan], dibulatkan ke 2 desimal."""
    for code in (source, target):
        if code not in rates:
            raise ValueError(f"Mata uang {code} tidak dikenal.")
    value = amount / rates[source] * rates[target]
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def format_money(value):
    """Format Indonesia: 1234567.5 -> '1.234.567,50'."""
    text = f"{value.quantize(CENT, rounding=ROUND_HALF_UP):,.2f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


# --- data kurs ---------------------------------------------------------------

def _get_json(url, urlopen):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_rates(data):
    """JSON Frankfurter -> (tanggal, {kode: Decimal}). EUR sendiri ditambahkan dengan kurs 1."""
    try:
        base = data["base"]
        rates = {code: Decimal(str(value)) for code, value in data["rates"].items()}
        date = data["date"]
    except (KeyError, TypeError, AttributeError, ArithmeticError):
        raise RatesError("Format data kurs tidak dikenali.") from None
    if base != "EUR" or not rates or any(v <= 0 for v in rates.values()):
        raise RatesError("Format data kurs tidak dikenali.")
    rates["EUR"] = Decimal(1)
    return date, rates


def load_rates(urlopen=urllib.request.urlopen, cache_path=CACHE):
    """Ambil kurs terbaru + nama mata uang. Kalau gagal, pakai cache. Hasil: dict berisi date, rates, names, offline."""
    try:
        date, rates = parse_rates(_get_json(f"{API}/latest", urlopen))
        names = _get_json(f"{API}/currencies", urlopen)
        if not isinstance(names, dict):
            names = {}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, RatesError) as error:
        cached = read_cache(cache_path)
        if cached is None:
            raise RatesError(f"Tidak bisa mengambil kurs ({describe_error(error)}) dan belum ada cache.") from None
        cached["offline"] = True
        return cached
    write_cache(cache_path, date, rates, names)
    return {"date": date, "rates": rates, "names": names, "offline": False}


def describe_error(error):
    if isinstance(error, urllib.error.HTTPError):
        return f"server menjawab kode {error.code}"
    if isinstance(error, (urllib.error.URLError, TimeoutError)):
        return "tidak ada koneksi internet"
    return "data tidak valid"


def write_cache(path, date, rates, names):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        temp = path + ".tmp"
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump({"date": date, "rates": {k: str(v) for k, v in rates.items()}, "names": names}, handle)
        os.replace(temp, path)
    except OSError:
        pass  # cache hanya pelengkap


def read_cache(path):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        rates = {code: Decimal(value) for code, value in data["rates"].items()}
        if not rates or any(v <= 0 for v in rates.values()):
            return None
        return {"date": data["date"], "rates": rates, "names": dict(data.get("names") or {})}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ArithmeticError):
        return None


def currency_choices(rates, names):
    """Daftar terurut 'IDR - Indonesian Rupiah'."""
    return [f"{code} - {names.get(code, code)}" for code in sorted(rates)]


def code_of(choice):
    return choice.split(" ", 1)[0].strip().upper()


# --- tampilan Tkinter ------------------------------------------------------------

class ConverterApp:
    def __init__(self, root, data):
        import tkinter as tk
        from tkinter import ttk

        self.root = root
        self.rates = data["rates"]
        choices = currency_choices(self.rates, data["names"])
        root.title("Currency Converter")
        root.resizable(False, False)
        frame = ttk.Frame(root, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Jumlah").grid(row=0, column=0, sticky="w")
        self.amount = tk.StringVar(value="100")
        self.amount_entry = ttk.Entry(frame, textvariable=self.amount, width=18, font=("Segoe UI", 12))
        self.amount_entry.grid(row=1, column=0, sticky="we", pady=(2, 0))
        self.error = tk.StringVar()
        ttk.Label(frame, textvariable=self.error, foreground="#b3261e").grid(row=2, column=0, columnspan=3,
                                                                              sticky="w", pady=(2, 8))

        ttk.Label(frame, text="Dari").grid(row=3, column=0, sticky="w")
        ttk.Label(frame, text="Ke").grid(row=3, column=2, sticky="w")
        self.source = ttk.Combobox(frame, values=choices, state="readonly", width=30)
        self.target = ttk.Combobox(frame, values=choices, state="readonly", width=30)
        self.source.grid(row=4, column=0, sticky="we")
        self.target.grid(row=4, column=2, sticky="we")
        self.source.set(self._choice("USD", choices))
        self.target.set(self._choice("IDR", choices))
        ttk.Button(frame, text="⇄", width=3, command=self.swap).grid(row=4, column=1, padx=8)

        ttk.Label(frame, text="Hasil").grid(row=5, column=0, sticky="w", pady=(14, 0))
        self.result = tk.StringVar()
        result_entry = ttk.Entry(frame, textvariable=self.result, state="readonly", font=("Segoe UI", 14, "bold"))
        result_entry.grid(row=6, column=0, columnspan=3, sticky="we", pady=(2, 0))
        note = f"Kurs referensi ECB tanggal {data['date']}"
        if data.get("offline"):
            note += " (offline: memakai kurs tersimpan)"
        ttk.Label(frame, text=note, foreground="#666").grid(row=7, column=0, columnspan=3, sticky="w", pady=(10, 0))

        self.amount.trace_add("write", lambda *_: self.update())
        for box in (self.source, self.target):
            box.bind("<<ComboboxSelected>>", lambda _e: self.update())
        self.update()
        self.amount_entry.focus_set()

    @staticmethod
    def _choice(code, choices):
        return next((c for c in choices if code_of(c) == code), choices[0])

    def swap(self):
        source, target = self.source.get(), self.target.get()
        self.source.set(target)
        self.target.set(source)
        self.update()

    def update(self):
        if not self.amount.get().strip():
            self.error.set("")  # kotak kosong saat mengetik ulang bukan kesalahan
            self.result.set("")
            return
        try:
            amount = parse_amount(self.amount.get())
        except ValueError as error:
            if self.error.get() != str(error):
                self.root.bell()
            self.error.set(str(error))
            self.result.set("")
            return
        self.error.set("")
        source, target = code_of(self.source.get()), code_of(self.target.get())
        value = convert(amount, source, target, self.rates)
        self.result.set(f"{format_money(value)} {target}")


# --- baris perintah ----------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(description="Konversi mata uang dengan kurs ECB.")
    parser.add_argument("amount", nargs="?", help="jumlah, misalnya 100 atau 12,50")
    parser.add_argument("source", nargs="?", help="kode mata uang asal, misalnya USD")
    parser.add_argument("target", nargs="?", help="kode mata uang tujuan, misalnya IDR")
    parser.add_argument("--list", action="store_true", help="tampilkan daftar mata uang")
    return parser


def main(argv=None, urlopen=urllib.request.urlopen, cache_path=CACHE, gui=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    if args.amount and not (args.source and args.target):
        print("Error: tulis jumlah, mata uang asal, dan mata uang tujuan. Contoh: 100 USD IDR", file=sys.stderr)
        return 2
    try:
        data = load_rates(urlopen, cache_path)
    except RatesError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    note = f"kurs ECB {data['date']}" + (", offline" if data["offline"] else "")
    if args.list:
        for choice in currency_choices(data["rates"], data["names"]):
            print(choice)
        return 0
    if args.amount:
        try:
            amount = parse_amount(args.amount)
            source, target = args.source.upper(), args.target.upper()
            value = convert(amount, source, target, data["rates"])
        except ValueError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        print(f"{format_money(amount)} {source} = {format_money(value)} {target} ({note})")
        return 0
    (gui or run_gui)(data)
    return 0


def run_gui(data):
    import tkinter as tk

    root = tk.Tk()
    ConverterApp(root, data)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())
