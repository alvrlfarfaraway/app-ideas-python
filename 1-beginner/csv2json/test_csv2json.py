import json
import os
import tempfile
import unittest

from csv2json import csv_to_json, infer_type, json_to_csv, main, parse_csv


class ParseCsvTest(unittest.TestCase):
    def test_dasar(self):
        self.assertEqual(parse_csv("a,b\n1,2\n"), [["a", "b"], ["1", "2"]])

    def test_crlf_dan_tanpa_baris_akhir(self):
        self.assertEqual(parse_csv("a,b\r\n1,2"), [["a", "b"], ["1", "2"]])

    def test_sel_berkutip(self):
        self.assertEqual(parse_csv('k\n"x,y"\n'), [["k"], ["x,y"]])
        self.assertEqual(parse_csv('k\n"dia ""hai"""\n'), [["k"], ['dia "hai"']])
        self.assertEqual(parse_csv('k\n"baris1\nbaris2"\n'), [["k"], ["baris1\nbaris2"]])

    def test_sel_kosong(self):
        self.assertEqual(parse_csv("a,b,c\n1,,3\n"), [["a", "b", "c"], ["1", "", "3"]])
        self.assertEqual(parse_csv('a,b\n"",x\n'), [["a", "b"], ["", "x"]])

    def test_baris_kosong_dilewati(self):
        self.assertEqual(parse_csv("a\n\n1\n\n"), [["a"], ["1"]])

    def test_kutip_tidak_ditutup(self):
        with self.assertRaises(ValueError):
            parse_csv('a\n"belum ditutup\n')

    def test_kutip_di_tengah_sel(self):
        with self.assertRaises(ValueError):
            parse_csv('a\nab"c"\n')


class InferTypeTest(unittest.TestCase):
    def test_tipe(self):
        self.assertIs(infer_type("true"), True)
        self.assertIs(infer_type("false"), False)
        self.assertEqual(infer_type("42"), 42)
        self.assertEqual(infer_type("-3.5"), -3.5)
        self.assertEqual(infer_type("abc"), "abc")
        self.assertEqual(infer_type(""), "")
        self.assertEqual(infer_type("nan"), "nan")
        self.assertEqual(infer_type("inf"), "inf")


class CsvToJsonTest(unittest.TestCase):
    def test_semua_teks_secara_bawaan(self):
        result = json.loads(csv_to_json("nama,umur\nAni,20\nBudi,31\n"))
        self.assertEqual(result, [{"nama": "Ani", "umur": "20"}, {"nama": "Budi", "umur": "31"}])

    def test_dengan_tipe(self):
        result = json.loads(csv_to_json("nama,umur,aktif\nAni,20,true\n", types=True))
        self.assertEqual(result, [{"nama": "Ani", "umur": 20, "aktif": True}])

    def test_hanya_header(self):
        self.assertEqual(json.loads(csv_to_json("a,b\n")), [])

    def test_kosong(self):
        for text in ("", " \n\n"):
            with self.assertRaises(ValueError):
                csv_to_json(text)

    def test_csv_tidak_valid(self):
        for text in ("a,b\n1\n", "a,b\n1,2,3\n", "a,a\n1,2\n", "a,\n1,2\n", 'a\n"x\n'):
            with self.assertRaises(ValueError, msg=text):
                csv_to_json(text)

    def test_bolak_balik(self):
        original = [{"nama": 'Ani, "si A"', "catatan": "baris1\nbaris2", "kosong": ""}]
        csv_text = json_to_csv(json.dumps(original))
        self.assertEqual(json.loads(csv_to_json(csv_text)), original)


class JsonToCsvTest(unittest.TestCase):
    def test_salinan_json2csv(self):
        self.assertEqual(json_to_csv('[{"a": 1}, {"b": 2, "a": 3}]'), "a,b\n1,\n3,2\n")
        with self.assertRaises(ValueError):
            json_to_csv('[{"a": {"b": 1}}]')
        with self.assertRaises(ValueError):
            json_to_csv("{rusak")


class CliTest(unittest.TestCase):
    def test_buka_dan_simpan_dua_arah(self):
        with tempfile.TemporaryDirectory() as folder:
            csv_path = os.path.join(folder, "in.csv")
            json_path = os.path.join(folder, "out.json")
            back_path = os.path.join(folder, "back.csv")
            with open(csv_path, "w", encoding="utf-8") as file:
                file.write("a,b\n1,x\n")
            self.assertEqual(main(["to-json", csv_path, "-o", json_path, "--types"]), 0)
            with open(json_path, encoding="utf-8") as file:
                self.assertEqual(json.load(file), [{"a": 1, "b": "x"}])
            self.assertEqual(main(["to-csv", json_path, "-o", back_path]), 0)
            with open(back_path, encoding="utf-8", newline="") as file:
                self.assertEqual(file.read(), "a,b\n1,x\n")

    def test_berkas_tidak_ditemukan(self):
        self.assertEqual(main(["to-json", "tidak-ada.csv"]), 1)
        self.assertEqual(main(["to-csv", "tidak-ada.json"]), 1)

    def test_simpan_gagal(self):
        with tempfile.TemporaryDirectory() as folder:
            source = os.path.join(folder, "in.csv")
            with open(source, "w", encoding="utf-8") as file:
                file.write("a\n1\n")
            self.assertEqual(main(["to-json", source, "-o", os.path.join(folder, "x", "y.json")]), 1)


if __name__ == "__main__":
    unittest.main()
