"""Weather App: suhu, kondisi cuaca, siang atau malam, dan ikon untuk sebuah kota.

Memakai Open-Meteo (https://open-meteo.com): geokoding untuk mencari kota, lalu cuaca saat ini.
Gratis dan tanpa kunci API. Hanya pustaka bawaan Python.

Jalankan:
    python weather.py Semarang          # cuaca kota itu (kota disimpan untuk berikutnya)
    python weather.py                   # memakai kota terakhir, atau menanyakannya
    python weather.py Jakarta --list    # tampilkan beberapa kota yang namanya cocok
    python weather.py Bandung --pick 2  # pilih hasil kedua
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_STATE = os.path.join(os.path.expanduser("~"), ".app-ideas-python", "weather-city.json")

# Kode cuaca WMO -> (deskripsi, ikon siang, ikon malam)
CONDITIONS = {
    0: ("Cerah", "☀️", "🌙"),
    1: ("Hampir cerah", "🌤️", "🌙"),
    2: ("Berawan sebagian", "⛅", "☁️"),
    3: ("Mendung", "☁️", "☁️"),
    45: ("Berkabut", "🌫️", "🌫️"),
    48: ("Kabut beku", "🌫️", "🌫️"),
    51: ("Gerimis ringan", "🌦️", "🌧️"),
    53: ("Gerimis sedang", "🌦️", "🌧️"),
    55: ("Gerimis lebat", "🌧️", "🌧️"),
    56: ("Gerimis beku ringan", "🌧️", "🌧️"),
    57: ("Gerimis beku lebat", "🌧️", "🌧️"),
    61: ("Hujan ringan", "🌦️", "🌧️"),
    63: ("Hujan sedang", "🌧️", "🌧️"),
    65: ("Hujan lebat", "🌧️", "🌧️"),
    66: ("Hujan beku ringan", "🌧️", "🌧️"),
    67: ("Hujan beku lebat", "🌧️", "🌧️"),
    71: ("Salju ringan", "🌨️", "🌨️"),
    73: ("Salju sedang", "🌨️", "🌨️"),
    75: ("Salju lebat", "❄️", "❄️"),
    77: ("Butiran salju", "🌨️", "🌨️"),
    80: ("Hujan lokal ringan", "🌦️", "🌧️"),
    81: ("Hujan lokal sedang", "🌧️", "🌧️"),
    82: ("Hujan lokal deras", "⛈️", "⛈️"),
    85: ("Hujan salju lokal ringan", "🌨️", "🌨️"),
    86: ("Hujan salju lokal lebat", "❄️", "❄️"),
    95: ("Badai petir", "⛈️", "⛈️"),
    96: ("Badai petir dengan es ringan", "⛈️", "⛈️"),
    99: ("Badai petir dengan es lebat", "⛈️", "⛈️"),
}


def fetch_json(url, params, urlopen=urllib.request.urlopen):
    full = f"{url}?{urllib.parse.urlencode(params)}"
    try:
        with urlopen(full, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise ValueError(f"Layanan cuaca menjawab kode {error.code}.") from None
    except (urllib.error.URLError, TimeoutError):
        raise ValueError("Tidak bisa menjangkau layanan cuaca. Periksa koneksi internet.") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("Jawaban layanan cuaca bukan JSON yang valid.") from None


def clean_city(text):
    city = " ".join(str(text).split())
    if not city:
        raise ValueError("Nama kota belum diisi.")
    if len(city) > 100 or any(ord(c) < 32 for c in city):
        raise ValueError("Nama kota tidak valid.")
    return city


def find_places(city, count=5, urlopen=urllib.request.urlopen):
    """Daftar tempat yang namanya cocok (dict dengan name, admin1, country, latitude, longitude)."""
    data = fetch_json(GEOCODE_URL, {"name": clean_city(city), "count": count, "language": "id", "format": "json"}, urlopen)
    places = data.get("results") if isinstance(data, dict) else None
    if not places:
        raise ValueError(f"Kota '{clean_city(city)}' tidak ditemukan. Periksa ejaannya.")
    return places


def place_label(place):
    parts = [place.get("name"), place.get("admin1"), place.get("country")]
    seen = []
    for part in parts:
        if part and part not in seen:
            seen.append(part)
    return ", ".join(seen)


def current_weather(place, urlopen=urllib.request.urlopen):
    data = fetch_json(FORECAST_URL, {
        "latitude": place["latitude"], "longitude": place["longitude"], "timezone": "auto",
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,is_day",
    }, urlopen)
    try:
        current = data["current"]
        code = int(current["weather_code"])
        return {
            "place": place_label(place),
            "temperature": float(current["temperature_2m"]),
            "feels_like": float(current["apparent_temperature"]),
            "humidity": int(current["relative_humidity_2m"]),
            "wind": float(current["wind_speed_10m"]),
            "is_day": bool(current["is_day"]),
            "code": code,
            "time": str(current.get("time", "")).replace("T", " "),
        }
    except (KeyError, TypeError, ValueError):
        raise ValueError("Data cuaca dari layanan tidak lengkap atau formatnya berubah.") from None


def describe_condition(code, is_day):
    """(deskripsi, ikon) untuk kode cuaca WMO, berbeda untuk siang dan malam."""
    if code not in CONDITIONS:
        return f"Kondisi tidak dikenal (kode {code})", "❔"
    text, day_icon, night_icon = CONDITIONS[code]
    return text, day_icon if is_day else night_icon


def format_weather(weather):
    text, icon = describe_condition(weather["code"], weather["is_day"])
    moment = "Siang ☀️" if weather["is_day"] else "Malam 🌙"
    return "\n".join([
        f"{weather['place']}",
        f"{icon}  {text}  ·  {moment}",
        f"Suhu        : {weather['temperature']:.1f} °C (terasa {weather['feels_like']:.1f} °C)",
        f"Kelembapan  : {weather['humidity']}%",
        f"Angin       : {weather['wind']:.1f} km/jam",
        f"Waktu data  : {weather['time']} (waktu setempat)",
    ])


class CityMemory:
    """Menyimpan kota terakhir antar sesi (pengganti localStorage di browser)."""

    def __init__(self, path=DEFAULT_STATE):
        self.path = path

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as file:
                city = json.load(file).get("city")
            return city if isinstance(city, str) and city.strip() else None
        except (OSError, json.JSONDecodeError, AttributeError):
            return None  # berkas hilang atau rusak: anggap belum ada kota tersimpan

    def save(self, city):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump({"city": city}, file, ensure_ascii=False)


def run(city, pick=1, list_only=False, memory=None, urlopen=urllib.request.urlopen, out=print):
    """Cari kota, tampilkan cuacanya, lalu ingat kotanya. Mengembalikan teks yang ditampilkan."""
    places = find_places(city, urlopen=urlopen)
    if list_only:
        text = "\n".join(f"  {i}. {place_label(p)}" for i, p in enumerate(places, start=1))
        out(text)
        return text
    if not 1 <= pick <= len(places):
        raise ValueError(f"--pick harus 1 sampai {len(places)} untuk '{city}'.")
    text = format_weather(current_weather(places[pick - 1], urlopen))
    if len(places) > 1 and pick == 1:
        text += f"\n(Ada {len(places)} kota bernama mirip; jalankan dengan --list lalu --pick N untuk memilih lain.)"
    out(text)
    if memory:
        memory.save(clean_city(city))
    return text


def main(argv=None, urlopen=urllib.request.urlopen):
    parser = argparse.ArgumentParser(description="Cuaca saat ini untuk sebuah kota.")
    parser.add_argument("city", nargs="*", help="nama kota; kosong = kota terakhir")
    parser.add_argument("--list", action="store_true", help="tampilkan kota yang cocok, tanpa cuaca")
    parser.add_argument("--pick", type=int, default=1, help="pilih hasil ke-N (bawaan 1)")
    parser.add_argument("--state-file", default=DEFAULT_STATE, help="berkas penyimpan kota terakhir")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    memory = CityMemory(args.state_file)
    try:
        city = " ".join(args.city) or memory.load()
        if not city:
            city = input("Nama kota: ")
        elif not args.city:
            print(f"(memakai kota terakhir: {city})")
        run(city, args.pick, args.list, memory, urlopen)
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    except EOFError:
        print("Error: Nama kota belum diisi.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
