"""Chrome Theme Extension: buat tema Chrome (dan Firefox) dari warna pilihan sendiri.

Dari satu warna dasar, program menyusun palet tema, memilih warna teks dengan
kontras yang cukup (WCAG), lalu menulis folder ekstensi tema yang bisa dipasang
lewat chrome://extensions > "Load unpacked". Gambar pratinjau dibuat dengan Pillow
supaya warnanya bisa dilihat sebelum dipasang.

Jalankan:
    python chrome_theme.py --base "#1f6f78" --name "Teal Malam" -o tema-teal
    python chrome_theme.py --preset kontras-tinggi -o tema-kontras --firefox --zip
    python chrome_theme.py --base "#f4efe6" --text "#3a3a3a" -o tema-krem
    python chrome_theme.py --list-presets
"""

import argparse
import colorsys
import json
import os
import re
import sys
import zipfile

WCAG_AA = 4.5  # kontras minimum teks biasa menurut WCAG 2.x

# Preset. Okabe-Ito adalah palet yang tetap bisa dibedakan oleh penderita buta warna merah-hijau.
PRESETS = {
    "kontras-tinggi": {"description": "Hitam dan kuning, kontras sangat tinggi",
                       "base": "#000000", "text": "#ffd60a", "ntp": "#000000"},
    "okabe-biru": {"description": "Biru Okabe-Ito, aman untuk buta warna merah-hijau", "base": "#0072b2"},
    "okabe-oranye": {"description": "Oranye Okabe-Ito, aman untuk buta warna merah-hijau", "base": "#e69f00"},
    "sepia-malam": {"description": "Cokelat hangat yang redup untuk malam hari", "base": "#3b2f2a", "ntp": "#2a211d"},
    "gelap": {"description": "Abu-abu gelap netral", "base": "#2b2b2e"},
    "terang": {"description": "Abu-abu terang netral", "base": "#eceef1"},
}

HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


# --- warna ----------------------------------------------------------------

def parse_hex(text):
    """'#1f6f78', '1f6f78', atau '#abc' -> (r, g, b)."""
    match = HEX_RE.match(text.strip())
    if not match:
        raise ValueError(f"'{text}' bukan warna hex. Contoh: #1f6f78 atau #abc.")
    digits = match.group(1)
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    return tuple(int(digits[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(rgb):
    return "#" + "".join(f"{v:02x}" for v in rgb)


def relative_luminance(rgb):
    """Luminans relatif WCAG 2.x (0 = hitam, 1 = putih)."""
    def channel(value):
        c = value / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    la, lb = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def shade(rgb, amount):
    """Ubah kecerahan (lightness HLS). amount > 0 lebih terang, < 0 lebih gelap."""
    h, l, s = colorsys.rgb_to_hls(*(v / 255 for v in rgb))
    l = min(1.0, max(0.0, l + amount))
    return tuple(round(v * 255) for v in colorsys.hls_to_rgb(h, l, s))


def mix(a, b, amount):
    """amount=0 -> a, amount=1 -> b."""
    return tuple(round(x + (y - x) * amount) for x, y in zip(a, b))


DARK_TEXT = (26, 26, 26)
LIGHT_TEXT = (255, 255, 255)
PURE_BLACK = (0, 0, 0)


def best_text(background):
    """Teks gelap atau putih, mana yang kontrasnya lebih tinggi terhadap latar.

    Untuk latar berkecerahan sedang, abu-abu tua bisa kurang dari 4.5:1. Hitam murni
    selalu cukup di situ: kontras terhadap hitam dikali kontras terhadap putih selalu 21,
    jadi salah satunya pasti minimal akar 21 (sekitar 4.58).
    """
    dark, light = contrast_ratio(background, DARK_TEXT), contrast_ratio(background, LIGHT_TEXT)
    if max(dark, light) < WCAG_AA:
        return PURE_BLACK if contrast_ratio(background, PURE_BLACK) >= light else LIGHT_TEXT
    return DARK_TEXT if dark >= light else LIGHT_TEXT


def is_dark(rgb):
    return best_text(rgb) == LIGHT_TEXT


# --- palet ----------------------------------------------------------------

def build_palette(base, frame=None, text=None, ntp=None, accent=None):
    """Susun semua warna tema dari warna dasar. Argumen lain (rgb) menimpa hasil turunan."""
    toolbar = base
    dark = is_dark(base)
    if frame is None:
        # Bingkai sedikit lebih gelap dari toolbar; untuk warna yang sudah hampir hitam, sedikit lebih terang.
        frame = shade(base, -0.12) if relative_luminance(base) > 0.02 else shade(base, 0.08)
    omnibox = shade(toolbar, 0.10 if dark else -0.07)
    if ntp is None:
        ntp = shade(base, -0.05) if dark else shade(base, 0.04)
    palette = {
        "frame": frame,
        "frame_inactive": mix(frame, (128, 128, 128), 0.25),
        "toolbar": toolbar,
        "tab_text": text or best_text(toolbar),
        "tab_background_text": text or best_text(frame),
        "bookmark_text": text or best_text(toolbar),
        "toolbar_button_icon": text or best_text(toolbar),
        "omnibox_background": omnibox,
        "omnibox_text": text or best_text(omnibox),
        "ntp_background": ntp,
        "ntp_text": text or best_text(ntp),
    }
    palette["ntp_link"] = accent or pick_link_color(ntp, palette["ntp_text"])
    return palette


def pick_link_color(background, text):
    """Warna tautan: biru/kuning yang masih kontras dengan latar, atau warna teks kalau tidak ada."""
    candidates = [(138, 180, 248), (255, 214, 10)] if is_dark(background) else [(26, 84, 196), (122, 74, 0)]
    for candidate in candidates:
        if contrast_ratio(candidate, background) >= WCAG_AA:
            return candidate
    return text


CHECKS = (
    ("Teks tab aktif", "tab_text", "toolbar"),
    ("Teks tab tidak aktif", "tab_background_text", "frame"),
    ("Teks bookmark", "bookmark_text", "toolbar"),
    ("Teks bilah alamat", "omnibox_text", "omnibox_background"),
    ("Teks tab baru", "ntp_text", "ntp_background"),
    ("Tautan tab baru", "ntp_link", "ntp_background"),
)


def contrast_report(palette):
    """Daftar (label, rasio, lulus) untuk setiap pasangan teks dan latar."""
    rows = []
    for label, fg, bg in CHECKS:
        ratio = contrast_ratio(palette[fg], palette[bg])
        rows.append((label, ratio, ratio >= WCAG_AA))
    return rows


# --- manifest ----------------------------------------------------------------

def chrome_manifest(name, palette, version="1.0"):
    return {
        "manifest_version": 3,
        "name": name,
        "version": version,
        "description": f"Tema Chrome buatan sendiri: {name}",
        "theme": {
            "colors": {key: list(rgb) for key, rgb in palette.items()},
            "tints": {"buttons": tint_for(palette["toolbar_button_icon"])},
            "properties": {"ntp_background_alignment": "bottom"},
        },
    }


def tint_for(rgb):
    """Tint HSL untuk ikon tombol: [-1, -1, l] = pertahankan warna, ubah kecerahan saja."""
    _, l, _ = colorsys.rgb_to_hls(*(v / 255 for v in rgb))
    return [-1, -1, round(l, 2)]


def slug(name):
    cleaned = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return cleaned or "tema"


def firefox_manifest(name, palette, version="1.0"):
    """Firefox memakai nama kunci yang sedikit berbeda dan nilai warna CSS."""
    c = {key: to_hex(rgb) for key, rgb in palette.items()}
    return {
        "manifest_version": 3,
        "name": name,
        "version": version,
        "description": f"Tema Firefox buatan sendiri: {name}",
        "browser_specific_settings": {"gecko": {"id": f"{slug(name)}@app-ideas-python.local"}},
        "theme": {
            "colors": {
                "frame": c["frame"],
                "frame_inactive": c["frame_inactive"],
                "tab_background_text": c["tab_background_text"],
                "tab_selected": c["toolbar"],
                "tab_text": c["tab_text"],
                "tab_line": c["ntp_link"],
                "toolbar": c["toolbar"],
                "toolbar_text": c["bookmark_text"],
                "icons": c["toolbar_button_icon"],
                "toolbar_field": c["omnibox_background"],
                "toolbar_field_text": c["omnibox_text"],
                "popup": c["toolbar"],
                "popup_text": c["tab_text"],
                "ntp_background": c["ntp_background"],
                "ntp_text": c["ntp_text"],
            }
        },
    }


# --- pratinjau ---------------------------------------------------------------

def _font(size):
    from PIL import ImageFont
    for name in ("segoeui.ttf", "DejaVuSans.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_preview(palette, name, size=(960, 540)):
    """Gambar tiruan jendela browser dengan warna tema (objek PIL.Image)."""
    from PIL import Image, ImageDraw

    width, height = size
    p = palette
    img = Image.new("RGB", size, p["ntp_background"])
    draw = ImageDraw.Draw(img)
    small, normal, big = _font(14), _font(16), _font(34)

    # Bingkai dan tab
    draw.rectangle((0, 0, width, 46), fill=p["frame"])
    tabs = [("Tab Baru", True), ("Dokumentasi", False), ("Catatan", False)]
    x = 12
    for label, active in tabs:
        box = (x, 8, x + 210, 46)
        if active:
            draw.rounded_rectangle(box, radius=10, fill=p["toolbar"])
            draw.rectangle((box[0], 30, box[2], 46), fill=p["toolbar"])
        color = p["tab_text"] if active else p["tab_background_text"]
        draw.ellipse((x + 14, 20, x + 28, 34), outline=color, width=2)
        draw.text((x + 38, 17), label, font=small, fill=color)
        draw.text((x + 188, 15), "×", font=normal, fill=color)
        x += 218

    # Toolbar dan bilah alamat
    draw.rectangle((0, 46, width, 94), fill=p["toolbar"])
    icon = p["toolbar_button_icon"]
    for i, glyph in enumerate(("←", "→")):
        draw.text((18 + i * 34, 56), glyph, font=normal, fill=icon)
    draw.arc((88, 61, 106, 79), start=-60, end=250, fill=icon, width=2)  # ikon muat ulang
    draw.polygon([(102, 57), (110, 63), (101, 67)], fill=icon)
    draw.rounded_rectangle((120, 53, width - 70, 87), radius=17, fill=p["omnibox_background"])
    draw.text((142, 60), "Telusuri atau ketik alamat web", font=normal, fill=p["omnibox_text"])
    draw.ellipse((width - 50, 58, width - 26, 82), outline=icon, width=2)

    # Bilah bookmark
    draw.rectangle((0, 94, width, 122), fill=p["toolbar"])
    for i, label in enumerate(("Kuliah", "Proyek", "Python Docs", "Berita")):
        draw.text((20 + i * 120, 99), label, font=small, fill=p["bookmark_text"])

    # Halaman tab baru
    title_box = draw.textbbox((0, 0), name, font=big)
    title_w = title_box[2] - title_box[0]
    draw.text(((width - title_w) / 2, 220), name, font=big, fill=p["ntp_text"])
    draw.rounded_rectangle((width / 2 - 260, 290, width / 2 + 260, 334), radius=22,
                           outline=p["ntp_text"], width=2)
    draw.text((width / 2 - 236, 300), "Cari di web", font=normal, fill=p["ntp_text"])
    links = "Pintasan  ·  Riwayat  ·  Unduhan"
    link_box = draw.textbbox((0, 0), links, font=normal)
    draw.text(((width - (link_box[2] - link_box[0])) / 2, 370), links, font=normal, fill=p["ntp_link"])
    return img


# --- menulis berkas ------------------------------------------------------------

NUMBER_LIST_RE = re.compile(r"\[\s*(-?[\d.]+),\s*(-?[\d.]+),\s*(-?[\d.]+)\s*\]")


def dump_manifest(manifest):
    """JSON berindentasi, tapi daftar angka (warna RGB) tetap satu baris supaya mudah dibaca."""
    text = json.dumps(manifest, indent=2, ensure_ascii=False)
    return NUMBER_LIST_RE.sub(r"[\1, \2, \3]", text) + "\n"


def write_extension(folder, manifest):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "manifest.json")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(dump_manifest(manifest))
    return path


def zip_folder(folder, target):
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for root, _, files in os.walk(folder):
            for file in sorted(files):
                full = os.path.join(root, file)
                archive.write(full, os.path.relpath(full, folder))
    return target


def format_report(rows):
    lines = ["Kontras teks (minimal WCAG AA 4.5:1):"]
    for label, ratio, ok in rows:
        lines.append(f"  {'OK   ' if ok else 'KURANG'} {label:<22} {ratio:5.2f}:1")
    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(description="Buat tema Chrome (dan Firefox) dari warna pilihan sendiri.")
    parser.add_argument("--name", help="nama tema (bawaan: dari preset atau warna dasar)")
    parser.add_argument("--base", help="warna dasar toolbar, misalnya #1f6f78")
    parser.add_argument("--preset", choices=sorted(PRESETS), help="pakai preset warna")
    parser.add_argument("--frame", help="timpa warna bingkai jendela")
    parser.add_argument("--text", help="timpa semua warna teks")
    parser.add_argument("--ntp", help="timpa latar halaman tab baru")
    parser.add_argument("--accent", help="timpa warna tautan di tab baru")
    parser.add_argument("-o", "--out", help="folder keluaran (bawaan: tema-<nama>)")
    parser.add_argument("--firefox", action="store_true", help="buat juga versi Firefox")
    parser.add_argument("--zip", action="store_true", help="buat berkas .zip untuk diunggah ke toko ekstensi")
    parser.add_argument("--strict", action="store_true", help="gagal kalau ada teks dengan kontras kurang")
    parser.add_argument("--no-preview", action="store_true", help="jangan buat gambar pratinjau")
    parser.add_argument("--list-presets", action="store_true", help="tampilkan daftar preset")
    return parser


def resolve_options(args):
    """Gabungkan preset dan argumen. Mengembalikan (nama, warna dasar, kamus timpaan)."""
    chosen = dict(PRESETS[args.preset]) if args.preset else {}
    base_text = args.base or chosen.get("base")
    if not base_text:
        raise ValueError("Pilih --base WARNA atau --preset NAMA (lihat --list-presets).")
    overrides = {}
    for key in ("frame", "text", "ntp", "accent"):
        value = getattr(args, key) or chosen.get(key)
        if value:
            overrides[key] = parse_hex(value)
    base = parse_hex(base_text)
    name = args.name or (f"Tema {args.preset}" if args.preset else f"Tema {to_hex(base)}")
    return name.strip(), base, overrides


def main(argv=None):
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    if args.list_presets:
        for key, preset in sorted(PRESETS.items()):
            print(f"{key:<16} {preset['base']}  {preset['description']}")
        return 0
    try:
        name, base, overrides = resolve_options(args)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    if not name or len(name) > 45:
        print("Error: nama tema harus 1 sampai 45 karakter.", file=sys.stderr)
        return 1
    palette = build_palette(base, **overrides)
    rows = contrast_report(palette)
    print(format_report(rows))
    weak = [label for label, _, ok in rows if not ok]
    if weak and args.strict:
        print(f"Error: kontras kurang untuk {', '.join(weak)}. Pilih warna teks atau latar lain.", file=sys.stderr)
        return 1
    if weak:
        print("Peringatan: sebagian teks kontrasnya kurang dan bisa sulit dibaca.")

    out = args.out or f"tema-{slug(name)}"
    chrome_dir = os.path.join(out, "chrome")
    write_extension(chrome_dir, chrome_manifest(name, palette))
    print(f"\nTema Chrome: {chrome_dir}")
    print("  Pasang: buka chrome://extensions, nyalakan Developer mode, klik 'Load unpacked', pilih folder itu.")
    if args.firefox:
        firefox_dir = os.path.join(out, "firefox")
        write_extension(firefox_dir, firefox_manifest(name, palette))
        print(f"Tema Firefox: {firefox_dir}")
        print("  Pasang sementara: buka about:debugging > This Firefox > 'Load Temporary Add-on', pilih manifest.json.")
    if args.zip:
        print(f"Zip Chrome Web Store: {zip_folder(chrome_dir, os.path.join(out, slug(name) + '-chrome.zip'))}")
        if args.firefox:
            print(f"Zip Firefox Add-ons: {zip_folder(firefox_dir, os.path.join(out, slug(name) + '-firefox.zip'))}")
    if not args.no_preview:
        preview = os.path.join(out, "preview.png")
        render_preview(palette, name).save(preview)
        print(f"Pratinjau: {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
