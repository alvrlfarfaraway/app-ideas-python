"""First DB App: panel kontrol Load DB / Query DB / Clear DB di terminal.

Jalankan:
    python app.py                 # database di customers.db di folder ini
    python app.py --db contoh.db
Perintah: load, query, clear, log, quit
"""

import argparse
import os
from datetime import datetime

from customers import Customer

HERE = os.path.dirname(os.path.abspath(__file__))


class App:
    """Logika panel: tombol, notifikasi, dan log. Terpisah dari input/output supaya bisa diuji."""

    def __init__(self, customer):
        self.customer = customer
        self.log = []  # riwayat semua notifikasi (panel log)
        self.notification = ""  # notifikasi terbaru (panel notifikasi)
        # Status awal tombol bergantung pada isi database yang sudah ada.
        self.has_data = bool(customer.query_all_rows())

    def buttons(self):
        """Tombol aktif/nonaktif sesuai tabel bonus pada spesifikasi."""
        return {"load": not self.has_data, "query": True, "clear": self.has_data}

    def _notify(self, message):
        self.notification = message
        self.log.append(f"{datetime.now():%H:%M:%S}  {message}")

    def _guard(self, name):
        if not self.buttons()[name]:
            self._notify(f"Tombol '{name}' sedang nonaktif.")
            return False
        return True

    def load_db(self):
        if not self._guard("load"):
            return
        self._notify("Memuat database...")
        count = self.customer.initial_load()
        self.has_data = True
        self._notify(f"Selesai memuat {count} pelanggan.")

    def query_db(self):
        self._notify("Query dimulai...")
        rows = self.customer.query_all_rows()
        self._notify(f"Query selesai: {len(rows)} baris.")
        return rows

    def clear_db(self):
        if not self._guard("clear"):
            return
        self._notify("Menghapus semua baris...")
        removed = self.customer.remove_all_rows()
        self.has_data = False
        self._notify(f"Selesai menghapus {removed} baris.")


def format_rows(rows):
    if not rows:
        return "(tidak ada baris untuk ditampilkan)"
    header = f"{'ID':<6}{'Nama':<10}{'Email':<22}{'Order terakhir':<16}{'Penjualan/tahun':>16}"
    lines = [header, "-" * len(header)]
    for userid, name, email, last_order, sales in rows:
        lines.append(f"{userid:<6}{name:<10}{email:<22}{last_order or '-':<16}{sales:>16,.2f}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="First DB App (SQLite).")
    parser.add_argument("--db", default=os.path.join(HERE, "customers.db"))
    args = parser.parse_args(argv)
    app = App(Customer(args.db))
    print("Perintah: load, query, clear, log, quit")
    while True:
        state = " ".join(f"[{name.upper()}{'' if on else ' (nonaktif)'}]" for name, on in app.buttons().items())
        try:
            command = input(f"{state}\n> ").strip().lower()
        except EOFError:
            return 0
        if command in ("quit", "q", "exit"):
            return 0
        if command == "load":
            app.load_db()
        elif command == "query":
            rows = app.query_db()
            print(format_rows(rows))
        elif command == "clear":
            app.clear_db()
        elif command == "log":
            print("\n".join(app.log) or "(log kosong)")
            continue
        else:
            print("Perintah tidak dikenal.")
            continue
        print(f"Notifikasi: {app.notification}")


if __name__ == "__main__":
    raise SystemExit(main())
