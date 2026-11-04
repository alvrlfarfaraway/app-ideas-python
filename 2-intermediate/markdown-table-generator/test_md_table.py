import contextlib
import io
import os
import tempfile
import unittest

import mistune

import md_table
from md_table import Table, display_width, escape_cell, main, parse_aligns

TO_HTML = mistune.create_markdown(plugins=["table"])


def sample():
    return Table.from_rows([["Kota", "Provinsi"], ["Surabaya", "Jawa Timur"], ["Medan", "Sumatera Utara"]])


class WidthTest(unittest.TestCase):
    def test_lebar_tampilan(self):
        self.assertEqual(display_width("abc"), 3)
        self.assertEqual(display_width("東京"), 4)
        self.assertEqual(display_width("é"), 1)
        self.assertEqual(display_width("é"), 1)  # huruf + tanda aksen gabung

    def test_escape(self):
        self.assertEqual(escape_cell(" a | b "), "a \\| b")
        self.assertEqual(escape_cell("a \\| b"), "a \\| b")  # tidak di-escape dua kali
        self.assertEqual(escape_cell("baris 1\nbaris 2"), "baris 1<br>baris 2")
        self.assertEqual(escape_cell(42), "42")


class MarkdownTest(unittest.TestCase):
    def test_tabel_rapi(self):
        self.assertEqual(sample().to_markdown(), "\n".join([
            "| Kota     | Provinsi       |",
            "| -------- | -------------- |",
            "| Surabaya | Jawa Timur     |",
            "| Medan    | Sumatera Utara |",
        ]))

    def test_perataan(self):
        table = sample()
        table.align_col(0, "right")
        table.align_col(1, "center")
        self.assertEqual(table.to_markdown().splitlines()[1], "| -------: | :------------: |")
        self.assertEqual(table.to_markdown().splitlines()[2], "| Surabaya |   Jawa Timur   |")
        table.align_all("left")
        self.assertEqual(table.to_markdown().splitlines()[1], "| :------- | :------------- |")

    def test_kolom_pendek_tetap_tiga_garis(self):
        table = Table.from_rows([["a", "b"], ["1", "2"]])
        table.align_col(1, "center")
        self.assertEqual(table.to_markdown().splitlines()[1], "| --- | :-: |")

    def test_tanpa_padding(self):
        self.assertEqual(sample().to_markdown(pad=False).splitlines()[2], "| Surabaya | Jawa Timur |")

    def test_huruf_lebar_tetap_lurus(self):
        table = Table.from_rows([["Kota", "x"], ["東京", "y"], ["Paris", "z"]])
        lines = table.to_markdown().splitlines()
        self.assertEqual(len({display_width(line) for line in lines}), 1)

    def test_hasil_dibaca_parser_markdown(self):
        table = Table.from_rows([["A", "B|C"], ["1", "2"], ["", "kosong"]])
        table.align_col(0, "right")
        html = TO_HTML(table.to_markdown())
        self.assertIn('<th style="text-align:right">A</th>', html)
        self.assertIn("<th>B|C</th>", html)
        self.assertEqual(html.count("<tr>"), 3)


class EditTest(unittest.TestCase):
    def test_sisip_dan_hapus(self):
        table = sample()
        table.insert_row(1)
        self.assertEqual(table.rows[1], ["", ""])
        table.insert_col(1)
        self.assertEqual(table.rows[0], ["Kota", "", "Provinsi"])
        self.assertEqual(table.aligns, ["none", "none", "none"])
        table.align_col(2, "right")
        table.delete_col(1)
        self.assertEqual(table.aligns, ["none", "right"])  # perataan ikut bergeser
        table.delete_row(1)
        self.assertEqual(table.rows, sample().rows)

    def test_perataan_ikut_bergeser_saat_kolom_disisipkan(self):
        table = sample()
        table.align_col(1, "right")
        table.insert_col(0)
        self.assertEqual(table.aligns, ["none", "none", "right"])
        self.assertEqual(table.rows[1], ["", "Surabaya", "Jawa Timur"])

    def test_posisi_di_luar_batas_dijepit(self):
        table = sample()
        table.insert_row(99)
        self.assertEqual(table.row_count, 4)
        self.assertEqual(table.rows[-1], ["", ""])
        table.insert_col(-5)
        self.assertEqual(table.rows[0][0], "")

    def test_batas(self):
        table = Table(1, 1)
        with self.assertRaises(ValueError):
            table.delete_row(0)
        with self.assertRaises(ValueError):
            table.delete_col(0)
        with self.assertRaises(ValueError):
            Table(0, 3)
        with self.assertRaises(ValueError):
            table.align_col(0, "justify")

    def test_from_rows_mengisi_baris_pendek(self):
        table = Table.from_rows([["a", "b", "c"], ["1"]])
        self.assertEqual(table.rows[1], ["1", "", ""])


class AlignArgTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_aligns("l,c,r", 3), ["left", "center", "right"])
        self.assertEqual(parse_aligns("c", 2), ["center", "center"])
        self.assertEqual(parse_aligns("right, n", 2), ["right", "none"])
        for bad, count in (("l,c", 3), ("x", 1)):
            with self.assertRaises(ValueError):
                parse_aligns(bad, count)


class CliTest(unittest.TestCase):
    def test_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.csv")
            with open(path, "w", encoding="utf-8-sig", newline="") as handle:
                handle.write('Kota,Catatan\nMedan,"ada, koma"\n\nBali,"a | b"\n')
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main([path, "--align", "l,r"]), 0)
            lines = out.getvalue().splitlines()
            self.assertEqual(lines[0], "| Kota  |   Catatan |")  # BOM dari Excel dibuang
            self.assertEqual(lines[1], "| :---- | --------: |")
            self.assertEqual(lines[2], "| Medan | ada, koma |")
            self.assertEqual(lines[3], "| Bali  |    a \\| b |")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main([path, "--align", "l,c,r"]), 1)
                self.assertEqual(main([os.path.join(tmp, "hilang.csv")]), 1)

    def test_tanpa_argumen_membuka_jendela(self):
        opened = []
        self.assertEqual(main([], gui=lambda: opened.append(1)), 0)
        self.assertEqual(opened, [1])


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.app = md_table.TableApp(self.root, Table(2, 2))

    def tearDown(self):
        self.root.destroy()

    def markdown(self):
        return self.app.output.get("1.0", "end-1c")

    def test_ketik_langsung_tergenerate(self):
        self.app.vars[0][0].set("Nama")
        self.app.vars[1][0].set("Sari")
        self.assertIn("| Nama |", self.markdown())
        self.assertIn("| Sari |", self.markdown())
        self.assertEqual(len(self.app.preview.winfo_children()), 4)

    def test_menu_sisip_hapus_dan_rata(self):
        self.app.focus = (0, 1)
        self.app.edit("col", 1)
        self.assertEqual(self.app.table.col_count, 3)
        self.assertEqual(self.app.cols_var.get(), 3)
        self.app.align_col("center")
        self.assertIn(":-:", self.markdown())
        self.app.focus = (1, 0)
        self.app.edit("delrow")
        self.app.edit("delrow")  # baris terakhir tidak bisa dihapus
        self.assertEqual(self.app.table.row_count, 1)
        self.assertIn("tidak bisa", self.app.status.get())

    def test_buat_baru_dan_salin(self):
        self.app.rows_var.set(4)
        self.app.cols_var.set(5)
        self.app.new_table()
        self.assertEqual((self.app.table.row_count, self.app.table.col_count), (4, 5))
        self.app.copy()
        self.assertEqual(self.root.clipboard_get(), self.markdown())


if __name__ == "__main__":
    unittest.main()
