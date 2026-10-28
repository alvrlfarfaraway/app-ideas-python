"""CSV2JSON: ubah CSV menjadi JSON, dan (salinan dari JSON2CSV) JSON menjadi CSV.

Batasan spesifikasi: tidak memakai modul `csv` atau pustaka konversi lain, dan
JSON bersarang tidak didukung. Modul `json` hanya dipakai untuk membaca dan
menulis teks JSON; pembacaan CSV (parser dengan kutip) ditulis sendiri.

Jalankan:
    python csv2json.py to-json data.csv                # CSV -> JSON ke layar
    python csv2json.py to-json data.csv -o data.json   # simpan ke berkas
    python csv2json.py to-json data.csv --types        # angka dan true/false jadi tipe JSON
    python csv2json.py to-csv data.json -o data.csv    # JSON -> CSV
"""

import argparse
import json
import sys


# --- JSON -> CSV (disalin dari ../json2csv/json2csv.py) ---------------------

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


# --- CSV -> JSON (baru) ------------------------------------------------------

def parse_csv(text):
    """Pecah teks CSV menjadi daftar baris (daftar sel). Mendukung sel berkutip,
    koma/baris baru di dalam kutip, dan "" sebagai kutip literal."""
    rows, row, cell = [], [], []
    in_quotes = False
    cell_started = False  # sel sudah berisi sesuatu (termasuk sel kosong berkutip)
    i, length = 0, len(text)
    while i < length:
        char = text[i]
        if in_quotes:
            if char == '"':
                if i + 1 < length and text[i + 1] == '"':
                    cell.append('"')
                    i += 1
                else:
                    in_quotes = False
            else:
                cell.append(char)
        elif char == '"':
            if cell:
                raise ValueError(f"Kutip tidak pada tempatnya di baris {len(rows) + 1}.")
            in_quotes = True
            cell_started = True
        elif char == ",":
            row.append("".join(cell))
            cell, cell_started = [], False
        elif char in "\r\n":
            if char == "\r" and i + 1 < length and text[i + 1] == "\n":
                i += 1
            row.append("".join(cell))
            if row != [""] or cell_started:  # lewati baris kosong
                rows.append(row)
            row, cell, cell_started = [], [], False
        else:
            cell.append(char)
            cell_started = True
        i += 1
    if in_quotes:
        raise ValueError("Tanda kutip dibuka tetapi tidak pernah ditutup.")
    row.append("".join(cell))
    if row != [""] or cell_started:
        rows.append(row)
    return rows


def infer_type(text):
    """Ubah 'true'/'false', bilangan bulat, dan desimal menjadi tipe JSON; lainnya tetap teks."""
    if text == "true":
        return True
    if text == "false":
        return False
    for convert in (int, float):
        try:
            value = convert(text)
        except ValueError:
            continue
        if convert is float and (value != value or value in (float("inf"), float("-inf"))):
            return text
        return value
    return text


def csv_to_json(text, types=False):
    """Kembalikan JSON (daftar objek) dari teks CSV yang barisnya pertama adalah header."""
    if not text.strip():
        raise ValueError("Teks CSV kosong.")
    rows = parse_csv(text)
    if not rows:
        raise ValueError("Teks CSV kosong.")
    headers = rows[0]
    if any(not name.strip() for name in headers):
        raise ValueError("Header memiliki nama kolom yang kosong.")
    if len(set(headers)) != len(headers):
        raise ValueError("Header memiliki nama kolom ganda.")
    records = []
    for number, row in enumerate(rows[1:], start=2):
        if len(row) != len(headers):
            raise ValueError(f"Baris data ke-{number} punya {len(row)} kolom, header punya {len(headers)}.")
        records.append({name: infer_type(cell) if types else cell for name, cell in zip(headers, row)})
    return json.dumps(records, ensure_ascii=False, indent=2) + "\n"


# --- berkas dan CLI ----------------------------------------------------------

def read_text(path):
    if path is None:
        return sys.stdin.read()
    try:
        with open(path, encoding="utf-8-sig") as file:
            return file.read()
    except FileNotFoundError:
        raise ValueError(f"Berkas '{path}' tidak ditemukan.") from None
    except OSError as error:
        raise ValueError(f"Berkas '{path}' tidak bisa dibaca: {error.strerror}.") from None


def write_text(path, text):
    if not text.strip():
        raise ValueError("Tidak ada hasil untuk disimpan.")
    try:
        with open(path, "w", encoding="utf-8", newline="") as file:
            file.write(text)
    except OSError as error:
        raise ValueError(f"Gagal menyimpan '{path}': {error.strerror}.") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Konversi CSV <-> JSON.")
    sub = parser.add_subparsers(dest="command", required=True)
    to_json = sub.add_parser("to-json", help="CSV ke JSON")
    to_json.add_argument("--types", action="store_true", help="angka dan true/false menjadi tipe JSON")
    to_csv = sub.add_parser("to-csv", help="JSON ke CSV")
    for p in (to_json, to_csv):
        p.add_argument("input", nargs="?", help="berkas masukan; kosong = baca dari stdin")
        p.add_argument("-o", "--output", help="simpan hasil ke berkas ini")
    args = parser.parse_args(argv)
    try:
        source = read_text(args.input)
        result = csv_to_json(source, args.types) if args.command == "to-json" else json_to_csv(source)
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
