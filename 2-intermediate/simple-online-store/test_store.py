import json
import os
import tempfile
import unittest
from datetime import datetime

import store
from store import Cart, Inventory, Product, StoreError, load_catalog, place_order, rupiah

ADDRESS = "Rina Kartika\nJl. Malioboro 10, Yogyakarta"


def inventory(path=None):
    products = [Product("A", "Mug", 65000, 3, "pendek", "panjang"),
                Product("B", "Kaos", 120000, 1, "pendek", "panjang"),
                Product("C", "Stiker", 25000, 0, "pendek", "panjang")]
    return Inventory(products, path)


def fixed(*_):
    return "ABC123"


class CatalogTest(unittest.TestCase):
    def test_katalog_bawaan(self):
        products = load_catalog()
        self.assertEqual(len(products), 8)
        self.assertEqual(len({p.id for p in products}), 8)
        self.assertTrue(all(p.price > 0 and p.short and p.long for p in products))
        self.assertIn(0, [p.stock for p in products])  # ada produk habis untuk contoh

    def test_katalog_salah(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "p.json")
            for data in ([{"id": "A", "name": "x", "price": -1, "stock": 1, "short": "", "long": ""}],
                         [{"id": "A", "name": "x", "price": 1, "stock": 1, "short": "", "long": ""}] * 2):
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump(data, handle)
                with self.assertRaises(StoreError):
                    load_catalog(path)


class CartTest(unittest.TestCase):
    def setUp(self):
        self.cart = Cart(inventory())

    def test_tambah_dan_stok(self):
        self.cart.add("A")
        self.cart.add("A", 2)
        self.assertEqual(self.cart.count, 3)
        with self.assertRaises(StoreError) as ctx:
            self.cart.add("A")
        self.assertIn("hanya 3", str(ctx.exception))
        with self.assertRaises(StoreError) as ctx:
            self.cart.add("C")
        self.assertIn("habis", str(ctx.exception))

    def test_ubah_jumlah(self):
        self.cart.add("A")
        self.cart.set_quantity("A", 2)
        self.assertEqual(self.cart.quantities["A"], 2)
        for bad in (-1, 4):
            with self.assertRaises(StoreError):
                self.cart.set_quantity("A", bad)

    def test_total_ongkir_dan_pajak(self):
        self.assertEqual(self.cart.totals(), {"subtotal": 0, "shipping": 0, "tax": 0, "total": 0})
        self.cart.add("A")  # 65.000 < 200.000 -> ongkir 15.000
        self.assertEqual(self.cart.totals(), {"subtotal": 65000, "shipping": 15000, "tax": 7150, "total": 87150})
        self.cart.add("A", 2)
        self.cart.add("B")  # 315.000 -> gratis ongkir
        totals = self.cart.totals()
        self.assertEqual((totals["subtotal"], totals["shipping"], totals["tax"]), (315000, 0, 34650))

    def test_batalkan_pesanan(self):
        self.cart.add("A", 2)
        self.cart.add("B")
        self.cart.clear()
        self.assertEqual(self.cart.count, 0)
        self.assertEqual(list(self.cart.quantities), ["A", "B"])  # produk tetap terlihat, jumlahnya nol
        self.assertEqual(self.cart.totals()["total"], 0)


class OrderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.stock = os.path.join(self.tmp.name, "stock.json")
        self.orders = os.path.join(self.tmp.name, "orders.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_pesan(self):
        cart = Cart(inventory(self.stock))
        cart.add("A", 2)
        number = place_order(cart, ADDRESS, "", self.orders, lambda: datetime(2026, 11, 4, 10), fixed)
        self.assertEqual(number, "ORD-20261104-ABC123")
        self.assertEqual(cart.count, 0)
        with open(self.orders, encoding="utf-8") as handle:
            order = json.load(handle)[0]
        self.assertEqual(order["ship_to"], order["bill_to"])  # kirim ke kosong -> sama dengan tagihan
        self.assertEqual(order["items"], [{"id": "A", "name": "Mug", "price": 65000, "quantity": 2}])
        self.assertEqual(order["total"], 130000 + 15000 + 14300)
        self.assertEqual(inventory(self.stock).get("A").stock, 1)  # stok tersisa tersimpan

    def test_pesanan_kedua_ditambahkan(self):
        for _ in range(2):
            cart = Cart(inventory(self.stock))
            cart.add("A")
            place_order(cart, ADDRESS, ADDRESS, self.orders, token=fixed)
        with open(self.orders, encoding="utf-8") as handle:
            self.assertEqual(len(json.load(handle)), 2)

    def test_gagal_tanpa_mengubah_apa_pun(self):
        cart = Cart(inventory(self.stock))
        with self.assertRaises(StoreError):
            place_order(cart, ADDRESS, "", self.orders)  # keranjang kosong
        cart.add("A")
        for bill in ("", "Rina", "Rina\nJl."):
            with self.assertRaises(StoreError):
                place_order(cart, bill, "", self.orders)
        self.assertFalse(os.path.exists(self.orders))
        self.assertEqual(cart.count, 1)

    def test_stok_berubah_sebelum_dipesan(self):
        inv = inventory()
        cart = Cart(inv)
        cart.add("A", 3)
        inv.get("A").stock = 2  # misalnya dibeli orang lain
        with self.assertRaises(StoreError):
            place_order(cart, ADDRESS, "")
        self.assertEqual(inv.get("A").stock, 2)

    def test_rupiah(self):
        self.assertEqual(rupiah(1234567.4), "Rp1.234.567")


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.app = store.StoreApp(self.root, inventory())

    def tearDown(self):
        self.root.destroy()

    def test_navigasi_dan_keranjang(self):
        self.assertEqual(self.app.page, "landing")
        self.assertEqual(self.app.cart_button.winfo_manager(), "pack")  # tombol keranjang di beranda
        self.app.show_products()
        self.app.show_details("A")
        self.assertTrue(self.app.add_to_cart("A"))
        self.assertIn("ditambahkan", self.app.message.get())
        self.assertEqual(self.app.cart_button.cget("text"), "Keranjang (1)")
        self.assertFalse(self.app.add_to_cart("C"))
        self.app.show_cart()
        self.assertEqual(self.app.cart_button.winfo_manager(), "")
        self.app.qty_vars["A"].set("2")
        self.assertIn("Rp130.000", self.app.totals.get())
        self.assertEqual(self.app.subtotal_labels["A"].cget("text"), "Rp130.000")
        self.app.qty_vars["A"].set("9")
        self.assertIn("melebihi stok", self.app.message.get())

    def test_batal_lalu_pesan(self):
        self.app.add_to_cart("B")
        self.app.show_cart()
        self.app.cancel()
        self.assertIn("TOTAL", self.app.totals.get())
        self.assertIn("Rp0", self.app.totals.get().splitlines()[-1])
        self.app.qty_vars["B"].set("1")
        self.assertIsNone(self.app.place())  # alamat kosong
        self.app.bill.insert("1.0", ADDRESS)
        number = self.app.place()
        self.assertTrue(number.startswith("ORD-"))
        self.assertIn(number, self.app.message.get())
        self.assertEqual(self.app.page, "landing")


if __name__ == "__main__":
    unittest.main()
