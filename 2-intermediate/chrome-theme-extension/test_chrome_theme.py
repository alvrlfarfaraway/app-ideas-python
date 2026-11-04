import contextlib
import io
import json
import os
import re
import tempfile
import unittest
import zipfile

from chrome_theme import (
    PRESETS,
    WCAG_AA,
    best_text,
    build_palette,
    chrome_manifest,
    contrast_ratio,
    contrast_report,
    dump_manifest,
    firefox_manifest,
    main,
    parse_hex,
    relative_luminance,
    render_preview,
    shade,
    slug,
    to_hex,
)

WHITE, BLACK = (255, 255, 255), (0, 0, 0)


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(list(argv))
        except SystemExit as exit_:
            code = exit_.code
    return code, out.getvalue(), err.getvalue()


class ColorTest(unittest.TestCase):
    def test_parse_hex(self):
        self.assertEqual(parse_hex("#1f6f78"), (31, 111, 120))
        self.assertEqual(parse_hex("1F6F78"), (31, 111, 120))
        self.assertEqual(parse_hex(" #abc "), (170, 187, 204))
        for bad in ("", "#12", "#12345", "#ggg", "red", "#1234567"):
            with self.assertRaises(ValueError, msg=bad):
                parse_hex(bad)
        self.assertEqual(to_hex((31, 111, 120)), "#1f6f78")

    def test_kontras_wcag(self):
        self.assertAlmostEqual(relative_luminance(WHITE), 1.0)
        self.assertAlmostEqual(relative_luminance(BLACK), 0.0)
        self.assertAlmostEqual(contrast_ratio(BLACK, WHITE), 21.0)
        self.assertAlmostEqual(contrast_ratio(WHITE, BLACK), 21.0)
        self.assertAlmostEqual(contrast_ratio((119, 119, 119), WHITE), 4.48, places=2)  # #777 di atas putih

    def test_best_text(self):
        self.assertEqual(best_text(BLACK), WHITE)
        self.assertEqual(best_text(WHITE), (26, 26, 26))
        self.assertEqual(best_text((255, 214, 10)), (26, 26, 26))  # kuning terang -> teks gelap
        self.assertEqual(best_text((0, 114, 178)), WHITE)

    def test_shade(self):
        self.assertLess(relative_luminance(shade((31, 111, 120), -0.1)), relative_luminance((31, 111, 120)))
        self.assertGreater(relative_luminance(shade((31, 111, 120), 0.1)), relative_luminance((31, 111, 120)))
        self.assertEqual(shade(WHITE, 0.5), WHITE)
        self.assertEqual(shade(BLACK, -0.5), BLACK)


class PaletteTest(unittest.TestCase):
    def test_semua_preset_lulus_kontras(self):
        for key, preset in PRESETS.items():
            overrides = {k: parse_hex(preset[k]) for k in ("text", "ntp", "frame", "accent") if k in preset}
            palette = build_palette(parse_hex(preset["base"]), **overrides)
            for label, ratio, ok in contrast_report(palette):
                self.assertTrue(ok, f"{key}: {label} {ratio:.2f}")

    def test_warna_acak_selalu_terbaca(self):
        # Teks otomatis (hitam/putih) harus lulus AA untuk warna dasar apa pun.
        for r in range(0, 256, 51):
            for g in range(0, 256, 51):
                for b in range(0, 256, 51):
                    palette = build_palette((r, g, b))
                    for fg, bg in (("tab_text", "toolbar"), ("tab_background_text", "frame"),
                                   ("ntp_text", "ntp_background"), ("ntp_link", "ntp_background")):
                        self.assertGreaterEqual(contrast_ratio(palette[fg], palette[bg]), WCAG_AA - 0.01,
                                                (r, g, b, fg))

    def test_timpaan(self):
        palette = build_palette((0, 0, 0), text=(255, 214, 10), ntp=(10, 10, 10), frame=(20, 20, 20))
        self.assertEqual(palette["tab_text"], (255, 214, 10))
        self.assertEqual(palette["ntp_background"], (10, 10, 10))
        self.assertEqual(palette["frame"], (20, 20, 20))

    def test_teks_kurang_kontras_dilaporkan(self):
        palette = build_palette((119, 119, 119), text=(136, 136, 136))
        self.assertTrue(all(not ok for _, _, ok in contrast_report(palette)))


class ManifestTest(unittest.TestCase):
    def setUp(self):
        self.palette = build_palette(parse_hex("#1f6f78"))

    def test_chrome_mengikuti_aturan_chrome(self):
        manifest = chrome_manifest("Teal Malam", self.palette)
        self.assertEqual(manifest["manifest_version"], 3)
        # Aturan yang sama dengan pesan error Chrome saat --pack-extension.
        self.assertRegex(manifest["version"], r"^\d{1,5}(\.\d{1,5}){0,3}$")
        colors = manifest["theme"]["colors"]
        for key in ("frame", "toolbar", "tab_text", "tab_background_text", "bookmark_text", "ntp_background",
                    "ntp_text", "ntp_link", "omnibox_background", "omnibox_text", "toolbar_button_icon"):
            self.assertIn(key, colors)
        for value in colors.values():
            self.assertEqual(len(value), 3)
            self.assertTrue(all(isinstance(v, int) and 0 <= v <= 255 for v in value))
        h, s, l = manifest["theme"]["tints"]["buttons"]
        self.assertEqual((h, s), (-1, -1))
        self.assertTrue(0 <= l <= 1)

    def test_firefox_memakai_warna_css(self):
        manifest = firefox_manifest("Teal Malam", self.palette)
        self.assertEqual(manifest["browser_specific_settings"]["gecko"]["id"], "teal-malam@app-ideas-python.local")
        colors = manifest["theme"]["colors"]
        for key in ("frame", "tab_background_text", "toolbar", "toolbar_text", "toolbar_field", "tab_selected"):
            self.assertRegex(colors[key], r"^#[0-9a-f]{6}$")
        self.assertEqual(colors["toolbar"], "#1f6f78")

    def test_dump_ringkas_dan_tetap_json(self):
        manifest = chrome_manifest("Teal", self.palette)
        text = dump_manifest(manifest)
        self.assertEqual(json.loads(text), manifest)
        self.assertIn('"toolbar": [31, 111, 120]', text)
        self.assertIn('"buttons": [-1, -1, 1.0]', text)

    def test_slug(self):
        self.assertEqual(slug("Teal Malam!"), "teal-malam")
        self.assertEqual(slug("   "), "tema")
        self.assertEqual(slug("Tema #1f6f78"), "tema-1f6f78")


class PreviewTest(unittest.TestCase):
    def test_warna_tema_terlihat_di_gambar(self):
        palette = build_palette(parse_hex("#1f6f78"))
        img = render_preview(palette, "Teal", size=(960, 540))
        self.assertEqual(img.size, (960, 540))
        self.assertEqual(img.getpixel((900, 5)), palette["frame"])
        self.assertEqual(img.getpixel((5, 70)), palette["toolbar"])
        self.assertEqual(img.getpixel((50, 500)), palette["ntp_background"])


class CliTest(unittest.TestCase):
    def test_membuat_folder_tema_lengkap(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "tema")
            code, stdout, _ = run("--base", "#1f6f78", "--name", "Teal Malam", "-o", out, "--firefox", "--zip")
            self.assertEqual(code, 0)
            self.assertIn("Load unpacked", stdout)
            with open(os.path.join(out, "chrome", "manifest.json"), encoding="utf-8") as handle:
                self.assertEqual(json.load(handle)["name"], "Teal Malam")
            with open(os.path.join(out, "firefox", "manifest.json"), encoding="utf-8") as handle:
                self.assertIn("gecko", json.load(handle)["browser_specific_settings"])
            with zipfile.ZipFile(os.path.join(out, "teal-malam-chrome.zip")) as archive:
                self.assertEqual(archive.namelist(), ["manifest.json"])  # manifest di akar zip
            self.assertTrue(os.path.exists(os.path.join(out, "teal-malam-firefox.zip")))
            self.assertTrue(os.path.exists(os.path.join(out, "preview.png")))

    def test_preset(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, stdout, _ = run("--preset", "kontras-tinggi", "-o", tmp, "--no-preview")
            self.assertEqual(code, 0)
            with open(os.path.join(tmp, "chrome", "manifest.json"), encoding="utf-8") as handle:
                manifest = json.load(handle)
            self.assertEqual(manifest["name"], "Tema kontras-tinggi")
            self.assertEqual(manifest["theme"]["colors"]["tab_text"], [255, 214, 10])
            self.assertNotIn("KURANG", stdout)

    def test_strict_menolak_kontras_kurang(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "x")
            code, stdout, err = run("--base", "#777777", "--text", "#888888", "-o", out, "--strict")
            self.assertEqual(code, 1)
            self.assertIn("KURANG", stdout)
            self.assertIn("kontras kurang", err)
            self.assertFalse(os.path.exists(out))
            code, stdout, _ = run("--base", "#777777", "--text", "#888888", "-o", out, "--no-preview")
            self.assertEqual(code, 0)
            self.assertIn("Peringatan", stdout)

    def test_input_salah(self):
        self.assertEqual(run()[0], 1)
        code, _, err = run("--base", "merah")
        self.assertEqual(code, 1)
        self.assertIn("bukan warna hex", err)
        self.assertEqual(run("--base", "#000", "--name", "x" * 46)[0], 1)

    def test_daftar_preset(self):
        code, stdout, _ = run("--list-presets")
        self.assertEqual(code, 0)
        for key in PRESETS:
            self.assertIn(key, stdout)


if __name__ == "__main__":
    unittest.main()
