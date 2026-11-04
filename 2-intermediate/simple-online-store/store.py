"""Simple Online Store: beranda, katalog produk, detail produk, dan keranjang belanja.

Inventaris dibaca dari products.json (berkas terpisah dari kode). Stok yang
tersisa setelah pesanan disimpan di ~/.app-ideas-python/store-inventory.json,
dan setiap pesanan dicatat di store-orders.json.

Jalankan:
    python store.py
"""

import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "products.json")
DATA_DIR = os.path.join(os.path.expanduser("~"), ".app-ideas-python")
TAX_RATE = 0.11  # PPN 11%
FREE_SHIPPING_FROM = 200_000
SHIPPING_FEE = 15_000


class StoreError(ValueError):
    """Kesalahan yang ditampilkan ke pengguna sebagai pesan biasa."""


@dataclass
class Product:
    id: str
    name: str
    price: int
    stock: int
    short: str
    long: str
    color: str = "#2e78c7"


def rupiah(amount):
    return "Rp" + f"{int(round(amount)):,}".replace(",", ".")


def load_catalog(path=CATALOG):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    products = []
    for raw in data:
        product = Product(**raw)
        if product.price < 0 or product.stock < 0:
            raise StoreError(f"Data produk {product.id} tidak valid.")
        products.append(product)
    if len({p.id for p in products}) != len(products):
        raise StoreError("Ada id produk yang sama di katalog.")
    return products


class Inventory:
    """Katalog + stok yang tersisa (disimpan terpisah supaya products.json tidak berubah)."""

    def __init__(self, products, stock_path=None):
        self.products = {p.id: p for p in products}
        self.stock_path = stock_path
        if stock_path and os.path.exists(stock_path):
            with open(stock_path, encoding="utf-8") as handle:
                saved = json.load(handle)
            for product_id, stock in saved.items():
                if product_id in self.products and isinstance(stock, int) and stock >= 0:
                    self.products[product_id].stock = stock

    def __iter__(self):
        return iter(self.products.values())

    def get(self, product_id):
        return self.products[product_id]

    def take(self, quantities):
        """Kurangi stok untuk satu pesanan. Gagal tanpa mengubah apa pun kalau stok tidak cukup."""
        for product_id, quantity in quantities.items():
            if quantity > self.products[product_id].stock:
                raise StoreError(f"Stok {self.products[product_id].name} tidak cukup.")
        for product_id, quantity in quantities.items():
            self.products[product_id].stock -= quantity
        if self.stock_path:
            _write_json(self.stock_path, {p.id: p.stock for p in self.products.values()})


def _write_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)
    os.replace(temp, path)


class Cart:
    def __init__(self, inventory):
        self.inventory = inventory
        self.quantities = {}  # id produk -> jumlah, urut sesuai waktu ditambahkan

    def add(self, product_id, quantity=1):
        """Tambah ke keranjang. StoreError kalau melebihi stok yang ada."""
        product = self.inventory.get(product_id)
        in_cart = self.quantities.get(product_id, 0)
        if product.stock == 0:
            raise StoreError(f"{product.name} sedang habis.")
        if in_cart + quantity > product.stock:
            raise StoreError(f"Stok {product.name} hanya {product.stock}, dan {in_cart} sudah ada di keranjang.")
        self.quantities[product_id] = in_cart + quantity

    def set_quantity(self, product_id, quantity):
        product = self.inventory.get(product_id)
        if quantity < 0:
            raise StoreError("Jumlah tidak boleh negatif.")
        if quantity > product.stock:
            raise StoreError(f"Jumlah {product.name} melebihi stok ({product.stock}).")
        self.quantities[product_id] = quantity

    def clear(self):
        """Batalkan pesanan: semua jumlah menjadi nol (produk tetap terlihat di keranjang)."""
        for product_id in self.quantities:
            self.quantities[product_id] = 0

    @property
    def count(self):
        return sum(self.quantities.values())

    def lines(self):
        return [(self.inventory.get(pid), qty) for pid, qty in self.quantities.items()]

    def totals(self):
        subtotal = sum(product.price * qty for product, qty in self.lines())
        shipping = 0 if subtotal == 0 or subtotal >= FREE_SHIPPING_FROM else SHIPPING_FEE
        tax = round(subtotal * TAX_RATE)
        return {"subtotal": subtotal, "shipping": shipping, "tax": tax, "total": subtotal + shipping + tax}


def validate_address(text, label):
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if len(lines) < 2 or len(" ".join(lines)) < 15:
        raise StoreError(f"{label} belum lengkap: tulis nama penerima dan alamat (minimal 2 baris).")
    return "\n".join(lines)


def place_order(cart, bill_to, ship_to, orders_path=None, clock=datetime.now, token=secrets.token_hex):
    """Selesaikan pesanan: cek alamat dan stok, kurangi stok, catat pesanan. Mengembalikan nomor konfirmasi."""
    items = [(product, qty) for product, qty in cart.lines() if qty > 0]
    if not items:
        raise StoreError("Keranjang masih kosong.")
    bill_to = validate_address(bill_to, "Alamat tagihan")
    ship_to = validate_address(ship_to, "Alamat pengiriman") if ship_to.strip() else bill_to
    cart.inventory.take({product.id: qty for product, qty in items})
    now = clock()
    number = f"ORD-{now:%Y%m%d}-{token(3).upper()}"
    order = {"number": number, "placed_at": now.isoformat(timespec="seconds"), "bill_to": bill_to,
             "ship_to": ship_to, "items": [{"id": p.id, "name": p.name, "price": p.price, "quantity": q}
                                           for p, q in items], **cart.totals()}
    if orders_path:
        existing = []
        if os.path.exists(orders_path):
            with open(orders_path, encoding="utf-8") as handle:
                existing = json.load(handle)
        _write_json(orders_path, existing + [order])
    cart.quantities.clear()
    return number


# --- tampilan Tkinter ---------------------------------------------------------------

def product_image(product, size=(180, 120)):
    """Gambar produk sederhana: latar berwarna dengan inisial nama produk."""
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", size, product.color)
    draw = ImageDraw.Draw(image)
    initials = "".join(word[0] for word in product.name.split()[:2]).upper()
    try:
        font = ImageFont.truetype("segoeuib.ttf", size[1] // 2)
    except OSError:
        font = ImageFont.load_default(size[1] // 2)
    draw.text((size[0] / 2, size[1] / 2), initials, font=font, fill="white", anchor="mm")
    if product.stock == 0:
        draw.rectangle((0, size[1] - 26, size[0], size[1]), fill="#1d1d1b")
        draw.text((size[0] / 2, size[1] - 13), "HABIS", font=ImageFont.load_default(14), fill="white", anchor="mm")
    return image


class StoreApp:
    def __init__(self, root, inventory, orders_path=None, clock=datetime.now):
        import tkinter as tk
        from tkinter import ttk

        self.tk, self.ttk = tk, ttk
        self.root = root
        self.inventory = inventory
        self.cart = Cart(inventory)
        self.orders_path = orders_path
        self.clock = clock
        self.images = {}
        self.page = None
        root.title("Toko Python")
        root.minsize(880, 560)
        self.bar = ttk.Frame(root, padding=(14, 10))
        self.bar.pack(fill="x")
        ttk.Button(self.bar, text="Toko Python", command=self.show_landing).pack(side="left")
        self.cart_button = ttk.Button(self.bar, command=self.show_cart)
        self.message = tk.StringVar()
        self.message_label = ttk.Label(self.bar, textvariable=self.message, foreground="#2a7d46")
        self.message_label.pack(side="left", padx=12)
        self.body = ttk.Frame(root, padding=(14, 0, 14, 14))
        self.body.pack(fill="both", expand=True)
        self.show_landing()

    # --- navigasi --------------------------------------------------------------------
    def new_page(self, name, cart_button=True):
        for child in self.body.winfo_children():
            child.destroy()
        self.page = name
        self.cart_button.pack_forget()
        if cart_button:
            self.cart_button.pack(side="right")
        self.update_cart_button()
        return self.body

    def update_cart_button(self):
        self.cart_button.configure(text=f"Keranjang ({self.cart.count})")

    def notify(self, text, error=False):
        self.message.set(text)
        self.message_label.configure(foreground="#b3261e" if error else "#2a7d46")

    def photo(self, product, size):
        from PIL import ImageTk

        key = (product.id, size, product.stock == 0)
        if key not in self.images:
            self.images[key] = ImageTk.PhotoImage(product_image(product, size), master=self.root)
        return self.images[key]

    def show_landing(self):
        ttk = self.ttk
        page = self.new_page("landing")
        hero = ttk.Frame(page, padding=40)
        hero.pack(expand=True)
        ttk.Label(hero, text="Toko Python", font=("Segoe UI", 30, "bold")).pack()
        ttk.Label(hero, text="Perlengkapan kecil untuk para Pythonista: mug, kaos, stiker, dan lainnya.",
                  font=("Segoe UI", 12), foreground="#555").pack(pady=(6, 20))
        ttk.Button(hero, text="View Products", command=self.show_products).pack(ipadx=20, ipady=6)

    def show_products(self):
        ttk, tk = self.ttk, self.tk
        page = self.new_page("products")
        ttk.Label(page, text="Produk", font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 8))
        grid = ttk.Frame(page)
        grid.pack(fill="both", expand=True)
        for index, product in enumerate(self.inventory):
            card = tk.Frame(grid, background="#ffffff", highlightthickness=1, highlightbackground="#d8d8d2",
                            padx=8, pady=8)
            card.grid(row=index // 4, column=index % 4, padx=5, pady=5, sticky="nsew")
            tk.Label(card, image=self.photo(product, (180, 64)), background="#ffffff").pack()
            tk.Label(card, text=product.name, font=("Segoe UI", 11, "bold"), background="#ffffff").pack(anchor="w")
            tk.Label(card, text=rupiah(product.price), font=("Segoe UI", 10), background="#ffffff",
                     foreground="#2e78c7").pack(anchor="w")
            tk.Label(card, text=product.short, font=("Segoe UI", 9), background="#ffffff", foreground="#555",
                     wraplength=180, justify="left", height=3, anchor="nw").pack(anchor="w", fill="x")
            ttk.Button(card, text="Select", command=lambda p=product: self.show_details(p.id)).pack(anchor="e")
        for column in range(4):
            grid.columnconfigure(column, weight=1)

    def show_details(self, product_id):
        ttk, tk = self.ttk, self.tk
        product = self.inventory.get(product_id)
        page = self.new_page("details")
        row = ttk.Frame(page)
        row.pack(fill="x", pady=10)
        tk.Label(row, image=self.photo(product, (320, 220))).pack(side="left")
        info = ttk.Frame(row, padding=(20, 0))
        info.pack(side="left", fill="both", expand=True)
        ttk.Label(info, text=product.name, font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(info, text=f"ID produk: {product.id}", foreground="#777").pack(anchor="w")
        ttk.Label(info, text=rupiah(product.price), font=("Segoe UI", 16), foreground="#2e78c7").pack(anchor="w", pady=6)
        stock = f"Stok: {product.stock}" if product.stock else "Stok habis"
        ttk.Label(info, text=stock, foreground="#2a7d46" if product.stock else "#b3261e").pack(anchor="w")
        ttk.Label(info, text=product.short, font=("Segoe UI", 11, "bold"), wraplength=460).pack(anchor="w", pady=(12, 4))
        ttk.Label(info, text=product.long, wraplength=460, justify="left").pack(anchor="w")
        buttons = ttk.Frame(info)
        buttons.pack(anchor="w", pady=16)
        ttk.Button(buttons, text="Add to Cart", command=lambda: self.add_to_cart(product.id)).pack(side="left")
        ttk.Button(buttons, text="See More Products", command=self.show_products).pack(side="left", padx=8)

    def add_to_cart(self, product_id):
        try:
            self.cart.add(product_id)
        except StoreError as error:
            self.notify(str(error), error=True)
            return False
        self.notify(f"{self.inventory.get(product_id).name} ditambahkan ke keranjang.")
        self.update_cart_button()
        return True

    def show_cart(self):
        ttk, tk = self.ttk, self.tk
        page = self.new_page("cart", cart_button=False)
        ttk.Label(page, text="Keranjang Belanja", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        table = ttk.Frame(page)
        table.pack(fill="x", pady=8)
        for column, title in enumerate(("ID", "Produk", "Harga", "Jumlah", "Subtotal")):
            ttk.Label(table, text=title, font=("Segoe UI", 10, "bold")).grid(row=0, column=column, sticky="w", padx=6)
        self.qty_vars = {}
        self.subtotal_labels = {}
        if not self.cart.quantities:
            ttk.Label(table, text="Keranjang masih kosong.", foreground="#777").grid(row=1, column=0, columnspan=5,
                                                                                 sticky="w", padx=6, pady=6)
        for row, (product, qty) in enumerate(self.cart.lines(), start=1):
            var = tk.StringVar(value=str(qty))
            self.qty_vars[product.id] = var
            for column, text in enumerate((product.id, product.name, rupiah(product.price))):
                ttk.Label(table, text=text).grid(row=row, column=column, sticky="w", padx=6, pady=3)
            spin = ttk.Spinbox(table, from_=0, to=99, width=5, textvariable=var)
            spin.grid(row=row, column=3, sticky="w", padx=6)
            var.trace_add("write", lambda *_a, p=product.id: self.change_quantity(p))
            label = ttk.Label(table, text=rupiah(product.price * qty))
            label.grid(row=row, column=4, sticky="e", padx=6)
            self.subtotal_labels[product.id] = label
        self.totals = tk.StringVar()
        ttk.Label(page, textvariable=self.totals, font=("Consolas", 11), justify="right").pack(anchor="e")
        address = ttk.Frame(page)
        address.pack(fill="x", pady=8)
        self.bill = tk.Text(address, height=4, width=40, font=("Segoe UI", 10))
        self.ship = tk.Text(address, height=4, width=40, font=("Segoe UI", 10))
        ttk.Label(address, text="Tagihan ke (nama, alamat)").grid(row=0, column=0, sticky="w")
        ttk.Label(address, text="Kirim ke (kosongkan kalau sama)").grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.bill.grid(row=1, column=0, sticky="we")
        self.ship.grid(row=1, column=1, sticky="we", padx=(12, 0))
        buttons = ttk.Frame(page)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Place Order", command=self.place).pack(side="right")
        ttk.Button(buttons, text="Cancel Order", command=self.cancel).pack(side="right", padx=8)
        ttk.Button(buttons, text="See More Products", command=self.show_products).pack(side="left")
        self.refresh_totals()

    def change_quantity(self, product_id):
        text = self.qty_vars[product_id].get().strip()
        try:
            self.cart.set_quantity(product_id, int(text or 0))
        except ValueError as error:  # StoreError adalah ValueError; int() juga
            self.notify(str(error) if isinstance(error, StoreError) else "Jumlah harus angka.", error=True)
            return
        self.notify("")
        product = self.inventory.get(product_id)
        self.subtotal_labels[product_id].configure(text=rupiah(product.price * self.cart.quantities[product_id]))
        self.refresh_totals()

    def refresh_totals(self):
        t = self.cart.totals()
        shipping = "gratis" if t["subtotal"] >= FREE_SHIPPING_FROM else rupiah(t["shipping"])
        self.totals.set(f"Subtotal {rupiah(t['subtotal']):>14}\nOngkos kirim {shipping:>10}\n"
                        f"PPN 11% {rupiah(t['tax']):>15}\nTOTAL {rupiah(t['total']):>17}")
        self.update_cart_button()

    def cancel(self):
        self.cart.clear()
        for var in self.qty_vars.values():
            var.set("0")  # memicu change_quantity, jadi subtotal per baris ikut menjadi Rp0
        self.refresh_totals()
        self.notify("Pesanan dibatalkan; jumlah dan total kembali ke nol.")

    def place(self):
        try:
            number = place_order(self.cart, self.bill.get("1.0", "end"), self.ship.get("1.0", "end"),
                                 self.orders_path, self.clock)
        except StoreError as error:
            self.notify(str(error), error=True)
            return None
        self.images.clear()  # stok berubah: gambar "HABIS" mungkin perlu diperbarui
        self.show_landing()
        self.notify(f"Pesanan berhasil! Nomor konfirmasi: {number}")
        return number


def main():
    import tkinter as tk

    inventory = Inventory(load_catalog(), os.path.join(DATA_DIR, "store-inventory.json"))
    root = tk.Tk()
    StoreApp(root, inventory, os.path.join(DATA_DIR, "store-orders.json"))
    root.mainloop()


if __name__ == "__main__":
    main()
