import os
import tempfile
import unittest

from json2csv import format_field, json_to_csv, main


class FormatFieldTest(unittest.TestCase):
    def test_nilai_dasar(self):
        self.assertEqual(format_field("abc"), "abc")
        self.assertEqual(format_field(42), "42")
        self.assertEqual(format_field(3.5), "3.5")
        self.assertEqual(format_field(True), "true")
        self.assertEqual(format_field(None), "")

    def test_kutip_bila_perlu(self):
        self.assertEqual(format_field("a,b"), '"a,b"')
        self.assertEqual(format_field('dia bilang "hai"'), '"dia bilang ""hai"""')
        self.assertEqual(format_field("baris1\nbaris2"), '"baris1\nbaris2"')
        self.assertEqual(format_field(" spasi "), '" spasi "')

    def test_bersarang_ditolak(self):
        for value in ({"a": 1}, [1, 2]):
            with self.assertRaises(ValueError):
                format_field(value)


class JsonToCsvTest(unittest.TestCase):
    def test_daftar_objek(self):
        text = '[{"nama": "Ani", "umur": 20}, {"nama": "Budi", "umur": 31}]'
        self.assertEqual(json_to_csv(text), "nama,umur\nAni,20\nBudi,31\n")

    def test_satu_objek(self):
        self.assertEqual(json_to_csv('{"a": 1, "b": 2}'), "a,b\n1,2\n")

    def test_kunci_tidak_seragam(self):
        text = '[{"a": 1}, {"b": 2, "a": 3}]'
        self.assertEqual(json_to_csv(text), "a,b\n1,\n3,2\n")

    def test_koma_dan_kutip_di_nilai(self):
        self.assertEqual(json_to_csv('[{"k": "x,y"}]'), 'k\n"x,y"\n')

    def test_kosong(self):
        for text in ("", "  \n"):
            with self.assertRaises(ValueError):
                json_to_csv(text)

    def test_json_tidak_valid(self):
        for text in ("{bukan json}", '[{"a": 1},]', "[1, 2"):
            with self.assertRaises(ValueError, msg=text):
                json_to_csv(text)

    def test_bentuk_tidak_didukung(self):
        for text in ("[]", "42", '"teks"', "[1, 2]", '[{"a": {"b": 1}}]', '[{"a": [1]}]'):
            with self.assertRaises(ValueError, msg=text):
                json_to_csv(text)


class CliTest(unittest.TestCase):
    def test_buka_dan_simpan(self):
        with tempfile.TemporaryDirectory() as folder:
            source = os.path.join(folder, "in.json")
            target = os.path.join(folder, "out.csv")
            with open(source, "w", encoding="utf-8") as file:
                file.write('[{"a": 1, "b": "x"}]')
            self.assertEqual(main([source, "-o", target]), 0)
            with open(target, encoding="utf-8", newline="") as file:
                self.assertEqual(file.read(), "a,b\n1,x\n")

    def test_berkas_tidak_ditemukan(self):
        self.assertEqual(main(["tidak-ada.json"]), 1)

    def test_simpan_gagal(self):
        with tempfile.TemporaryDirectory() as folder:
            source = os.path.join(folder, "in.json")
            with open(source, "w", encoding="utf-8") as file:
                file.write('[{"a": 1}]')
            self.assertEqual(main([source, "-o", os.path.join(folder, "tidak", "ada", "out.csv")]), 1)


if __name__ == "__main__":
    unittest.main()
