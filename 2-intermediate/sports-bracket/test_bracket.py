import os
import tempfile
import unittest
from datetime import date

import bracket
from bracket import BYE, BracketError, Tournament, load, round_names, save


def make(count=8):
    return Tournament.create("Piala Kampus", "16-11-2026", "29-11-2026", count)


class CreateTest(unittest.TestCase):
    def test_data_benar(self):
        t = make(8)
        self.assertEqual((t.name, t.start, t.end), ("Piala Kampus", date(2026, 11, 16), date(2026, 11, 29)))
        self.assertEqual(t.teams[0], "Tim 1")
        self.assertEqual((t.size, t.rounds), (8, 3))

    def test_peringatan(self):
        cases = {("", "16-11-2026", "29-11-2026", 8): "nama",
                 ("A", "31-02-2026", "29-11-2026", 8): "Tanggal mulai",
                 ("A", "16-11-2026", "2026-11-29", 8): "Tanggal selesai",
                 ("A", "29-11-2026", "16-11-2026", 8): "sebelum",
                 ("A", "16-11-2026", "29-11-2026", 7): "ganjil",
                 ("A", "16-11-2026", "29-11-2026", "x"): "angka",
                 ("A", "16-11-2026", "29-11-2026", 0): "minimal 2",
                 ("A", "16-11-2026", "29-11-2026", 66): "Maksimal"}
        for args, text in cases.items():
            with self.assertRaises(BracketError) as ctx:
                Tournament.create(*args)
            self.assertIn(text, str(ctx.exception), args)

    def test_nama_babak(self):
        self.assertEqual(round_names(4), ["Babak 1", "Perempat final", "Semifinal", "Final"])
        self.assertEqual(round_names(1), ["Final"])


class StructureTest(unittest.TestCase):
    def test_pangkat_dua_tanpa_bye(self):
        t = make(8)
        self.assertEqual(t.slots(), list(range(8)))
        self.assertEqual([t.matches_in(r) for r in range(3)], [4, 2, 1])

    def test_bye_untuk_jumlah_bukan_pangkat_dua(self):
        t = make(6)
        self.assertEqual(t.slots(), [0, BYE, 1, BYE, 2, 3, 4, 5])
        self.assertTrue(t.is_bye(0, 0))
        self.assertEqual(t.winner(0, 0), 0)  # bye langsung lolos
        self.assertEqual(t.participants(1, 0), (0, 1))
        for n in range(2, 65, 2):
            slots = make(n).slots()
            self.assertEqual(sorted(s for s in slots if s is not BYE), list(range(n)))
            self.assertTrue(all(slots[i] is not BYE for i in range(0, len(slots), 2)))  # tidak ada bye lawan bye


class ResultTest(unittest.TestCase):
    def test_pemenang_maju_sampai_juara(self):
        t = make(4)
        t.set_result(0, 0, "16-11-2026", 2, 1)
        t.set_result(0, 1, "", 0, 3)
        self.assertEqual(t.participants(1, 0), (0, 3))
        self.assertIsNone(t.champion)
        t.set_result(1, 0, "29-11-2026", 1, 4)
        self.assertEqual(t.champion, "Tim 4")
        self.assertEqual(t.data(1, 0)["date"], "29-11-2026")

    def test_aturan_skor_dan_tanggal(self):
        t = make(4)
        for args, text in (((0, 0, "", 1, 1), "seri"), ((0, 0, "", 1, None), "kedua tim"),
                           ((0, 0, "", -1, 2), "0 atau lebih"), ((0, 0, "01-12-2026", 1, 0), "antara"),
                           ((0, 0, "1/12/26", 1, 0), "tidak valid"), ((1, 0, "", 1, 0), "belum diketahui")):
            with self.assertRaises(BracketError) as ctx:
                t.set_result(*args)
            self.assertIn(text, str(ctx.exception), args)
        with self.assertRaises(BracketError):
            make(6).set_result(0, 0, "", 1, 0)  # pertandingan bye

    def test_mengubah_skor_membatalkan_babak_berikutnya(self):
        t = make(4)
        t.set_result(0, 0, "", 2, 1)
        t.set_result(0, 1, "", 0, 3)
        t.set_result(1, 0, "", 1, 0)
        self.assertEqual(t.champion, "Tim 1")
        t.set_result(0, 0, "", 0, 5)  # pemenang babak 1 berubah
        self.assertIsNone(t.champion)
        self.assertIsNone(t.data(1, 0)["score_a"])
        t.set_result(0, 1, "", 1, 3)  # pemenang sama: babak berikutnya tidak disentuh
        self.assertEqual(t.participants(1, 0), (1, 3))

    def test_nama_tim(self):
        t = make(4)
        t.rename_team(0, "  Teknik  Sipil ")
        self.assertEqual(t.teams[0], "Teknik Sipil")
        with self.assertRaises(BracketError):
            t.rename_team(1, "teknik sipil")
        with self.assertRaises(BracketError):
            t.rename_team(1, " ")


class SaveTest(unittest.TestCase):
    def test_tersimpan_antar_sesi(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sub", "b.json")
            self.assertIsNone(load(path))
            t = make(4)
            t.rename_team(0, "Teknik")
            t.set_result(0, 0, "16-11-2026", 2, 1)
            save(t, path)
            again = load(path)
            self.assertEqual(again.teams[0], "Teknik")
            self.assertEqual(again.winner(0, 0), 0)
            self.assertEqual(again.start, date(2026, 11, 16))
            with open(path, "w") as handle:
                handle.write("{rusak")
            with self.assertRaises(BracketError):
                load(path)


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "b.json")
        self.notes = []
        self.app = bracket.BracketApp(self.root, save_path=self.path, notify=self.notes.append)

    def tearDown(self):
        self.root.destroy()
        self.tmp.cleanup()

    def test_peringatan_di_formulir(self):
        self.app.count.set("5")
        self.assertIsNone(self.app.create())
        self.assertIn("ganjil", self.app.warning.get())
        self.app.count.set("4")
        self.app.end.set("99-99-2026")
        self.assertIsNone(self.app.create())
        self.assertIn("Tanggal selesai", self.app.warning.get())

    def test_isi_pertandingan_dan_simpan(self):
        self.app.count.set("4")
        self.app.create()
        self.assertTrue(self.app.update_match(0, 0, "Teknik", "Hukum", "16-11-2026", "2", "1"))
        self.assertFalse(self.app.update_match(0, 1, None, None, "", "x", "1"))
        self.assertIn("angka", self.notes[-1])
        self.assertTrue(self.app.canvas.find_withtag("match-1-0"))
        reopened = bracket.BracketApp(self.root, save_path=self.path, notify=self.notes.append)
        self.assertEqual(reopened.tournament.teams[:2], ["Teknik", "Hukum"])
        self.assertEqual(reopened.count.get(), "4")


if __name__ == "__main__":
    unittest.main()
