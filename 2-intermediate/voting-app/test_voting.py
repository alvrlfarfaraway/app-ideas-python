import contextlib
import io
import os
import tempfile
import unittest

import voting
from voting import (
    DEFAULT_ITEMS,
    VoteError,
    add_item,
    cast_vote,
    connect,
    format_results,
    items,
    login,
    my_vote,
    register,
    results,
)


class AccountTest(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")

    def tearDown(self):
        self.db.close()

    def test_daftar_dan_masuk(self):
        uid = register(self.db, "  Rina ", "kopi-senja-2026")
        self.assertEqual(login(self.db, "rina", "kopi-senja-2026"), uid)
        self.assertEqual(login(self.db, "RINA", "kopi-senja-2026"), uid)  # nama tidak peka huruf besar

    def test_password_tidak_disimpan_apa_adanya(self):
        register(self.db, "rina", "kopi-senja-2026")
        row = self.db.execute("SELECT salt, password_hash FROM users").fetchone()
        self.assertNotIn(b"kopi-senja-2026", bytes(row["password_hash"]))
        self.assertEqual(len(row["salt"]), 16)
        register(self.db, "budi", "kopi-senja-2026")  # password sama, hash berbeda karena salt berbeda
        hashes = {bytes(r[0]) for r in self.db.execute("SELECT password_hash FROM users")}
        self.assertEqual(len(hashes), 2)

    def test_pesan_salah_sama_untuk_nama_dan_password(self):
        register(self.db, "rina", "kopi-senja-2026")
        messages = set()
        for name, password in (("rina", "salah-password"), ("hantu", "kopi-senja-2026")):
            with self.assertRaises(VoteError) as ctx:
                login(self.db, name, password)
            messages.add(str(ctx.exception))
        self.assertEqual(len(messages), 1)

    def test_aturan_akun(self):
        for name, password in (("ri", "panjang-sekali"), ("Rina Kartika", "panjang-sekali"), ("rina", "pendek"),
                               ("rinarina", "rinarina")):
            with self.assertRaises(VoteError, msg=(name, password)):
                register(self.db, name, password)
        register(self.db, "rina", "kopi-senja-2026")
        with self.assertRaises(VoteError):
            register(self.db, "RINA", "lain-lagi-123")


class VoteTest(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")
        self.rina = register(self.db, "rina", "kopi-senja-2026")
        self.budi = register(self.db, "budi", "teh-manis-2026")

    def tearDown(self):
        self.db.close()

    def test_pilihan_bawaan(self):
        self.assertEqual([r["name"] for r in items(self.db)], list(DEFAULT_ITEMS))

    def test_satu_suara_per_akun_boleh_diganti(self):
        self.assertFalse(cast_vote(self.db, self.rina, 1))
        self.assertTrue(cast_vote(self.db, self.rina, 3))
        self.assertFalse(cast_vote(self.db, self.rina, 3))
        self.assertEqual(my_vote(self.db, self.rina), 3)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM votes").fetchone()[0], 1)

    def test_harus_masuk_dan_pilihan_harus_ada(self):
        with self.assertRaises(VoteError):
            cast_vote(self.db, None, 1)
        with self.assertRaises(VoteError):
            cast_vote(self.db, self.rina, 99)

    def test_hasil(self):
        cast_vote(self.db, self.rina, 1)
        cast_vote(self.db, self.budi, 1)
        rows = results(self.db)
        self.assertEqual(rows[0], (1, "Python", 2, 100.0))
        self.assertEqual(sum(r[2] for r in rows), 2)
        self.assertEqual(len(rows), len(DEFAULT_ITEMS))  # pilihan tanpa suara tetap ada
        self.assertIn("Total 2 suara", format_results(rows))

    def test_tambah_pilihan(self):
        add_item(self.db, "  Kotlin ")
        self.assertEqual(items(self.db)[-1]["name"], "Kotlin")
        with self.assertRaises(VoteError):
            add_item(self.db, "python")  # sudah ada (tidak peka huruf besar)
        with self.assertRaises(VoteError):
            add_item(self.db, " ")

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "v.db")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(voting.main(["--db", path, "--add-item", "Kotlin"]), 0)
                self.assertEqual(voting.main(["--db", path, "--results"]), 0)
            self.assertIn("Kotlin", out.getvalue())
            self.assertIn("Total 0 suara", out.getvalue())


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.db = connect(":memory:")
        self.app = voting.VotingApp(self.root, self.db)

    def tearDown(self):
        self.root.destroy()
        self.db.close()

    def bars(self):
        return [w for row in self.app.body.winfo_children() for w in row.winfo_children() if w.winfo_class() == "Canvas"]

    def test_tanpa_login_tidak_bisa_memilih_dan_hasil_tersembunyi(self):
        self.assertFalse(self.app.vote(1))
        self.assertIn("Masuk dulu", self.app.status.get())
        self.assertEqual(self.bars(), [])

    def test_daftar_pilih_lalu_lihat_hasil(self):
        self.app.user_var.set("rina")
        self.app.pass_var.set("kopi-senja-2026")
        self.assertTrue(self.app.do_register())
        self.assertEqual(self.bars(), [])  # belum memilih: hasil belum terlihat
        self.assertTrue(self.app.vote(2))
        self.assertEqual(len(self.bars()), len(DEFAULT_ITEMS))
        self.assertIn("JavaScript", self.app.status.get())
        self.app.logout()
        self.assertIsNone(self.app.user_id)
        self.app.user_var.set("rina")
        self.app.pass_var.set("salah-password")
        self.assertFalse(self.app.do_login())
        self.assertIn("salah", self.app.status.get())


if __name__ == "__main__":
    unittest.main()
