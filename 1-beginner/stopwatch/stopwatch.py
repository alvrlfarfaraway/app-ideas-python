"""Stopwatch: hitung waktu dengan start, stop (lanjut lagi), restart, dan lap.

Kelas Stopwatch tidak membaca jam sendiri; waktu dikirim lewat parameter `now`, jadi bisa diuji
tanpa menunggu.

Jalankan:
    python stopwatch.py
Perintah (ketik lalu Enter): s = start, x = stop, r = restart, l = lap, c = hapus lap, q = keluar
"""

import queue
import sys
import threading
import time


def format_time(seconds):
    """mm:ss.cc (atau h:mm:ss.cc bila lebih dari satu jam). Dipotong, bukan dibulatkan, ke 1/100 detik."""
    hundredths = int(max(0, seconds) * 100 + 1e-9)
    secs, hundredths = divmod(hundredths, 100)
    minutes, secs = divmod(secs, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}.{hundredths:02d}"
    return f"{minutes:02d}:{secs:02d}.{hundredths:02d}"


class Stopwatch:
    def __init__(self):
        self.elapsed = 0.0  # waktu yang sudah terkumpul sebelum sesi berjalan saat ini
        self.running = False
        self._started_at = None
        self.laps = []  # tiap lap: (total waktu saat lap, selisih dari lap sebelumnya)
        self._lap_base = 0.0  # total waktu pada lap terakhir; acuan selisih lap berikutnya

    def time(self, now):
        """Waktu yang tampil di jam saat ini."""
        return self.elapsed + (now - self._started_at if self.running else 0.0)

    def start(self, now):
        """Mulai, atau lanjutkan dari waktu terakhir setelah stop."""
        if not self.running:
            self.running = True
            self._started_at = now

    def stop(self, now):
        if self.running:
            self.elapsed = self.time(now)
            self.running = False
            self._started_at = None

    def restart(self, now):
        """Kembalikan ke 00:00 dan langsung mulai menghitung lagi. Lap yang tercatat dibiarkan,
        tetapi selisih lap berikutnya dihitung dari 00:00 yang baru."""
        self.elapsed = 0.0
        self.running = True
        self._started_at = now
        self._lap_base = 0.0

    def lap(self, now):
        """Catat lap. Hanya bisa saat jam berjalan; mengembalikan (total, selisih)."""
        if not self.running:
            raise ValueError("Lap hanya bisa dicatat saat jam berjalan.")
        total = self.time(now)
        entry = (total, total - self._lap_base)
        self._lap_base = total
        self.laps.append(entry)
        return entry

    def clear_laps(self):
        """Hapus semua lap; lap berikutnya dihitung dari awal jam lagi."""
        self.laps.clear()
        self._lap_base = 0.0


def format_lap(number, lap):
    total, split = lap
    return f"Lap {number:>2}   {format_time(split)}   (total {format_time(total)})"


def main():
    watch = Stopwatch()
    commands = queue.Queue()

    def read_commands():
        for line in sys.stdin:
            commands.put(line.strip().lower())

    threading.Thread(target=read_commands, daemon=True).start()
    print("Perintah (lalu Enter): s = start, x = stop, r = restart, l = lap, c = hapus lap, q = keluar")
    try:
        while True:
            now = time.monotonic()
            while not commands.empty():
                command = commands.get()
                if command == "s":
                    watch.start(now)
                elif command == "x":
                    watch.stop(now)
                elif command == "r":
                    watch.restart(now)
                elif command == "l":
                    try:
                        print("\n" + format_lap(len(watch.laps) + 1, watch.lap(now)))
                    except ValueError as error:
                        print(f"\n{error}")
                elif command == "c":
                    watch.clear_laps()
                    print("\nLap dihapus.")
                elif command == "q":
                    print()
                    return 0
            state = "berjalan" if watch.running else "berhenti"
            print(f"\r{format_time(watch.time(now))}  ({state})   ", end="", flush=True)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
