import unittest

from stopwatch import Stopwatch, format_lap, format_time


class FormatTest(unittest.TestCase):
    def test_format(self):
        self.assertEqual(format_time(0), "00:00.00")
        self.assertEqual(format_time(5.25), "00:05.25")
        self.assertEqual(format_time(65.5), "01:05.50")
        self.assertEqual(format_time(3600), "1:00:00.00")
        self.assertEqual(format_time(3725.07), "1:02:05.07")
        self.assertEqual(format_time(-3), "00:00.00")

    def test_dipotong_bukan_dibulatkan(self):
        self.assertEqual(format_time(59.999), "00:59.99")
        self.assertEqual(format_time(0.29), "00:00.29")  # float 0.29*100 = 28.999... tidak boleh jadi .28


class StopwatchTest(unittest.TestCase):
    def test_start_dan_hitung_naik(self):
        watch = Stopwatch()
        self.assertEqual(watch.time(50), 0)
        watch.start(100)
        self.assertEqual(watch.time(100), 0)
        self.assertEqual(watch.time(107.5), 7.5)

    def test_stop_menahan_waktu(self):
        watch = Stopwatch()
        watch.start(0)
        watch.stop(10)
        self.assertEqual(watch.time(10), 10)
        self.assertEqual(watch.time(9999), 10)
        self.assertFalse(watch.running)

    def test_start_lagi_melanjutkan_bukan_mengulang(self):
        watch = Stopwatch()
        watch.start(0)
        watch.stop(10)
        watch.start(500)  # jeda panjang tidak dihitung
        self.assertEqual(watch.time(503), 13)
        watch.stop(505)
        watch.start(900)
        self.assertEqual(watch.time(901), 16)

    def test_start_dua_kali_tidak_mengulang_jam(self):
        watch = Stopwatch()
        watch.start(0)
        watch.start(5)
        self.assertEqual(watch.time(10), 10)

    def test_stop_saat_berhenti_tidak_mengubah_apa_apa(self):
        watch = Stopwatch()
        watch.stop(5)
        self.assertEqual(watch.time(9), 0)
        watch.start(10)
        watch.stop(14)
        watch.stop(99)
        self.assertEqual(watch.time(200), 4)

    def test_restart_nol_dan_langsung_jalan(self):
        watch = Stopwatch()
        watch.start(0)
        watch.restart(30)
        self.assertEqual(watch.time(30), 0)
        self.assertEqual(watch.time(35), 5)
        self.assertTrue(watch.running)

    def test_restart_dari_keadaan_berhenti(self):
        watch = Stopwatch()
        watch.start(0)
        watch.stop(20)
        watch.restart(100)
        self.assertEqual(watch.time(102), 2)


class LapTest(unittest.TestCase):
    def test_lap_mencatat_total_dan_selisih(self):
        watch = Stopwatch()
        watch.start(0)
        self.assertEqual(watch.lap(12), (12, 12))
        self.assertEqual(watch.lap(30), (30, 18))
        self.assertEqual(watch.lap(31), (31, 1))
        self.assertEqual(len(watch.laps), 3)

    def test_lap_melewati_stop(self):
        watch = Stopwatch()
        watch.start(0)
        watch.lap(10)
        watch.stop(15)
        watch.start(100)
        self.assertEqual(watch.lap(105), (20, 10))  # 15 + 5 detik jalan

    def test_lap_saat_berhenti_ditolak(self):
        watch = Stopwatch()
        with self.assertRaises(ValueError):
            watch.lap(1)
        watch.start(0)
        watch.stop(5)
        with self.assertRaises(ValueError):
            watch.lap(6)

    def test_hapus_lap(self):
        watch = Stopwatch()
        watch.start(0)
        watch.lap(5)
        watch.lap(9)
        watch.clear_laps()
        self.assertEqual(watch.laps, [])
        self.assertEqual(watch.lap(12), (12, 12))  # lap pertama baru, selisih dari awal jam
        self.assertTrue(watch.running)  # menghapus lap tidak menghentikan jam

    def test_restart_tidak_menghapus_lap_tapi_selisih_mulai_dari_nol(self):
        watch = Stopwatch()
        watch.start(0)
        watch.lap(5)
        watch.restart(10)
        self.assertEqual(len(watch.laps), 1)
        self.assertEqual(watch.lap(12), (2, 2))  # bukan (2, -3)

    def test_format_lap(self):
        self.assertEqual(format_lap(3, (75.5, 12.25)), "Lap  3   00:12.25   (total 01:15.50)")


if __name__ == "__main__":
    unittest.main()
