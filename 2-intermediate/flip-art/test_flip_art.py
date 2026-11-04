import os
import tempfile
import unittest

from PIL import Image

import flip_art
from flip_art import (
    BACKDROP,
    EASINGS,
    SPEEDS,
    FlipArt,
    cubic_bezier,
    demo_frames,
    fit,
    interval_for,
    render_step,
    timeline,
)


def solid(color, size=(40, 30)):
    return Image.new("RGB", size, color)


class EasingTest(unittest.TestCase):
    def test_ujung_kurva(self):
        for name, easing in EASINGS.items():
            if easing is None:
                continue
            self.assertEqual(easing(0), 0.0, name)
            self.assertEqual(easing(1), 1.0, name)
            self.assertEqual(easing(-1), 0.0, name)
            self.assertEqual(easing(2), 1.0, name)

    def test_linear(self):
        for t in (0.1, 0.25, 0.5, 0.9):
            self.assertAlmostEqual(EASINGS["linear"](t), t, places=6)

    def test_bentuk_kurva_seperti_css(self):
        ease_in, ease_out, ease_in_out = EASINGS["ease-in"], EASINGS["ease-out"], EASINGS["ease-in-out"]
        self.assertLess(ease_in(0.25), 0.25)  # mulai pelan
        self.assertGreater(ease_out(0.25), 0.25)  # mulai cepat
        self.assertAlmostEqual(ease_in_out(0.5), 0.5, places=6)  # simetris
        self.assertAlmostEqual(ease_in(0.5) + ease_out(0.5), 1.0, places=6)
        # Nilai acuan cubic-bezier(0.25, 0.1, 0.25, 1) pada t = 0.5 kira-kira 0.8024.
        self.assertAlmostEqual(EASINGS["ease"](0.5), 0.8024, places=3)

    def test_naik_monoton(self):
        for name, easing in EASINGS.items():
            if easing is None:
                continue
            values = [easing(i / 100) for i in range(101)]
            self.assertEqual(values, sorted(values), name)

    def test_cubic_bezier_custom(self):
        self.assertAlmostEqual(cubic_bezier(0, 0, 1, 1)(0.3), 0.3, places=6)


class SpeedTest(unittest.TestCase):
    def test_lambat_ke_cepat(self):
        self.assertEqual(interval_for(1), 1500)
        self.assertEqual(interval_for(10), 100)
        self.assertEqual(list(SPEEDS), sorted(SPEEDS, reverse=True))
        for bad in (0, 11):
            with self.assertRaises(ValueError):
                interval_for(bad)


class TimelineTest(unittest.TestCase):
    def test_tanpa_transisi(self):
        self.assertEqual(timeline(3, 400), [(0, 0, 0.0, 400), (1, 1, 0.0, 400), (2, 2, 0.0, 400)])
        self.assertEqual(timeline(0, 400), [])

    def test_satu_frame(self):
        self.assertEqual(timeline(1, 400, "ease"), [(0, 0, 0.0, 400)])

    def test_crossfade_dan_durasi(self):
        steps = timeline(3, 400, "linear")
        self.assertAlmostEqual(sum(step[3] for step in steps), 3 * 400)
        self.assertEqual(steps[0], (0, 0, 0.0, 200))
        fade = [step for step in steps if step[0] == 0 and step[1] == 1]
        self.assertEqual(len(fade), 5)  # 200 ms / 40 ms
        self.assertEqual([round(step[2], 2) for step in fade], [0.2, 0.4, 0.6, 0.8, 1.0])
        self.assertEqual(steps[-1][:2], (2, 0))  # frame terakhir menyambung ke frame pertama

    def test_transisi_tidak_dikenal(self):
        with self.assertRaises(ValueError):
            timeline(2, 400, "bounce")


class ImageTest(unittest.TestCase):
    def test_fit_letterbox(self):
        wide = fit(solid((255, 0, 0), (200, 50)), (100, 100))
        self.assertEqual(wide.size, (100, 100))
        self.assertEqual(wide.getpixel((50, 50)), (255, 0, 0))
        self.assertEqual(wide.getpixel((50, 5)), BACKDROP)  # pita atas

    def test_render_step_mencampur(self):
        frames = [solid((0, 0, 0)), solid((200, 100, 0))]
        self.assertEqual(render_step(frames, (0, 1, 0.0, 10)).getpixel((0, 0)), (0, 0, 0))
        self.assertEqual(render_step(frames, (0, 1, 0.5, 10)).getpixel((0, 0)), (100, 50, 0))
        self.assertEqual(render_step(frames, (0, 1, 1.0, 10)).getpixel((0, 0)), (200, 100, 0))

    def test_demo_frames(self):
        frames = demo_frames()
        self.assertEqual(len(frames), 8)
        self.assertEqual(len({f.tobytes() for f in frames}), 8)


class FlipArtTest(unittest.TestCase):
    def test_slot_tambah_hapus_bersihkan(self):
        art = FlipArt()
        self.assertEqual(len(art.slots), 8)
        self.assertFalse(art.can_start)
        art.set(2, solid((255, 0, 0)), "merah.jpg")
        art.set(5, solid((0, 0, 255)), "biru.jpg")
        self.assertEqual(art.filled, [2, 5])
        self.assertTrue(art.can_start)
        art.remove(2)
        self.assertEqual(art.filled, [5])
        art.clear()
        self.assertEqual(art.filled, [])
        self.assertEqual(len(art.slots), 8)

    def test_slot_tambahan(self):
        art = FlipArt()
        self.assertEqual(art.add_slot(), 8)
        art.set(8, solid((1, 2, 3)))
        self.assertEqual(art.filled, [8])

    def test_pindah_urutan(self):
        art = FlipArt(4)
        for i, name in enumerate("abcd"):
            art.set(i, solid((i, i, i)), name)
        art.move(0, 2)
        self.assertEqual(art.names, ["b", "c", "a", "d"])
        art.move(3, 0)
        self.assertEqual(art.names, ["d", "b", "c", "a"])
        self.assertEqual(art.slots[0].getpixel((0, 0)), (3, 3, 3))

    def test_simpan_gif(self):
        art = FlipArt()
        art.set(0, solid((255, 0, 0)))
        art.set(3, solid((0, 0, 255)))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.gif")
            self.assertEqual(art.save_gif(path, 400, "none", size=(40, 30)), 2)
            with Image.open(path) as gif:
                self.assertEqual(gif.n_frames, 2)
                self.assertEqual(gif.info["loop"], 0)
                self.assertEqual(gif.info["duration"], 400)
            path = os.path.join(tmp, "b.gif")
            frames = art.save_gif(path, 400, "linear", size=(40, 30))
            self.assertGreater(frames, 2)
        with self.assertRaises(ValueError):
            FlipArt().save_gif(os.path.join(tempfile.gettempdir(), "x.gif"), 400)


class GuiTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            self.root = tk.Tk()
        except Exception as error:
            self.skipTest(f"Tk tidak tersedia: {error}")
        self.root.withdraw()
        self.sounds = []
        self.app = flip_art.FlipArtApp(self.root, sound=self.sounds.append)

    def tearDown(self):
        self.app.stop()
        self.root.destroy()

    def state(self):
        return str(self.app.start_button.cget("state"))

    def test_tombol_start_dan_label(self):
        self.assertEqual(self.state(), "disabled")
        self.assertEqual(self.app.slot_widgets[0]["button"].cget("text"), "+")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "a.jpg")
            solid((200, 30, 30), (64, 48)).save(path)
            self.app.load_into(0, path)
        self.assertEqual(self.state(), "normal")
        self.assertEqual(self.app.slot_widgets[0]["button"].cget("text"), "−")
        self.app.toggle()
        self.assertEqual(self.app.start_button.cget("text"), "Stop Animation")
        self.app.toggle()
        self.assertEqual(self.app.start_button.cget("text"), "Start Animation")
        self.app.on_slot_button(0)  # tombol "−" menghapus gambar
        self.assertEqual(self.state(), "disabled")
        self.assertEqual(self.sounds, ["add", "remove"])

    def test_animasi_dan_sorotan(self):
        for i, frame in enumerate(demo_frames(3)):
            self.app.art.set(i, frame)
        self.app.build_slots()
        self.app.transition.set("none")
        self.app.start()
        self.assertEqual(str(self.app.slot_widgets[0]["thumb"].cget("highlightbackground")), "#e8871e")
        self.app.root.after_cancel(self.app.job)
        self.app.tick()
        self.assertEqual(str(self.app.slot_widgets[1]["thumb"].cget("highlightbackground")), "#e8871e")
        self.assertEqual(str(self.app.slot_widgets[0]["thumb"].cget("highlightbackground")), "#ecebe6")
        self.app.clear()
        self.assertIsNone(self.app.job)
        self.assertEqual(self.app.art.filled, [])


if __name__ == "__main__":
    unittest.main()
