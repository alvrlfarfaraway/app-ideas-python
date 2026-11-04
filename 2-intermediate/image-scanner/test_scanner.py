import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest

import scanner
from scanner import (
    History,
    ScanError,
    extract,
    guess_name,
    main,
    normalize_phone,
    ocr,
    parse_tags,
    vcard,
)

CARD = ["Rina Kartika", "Desainer Produk - Studio Kopi Senja", "Telp: +62 812-3456-7890",
        "Kantor: (021) 555-0123", "Email: rina.kartika@kopisenja.co.id", "Web: https://kopisenja.co.id/tim",
        "www.example.org"]


class ExtractTest(unittest.TestCase):
    def test_kartu_nama(self):
        self.assertEqual(extract(CARD), {
            "phones": ["+62 812-3456-7890", "(021) 555-0123"],
            "emails": ["rina.kartika@kopisenja.co.id"],
            "links": ["https://kopisenja.co.id/tim", "www.example.org"],
        })

    def test_telepon(self):
        found = extract(["Hubungi 0812 3456 7890 atau (0274) 512-345", "WA: +62-821-1111-2222.",
                         "Tanggal 2026-11-04 atau 04-11-2026, harga Rp 150.000, kode 08123",
                         "fax 021.555.0199"])
        self.assertEqual(found["phones"], ["0812 3456 7890", "(0274) 512-345", "+62-821-1111-2222", "021.555.0199"])

    def test_telepon_ganda_dengan_format_beda_digabung(self):
        self.assertEqual(extract(["0812-3456-7890", "0812 3456 7890"])["phones"], ["0812-3456-7890"])

    def test_tautan(self):
        found = extract(["kunjungi github.com/alvrl dan https://x.dev/a?b=1).", "Daftar: bit.ly/python-jogja",
                         "foto.jpg jam 09.00 v1.2.3 Mr.Smith", "tokoku.id", "HTTPS://KOPISENJA.CO.ID/tim/"])
        self.assertEqual(found["links"], ["https://x.dev/a?b=1", "HTTPS://KOPISENJA.CO.ID/tim/", "github.com/alvrl",
                                          "bit.ly/python-jogja", "tokoku.id"])

    def test_email_bukan_tautan(self):
        found = extract(["mail: a.b@c.co.id, A.B@C.CO.ID", "panitia@pyjogja.org."])
        self.assertEqual(found["emails"], ["a.b@c.co.id", "panitia@pyjogja.org"])
        self.assertEqual(found["links"], [])

    def test_kosong(self):
        self.assertEqual(extract([]), {"phones": [], "emails": [], "links": []})

    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("+62 812-3456-7890"), "+6281234567890")
        self.assertEqual(normalize_phone("(021) 555-0123"), "0215550123")

    def test_guess_name(self):
        self.assertEqual(guess_name(CARD), "Rina Kartika")
        self.assertEqual(guess_name(["123 Jalan", "Budi Santoso", "08123456789"]), "Budi Santoso")
        self.assertEqual(guess_name(["0812", "a@b.co"]), "Kontak baru")


class VcardTest(unittest.TestCase):
    def test_format(self):
        text = vcard("Rina Kartika", ["+62 812-3456-7890"], ["rina@x.id"], ["www.example.org"])
        self.assertTrue(text.startswith("BEGIN:VCARD\r\nVERSION:3.0\r\n"))
        self.assertIn("FN:Rina Kartika\r\n", text)
        self.assertIn("N:Kartika;Rina;;;\r\n", text)
        self.assertIn("TEL;TYPE=CELL:+6281234567890\r\n", text)
        self.assertIn("EMAIL;TYPE=INTERNET:rina@x.id\r\n", text)
        self.assertIn("URL:https://www.example.org\r\n", text)
        self.assertTrue(text.endswith("END:VCARD\r\n"))

    def test_escape_dan_nama_tunggal(self):
        text = vcard("Toko; Kopi, Senja")
        self.assertIn("FN:Toko\\; Kopi\\, Senja", text)
        self.assertIn("N:Senja;Toko\\; Kopi\\,;;;", text)
        self.assertIn("N:Senja;;;;", vcard("Senja"))
        self.assertIn("FN:Kontak baru", vcard("  "))


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "h.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_tambah_tag_dan_cari(self):
        history = History(self.path, clock=lambda: "2026-11-04T10:00:00")
        a = history.add("kartu.jpg", CARD, extract(CARD), parse_tags("Kerja, kopi kerja"))
        b = history.add("poster.jpg", [], extract([]))
        self.assertEqual(a["tags"], ["kerja", "kopi"])
        self.assertEqual([e["id"] for e in history.search()], [b["id"], a["id"]])
        self.assertEqual([e["id"] for e in history.search("KOPI")], [a["id"]])
        history.set_tags(b["id"], ["acara"])
        again = History(self.path)
        self.assertEqual([e["source"] for e in again.search("acara")], ["poster.jpg"])
        self.assertEqual(again.entries[0]["phones"], ["+62 812-3456-7890", "(021) 555-0123"])
        with self.assertRaises(ScanError):
            again.set_tags(99, [])

    def test_berkas_rusak_tidak_ditimpa(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("{rusak")
        with self.assertRaises(ScanError):
            History(self.path)
        with open(self.path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "{rusak")


class FakeRun:
    def __init__(self, returncode=0, stdout=b"", stderr=b""):
        self.result = subprocess.CompletedProcess([], returncode, stdout, stderr)
        self.commands = []

    def __call__(self, command, **kwargs):
        self.commands.append(command)
        return self.result


class OcrWrapperTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.image = os.path.join(self.tmp.name, "a.jpg")
        open(self.image, "wb").close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_membaca_json(self):
        run = FakeRun(stdout=json.dumps({"lines": ["satu", "dua"], "language": "en-US"}).encode())
        self.assertEqual(ocr(self.image, run), ["satu", "dua"])
        self.assertIn("windows_ocr.ps1", run.commands[0][run.commands[0].index("-File") + 1])
        self.assertEqual(ocr(self.image, FakeRun(stdout=b'\xef\xbb\xbf{"lines": "satu"}')), ["satu"])
        self.assertEqual(ocr(self.image, FakeRun(stdout=b'{"lines": null}')), [])

    def test_gagal(self):
        with self.assertRaises(ScanError) as ctx:
            ocr(self.image, FakeRun(returncode=1, stderr=b"\nTidak ada bahasa OCR\n"))
        self.assertIn("Tidak ada bahasa OCR", str(ctx.exception))
        with self.assertRaises(ScanError):
            ocr(self.image, FakeRun(stdout=b"bukan json"))
        with self.assertRaises(ScanError):
            ocr(os.path.join(self.tmp.name, "hilang.jpg"), FakeRun())
        text = os.path.join(self.tmp.name, "catatan.txt")
        open(text, "w").close()
        with self.assertRaises(ScanError):
            ocr(text, FakeRun())


@unittest.skipUnless(os.name == "nt", "OCR bawaan hanya ada di Windows")
class WindowsOcrTest(unittest.TestCase):
    """Tes integrasi: OCR Windows sungguhan pada gambar yang dibuat Pillow."""

    def test_kartu_buatan(self):
        from PIL import Image, ImageDraw, ImageFont

        try:
            font = ImageFont.truetype("segoeui.ttf", 34)
        except OSError:
            self.skipTest("font Segoe UI tidak ada")
        image = Image.new("RGB", (900, 260), "white")
        draw = ImageDraw.Draw(image)
        for i, text in enumerate(["Telp: 0812 3456 7890", "Email: tes@contoh.co.id", "Web: https://contoh.co.id"]):
            draw.text((40, 30 + i * 70), text, font=font, fill="black")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "kartu.png")
            image.save(path)
            try:
                lines = ocr(path)
            except ScanError as error:
                self.skipTest(f"OCR Windows tidak tersedia: {error}")
        self.assertEqual(extract(lines), {"phones": ["0812 3456 7890"], "emails": ["tes@contoh.co.id"],
                                          "links": ["https://contoh.co.id"]})


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hist = os.path.join(self.tmp.name, "h.json")

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv), ocr_func=lambda path: CARD, history_path=self.hist)
        return code, out.getvalue(), err.getvalue()

    def test_pindai_simpan_kontak_dan_riwayat(self):
        vcf = os.path.join(self.tmp.name, "rina.vcf")
        code, out, _ = self.run_main("kartu.jpg", "--vcf", vcf, "--tag", "kerja")
        self.assertEqual(code, 0)
        self.assertIn("  - +62 812-3456-7890", out)
        self.assertIn("Kontak 'Rina Kartika'", out)
        with open(vcf, encoding="utf-8", newline="") as handle:
            self.assertIn("\r\nEND:VCARD\r\n", handle.read())
        self.run_main("lain.jpg", "--no-history")
        code, out, _ = self.run_main("--history", "--tag", "kerja")
        self.assertIn("#1", out)
        self.assertIn("2 telepon, 1 email, 2 tautan", out)
        self.assertNotIn("lain.jpg", self.run_main("--history")[1])


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.tmp = tempfile.TemporaryDirectory()
        self.notes = []
        self.saved = os.path.join(self.tmp.name, "k.vcf")
        self.app = scanner.ScannerApp(self.root, history=History(os.path.join(self.tmp.name, "h.json")),
                                      ocr_func=lambda path: CARD, ask_save=lambda _s: self.saved,
                                      notify=self.notes.append)

    def tearDown(self):
        self.root.destroy()
        self.tmp.cleanup()

    def test_pindai_kartu_dan_kontak(self):
        self.app.tags.set("kerja")
        entry = self.app.scan(os.path.join(self.tmp.name, "tidak-perlu-ada.jpg"))
        self.assertEqual(entry["tags"], ["kerja"])
        cards = [w for w in self.app.cards.winfo_children() if w.winfo_class() == "TLabelframe"]
        self.assertEqual([c.cget("text") for c in cards], ["Telepon (2)", "Email (1)", "Tautan (2)"])
        self.assertEqual(self.app.save_contact("emails", "rina.kartika@kopisenja.co.id"), self.saved)
        with open(self.saved, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("EMAIL;TYPE=INTERNET:rina.kartika@kopisenja.co.id", text)
        self.assertNotIn("TEL", text)

    def test_riwayat_dan_saring_tag(self):
        self.app.tags.set("kopi")
        self.app.scan("a.jpg")
        self.app.tags.set("")
        self.app.scan("b.jpg")
        self.assertEqual(self.app.history_list.size(), 2)
        self.app.tag_filter.set("kopi")
        self.assertEqual(self.app.history_list.size(), 1)
        self.app.history_list.selection_set(0)
        self.app.on_history_select()
        self.assertEqual(self.app.current["source"], "a.jpg")

    def test_simpan_kontak_tanpa_pindaian(self):
        self.assertIsNone(self.app.save_contact())
        self.assertEqual(self.notes, ["Pindai gambar dulu."])


if __name__ == "__main__":
    unittest.main()
