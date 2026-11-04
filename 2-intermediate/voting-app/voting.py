"""Voting App: daftar pilihan dengan tombol suara, hasilnya terlihat setelah memilih.

Pilihan, akun pengguna, dan suara disimpan di SQLite. Hanya pengguna yang
sudah masuk (login) yang bisa memilih, dan setiap akun punya satu suara
(boleh diganti). Password tidak disimpan apa adanya, melainkan sebagai hash
PBKDF2-SHA256 dengan salt acak per akun.

Jalankan:
    python voting.py                         # jendela Tkinter
    python voting.py --results               # hasil di terminal
    python voting.py --add-item "Kotlin"     # tambah pilihan
"""

import argparse
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import sys
from datetime import datetime

DEFAULT_DB = os.path.join(os.path.expanduser("~"), ".app-ideas-python", "voting.db")
QUESTION = "Bahasa pemrograman apa yang paling enak untuk mulai belajar?"
DEFAULT_ITEMS = ("Python", "JavaScript", "Go", "Java", "C", "Rust")
PBKDF2_ROUNDS = 200_000
USERNAME_RE = re.compile(r"^[a-z0-9_.]{3,20}$")
MIN_PASSWORD = 8

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE COLLATE NOCASE);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
    salt BLOB NOT NULL, password_hash BLOB NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS votes (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,  -- satu suara per akun
    item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    voted_at TEXT NOT NULL);
"""


class VoteError(ValueError):
    """Kesalahan yang ditampilkan ke pengguna."""


def connect(path, seed=True):
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA)
    if seed and db.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 0:
        with db:
            db.executemany("INSERT INTO items (name) VALUES (?)", [(name,) for name in DEFAULT_ITEMS])
    return db


# --- akun ------------------------------------------------------------------------

def hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)


def register(db, username, password, clock=datetime.now):
    username = username.strip().lower()
    if not USERNAME_RE.match(username):
        raise VoteError("Nama pengguna 3-20 karakter: huruf kecil, angka, titik, atau garis bawah.")
    if len(password) < MIN_PASSWORD:
        raise VoteError(f"Password minimal {MIN_PASSWORD} karakter.")
    if password.lower() == username:
        raise VoteError("Password tidak boleh sama dengan nama pengguna.")
    salt = secrets.token_bytes(16)
    try:
        with db:
            cursor = db.execute("INSERT INTO users (username, salt, password_hash, created_at) VALUES (?, ?, ?, ?)",
                                (username, salt, hash_password(password, salt), clock().isoformat(timespec="seconds")))
    except sqlite3.IntegrityError:
        raise VoteError(f"Nama pengguna '{username}' sudah dipakai.") from None
    return cursor.lastrowid


def login(db, username, password):
    """id pengguna kalau nama dan password cocok. Pesan error sama untuk keduanya, supaya tidak membocorkan akun."""
    row = db.execute("SELECT id, salt, password_hash FROM users WHERE username = ?",
                     (username.strip().lower(),)).fetchone()
    if row is None:
        hash_password(password, b"\0" * 16)  # waktu proses tetap sama walau akunnya tidak ada
        raise VoteError("Nama pengguna atau password salah.")
    if not hmac.compare_digest(hash_password(password, row["salt"]), row["password_hash"]):
        raise VoteError("Nama pengguna atau password salah.")
    return row["id"]


# --- pilihan dan suara ------------------------------------------------------------

def items(db):
    return db.execute("SELECT id, name FROM items ORDER BY id").fetchall()


def add_item(db, name):
    name = " ".join(name.split())
    if not name or len(name) > 40:
        raise VoteError("Nama pilihan 1-40 karakter.")
    try:
        with db:
            return db.execute("INSERT INTO items (name) VALUES (?)", (name,)).lastrowid
    except sqlite3.IntegrityError:
        raise VoteError(f"Pilihan '{name}' sudah ada.") from None


def cast_vote(db, user_id, item_id, clock=datetime.now):
    """Simpan (atau ganti) suara pengguna. Mengembalikan True kalau suara sebelumnya diganti."""
    if user_id is None:
        raise VoteError("Masuk dulu untuk memilih.")
    if db.execute("SELECT 1 FROM items WHERE id = ?", (item_id,)).fetchone() is None:
        raise VoteError("Pilihan itu tidak ada.")
    previous = my_vote(db, user_id)
    with db:
        db.execute("""INSERT INTO votes (user_id, item_id, voted_at) VALUES (?, ?, ?)
                      ON CONFLICT(user_id) DO UPDATE SET item_id = excluded.item_id, voted_at = excluded.voted_at""",
                   (user_id, item_id, clock().isoformat(timespec="seconds")))
    return previous is not None and previous != item_id


def my_vote(db, user_id):
    row = db.execute("SELECT item_id FROM votes WHERE user_id = ?", (user_id,)).fetchone()
    return row["item_id"] if row else None


def results(db):
    """[(id, nama, suara, persen)] urut suara terbanyak, lalu urutan pilihan."""
    rows = db.execute("""SELECT i.id, i.name, COUNT(v.user_id) AS votes FROM items i
                         LEFT JOIN votes v ON v.item_id = i.id GROUP BY i.id ORDER BY votes DESC, i.id""").fetchall()
    total = sum(r["votes"] for r in rows)
    return [(r["id"], r["name"], r["votes"], 100 * r["votes"] / total if total else 0.0) for r in rows]


def format_results(rows):
    total = sum(r[2] for r in rows)
    width = max((len(r[1]) for r in rows), default=5)
    lines = [QUESTION, ""]
    for _, name, votes, percent in rows:
        bar = "#" * round(percent / 5)
        lines.append(f"{name:<{width}}  {bar:<20} {votes:>3} ({percent:4.1f}%)")
    lines.append(f"\nTotal {total} suara")
    return "\n".join(lines)


# --- tampilan Tkinter ------------------------------------------------------------------

class VotingApp:
    def __init__(self, root, db):
        import tkinter as tk
        from tkinter import ttk

        self.tk, self.ttk = tk, ttk
        self.root = root
        self.db = db
        self.user_id = None
        self.username = None
        root.title("Voting App")
        root.minsize(560, 0)
        self.account = ttk.Frame(root, padding=(14, 10))
        self.account.pack(fill="x")
        self.body = ttk.Frame(root, padding=(14, 0, 14, 14))
        self.body.pack(fill="both", expand=True)
        self.status = tk.StringVar()
        self.render()

    def clear(self, frame):
        for child in frame.winfo_children():
            child.destroy()

    def render(self):
        self.render_account()
        self.render_items()

    def render_account(self):
        ttk, tk = self.ttk, self.tk
        self.clear(self.account)
        if self.user_id:
            ttk.Label(self.account, text=f"Masuk sebagai {self.username}").pack(side="left")
            ttk.Button(self.account, text="Keluar", command=self.logout).pack(side="right")
            return
        self.user_var = tk.StringVar()
        self.pass_var = tk.StringVar()
        ttk.Label(self.account, text="Nama").pack(side="left")
        ttk.Entry(self.account, textvariable=self.user_var, width=14).pack(side="left", padx=(4, 10))
        ttk.Label(self.account, text="Password").pack(side="left")
        entry = ttk.Entry(self.account, textvariable=self.pass_var, width=14, show="•")
        entry.pack(side="left", padx=(4, 10))
        entry.bind("<Return>", lambda _e: self.do_login())
        ttk.Button(self.account, text="Masuk", command=self.do_login).pack(side="left")
        ttk.Button(self.account, text="Daftar", command=self.do_register).pack(side="left", padx=4)

    def render_items(self):
        ttk, tk = self.ttk, self.tk
        self.clear(self.body)
        ttk.Label(self.body, text=QUESTION, font=("Segoe UI", 13, "bold"), wraplength=520).pack(anchor="w", pady=(4, 8))
        voted = my_vote(self.db, self.user_id) if self.user_id else None
        show_results = voted is not None
        rows = {r[0]: r for r in results(self.db)} if show_results else {}
        for item in items(self.db):
            row = ttk.Frame(self.body)
            row.pack(fill="x", pady=3)
            mine = item["id"] == voted
            button = ttk.Button(row, text="✓ Pilihanmu" if mine else "Pilih", width=12,
                                command=lambda i=item["id"]: self.vote(i))
            if not self.user_id or mine:
                button.state(["disabled"])
            button.pack(side="left")
            ttk.Label(row, text=item["name"], font=("Segoe UI", 11, "bold" if mine else "normal"), width=14).pack(
                side="left", padx=8)
            if show_results:
                _, _, votes, percent = rows[item["id"]]
                bar = tk.Canvas(row, width=220, height=16, highlightthickness=0, background="#e9e6df")
                bar.create_rectangle(0, 0, 220 * percent / 100, 16, fill="#2a9d55" if mine else "#2e78c7", outline="")
                bar.pack(side="left")
                ttk.Label(row, text=f"{votes} suara ({percent:.0f}%)", foreground="#555").pack(side="left", padx=8)
        if not self.user_id:
            self.status.set(self.status.get() or "Masuk atau daftar dulu untuk memilih. Hasil terlihat setelah memilih.")
        elif show_results:
            total = sum(r[2] for r in rows.values())
            self.status.set(self.status.get() or f"Total {total} suara. Kamu boleh mengganti pilihan.")
        ttk.Label(self.body, textvariable=self.status, foreground="#555", wraplength=520).pack(anchor="w", pady=(10, 0))

    def say(self, message):
        self.status.set(message)

    def do_login(self):
        try:
            self.user_id = login(self.db, self.user_var.get(), self.pass_var.get())
        except VoteError as error:
            self.say(str(error))
            self.render_items()
            return False
        self.username = self.user_var.get().strip().lower()
        self.say("")
        self.render()
        return True

    def do_register(self):
        try:
            register(self.db, self.user_var.get(), self.pass_var.get())
        except VoteError as error:
            self.say(str(error))
            self.render_items()
            return False
        return self.do_login()

    def logout(self):
        self.user_id = self.username = None
        self.say("")
        self.render()

    def vote(self, item_id):
        try:
            changed = cast_vote(self.db, self.user_id, item_id)
        except VoteError as error:
            self.say(str(error))
            return False
        name = next(i["name"] for i in items(self.db) if i["id"] == item_id)
        self.say(f"Pilihan diganti ke {name}." if changed else f"Terima kasih! Suaramu untuk {name} tercatat.")
        self.render_items()
        return True


def main(argv=None, gui=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Aplikasi pemungutan suara.")
    parser.add_argument("--db", default=DEFAULT_DB, help="berkas database SQLite")
    parser.add_argument("--results", action="store_true", help="tampilkan hasil lalu keluar")
    parser.add_argument("--add-item", help="tambah pilihan baru")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    db = connect(args.db)
    try:
        if args.add_item:
            add_item(db, args.add_item)
            print(f"Pilihan '{args.add_item}' ditambahkan.")
        elif args.results:
            print(format_results(results(db)))
        else:
            (gui or run_gui)(db)
    except VoteError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    finally:
        db.close()
    return 0


def run_gui(db):
    import tkinter as tk

    root = tk.Tk()
    VotingApp(root, db)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())
