"""Hello: panel login tiruan yang menyapa dalam bahasa asli negara pengguna.

Alur: IP-API (lokasi dari IP) -> HelloSalut/Fourtonfish (salam dalam bahasa negara itu,
dikirim dengan IP tadi) -> dekode entitas HTML (misalnya &uuml; menjadi ü).
Hanya memakai pustaka bawaan Python.

Jalankan:
    python hello.py              # panel interaktif: login, logout, quit
    python hello.py --lang id    # paksa kode bahasa (bonus, berguna untuk uji)
"""

import argparse
import getpass
import html
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

GEO_URL = "http://ip-api.com/json/?fields=status,message,country,city,regionName,zip,lat,lon,timezone,query"
HELLO_URL = "https://fourtonfish.com/hellosalut/"
FIELD_NAMES = {"username": "User Name", "password": "Password"}
RED, RESET = "\x1b[31;1m", "\x1b[0m"


class FieldError(ValueError):
    """Kolom wajib yang kosong; `fields` berisi kunci kolom itu (untuk diberi warna merah)."""

    def __init__(self, fields):
        self.fields = fields
        names = " dan ".join(FIELD_NAMES[f] for f in fields)
        super().__init__(f"{names} tidak boleh kosong.")


def fetch_json(url, urlopen=urllib.request.urlopen):
    try:
        with urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise ValueError(f"Layanan menjawab kode {error.code}.") from None
    except (urllib.error.URLError, TimeoutError):
        raise ValueError("Tidak bisa menjangkau layanan. Periksa koneksi internet.") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("Jawaban layanan bukan JSON yang valid.") from None


def locate(urlopen=urllib.request.urlopen):
    """Lokasi pengguna dari IP-nya (dict dengan query/city/regionName/country/zip/lat/lon/timezone)."""
    data = fetch_json(GEO_URL, urlopen)
    if data.get("status") != "success":
        raise ValueError(f"Geolokasi gagal: {data.get('message', 'alasan tidak diketahui')}.")
    return data


def get_greeting(ip=None, lang=None, urlopen=urllib.request.urlopen):
    """Salam dalam bahasa asli. `lang` (bonus) menggantikan IP; hasilnya didekode dari entitas HTML."""
    if lang:
        url = f"{HELLO_URL}?lang={urllib.parse.quote(lang)}"
    elif ip:
        url = f"{HELLO_URL}?ip={urllib.parse.quote(ip)}"
    else:
        url = HELLO_URL
    data = fetch_json(url, urlopen)
    if not isinstance(data, dict) or not data.get("hello"):
        raise ValueError("Salam tidak ditemukan dalam jawaban layanan.")
    return html.unescape(data["hello"])


class Session:
    """Status login tiruan. Dipisahkan dari input/output supaya mudah diuji."""

    def __init__(self, urlopen=urllib.request.urlopen):
        self.urlopen = urlopen
        self.user = None
        self.geo = None

    def login(self, username, password, lang=None):
        """Kembalikan (pesan sukses, daftar peringatan). FieldError kalau ada kolom kosong."""
        empty = [key for key, value in (("username", username), ("password", password)) if not value.strip()]
        if empty:
            raise FieldError(empty)
        warnings = []
        self.geo = None
        try:
            self.geo = locate(self.urlopen)
        except ValueError as error:
            if not lang:
                warnings.append(str(error))
        try:
            hello = get_greeting(self.geo["query"] if self.geo else None, lang, self.urlopen)
        except ValueError as error:
            warnings.append(f"Salam bahasa asli tidak tersedia ({error}) Memakai 'Hello'.")
            hello = "Hello"
        self.user = username.strip()
        return f"{hello} {self.user} you have successfully logged in!", warnings

    def logout(self):
        if self.user is None:
            raise ValueError("Belum login.")
        message = f"Have a great day {self.user}!"
        self.user = None
        self.geo = None
        return message


def format_geo(geo):
    rows = [("IP", geo["query"]), ("Kota", geo["city"]), ("Wilayah", geo["regionName"]),
            ("Negara", geo["country"]), ("Kode pos", geo["zip"] or "-"),
            ("Bujur (lon)", geo["lon"]), ("Lintang (lat)", geo["lat"]), ("Zona waktu", geo["timezone"])]
    return "\n".join(f"  {label:<14}{value}" for label, value in rows)


def read_masked(prompt):
    """Baca password dan tampilkan * untuk tiap karakter (Windows); di OS lain memakai getpass."""
    try:
        import msvcrt
    except ImportError:
        return getpass.getpass(prompt)
    if not sys.stdin.isatty():
        return input(prompt)
    print(prompt, end="", flush=True)
    chars = []
    while True:
        char = msvcrt.getwch()
        if char in "\r\n":
            print()
            return "".join(chars)
        if char == "\x03":
            raise KeyboardInterrupt
        if char == "\x08":
            if chars:
                chars.pop()
                print("\b \b", end="", flush=True)
        elif char not in "\x00\xe0":
            chars.append(char)
            print("*", end="", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Hello: salam sesuai bahasa negara pengguna.")
    parser.add_argument("--lang", help="kode bahasa untuk menggantikan hasil geolokasi, misalnya id, de, fr")
    args = parser.parse_args(argv)
    session = Session()
    print("Panel login tiruan. Perintah: login, logout, quit")
    while True:
        try:
            command = input("> ").strip().lower()
            if command in ("quit", "q", "exit"):
                return 0
            if command == "login":
                username = input("User Name: ")
                password = read_masked("Password : ")
                try:
                    message, warnings = session.login(username, password, args.lang)
                except FieldError as error:
                    for field in error.fields:
                        print(f"{RED}[!] {FIELD_NAMES[field]} kosong{RESET}")
                    print(error)
                    continue
                for warning in warnings:
                    print(f"Peringatan: {warning}")
                print(message)
                if session.geo:
                    print(format_geo(session.geo))
            elif command == "logout":
                print(session.logout())
            else:
                print("Perintah tidak dikenal.")
        except ValueError as error:
            print(f"Error: {error}")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
