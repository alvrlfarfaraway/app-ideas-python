"""IOT Mailbox Simulator: kotak surat pintar yang mengabari lewat callback.

IOTMailbox mengukur tingkat cahaya di dalam kotak surat tiap interval dan memanggil
callback. Cahaya positif = pintu terbuka, negatif = tertutup. Panel menerima angka itu,
mencatat log, dan memberi notifikasi (bel, peringatan pintu dibiarkan terbuka).

Jalankan:
    python iot_mailbox.py                  # panel interaktif: start, stop, reset, log, quit
    python iot_mailbox.py --interval 0.3   # interval pemantauan dalam detik
    python iot_mailbox.py --demo 3         # nyalakan 3 detik lalu berhenti (tanpa input)
    python iot_mailbox.py --stuck-open     # simulasi pintu yang tidak ditutup lagi
"""

import argparse
import random
import threading
import time


class IOTMailbox:
    """Padanan kelas IOTMailbox di spesifikasi, memakai thread sebagai pengganti setInterval.

    Dua perbaikan atas kode JavaScript aslinya: callback menerima `lightLevel` yang sungguh
    dihitung (aslinya `this.lightLevel` yang tidak ada, sehingga undefined), dan tanda
    positif/negatif bergantian lewat status pintu, bukan lewat perbandingan nilai yang bisa
    ambigu saat tingkat cahaya tepat 0.
    """

    def __init__(self, signal_interval=0.5, signal_callback=None, random_fn=random.random, light_source=None):
        if signal_interval <= 0:
            raise ValueError("Interval harus lebih dari 0 detik.")
        self.signal_interval = signal_interval
        self.signal_callback = signal_callback or (lambda level: None)
        self.last_light_level = 0.0
        self._random = random_fn
        self._light_source = light_source or self._alternate
        self._stop = threading.Event()
        self._thread = None

    @property
    def monitoring(self):
        return self._thread is not None and self._thread.is_alive()

    def _alternate(self, last_level):
        """Pintu berganti terbuka/tertutup tiap interval; besar cahaya acak 0.01-1.00."""
        magnitude = max(0.01, round(self._random(), 2))
        return -magnitude if last_level > 0 else magnitude

    def start_monitoring(self):
        if self.monitoring:
            return
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, args=(self._stop,), daemon=True)
        self._thread.start()

    def stop_monitoring(self):
        if self._thread is None:
            return
        self._stop.set()
        self._thread.join()
        self._thread = None

    def _run(self, stop):
        while not stop.wait(self.signal_interval):
            self.signal_state_change()

    def signal_state_change(self):
        level = self._light_source(self.last_light_level)
        self.last_light_level = level
        self.signal_callback(level)


class Panel:
    """Panel kontrol: tombol, panel notifikasi, dan panel log."""

    def __init__(self, interval=0.5, open_alert_after=3, light_source=None, random_fn=random.random,
                 emit=print, bell=lambda: print("\a", end="", flush=True)):
        self.mailbox = IOTMailbox(interval, self.on_light_level, random_fn, light_source)
        self.open_alert_after = open_alert_after  # berapa pembacaan berturut-turut = "dibiarkan terbuka"
        self.log = []
        self.notifications = []
        self._emit = emit
        self._bell = bell
        self._lock = threading.Lock()
        self._open_streak = 0
        self._left_open_alerted = False

    def buttons(self):
        """Start nonaktif selagi memantau, Stop nonaktif selagi tidak (bonus)."""
        return {"start": not self.mailbox.monitoring, "stop": self.mailbox.monitoring, "reset": True}

    def _log(self, message):
        with self._lock:
            self.log.append(f"{time.strftime('%H:%M:%S')}  {message}")
            self._emit(f"  log: {message}")

    def _notify(self, message):
        with self._lock:
            self.notifications.append(message)
            self._emit(f"NOTIFIKASI: {message}")

    def start(self):
        if not self.buttons()["start"]:
            return False
        self._log(f"Pemantauan dimulai (interval {self.mailbox.signal_interval:g} detik).")
        self.mailbox.start_monitoring()
        return True

    def stop(self):
        if not self.buttons()["stop"]:
            return False
        self.mailbox.stop_monitoring()
        self._log("Pemantauan dihentikan.")
        return True

    def reset(self):
        if self.mailbox.monitoring:
            self.mailbox.stop_monitoring()
        with self._lock:
            self.log.clear()
            self.notifications.clear()
        self._open_streak = 0
        self._left_open_alerted = False
        self.mailbox.last_light_level = 0.0

    def on_light_level(self, level):
        """Callback yang dipanggil IOTMailbox tiap interval."""
        is_open = level > 0
        self._log(f"Tingkat cahaya {level:+.2f}: pintu {'TERBUKA' if is_open else 'tertutup'}.")
        if is_open:
            if self._open_streak == 0:
                self._notify("Pintu kotak surat dibuka! Mungkin ada surat.")
                self._bell()
            self._open_streak += 1
            if self._open_streak >= self.open_alert_after and not self._left_open_alerted:
                self._left_open_alerted = True
                self._notify("Pintu dibiarkan terbuka! Tutup kembali kotak suratnya.")
        else:
            self._open_streak = 0
            self._left_open_alerted = False


def stuck_open_source(random_fn=random.random):
    """Sumber cahaya: pintu dibuka lalu tidak pernah ditutup lagi."""
    def source(last_level):
        return max(0.01, round(random_fn(), 2))  # selalu positif = pintu terus terbuka
    return source


def main(argv=None):
    parser = argparse.ArgumentParser(description="Simulator kotak surat IOT.")
    parser.add_argument("--interval", type=float, default=0.5, help="interval pemantauan (detik)")
    parser.add_argument("--demo", type=float, metavar="DETIK", help="nyalakan selama DETIK lalu berhenti")
    parser.add_argument("--stuck-open", action="store_true", help="pintu tidak pernah ditutup lagi setelah dibuka")
    args = parser.parse_args(argv)
    try:
        panel = Panel(args.interval, light_source=stuck_open_source() if args.stuck_open else None)
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    if args.demo is not None:
        panel.start()
        time.sleep(args.demo)
        panel.stop()
        return 0
    print("Perintah: start, stop, reset, log, quit")
    try:
        while True:
            state = " ".join(f"[{name.upper()}{'' if on else ' (nonaktif)'}]" for name, on in panel.buttons().items())
            command = input(f"{state}\n> ").strip().lower()
            if command in ("quit", "q", "exit"):
                break
            if command in ("start", "stop"):
                if not getattr(panel, command)():
                    print(f"Tombol '{command}' sedang nonaktif.")
            elif command == "reset":
                panel.reset()
                print("Log dan notifikasi dikosongkan.")
            elif command == "log":
                print("\n".join(panel.log) or "(log kosong)")
            else:
                print("Perintah tidak dikenal.")
    except (EOFError, KeyboardInterrupt):
        print()
    panel.mailbox.stop_monitoring()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
