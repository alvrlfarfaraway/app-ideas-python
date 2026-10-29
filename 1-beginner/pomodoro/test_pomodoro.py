import unittest

from pomodoro import LONG, SHORT, WORK, Pomodoro, format_clock

MIN = 60


class FormatTest(unittest.TestCase):
    def test_format(self):
        self.assertEqual(format_clock(25 * MIN), "25:00")
        self.assertEqual(format_clock(61), "01:01")
        self.assertEqual(format_clock(0.2), "00:01")  # dibulatkan ke atas
        self.assertEqual(format_clock(0), "00:00")
        self.assertEqual(format_clock(-5), "00:00")


class TimerBasicsTest(unittest.TestCase):
    def test_awal_25_menit_kerja(self):
        timer = Pomodoro()
        self.assertEqual((timer.phase, timer.remaining, timer.running), (WORK, 25 * MIN, False))

    def test_tidak_berjalan_sebelum_start(self):
        timer = Pomodoro()
        timer.update(1000)
        self.assertEqual(timer.remaining, 25 * MIN)

    def test_start_dan_waktu_berkurang(self):
        timer = Pomodoro()
        timer.start(100)
        timer.update(160)
        self.assertEqual(timer.remaining, 24 * MIN)

    def test_pause_menahan_sisa_waktu(self):
        timer = Pomodoro()
        timer.start(0)
        timer.pause(300)
        timer.update(9999)  # waktu berjalan tapi timer dijeda
        self.assertEqual(timer.remaining, 20 * MIN)
        timer.start(10000)
        timer.update(10060)
        self.assertEqual(timer.remaining, 19 * MIN)

    def test_toggle(self):
        timer = Pomodoro()
        timer.toggle(0)
        self.assertTrue(timer.running)
        timer.toggle(10)
        self.assertFalse(timer.running)
        self.assertEqual(timer.remaining, 25 * MIN - 10)

    def test_start_dua_kali_tidak_mengulang_jam(self):
        timer = Pomodoro()
        timer.start(0)
        timer.start(500)  # diabaikan
        timer.update(600)
        self.assertEqual(timer.remaining, 25 * MIN - 600)


class StopResetTest(unittest.TestCase):
    def test_stop_mengembalikan_sesi_ke_penuh_tanpa_mengubah_siklus(self):
        timer = Pomodoro()
        timer.start(0)
        timer.update(25 * MIN)  # kerja 1 selesai -> istirahat
        timer.update(25 * MIN + 100)
        timer.stop()
        self.assertEqual((timer.phase, timer.remaining, timer.running), (SHORT, 5 * MIN, False))
        self.assertEqual(timer.work_completed, 1)

    def test_reset_kembali_ke_awal(self):
        timer = Pomodoro()
        timer.start(0)
        timer.update(31 * MIN)
        timer.reset()
        self.assertEqual((timer.phase, timer.remaining, timer.running), (WORK, 25 * MIN, False))
        self.assertEqual((timer.work_completed, timer.breaks_started), (0, 0))


class CycleTest(unittest.TestCase):
    def test_kerja_lalu_istirahat_5_menit(self):
        timer = Pomodoro()
        timer.start(0)
        timer.update(25 * MIN)
        self.assertEqual((timer.phase, timer.remaining), (SHORT, 5 * MIN))
        timer.update(30 * MIN)
        self.assertEqual((timer.phase, timer.remaining), (WORK, 25 * MIN))

    def test_istirahat_ke_4_adalah_panjang_10_menit(self):
        timer = Pomodoro()
        timer.start(0)
        t = 0
        seen = []
        for _ in range(7):
            t += timer.remaining
            timer.update(t)
            seen.append(timer.phase)
        self.assertEqual(seen, [SHORT, WORK, SHORT, WORK, SHORT, WORK, LONG])
        self.assertEqual(timer.remaining, 10 * MIN)

    def test_siklus_berulang_setelah_istirahat_panjang(self):
        timer = Pomodoro()
        timer.start(0)
        t, seen = 0, []
        for _ in range(16):
            t += timer.remaining
            timer.update(t)
            seen.append(timer.phase)
        self.assertEqual(seen.count(LONG), 2)  # istirahat ke-4 dan ke-8
        self.assertEqual(seen[6], LONG)
        self.assertEqual(seen[14], LONG)

    def test_istirahat_panjang_bisa_dimatikan(self):
        timer = Pomodoro(long=0)
        timer.start(0)
        t = 0
        for _ in range(8):
            t += timer.remaining
            timer.update(t)
            self.assertNotEqual(timer.phase, LONG)

    def test_callback_dan_bunyi_saat_habis(self):
        ended = []
        timer = Pomodoro(on_end=ended.append)
        timer.start(0)
        timer.update(25 * MIN - 1)
        self.assertEqual(ended, [])
        timer.update(25 * MIN)
        timer.update(30 * MIN)
        self.assertEqual(ended, [WORK, SHORT])

    def test_keterlambatan_tick_dibawa_ke_sesi_berikut(self):
        timer = Pomodoro()
        timer.start(0)
        timer.update(25 * MIN + 30)  # tick telat 30 detik
        self.assertEqual(timer.phase, SHORT)
        self.assertEqual(timer.remaining, 5 * MIN - 30)

    def test_tick_sangat_telat_melewati_beberapa_sesi(self):
        timer = Pomodoro()
        timer.start(0)
        timer.update(61 * MIN)  # kerja(25)+istirahat(5)+kerja(25)+istirahat(5)+1 menit
        self.assertEqual((timer.phase, timer.work_completed), (WORK, 2))
        self.assertEqual(timer.remaining, 25 * MIN - 1 * MIN)


class ConfigTest(unittest.TestCase):
    def test_durasi_khusus(self):
        timer = Pomodoro(work=50, short=10, long=20)
        timer.start(0)
        timer.update(50 * MIN)
        self.assertEqual((timer.phase, timer.remaining), (SHORT, 10 * MIN))

    def test_durasi_tidak_valid(self):
        for kwargs in ({"work": 0}, {"work": -1}, {"short": 0}, {"long": -1}, {"long_every": 0}):
            with self.assertRaises(ValueError, msg=str(kwargs)):
                Pomodoro(**kwargs)


if __name__ == "__main__":
    unittest.main()
