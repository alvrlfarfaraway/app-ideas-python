"""Wind Chill: suhu yang terasa dari suhu udara dan kecepatan angin.

Rumus resmi US National Weather Service / Meteorological Service of Canada (2001):
    Metrik   (T dalam °C, v dalam km/jam): WC = 13.12 + 0.6215 T - 11.37 v^0.16 + 0.3965 T v^0.16
    Inggris  (T dalam °F, v dalam mph)   : WC = 35.74 + 0.6215 T - 35.75 v^0.16 + 0.4275 T v^0.16

Rumus ini hanya berlaku bila T <= 10 °C (50 °F) dan v >= 4.8 km/jam (3 mph); di luar itu hasilnya
tidak bermakna, jadi program menolaknya.

Jalankan:
    python windchill.py -20 30              # metrik: -20 °C, 30 km/jam
    python windchill.py 0 15 --system english
    python windchill.py                     # mode interaktif
"""

import argparse
import math

SYSTEMS = {
    "metric": {"name": "Metrik", "temp": "°C", "speed": "km/jam", "max_temp": 10.0, "min_speed": 4.8,
               "coef": (13.12, 0.6215, 11.37, 0.3965)},
    "english": {"name": "Inggris", "temp": "°F", "speed": "mph", "max_temp": 50.0, "min_speed": 3.0,
                "coef": (35.74, 0.6215, 35.75, 0.4275)},
}


def parse_value(text, label):
    text = str(text).strip()
    if not text:
        raise ValueError(f"{label} belum diisi.")
    try:
        value = float(text)
    except ValueError:
        raise ValueError(f"{label} '{text}' bukan angka.") from None
    if not math.isfinite(value):
        raise ValueError(f"{label} '{text}' bukan angka yang valid.")
    return value


def wind_chill(temperature, speed, system="metric"):
    """Hitung wind chill; ValueError kalau di luar rentang berlaku, atau (pemeriksaan internal) hasilnya tidak masuk akal."""
    if system not in SYSTEMS:
        raise ValueError(f"Sistem satuan harus salah satu dari: {', '.join(SYSTEMS)}.")
    unit = SYSTEMS[system]
    if temperature > unit["max_temp"]:
        raise ValueError(f"Wind chill hanya berlaku untuk suhu <= {unit['max_temp']:g} {unit['temp']} "
                         f"(diterima {temperature:g}).")
    if speed < unit["min_speed"]:
        raise ValueError(f"Wind chill hanya berlaku untuk kecepatan angin >= {unit['min_speed']:g} {unit['speed']} "
                         f"(diterima {speed:g}).")
    a, b, c, d = unit["coef"]
    factor = speed ** 0.16
    result = a + b * temperature - c * factor + d * temperature * factor
    # Dalam rentang berlaku, suhu terasa selalu lebih dingin dari suhu udara. Kalau tidak, ada yang salah.
    if result >= temperature:
        raise ValueError(f"Kesalahan internal: wind chill ({result:.1f}) tidak lebih rendah dari suhu udara ({temperature:g}).")
    return result


class Calculator:
    """Melacak masukan terakhir: menghitung ulang tanpa mengubah apa pun diminta memasukkan nilai baru (bonus)."""

    def __init__(self):
        self._last = None

    def calculate(self, temperature_text, speed_text, system="metric"):
        temperature = parse_value(temperature_text, "Suhu")
        speed = parse_value(speed_text, "Kecepatan angin")
        key = (temperature, speed, system)
        if key == self._last:
            raise ValueError("Nilai sama dengan perhitungan sebelumnya. Masukkan suhu atau kecepatan angin yang baru.")
        result = wind_chill(temperature, speed, system)
        self._last = key
        return result


def describe(temperature, speed, system, result):
    unit = SYSTEMS[system]
    return (f"Suhu udara {temperature:g} {unit['temp']}, angin {speed:g} {unit['speed']}  ->  "
            f"terasa seperti {result:.1f} {unit['temp']}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Hitung wind chill.")
    parser.add_argument("temperature", nargs="?", help="suhu udara")
    parser.add_argument("speed", nargs="?", help="kecepatan angin")
    parser.add_argument("--system", choices=list(SYSTEMS), default="metric", help="metric (°C, km/jam) atau english (°F, mph)")
    args = parser.parse_args(argv)
    calculator = Calculator()
    if args.temperature is not None or args.speed is not None:
        try:
            temperature = parse_value(args.temperature or "", "Suhu")
            speed = parse_value(args.speed or "", "Kecepatan angin")
            print(describe(temperature, speed, args.system, calculator.calculate(args.temperature, args.speed, args.system)))
        except ValueError as error:
            print(f"Error: {error}")
            return 1
        return 0
    system = args.system
    print(f"Sistem {SYSTEMS[system]['name']}. Ketik 'ganti' untuk mengubah sistem, kosongkan suhu untuk keluar.")
    while True:
        unit = SYSTEMS[system]
        try:
            temperature_text = input(f"Suhu udara ({unit['temp']}): ")
            if not temperature_text.strip():
                return 0
            if temperature_text.strip().lower() == "ganti":
                system = "english" if system == "metric" else "metric"
                print(f"Sistem sekarang: {SYSTEMS[system]['name']}")
                calculator = Calculator()
                continue
            speed_text = input(f"Kecepatan angin ({unit['speed']}): ")
            result = calculator.calculate(temperature_text, speed_text, system)
            print(describe(parse_value(temperature_text, ""), parse_value(speed_text, ""), system, result))
        except ValueError as error:
            print(f"Error: {error}")
        except EOFError:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
