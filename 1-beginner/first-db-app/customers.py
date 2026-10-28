"""Lapisan database: kelas Customer di atas SQLite (padanan IndexedDB di spesifikasi)."""

import sqlite3

SAMPLE_CUSTOMERS = [
    # userid, name, email, last_order (YYYY-MM-DD), yearly_sales
    ("444", "Bill", "bill@company.com", "2026-09-14", 1250.50),
    ("555", "Donna", "donna@home.org", "2026-10-02", 830.00),
]


class Customer:
    def __init__(self, db_path):
        self.db_path = db_path

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.execute(
            """CREATE TABLE IF NOT EXISTS customers (
                   userid TEXT PRIMARY KEY,
                   name TEXT NOT NULL,
                   email TEXT NOT NULL UNIQUE,
                   last_order TEXT,
                   yearly_sales REAL)"""
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_customers_name ON customers (name)")
        return connection

    def initial_load(self, customers=SAMPLE_CUSTOMERS):
        """Isi tabel dengan data awal; userid yang sudah ada diperbarui (seperti objectStore.put)."""
        connection = self._connect()
        try:
            with connection:  # satu transaksi: berhasil semua atau batal semua
                # Upsert per userid. INSERT OR REPLACE tidak dipakai karena ia juga
                # menghapus baris lain yang emailnya bentrok, bukan menolaknya.
                connection.executemany(
                    """INSERT INTO customers VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(userid) DO UPDATE SET
                           name = excluded.name, email = excluded.email,
                           last_order = excluded.last_order, yearly_sales = excluded.yearly_sales""",
                    customers,
                )
        finally:
            connection.close()
        return len(customers)

    def query_all_rows(self):
        connection = self._connect()
        try:
            return connection.execute(
                "SELECT userid, name, email, last_order, yearly_sales FROM customers ORDER BY userid"
            ).fetchall()
        finally:
            connection.close()

    def remove_all_rows(self):
        connection = self._connect()
        try:
            with connection:
                return connection.execute("DELETE FROM customers").rowcount
        finally:
            connection.close()
