import os
import sqlite3
import tempfile
import unittest

from app import App, format_rows
from customers import Customer


class DbTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "test.db")
        self.customer = Customer(self.path)

    def tearDown(self):
        self.dir.cleanup()


class CustomerTest(DbTestCase):
    def test_kosong_di_awal(self):
        self.assertEqual(self.customer.query_all_rows(), [])

    def test_load_lalu_query(self):
        self.assertEqual(self.customer.initial_load(), 2)
        rows = self.customer.query_all_rows()
        self.assertEqual([r[0] for r in rows], ["444", "555"])
        self.assertEqual(rows[0][1:3], ("Bill", "bill@company.com"))

    def test_load_dua_kali_tidak_menggandakan(self):
        self.customer.initial_load()
        self.customer.initial_load()
        self.assertEqual(len(self.customer.query_all_rows()), 2)

    def test_clear(self):
        self.customer.initial_load()
        self.assertEqual(self.customer.remove_all_rows(), 2)
        self.assertEqual(self.customer.query_all_rows(), [])

    def test_persisten_antar_sesi(self):
        self.customer.initial_load()
        self.assertEqual(len(Customer(self.path).query_all_rows()), 2)

    def test_email_harus_unik_dan_transaksi_dibatalkan(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.customer.initial_load([("1", "A", "x@y.z", None, 0), ("2", "B", "x@y.z", None, 0)])
        self.assertEqual(self.customer.query_all_rows(), [])


class AppTest(DbTestCase):
    def test_tabel_status_tombol(self):
        app = App(self.customer)
        self.assertEqual(app.buttons(), {"load": True, "query": True, "clear": False})  # awal
        app.load_db()
        self.assertEqual(app.buttons(), {"load": False, "query": True, "clear": True})  # setelah Load
        app.query_db()
        self.assertEqual(app.buttons(), {"load": False, "query": True, "clear": True})  # setelah Query
        app.clear_db()
        self.assertEqual(app.buttons(), {"load": True, "query": True, "clear": False})  # setelah Clear

    def test_status_awal_mengikuti_isi_database(self):
        self.customer.initial_load()
        self.assertEqual(App(self.customer).buttons(), {"load": False, "query": True, "clear": True})

    def test_notifikasi_awal_dan_akhir_dan_riwayat_log(self):
        app = App(self.customer)
        app.load_db()
        app.query_db()
        app.clear_db()
        self.assertEqual(len(app.log), 6)  # mulai + selesai untuk tiga operasi
        self.assertIn("Selesai menghapus 2 baris", app.notification)
        self.assertIn("Memuat", app.log[0])

    def test_tombol_nonaktif_tidak_bekerja(self):
        app = App(self.customer)
        app.clear_db()  # nonaktif karena database kosong
        self.assertIn("nonaktif", app.notification)
        app.load_db()
        app.load_db()  # nonaktif karena sudah terisi
        self.assertEqual(len(self.customer.query_all_rows()), 2)

    def test_format_rows(self):
        self.assertIn("tidak ada baris", format_rows([]))
        self.customer.initial_load()
        text = format_rows(self.customer.query_all_rows())
        self.assertIn("Donna", text)
        self.assertIn("1,250.50", text)


if __name__ == "__main__":
    unittest.main()
