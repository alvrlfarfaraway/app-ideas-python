import time
import unittest

from iot_mailbox import IOTMailbox, Panel, stuck_open_source


def make_panel(light_source=None, open_alert_after=3):
    lines, bells = [], []
    panel = Panel(0.01, open_alert_after, light_source, random_fn=lambda: 0.5,
                  emit=lines.append, bell=lambda: bells.append(1))
    return panel, lines, bells


class IOTMailboxTest(unittest.TestCase):
    def test_tanda_bergantian_dan_callback_menerima_nilai_nyata(self):
        received = []
        box = IOTMailbox(1, received.append, random_fn=lambda: 0.42)
        for _ in range(4):
            box.signal_state_change()
        self.assertEqual(received, [0.42, -0.42, 0.42, -0.42])  # aslinya JS mengirim undefined

    def test_cahaya_nol_tidak_ambigu(self):
        received = []
        box = IOTMailbox(1, received.append, random_fn=lambda: 0.0)
        for _ in range(3):
            box.signal_state_change()
        self.assertEqual(received, [0.01, -0.01, 0.01])  # tetap bergantian, tidak pernah 0

    def test_interval_harus_positif(self):
        for interval in (0, -1):
            with self.assertRaises(ValueError):
                IOTMailbox(interval)

    def test_start_stop_dengan_thread_nyata(self):
        received = []
        box = IOTMailbox(0.01, received.append)
        box.start_monitoring()
        box.start_monitoring()  # kedua kalinya tidak membuat thread kedua
        time.sleep(0.15)
        box.stop_monitoring()
        count = len(received)
        self.assertGreaterEqual(count, 3)
        time.sleep(0.05)
        self.assertEqual(len(received), count)  # sudah berhenti
        self.assertFalse(box.monitoring)

    def test_stop_tanpa_start_aman(self):
        IOTMailbox(1).stop_monitoring()


class PanelTest(unittest.TestCase):
    def test_log_tiap_pembacaan_dan_notifikasi_saat_dibuka(self):
        panel, lines, bells = make_panel()
        for level in (0.8, -0.3, 0.5):
            panel.on_light_level(level)
        self.assertEqual(len(panel.log), 3)
        self.assertIn("+0.80", panel.log[0])
        self.assertIn("TERBUKA", panel.log[0])
        self.assertIn("tertutup", panel.log[1])
        self.assertEqual(len(panel.notifications), 2)  # dibuka dua kali
        self.assertEqual(len(bells), 2)  # bunyi tiap pintu dibuka (bonus)

    def test_tidak_ada_notifikasi_saat_tertutup(self):
        panel, _, bells = make_panel()
        panel.on_light_level(-0.5)
        self.assertEqual(panel.notifications, [])
        self.assertEqual(bells, [])

    def test_pintu_dibiarkan_terbuka_hanya_sekali(self):
        panel, _, _ = make_panel(open_alert_after=3)
        for _ in range(6):
            panel.on_light_level(0.4)
        texts = [n for n in panel.notifications if "dibiarkan terbuka" in n]
        self.assertEqual(len(texts), 1)
        panel.on_light_level(-0.4)  # ditutup, lalu dibuka lagi: peringatan bisa muncul lagi
        for _ in range(3):
            panel.on_light_level(0.4)
        self.assertEqual(len([n for n in panel.notifications if "dibiarkan terbuka" in n]), 2)

    def test_pintu_yang_ditutup_tepat_waktu_tidak_diperingatkan(self):
        panel, _, _ = make_panel(open_alert_after=3)
        for level in (0.4, 0.4, -0.4, 0.4, 0.4, -0.4):
            panel.on_light_level(level)
        self.assertFalse(any("dibiarkan terbuka" in n for n in panel.notifications))

    def test_status_tombol(self):
        panel, _, _ = make_panel()
        self.assertEqual(panel.buttons(), {"start": True, "stop": False, "reset": True})
        panel.start()
        try:
            self.assertEqual(panel.buttons(), {"start": False, "stop": True, "reset": True})
            self.assertFalse(panel.start())  # nonaktif selama berjalan
        finally:
            panel.stop()
        self.assertEqual(panel.buttons(), {"start": True, "stop": False, "reset": True})
        self.assertFalse(panel.stop())

    def test_pesan_log_saat_mulai_dan_berhenti(self):
        panel, _, _ = make_panel()
        panel.start()
        panel.stop()
        self.assertIn("dimulai", panel.log[0])
        self.assertIn("dihentikan", panel.log[-1])

    def test_reset_mengosongkan_dan_menghentikan(self):
        panel, _, _ = make_panel()
        panel.start()
        time.sleep(0.05)
        panel.reset()
        self.assertFalse(panel.mailbox.monitoring)
        self.assertEqual((panel.log, panel.notifications), ([], []))

    def test_pintu_macet_terbuka_memicu_peringatan_dari_thread_nyata(self):
        panel, _, _ = make_panel(stuck_open_source(lambda: 0.5), open_alert_after=3)
        panel.start()
        time.sleep(0.2)
        panel.stop()
        self.assertTrue(any("dibiarkan terbuka" in n for n in panel.notifications))


if __name__ == "__main__":
    unittest.main()
