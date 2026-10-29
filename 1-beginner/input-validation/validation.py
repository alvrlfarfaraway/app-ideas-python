"""Input Validation: validasi isian formulir dengan ekspresi reguler (regex).

Tiga isian:
- password : tepat 5 huruf kapital, 6 simbol, dan 2 tanda hubung (-), urutan bebas (13 karakter)
- username : hanya huruf, tanpa spasi
- email    : alamat Gmail (...@gmail.com)

Formulir baru "terkirim" kalau SEMUA isian valid.

Jalankan:
    python validation.py        # isi formulir; isian yang salah diminta ulang
"""

import re

SYMBOLS = r"""!@#$%^&*()_+=\[\]{};:'",.<>/?\\|`~"""

# Tiga lookahead menghitung tiap jenis karakter; sisanya membatasi isi hanya ke tiga jenis itu.
PASSWORD = re.compile(
    rf"""^
    (?=(?:[^A-Z]*[A-Z]){{5}}[^A-Z]*$)          # tepat 5 huruf kapital
    (?=(?:[^{SYMBOLS}]*[{SYMBOLS}]){{6}}[^{SYMBOLS}]*$)  # tepat 6 simbol
    (?=(?:[^-]*-){{2}}[^-]*$)                  # tepat 2 tanda hubung
    [A-Z{SYMBOLS}-]{{13}}$                     # hanya ketiganya, total 13 karakter
    """,
    re.VERBOSE,
)
USERNAME = re.compile(r"[^\W\d_]+")  # huruf (termasuk beraksen) saja: bukan angka, garis bawah, atau spasi
EMAIL = re.compile(r"(?!\.)(?!.*\.\.)[A-Za-z0-9._%+-]+(?<!\.)@gmail\.com", re.IGNORECASE)

FIELDS = ("password", "username", "email")
LABELS = {"password": "Password", "username": "Username", "email": "Email"}


def describe_password(text):
    """Hitung isi password supaya pesan kesalahan menunjukkan apa yang kurang atau berlebih."""
    capitals = sum(1 for c in text if "A" <= c <= "Z")
    hyphens = text.count("-")
    symbols = sum(1 for c in text if re.fullmatch(f"[{SYMBOLS}]", c))
    others = len(text) - capitals - hyphens - symbols
    return capitals, symbols, hyphens, others


def validate_password(text):
    """Kembalikan None kalau valid, atau pesan kesalahan."""
    if PASSWORD.fullmatch(text):
        return None
    capitals, symbols, hyphens, others = describe_password(text)
    problems = []
    for name, have, need in (("huruf kapital", capitals, 5), ("simbol", symbols, 6), ("tanda hubung (-)", hyphens, 2)):
        if have != need:
            problems.append(f"{have} {name} (harus {need})")
    if others:
        problems.append(f"{others} karakter lain yang tidak boleh ada (huruf kecil, angka, atau spasi)")
    return "Password harus berisi tepat 5 huruf kapital, 6 simbol, dan 2 tanda hubung. Sekarang: " + "; ".join(problems) + "."


def validate_username(text):
    if USERNAME.fullmatch(text):
        return None
    if not text:
        return "Username tidak boleh kosong."
    if re.search(r"\s", text):
        return "Username tidak boleh mengandung spasi."
    return "Username hanya boleh berisi huruf."


def validate_email(text):
    if EMAIL.fullmatch(text):
        return None
    if not text:
        return "Email tidak boleh kosong."
    if not text.lower().endswith("@gmail.com"):
        return "Email harus alamat Gmail, berakhiran @gmail.com."
    return "Bagian sebelum @gmail.com tidak valid (hanya huruf, angka, . _ % + -; tidak boleh diawali/diakhiri titik atau berisi dua titik berturut-turut)."


VALIDATORS = {"password": validate_password, "username": validate_username, "email": validate_email}


def validate_form(values):
    """Kembalikan {isian: pesan kesalahan} untuk isian yang tidak valid (kosong = formulir valid)."""
    errors = {}
    for field in FIELDS:
        message = VALIDATORS[field](values.get(field, ""))
        if message:
            errors[field] = message
    return errors


def submit(values):
    """'Tombol submit': hanya berjalan kalau semua isian valid; kalau tidak, ValueError membawa semua kesalahan."""
    errors = validate_form(values)
    if errors:
        error = ValueError("; ".join(errors.values()))
        error.errors = errors
        raise error
    return {field: values[field] for field in FIELDS}


def main():
    print("Isi formulir. Isian yang salah akan diminta ulang; formulir terkirim kalau semuanya valid.")
    values = {}
    pending = list(FIELDS)
    while True:
        for field in pending:
            values[field] = input(f"{LABELS[field]}: ")
        try:
            result = submit(values)
        except ValueError as error:
            for field, message in error.errors.items():
                print(f"  [!] {message}")
            pending = list(error.errors)
            continue
        print("Formulir terkirim:", {k: ("*" * len(v) if k == "password" else v) for k, v in result.items()})
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EOFError, KeyboardInterrupt):
        print()
