"""Countdown Timer: hitung mundur hari, jam, menit, dan detik menuju sebuah event.

Hanya memakai modul bawaan Python (datetime, json, time).

Jalankan:
    python countdown.py start "Tahun Baru" 2027-01-01          # hitung mundur langsung
    python countdown.py start "Rapat" 2026-12-01 09:30
    python countdown.py add "Ulang Tahun" 2027-03-14           # simpan event
    python countdown.py watch                                   # hitung mundur semua event tersimpan
    python countdown.py list                                    # tampilkan sekali lalu selesai
    python countdown.py remove "Ulang Tahun"
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

MAX_DAYS = 9999  # batas tampilan: 4 digit hari
DEFAULT_FILE = os.path.join(os.path.expanduser("~"), ".app-ideas-python", "countdown.json")


def parse_event(name, date_text, time_text=""):
    """Validasi input pengguna dan kembalikan event {'name', 'when'}.

    Waktu boleh dikosongkan; artinya tengah malam (00:00) pada tanggal tersebut.
    """
    name = name.strip()
    if not name:
        raise ValueError("Nama event tidak boleh kosong.")
    try:
        moment = datetime.strptime(date_text.strip(), "%Y-%m-%d")
    except ValueError:
        raise ValueError("Tanggal harus berformat YYYY-MM-DD dan nyata, misalnya 2027-01-31.") from None
    time_text = time_text.strip()
    if time_text:
        try:
            clock = datetime.strptime(time_text, "%H:%M")
        except ValueError:
            raise ValueError("Waktu harus berformat HH:MM (24 jam), misalnya 18:30.") from None
        moment = moment.replace(hour=clock.hour, minute=clock.minute)
    return {"name": name, "when": moment.isoformat(timespec="minutes")}


def check_precision(event, now):
    """Tolak event yang terlalu jauh sehingga melebihi MAX_DAYS hari."""
    days = (datetime.fromisoformat(event["when"]) - now).days
    if days > MAX_DAYS:
        raise ValueError(f"Event terlalu jauh ({days} hari). Batas hitung mundur {MAX_DAYS} hari.")


def remaining(target, now):
    """Sisa waktu (hari, jam, menit, detik); (0, 0, 0, 0) kalau sudah lewat."""
    seconds = max(0, int((target - now).total_seconds()))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return days, hours, minutes, seconds


def render(events, now):
    """Satu baris per event. Mengembalikan (daftar baris, nama event yang sudah tercapai)."""
    lines, reached = [], []
    for event in events:
        target = datetime.fromisoformat(event["when"])
        if target <= now:
            lines.append(f"{event['name']}: TERCAPAI ({event['when'].replace('T', ' ')})")
            reached.append(event["name"])
        else:
            d, h, m, s = remaining(target, now)
            lines.append(f"{event['name']}: {d} hari {h:02d} jam {m:02d} menit {s:02d} detik")
    return lines, reached


def watch(events, once=False, now_fn=datetime.now, sleep=time.sleep, out=sys.stdout):
    """Tampilkan hitung mundur yang terus berkurang tiap detik sampai semua event tercapai."""
    alerted = set()
    previous_lines = 0
    while True:
        lines, reached = render(events, now_fn())
        if previous_lines:
            out.write(f"\x1b[{previous_lines}A")  # naik ke awal blok sebelumnya
        for line in lines:
            out.write("\x1b[2K" + line + "\n")  # hapus baris lalu tulis ulang
        out.flush()
        previous_lines = len(lines)
        for name in reached:
            if name not in alerted:
                alerted.add(name)
                out.write(f"\x07*** {name} sudah tercapai! ***\n")
                previous_lines += 1
        if once or len(reached) == len(events):
            return
        sleep(1)


def load_events(path):
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def save_events(path, events):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(events, file, ensure_ascii=False, indent=2)


def build_parser():
    parser = argparse.ArgumentParser(description="Hitung mundur menuju event.")
    parser.add_argument("-f", "--file", default=DEFAULT_FILE, help="berkas penyimpanan event")
    sub = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (("start", "hitung mundur langsung tanpa menyimpan"),
                               ("add", "simpan event baru")):
        p = sub.add_parser(command, help=help_text)
        p.add_argument("name")
        p.add_argument("date", help="YYYY-MM-DD")
        p.add_argument("time", nargs="?", default="", help="HH:MM, kosong = 00:00")
        p.add_argument("--once", action="store_true", help="tampilkan sekali saja")
    for command, help_text in (("watch", "hitung mundur semua event tersimpan"),
                               ("list", "tampilkan semua event sekali saja")):
        p = sub.add_parser(command, help=help_text)
        p.add_argument("--once", action="store_true", help="tampilkan sekali saja")
    sub.add_parser("remove", help="hapus event").add_argument("name")
    return parser


def main(argv=None, now_fn=datetime.now):
    args = build_parser().parse_args(argv)
    try:
        if args.command in ("start", "add"):
            event = parse_event(args.name, args.date, args.time)
            check_precision(event, now_fn())
            if args.command == "add":
                events = load_events(args.file)
                if any(e["name"] == event["name"] for e in events):
                    raise ValueError(f"Event '{event['name']}' sudah ada.")
                save_events(args.file, events + [event])
                print(f"Tersimpan: {event['name']} pada {event['when'].replace('T', ' ')}")
                return 0
            watch([event], once=args.once, now_fn=now_fn)
        elif args.command in ("watch", "list"):
            events = load_events(args.file)
            if not events:
                raise ValueError("Belum ada event tersimpan. Tambahkan dengan perintah 'add'.")
            watch(events, once=args.once or args.command == "list", now_fn=now_fn)
        elif args.command == "remove":
            events = load_events(args.file)
            kept = [e for e in events if e["name"] != args.name]
            if len(kept) == len(events):
                raise ValueError(f"Event '{args.name}' tidak ditemukan.")
            save_events(args.file, kept)
            print(f"Dihapus: {args.name}")
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
