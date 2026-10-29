"""Pomodoro Clock: sesi kerja 25 menit, istirahat 5 menit, dan istirahat panjang 10 menit tiap istirahat ke-4.

Inti timer (kelas Pomodoro) tidak membaca jam sendiri; waktu diberikan lewat parameter `now`,
sehingga bisa diuji tanpa menunggu.

Jalankan:
    python pomodoro.py                              # 25/5/10 menit
    python pomodoro.py --work 50 --short 10 --long 20
    python pomodoro.py --work 0.1 --short 0.05      # menit boleh pecahan (uji cepat)
Perintah (ketik lalu Enter): p = start/pause, s = stop, r = reset, q = keluar
"""

import argparse
import math
import queue
import sys
import threading
import time

WORK, SHORT, LONG = "work", "short_break", "long_break"
LABELS = {WORK: "KERJA", SHORT: "ISTIRAHAT", LONG: "ISTIRAHAT PANJANG"}


def format_clock(seconds):
    """mm:ss; dibulatkan ke atas supaya 00:00 hanya tampil saat sesi benar-benar habis."""
    total = max(0, math.ceil(seconds - 1e-9))
    return f"{total // 60:02d}:{total % 60:02d}"


class Pomodoro:
    def __init__(self, work=25, short=5, long=10, long_every=4, on_end=None):
        for name, value in (("work", work), ("short", short)):
            if value <= 0:
                raise ValueError(f"Durasi {name} harus lebih dari 0 menit.")
        if long < 0:
            raise ValueError("Durasi istirahat panjang tidak boleh negatif (0 = dimatikan).")
        if long_every < 1:
            raise ValueError("Istirahat panjang tiap berapa sesi harus minimal 1.")
        self.minutes = {WORK: work, SHORT: short, LONG: long}
        self.long_every = long_every
        self.on_end = on_end or (lambda phase: None)
        self.reset()

    def _full(self, phase):
        return self.minutes[phase] * 60

    def reset(self):
        """Kembali ke awal: sesi kerja pertama, hitungan siklus nol, berhenti."""
        self.phase = WORK
        self.remaining = self._full(WORK)
        self.running = False
        self.breaks_started = 0
        self.work_completed = 0
        self._last = None

    def stop(self):
        """Berhenti dan kembalikan sesi yang sedang berjalan ke durasi penuh (siklus tidak diubah)."""
        self.running = False
        self._last = None
        self.remaining = self._full(self.phase)

    def start(self, now):
        if not self.running:
            self.running = True
            self._last = now

    def pause(self, now):
        self.update(now)
        self.running = False
        self._last = None

    def toggle(self, now):
        self.pause(now) if self.running else self.start(now)

    def update(self, now):
        """Majukan waktu sampai `now`; pindah sesi (dengan sisa waktu terbawa) kalau sesi habis."""
        if not self.running:
            return
        self.remaining -= now - self._last
        self._last = now
        while self.remaining <= 0:
            overshoot = -self.remaining
            self._end_phase()
            self.remaining -= overshoot

    def _end_phase(self):
        ended = self.phase
        if ended == WORK:
            self.work_completed += 1
            self.breaks_started += 1
            use_long = self.minutes[LONG] > 0 and self.breaks_started % self.long_every == 0
            self.phase = LONG if use_long else SHORT
        else:
            self.phase = WORK
        self.remaining = self._full(self.phase)
        self.on_end(ended)


def beep():
    try:
        import winsound
        winsound.Beep(880, 400)
    except ImportError:
        print("\a", end="", flush=True)


def build_parser():
    parser = argparse.ArgumentParser(description="Pomodoro Clock.")
    parser.add_argument("--work", type=float, default=25, help="menit sesi kerja (bawaan 25)")
    parser.add_argument("--short", type=float, default=5, help="menit istirahat (bawaan 5)")
    parser.add_argument("--long", type=float, default=10, help="menit istirahat panjang (bawaan 10; 0 = matikan)")
    parser.add_argument("--cycles", type=int, help="berhenti setelah sekian sesi kerja selesai (untuk uji)")
    parser.add_argument("--silent", action="store_true", help="tanpa bunyi")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    events = []

    def on_end(phase):
        events.append(phase)
        if not args.silent:
            beep()

    try:
        timer = Pomodoro(args.work, args.short, args.long, on_end=on_end)
    except ValueError as error:
        print(f"Error: {error}")
        return 1

    commands = queue.Queue()

    def read_commands():
        for line in sys.stdin:
            commands.put(line.strip().lower())

    threading.Thread(target=read_commands, daemon=True).start()
    print("Perintah (lalu Enter): p = start/pause, s = stop, r = reset, q = keluar")
    last_phase = None
    try:
        while True:
            now = time.monotonic()
            while not commands.empty():
                command = commands.get()
                if command == "p":
                    timer.toggle(now)
                elif command == "s":
                    timer.stop()
                elif command == "r":
                    timer.reset()
                elif command == "q":
                    print()
                    return 0
            timer.update(now)
            if timer.phase != last_phase and last_phase is not None:
                print(f"\n>>> Sesi {LABELS[last_phase].lower()} selesai! Sekarang: {LABELS[timer.phase].lower()}.")
            last_phase = timer.phase
            if args.cycles and timer.work_completed >= args.cycles:
                print(f"\nSelesai: {timer.work_completed} sesi kerja.")
                return 0
            state = "berjalan" if timer.running else "dijeda"
            print(f"\r{LABELS[timer.phase]:<18}{format_clock(timer.remaining)}  ({state}, sesi kerja selesai: "
                  f"{timer.work_completed})   ", end="", flush=True)
            time.sleep(0.2)
    except KeyboardInterrupt:
        print()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
