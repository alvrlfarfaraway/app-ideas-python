"""JSON2CSV: ubah JSON (daftar objek datar) menjadi CSV.

Batasan spesifikasi: tidak memakai modul `csv` atau pustaka konversi lain, dan
JSON bersarang tidak didukung. Modul `json` hanya dipakai untuk membaca teks
JSON (validasi), sedangkan penulisan CSV dilakukan sendiri.

Jalankan:
    python json2csv.py data.json               # cetak CSV ke layar
    python json2csv.py data.json -o data.csv   # simpan ke berkas
    type data.json | python json2csv.py        # baca dari stdin
"""

import argparse
import json
import sys


def format_field(value):
    """Ubah satu nilai JSON datar menjadi teks sel CSV (dengan tanda kutip bila perlu)."""
    if isinstance(value, (dict, list)):
        raise ValueError("JSON bersarang (objek/daftar di dalam objek) tidak didukung.")
    if value is None:
        return ""
    if isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value)
    if any(char in text for char in ',"\r\n') or text != text.strip():
        text = '"' + text.replace('"', '""') + '"'
    return text


def json_to_csv(text):
    """Kembalikan teks CSV; header diambil dari gabungan kunci, urut kemunculan pertama."""
    if not text.strip():
        raise ValueError("Teks JSON kosong.")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON tidak valid: {error.msg} (baris {error.lineno}, kolom {error.colno}).") from None

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not data:
        raise ValueError("JSON harus berupa objek atau daftar objek yang tidak kosong.")
    for number, row in enumerate(data, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Item ke-{number} bukan objek; setiap item harus berupa objek.")

    headers = list(dict.fromkeys(key for row in data for key in row))
    lines = [",".join(format_field(key) for key in headers)]
    for row in data:
        lines.append(",".join(format_field(row.get(key)) for key in headers))
    return "\n".join(lines) + "\n"


def read_text(path):
    if path is None:
        return sys.stdin.read()
    try:
        with open(path, encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        raise ValueError(f"Berkas '{path}' tidak ditemukan.") from None
    except OSError as error:
        raise ValueError(f"Berkas '{path}' tidak bisa dibaca: {error.strerror}.") from None


def write_text(path, text):
    if not text.strip():
        raise ValueError("Tidak ada CSV untuk disimpan.")
    try:
        with open(path, "w", encoding="utf-8", newline="") as file:
            file.write(text)
    except OSError as error:
        raise ValueError(f"Gagal menyimpan '{path}': {error.strerror}.") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Konversi JSON ke CSV.")
    parser.add_argument("input", nargs="?", help="berkas JSON; kosong = baca dari stdin")
    parser.add_argument("-o", "--output", help="simpan CSV ke berkas ini")
    args = parser.parse_args(argv)
    try:
        result = json_to_csv(read_text(args.input))
        if args.output:
            write_text(args.output, result)
            print(f"Tersimpan: {args.output}")
        else:
            sys.stdout.write(result)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
