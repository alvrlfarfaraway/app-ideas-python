import contextlib
import io
import os
import tempfile
import unittest
from datetime import date, datetime

import sales
from sales import MENU, Register, clear_all, connect, daily_lines, daily_sales, main, receipt_lines, rupiah

KOPI, NASI, TEH = MENU[0], MENU[4], MENU[2]


def at(hour, minute=0, day=4):
    return lambda: datetime(2026, 11, day, hour, minute)


class RegisterTest(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")

    def tearDown(self):
        self.db.close()

    def test_total_bertambah(self):
        register = Register()
        self.assertEqual(register.total, 0)
        register.add(KOPI)
        register.add(NASI)
        self.assertEqual(register.total, 22000 + 28000)

    def test_clear_entry_dan_cancel_all(self):
        register = Register()
        register.add(KOPI)
        register.add(NASI)
        self.assertEqual(register.clear_entry(), NASI)  # item terakhir
        self.assertEqual(register.items, [KOPI])
        register.cancel_all()
        self.assertEqual(register.items, [])
        self.assertIsNone(register.clear_entry())

    def test_checkout_menyimpan_semua_item(self):
        register = Register()
        for item in (KOPI, NASI, KOPI):
            register.add(item)
        sale_id, sold_at, items, total = register.checkout(self.db, "  Sari   Dewi ", at(9, 15))
        self.assertEqual((sale_id, sold_at, total), (1, "2026-11-04T09:15:00", 72000))
        self.assertEqual(register.items, [])
        rows = self.db.execute("SELECT * FROM sales ORDER BY id").fetchall()
        self.assertEqual([r["item_number"] for r in rows], ["K01", "M01", "K01"])
        self.assertEqual({r["customer"] for r in rows}, {"Sari Dewi"})
        register.add(TEH)
        self.assertEqual(register.checkout(self.db, "", at(10))[0], 2)

    def test_checkout_kosong_ditolak(self):
        with self.assertRaises(ValueError):
            Register().checkout(self.db)


class DailyTest(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")
        for when, items, who in ((at(9), (KOPI, NASI), "Sari"), (at(10), (TEH,), ""), (at(9, day=3), (NASI,), "X")):
            register = Register()
            for item in items:
                register.add(item)
            register.checkout(self.db, who, when)

    def tearDown(self):
        self.db.close()

    def test_hanya_hari_itu(self):
        rows = daily_sales(self.db, date(2026, 11, 4))
        self.assertEqual(len(rows), 3)
        self.assertEqual(sum(r["unit_price"] for r in rows), 22000 + 28000 + 8000)
        self.assertEqual(len(daily_sales(self.db, date(2026, 11, 3))), 1)

    def test_rekap(self):
        lines = daily_lines(daily_sales(self.db, date(2026, 11, 4)), date(2026, 11, 4))
        text = "\n".join(lines)
        self.assertIn("#1  09:00  Sari", text)
        self.assertIn("#2  10:00  tanpa nama", text)
        self.assertIn("3 item, 2 transaksi", text)
        self.assertTrue(lines[-1].startswith("TOTAL") and lines[-1].endswith("Rp58.000"))
        self.assertTrue(all(len(line) <= sales.RECEIPT_WIDTH for line in lines))
        self.assertIn("Belum ada penjualan.", "\n".join(daily_lines([], date(2026, 1, 1))))

    def test_clear_all(self):
        self.assertEqual(clear_all(self.db), 4)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM sales").fetchone()[0], 0)


class ReceiptTest(unittest.TestCase):
    def test_struk(self):
        lines = receipt_lines([KOPI, NASI], "2026-11-04T09:15:00", "Sari", 50000, 7)
        text = "\n".join(lines)
        self.assertIn("Waktu   : 2026-11-04 09:15:00", text)
        self.assertIn("Nomor   : #7", text)
        self.assertIn("K01 Kopi Susu Gula Aren", text)
        self.assertTrue(any(line.startswith("TOTAL") and line.endswith("Rp50.000") for line in lines))
        self.assertTrue(all(len(line) <= sales.RECEIPT_WIDTH for line in lines))
        self.assertNotIn("TOTAL", "\n".join(receipt_lines([KOPI])))

    def test_rupiah(self):
        self.assertEqual(rupiah(0), "Rp0")
        self.assertEqual(rupiah(1250000), "Rp1.250.000")


class CliTest(unittest.TestCase):
    def test_daily(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(["--db", os.path.join(tmp, "s.db"), "--daily"]), 0)
            self.assertIn("Belum ada penjualan.", out.getvalue())


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.db = connect(":memory:")
        self.answer = True
        self.app = sales.SalesApp(self.root, self.db, clock=at(9, 30), confirm=lambda message: self.answer)

    def tearDown(self):
        self.root.destroy()
        self.db.close()

    def receipt(self):
        return self.app.receipt.get("1.0", "end-1c")

    def test_beli_struk_dan_checkout(self):
        self.app.customer.set("Budi")
        self.app.buy(KOPI)
        self.app.buy(TEH)
        self.assertEqual(self.app.total.get(), "Rp30.000")
        self.assertIn("Pelanggan: Budi", self.receipt())
        self.assertIn("2026-11-04 09:30:00", self.receipt())
        self.app.clear_entry()
        self.assertNotIn("Teh Manis", self.receipt())
        self.assertEqual(self.app.checkout(), 1)
        self.assertIn("TOTAL", self.receipt())
        self.assertEqual(self.app.total.get(), "Rp0")
        self.app.auto_clear()  # dipanggil after() beberapa detik setelah checkout
        self.assertEqual(self.receipt(), "")
        self.assertEqual(len(daily_sales(self.db, date(2026, 11, 4))), 1)

    def test_checkout_kosong_dan_cancel_all(self):
        self.assertIsNone(self.app.checkout())
        self.assertIn("Belum ada item", self.app.status.get())
        self.app.buy(NASI)
        self.app.cancel_all()
        self.assertEqual(self.app.total.get(), "Rp0")
        self.assertEqual(self.receipt(), "")

    def test_daily_dan_clear_all(self):
        self.app.buy(NASI)
        self.app.checkout()
        self.app.daily()
        self.assertIn("Rp28.000", self.receipt())
        self.answer = False
        self.app.clear_all()  # dibatalkan di dialog konfirmasi
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM sales").fetchone()[0], 1)
        self.answer = True
        self.app.clear_all()
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM sales").fetchone()[0], 0)
        self.assertIn("1 baris", self.app.status.get())


if __name__ == "__main__":
    unittest.main()
