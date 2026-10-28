import io
import os
import tempfile
import unittest
from datetime import datetime

from countdown import (MAX_DAYS, check_precision, load_events, main, parse_event,
                       remaining, render, save_events, watch)

NOW = datetime(2026, 10, 29, 12, 0, 0)


class ParseEventTest(unittest.TestCase):
    def test_tanpa_waktu_berarti_tengah_malam(self):
        self.assertEqual(parse_event("Tahun Baru", "2027-01-01")["when"], "2027-01-01T00:00")

    def test_dengan_waktu(self):
        self.assertEqual(parse_event("Rapat", "2026-12-01", "09:30")["when"], "2026-12-01T09:30")

    def test_nama_kosong_ditolak(self):
        for name in ("", "   "):
            with self.assertRaises(ValueError):
                parse_event(name, "2027-01-01")

    def test_tanggal_salah_ditolak(self):
        for date in ("", "01-01-2027", "2027-13-01", "2027-02-30", "besok"):
            with self.assertRaises(ValueError, msg=date):
                parse_event("X", date)

    def test_waktu_salah_ditolak(self):
        for clock in ("25:00", "9.30", "12:60", "abc"):
            with self.assertRaises(ValueError, msg=clock):
                parse_event("X", "2027-01-01", clock)


class PrecisionTest(unittest.TestCase):
    def test_batas(self):
        near = parse_event("X", "2030-01-01")
        check_precision(near, NOW)  # tidak melempar
        far = parse_event("X", "2099-01-01")
        with self.assertRaises(ValueError):
            check_precision(far, NOW)
        self.assertGreater((datetime(2099, 1, 1) - NOW).days, MAX_DAYS)


class RemainingTest(unittest.TestCase):
    def test_pecah_ke_satuan(self):
        target = datetime(2026, 10, 31, 14, 30, 45)
        self.assertEqual(remaining(target, NOW), (2, 2, 30, 45))

    def test_detik_turun_lalu_menit_ikut_turun(self):
        target = datetime(2026, 10, 29, 12, 5, 0)
        self.assertEqual(remaining(target, NOW), (0, 0, 5, 0))
        self.assertEqual(remaining(target, datetime(2026, 10, 29, 12, 0, 1)), (0, 0, 4, 59))

    def test_sudah_lewat_jadi_nol(self):
        self.assertEqual(remaining(datetime(2020, 1, 1), NOW), (0, 0, 0, 0))


class RenderTest(unittest.TestCase):
    def test_render_dan_tercapai(self):
        events = [parse_event("A", "2026-10-30", "12:00"), parse_event("B", "2026-10-29", "11:00")]
        lines, reached = render(events, NOW)
        self.assertEqual(lines[0], "A: 1 hari 00 jam 00 menit 00 detik")
        self.assertIn("TERCAPAI", lines[1])
        self.assertEqual(reached, ["B"])


class WatchTest(unittest.TestCase):
    def test_berhenti_dan_memberi_alert_saat_tercapai(self):
        event = parse_event("Mulai", "2026-10-29", "12:00")
        clock = iter([datetime(2026, 10, 29, 11, 59, 58), datetime(2026, 10, 29, 11, 59, 59),
                      datetime(2026, 10, 29, 12, 0, 0)])
        out = io.StringIO()
        watch([event], now_fn=lambda: next(clock), sleep=lambda s: None, out=out)
        text = out.getvalue()
        self.assertIn("0 hari 00 jam 00 menit 02 detik", text)
        self.assertIn("0 hari 00 jam 00 menit 01 detik", text)
        self.assertEqual(text.count("sudah tercapai"), 1)


class CliTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.file = os.path.join(self.dir.name, "events.json")

    def tearDown(self):
        self.dir.cleanup()

    def run_main(self, *args):
        return main(["-f", self.file, *args], now_fn=lambda: NOW)

    def test_tambah_banyak_event_dan_persisten(self):
        self.assertEqual(self.run_main("add", "A", "2027-01-01"), 0)
        self.assertEqual(self.run_main("add", "B", "2027-02-01", "08:00"), 0)
        self.assertEqual([e["name"] for e in load_events(self.file)], ["A", "B"])

    def test_nama_ganda_ditolak(self):
        self.run_main("add", "A", "2027-01-01")
        self.assertEqual(self.run_main("add", "A", "2027-02-01"), 1)

    def test_hapus(self):
        self.run_main("add", "A", "2027-01-01")
        self.assertEqual(self.run_main("remove", "A"), 0)
        self.assertEqual(load_events(self.file), [])
        self.assertEqual(self.run_main("remove", "A"), 1)

    def test_list_tanpa_event_gagal(self):
        self.assertEqual(self.run_main("list"), 1)

    def test_input_salah(self):
        self.assertEqual(self.run_main("add", "", "2027-01-01"), 1)
        self.assertEqual(self.run_main("add", "A", "salah"), 1)
        self.assertEqual(self.run_main("add", "A", "2099-01-01"), 1)

    def test_file_belum_ada_lalu_simpan(self):
        self.assertEqual(load_events(self.file), [])
        save_events(self.file, [{"name": "Z", "when": "2027-01-01T00:00"}])
        self.assertEqual(load_events(self.file)[0]["name"], "Z")


if __name__ == "__main__":
    unittest.main()
