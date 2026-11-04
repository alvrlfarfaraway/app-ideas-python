"""Sales Receipts: kasir sederhana. Klik item, lihat struk, checkout ke database SQLite.

Setiap item yang dibeli disimpan sebagai satu baris di tabel `sales`, lengkap
dengan nomor transaksi, waktu, dan nama pelanggan. 'Daily Sales' menampilkan
semua penjualan hari ini beserta totalnya.

Jalankan:
    python sales.py                    # jendela Tkinter
    python sales.py --daily            # rekap penjualan hari ini di terminal
    python sales.py --db toko.db       # pakai berkas database lain
"""

import argparse
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime

DEFAULT_DB = os.path.join(os.path.expanduser("~"), ".app-ideas-python", "sales.db")
RECEIPT_WIDTH = 42
AUTO_CLEAR_MS = 4000


@dataclass(frozen=True)
class Item:
    number: str
    description: str
    price: int  # rupiah
    color: str


MENU = (
    Item("K01", "Kopi Susu Gula Aren", 22000, "#8a5a3b"),
    Item("K02", "Americano", 18000, "#3b2a20"),
    Item("T01", "Teh Manis", 8000, "#c9822b"),
    Item("T02", "Es Teh Lemon", 12000, "#e0b43a"),
    Item("M01", "Nasi Goreng", 28000, "#d1495b"),
    Item("M02", "Mie Ayam", 25000, "#e8871e"),
    Item("R01", "Roti Bakar Cokelat", 15000, "#6c4ab6"),
    Item("R02", "Pisang Goreng", 12000, "#edc531"),
    Item("S01", "Air Mineral", 5000, "#2e78c7"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    sold_at TEXT NOT NULL,
    customer TEXT NOT NULL DEFAULT '',
    item_number TEXT NOT NULL,
    description TEXT NOT NULL,
    unit_price INTEGER NOT NULL CHECK (unit_price >= 0)
);
CREATE INDEX IF NOT EXISTS sales_by_day ON sales (sold_at);
"""


def rupiah(amount):
    """28000 -> 'Rp28.000'."""
    return "Rp" + f"{amount:,}".replace(",", ".")


def connect(path):
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


class Register:
    """Transaksi yang sedang berjalan (belum checkout)."""

    def __init__(self):
        self.items = []

    def add(self, item):
        self.items.append(item)

    def clear_entry(self):
        """Batalkan item terakhir. Mengembalikan item itu, atau None kalau kosong."""
        return self.items.pop() if self.items else None

    def cancel_all(self):
        self.items.clear()

    @property
    def total(self):
        return sum(item.price for item in self.items)

    def checkout(self, db, customer="", clock=datetime.now):
        """Simpan semua item ke database dalam satu transaksi. Mengembalikan (nomor, waktu, item, total)."""
        if not self.items:
            raise ValueError("Belum ada item yang dibeli.")
        customer = " ".join(customer.split())[:60]
        sold_at = clock().isoformat(timespec="seconds")
        with db:  # semua item tersimpan, atau tidak sama sekali
            sale_id = db.execute("SELECT COALESCE(MAX(sale_id), 0) + 1 FROM sales").fetchone()[0]
            db.executemany(
                "INSERT INTO sales (sale_id, sold_at, customer, item_number, description, unit_price) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [(sale_id, sold_at, customer, i.number, i.description, i.price) for i in self.items])
        done = (sale_id, sold_at, list(self.items), self.total)
        self.items.clear()
        return done


def daily_sales(db, day=None):
    """Semua item terjual pada `day` (datetime.date, bawaan hari ini), urut waktu."""
    day = (day or datetime.now().date()).isoformat()
    return db.execute("SELECT * FROM sales WHERE sold_at >= ? AND sold_at < ? ORDER BY sold_at, id",
                      (day, day + "T99")).fetchall()


def clear_all(db):
    with db:
        return db.execute("DELETE FROM sales").rowcount


def receipt_lines(items, when=None, customer="", total=None, sale_id=None):
    """Teks struk lebar tetap: tanggal, item (nomor, nama, harga), dan total kalau sudah checkout."""
    width = RECEIPT_WIDTH
    lines = ["KEDAI KOPI SENJA".center(width), "=" * width]
    if when:
        lines.append(f"Waktu   : {when.replace('T', ' ')}")
    if sale_id is not None:
        lines.append(f"Nomor   : #{sale_id}")
    if customer:
        lines.append(f"Pelanggan: {customer}")
    lines.append("-" * width)
    for item in items:
        price = rupiah(item.price)
        name = item.description[:width - len(price) - 6]
        lines.append(f"{item.number} {name:<{width - len(price) - 5}}{price:>{len(price) + 1}}")
    if total is not None:
        lines.append("-" * width)
        label = "TOTAL"
        lines.append(f"{label}{rupiah(total):>{width - len(label)}}")
        lines.append("=" * width)
        lines.append("Terima kasih!".center(width))
    return lines


def daily_lines(rows, day=None):
    width = RECEIPT_WIDTH
    day = day or datetime.now().date()
    lines = [f"PENJUALAN {day:%d-%m-%Y}".center(width), "=" * width]
    if not rows:
        lines.append("Belum ada penjualan.")
        return lines
    def money_line(label, amount):
        value = rupiah(amount)
        return f"{label[:width - len(value) - 1]:<{width - len(value)}}{value}"

    sale_ids = list(dict.fromkeys(row["sale_id"] for row in rows))  # urut sesuai waktu
    for sale_id in sale_ids:
        items = [row for row in rows if row["sale_id"] == sale_id]
        who = items[0]["customer"] or "tanpa nama"
        lines.append(f"#{sale_id}  {items[0]['sold_at'][11:16]}  {who}")
        lines += [money_line(f"   {row['item_number']} {row['description']}", row["unit_price"]) for row in items]
        lines.append(money_line("   Subtotal", sum(row["unit_price"] for row in items)))
    total = sum(row["unit_price"] for row in rows)
    lines += ["-" * width, f"{len(rows)} item, {len(sale_ids)} transaksi", money_line("TOTAL", total)]
    return lines


# --- tampilan Tkinter -----------------------------------------------------------------

def item_icon(item, size=40):
    """Thumbnail sederhana: lingkaran berwarna dengan kode item (digambar Pillow)."""
    from PIL import Image, ImageDraw, ImageFont

    scale = 3
    image = Image.new("RGB", (size * scale, size * scale), "#ffffff")
    draw = ImageDraw.Draw(image)
    draw.ellipse((2, 2, size * scale - 2, size * scale - 2), fill=item.color)
    try:
        font = ImageFont.truetype("segoeuib.ttf", 15 * scale)
    except OSError:
        font = ImageFont.load_default(15 * scale)
    draw.text((size * scale / 2, size * scale / 2), item.number, font=font, fill="white", anchor="mm")
    return image.resize((size, size), Image.Resampling.LANCZOS)


class SalesApp:
    def __init__(self, root, db, menu=MENU, clock=datetime.now, confirm=None):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.root = root
        self.db = db
        self.clock = clock
        self.confirm = confirm or self._confirm
        self.register = Register()
        self.started = None
        self.clear_job = None
        self.icons = []

        root.title("Sales Receipts")
        top = ttk.Frame(root, padding=12)
        top.pack(fill="both", expand=True)
        purchase = ttk.LabelFrame(top, text="Pembelian", padding=10)
        purchase.pack(side="left", fill="y")
        ttk.Label(purchase, text="Nama pelanggan").grid(row=0, column=0, columnspan=3, sticky="w")
        self.customer = tk.StringVar()
        ttk.Entry(purchase, textvariable=self.customer).grid(row=1, column=0, columnspan=3, sticky="we", pady=(2, 10))
        from PIL import ImageTk
        for index, item in enumerate(menu):
            icon = ImageTk.PhotoImage(item_icon(item), master=root)
            self.icons.append(icon)
            button = tk.Button(purchase, image=icon, compound="top", width=150, height=110, cursor="hand2",
                               wraplength=145,
                               text=f"{item.description}\n{rupiah(item.price)}", font=("Segoe UI", 9),
                               relief="groove", background="#ffffff", command=lambda i=item: self.buy(i))
            button.grid(row=2 + index // 3, column=index % 3, padx=3, pady=3)
        self.total = tk.StringVar(value=rupiah(0))
        row = ttk.Frame(purchase)
        row.grid(row=10, column=0, columnspan=3, sticky="we", pady=(10, 0))
        ttk.Label(row, text="Total", font=("Segoe UI", 12)).pack(side="left")
        ttk.Label(row, textvariable=self.total, font=("Segoe UI", 16, "bold")).pack(side="right")
        actions = ttk.Frame(purchase)
        actions.grid(row=11, column=0, columnspan=3, sticky="we", pady=(8, 0))
        ttk.Button(actions, text="Clear Entry", command=self.clear_entry).pack(side="left")
        ttk.Button(actions, text="Cancel All", command=self.cancel_all).pack(side="left", padx=6)
        ttk.Button(actions, text="Checkout", command=self.checkout).pack(side="right")

        receipt = ttk.LabelFrame(top, text="Struk", padding=10)
        receipt.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self.receipt = tk.Text(receipt, width=RECEIPT_WIDTH + 2, height=24, font=("Consolas", 11), state="disabled",
                               background="#fffdf7")
        self.receipt.pack(fill="both", expand=True)

        bottom = ttk.Frame(root, padding=(12, 0, 12, 12))
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Daily Sales", command=self.daily).pack(side="left")
        ttk.Button(bottom, text="Clear All", command=self.clear_all).pack(side="left", padx=6)
        self.status = tk.StringVar()
        ttk.Label(bottom, textvariable=self.status, foreground="#555").pack(side="left", padx=10)

    def show(self, lines):
        self.receipt.configure(state="normal")
        self.receipt.delete("1.0", "end")
        self.receipt.insert("1.0", "\n".join(lines))
        self.receipt.configure(state="disabled")

    def refresh(self):
        if not self.register.items:
            self.started = None
        when = self.started.isoformat(timespec="seconds") if self.started else None
        self.show(receipt_lines(self.register.items, when, self.customer.get().strip()) if self.register.items else [])
        self.total.set(rupiah(self.register.total))

    def buy(self, item):
        self.cancel_auto_clear()
        if not self.register.items:
            self.started = self.clock()
        self.register.add(item)
        self.refresh()

    def clear_entry(self):
        removed = self.register.clear_entry()
        if removed:
            self.status.set(f"Dibatalkan: {removed.description}")
        self.refresh()

    def cancel_all(self):
        self.register.cancel_all()
        self.status.set("Semua pembelian dibatalkan.")
        self.refresh()

    def checkout(self):
        customer = self.customer.get().strip()
        try:
            sale_id, sold_at, items, total = self.register.checkout(self.db, customer, self.clock)
        except ValueError as error:
            self.status.set(str(error))
            return None
        self.show(receipt_lines(items, sold_at, customer, total, sale_id))
        self.total.set(rupiah(0))
        self.customer.set("")
        self.status.set(f"Transaksi #{sale_id} tersimpan ({len(items)} item). Struk dibersihkan sebentar lagi.")
        self.clear_job = self.root.after(AUTO_CLEAR_MS, self.auto_clear)
        return sale_id

    def auto_clear(self):
        self.clear_job = None
        self.show([])

    def cancel_auto_clear(self):
        if self.clear_job:
            self.root.after_cancel(self.clear_job)
            self.clear_job = None

    def daily(self):
        self.cancel_auto_clear()
        today = self.clock().date()
        self.show(daily_lines(daily_sales(self.db, today), today))

    def clear_all(self):
        if not self.confirm("Hapus SEMUA catatan penjualan dari database?"):
            return
        count = clear_all(self.db)
        self.register.cancel_all()
        self.refresh()
        self.status.set(f"{count} baris penjualan dihapus.")

    def _confirm(self, message):
        from tkinter import messagebox

        return messagebox.askyesno("Clear All", message, parent=self.root, icon="warning")


def main(argv=None, gui=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Kasir dengan struk dan database penjualan.")
    parser.add_argument("--db", default=DEFAULT_DB, help="berkas database SQLite")
    parser.add_argument("--daily", action="store_true", help="tampilkan penjualan hari ini lalu keluar")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    db = connect(args.db)
    try:
        if args.daily:
            print("\n".join(daily_lines(daily_sales(db))))
        else:
            (gui or run_gui)(db)
    finally:
        db.close()
    return 0


def run_gui(db):
    import tkinter as tk

    root = tk.Tk()
    root.resizable(False, False)
    SalesApp(root, db)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())
