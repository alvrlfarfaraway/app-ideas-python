"""FlipImage: satu gambar diulang dalam matriks 2x2, tiap gambar bisa dibalik
vertikal atau horizontal dengan tombol panah di sampingnya.

Butuh Pillow (`pip install pillow`).

Jalankan:
    python flipimage.py                              # jendela Tkinter dengan gambar contoh
    python flipimage.py --image foto.jpg             # gambar sendiri (berkas atau URL)
    python flipimage.py --flip 1:left --flip 3:up -o hasil.png   # tanpa jendela, simpan ke berkas
Nomor gambar: 1 kiri-atas, 2 kanan-atas, 3 kiri-bawah, 4 kanan-bawah.
"""

import argparse
import io
import os
import urllib.error
import urllib.request

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

TILE = 220
DIRECTIONS = ("up", "down", "left", "right")


def sample_image(size=TILE):
    """Gambar contoh yang sengaja tidak simetris (huruf F di atas gradasi) supaya pembalikan terlihat."""
    image = Image.new("RGB", (size, size))
    pixels = image.load()
    for y in range(size):
        for x in range(size):
            pixels[x, y] = (40 + 180 * x // size, 90 + 100 * y // size, 200 - 120 * x // size)
    draw = ImageDraw.Draw(image)
    draw.text((size * 0.28, size * 0.1), "F", fill="white", font=ImageFont.load_default(size=int(size * 0.8)))
    draw.rectangle((0, 0, size - 1, size - 1), outline="white", width=3)
    return image


def load_image(source, size=TILE):
    """Muat gambar dari berkas atau URL http(s), dipotong ke persegi. ValueError bila tidak ada/bukan gambar."""
    try:
        if source.lower().startswith(("http://", "https://")):
            with urllib.request.urlopen(source, timeout=10) as response:
                data = io.BytesIO(response.read())
            image = Image.open(data)
        else:
            if not os.path.isfile(source):
                raise ValueError(f"Gambar '{source}' tidak ditemukan.")
            image = Image.open(source)
        image = image.convert("RGB")
    except (urllib.error.URLError, TimeoutError):
        raise ValueError(f"Gambar di '{source}' tidak ditemukan atau tidak bisa diunduh.") from None
    except (UnidentifiedImageError, OSError):
        raise ValueError(f"'{source}' bukan berkas gambar yang valid.") from None
    return ImageOps.fit(image, (size, size))


class FlipBoard:
    """Papan 2x2. Tiap gambar punya status balik horizontal dan vertikal sendiri-sendiri."""

    def __init__(self, image):
        self.image = image
        self.state = [{"h": False, "v": False} for _ in range(4)]

    def flip(self, index, direction):
        """Balik gambar ke-index (0-3). left/right membalik horizontal, up/down membalik vertikal."""
        if not 0 <= index < 4:
            raise ValueError("Nomor gambar harus 1 sampai 4.")
        if direction not in DIRECTIONS:
            raise ValueError(f"Arah harus salah satu dari: {', '.join(DIRECTIONS)}.")
        axis = "h" if direction in ("left", "right") else "v"
        self.state[index][axis] = not self.state[index][axis]

    def tile(self, index):
        tile = self.image
        if self.state[index]["h"]:
            tile = ImageOps.mirror(tile)
        if self.state[index]["v"]:
            tile = ImageOps.flip(tile)
        return tile

    def render(self, gap=6):
        width, height = self.image.size
        canvas = Image.new("RGB", (width * 2 + gap, height * 2 + gap), "white")
        for index in range(4):
            canvas.paste(self.tile(index), ((index % 2) * (width + gap), (index // 2) * (height + gap)))
        return canvas


def run_gui(board):
    """Jendela Tkinter: gambar 2x2 dengan empat tombol panah di samping tiap gambar."""
    import tkinter as tk

    from PIL import ImageTk

    root = tk.Tk()
    root.title("FlipImage")
    holders = []  # simpan referensi PhotoImage supaya tidak dibersihkan garbage collector
    labels = []

    def refresh(index):
        photo = ImageTk.PhotoImage(board.tile(index))
        holders[index] = photo
        labels[index].configure(image=photo)

    arrows = {"up": "▲", "down": "▼", "left": "◀", "right": "▶"}
    for index in range(4):
        cell = tk.Frame(root, padx=8, pady=8)
        cell.grid(row=index // 2, column=index % 2)
        holders.append(None)
        labels.append(tk.Label(cell))
        labels[index].grid(row=1, column=1)
        positions = {"up": (0, 1), "down": (2, 1), "left": (1, 0), "right": (1, 2)}
        for direction, (row, column) in positions.items():
            button = tk.Button(cell, text=arrows[direction], width=2,
                               command=lambda i=index, d=direction: (board.flip(i, d), refresh(i)))
            button.grid(row=row, column=column)
        refresh(index)
    return root


def main(argv=None):
    parser = argparse.ArgumentParser(description="FlipImage: balik gambar dalam matriks 2x2.")
    parser.add_argument("--image", help="berkas atau URL gambar (bawaan: gambar contoh)")
    parser.add_argument("--flip", action="append", default=[], metavar="N:ARAH",
                        help="balik gambar N (1-4); ARAH = up, down, left, right. Boleh diulang")
    parser.add_argument("-o", "--output", help="simpan hasil ke berkas dan tanpa jendela")
    args = parser.parse_args(argv)
    try:
        board = FlipBoard(load_image(args.image) if args.image else sample_image())
        for spec in args.flip:
            number, _, direction = spec.partition(":")
            if not number.isdigit():
                raise ValueError(f"Format --flip harus N:ARAH, misalnya 1:left (diterima '{spec}').")
            board.flip(int(number) - 1, direction)
        if args.output:
            board.render().save(args.output)
            print(f"Tersimpan: {args.output}")
            return 0
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    except OSError as error:
        print(f"Error: gagal menyimpan: {error.strerror}")
        return 1
    run_gui(board).mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
