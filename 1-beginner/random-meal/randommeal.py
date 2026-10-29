"""Random Meal Generator: ambil resep makanan acak dari TheMealDB (https://www.themealdb.com/api.php).

Menampilkan nama, bahan, instruksi, dan gambar makanan; video YouTube-nya sebagai bonus.
Hanya memakai pustaka bawaan Python; jendela gambar (--gui) memakai Tkinter dan Pillow.

Jalankan:
    python randommeal.py              # satu resep acak di terminal
    python randommeal.py --picture    # simpan gambarnya (meal.jpg) dan buka
    python randommeal.py --gui        # jendela dengan tombol dan gambar (butuh: pip install pillow)
"""

import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.request
import webbrowser

API = "https://www.themealdb.com/api/json/v1/1"
MAX_IMAGE_BYTES = 5_000_000
USER_AGENT = {"User-Agent": "app-ideas-python/1.0"}


class Meal:
    def __init__(self, id_, name, category, area, instructions, ingredients, thumbnail, youtube):
        self.id = id_
        self.name = name
        self.category = category
        self.area = area
        self.instructions = instructions
        self.ingredients = ingredients  # daftar (bahan, takaran)
        self.thumbnail = thumbnail
        self.youtube = youtube


def fetch_json(url, urlopen=urllib.request.urlopen):
    try:
        request = urllib.request.Request(url, headers=USER_AGENT)
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise ValueError(f"TheMealDB menjawab kode {error.code}.") from None
    except (urllib.error.URLError, TimeoutError):
        raise ValueError("Tidak bisa menjangkau TheMealDB. Periksa koneksi internet.") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("Jawaban TheMealDB bukan JSON yang valid.") from None


def parse_meal(raw):
    """Ubah satu objek meal dari API (strIngredient1..20 + strMeasure1..20) menjadi Meal."""
    try:
        name = raw["strMeal"].strip()
        instructions = (raw.get("strInstructions") or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        ingredients = []
        for number in range(1, 21):
            ingredient = (raw.get(f"strIngredient{number}") or "").strip()
            if ingredient:
                ingredients.append((ingredient, (raw.get(f"strMeasure{number}") or "").strip()))
        return Meal(raw.get("idMeal"), name, raw.get("strCategory") or "", raw.get("strArea") or "",
                    instructions, ingredients, raw.get("strMealThumb") or "", raw.get("strYoutube") or "")
    except (KeyError, AttributeError, TypeError):
        raise ValueError("Data makanan dari TheMealDB tidak lengkap atau formatnya berubah.") from None


def random_meal(urlopen=urllib.request.urlopen):
    data = fetch_json(f"{API}/random.php", urlopen)
    meals = data.get("meals") if isinstance(data, dict) else None
    if not meals:
        raise ValueError("TheMealDB tidak mengembalikan makanan.")
    return parse_meal(meals[0])


def fetch_image(url, urlopen=urllib.request.urlopen):
    """Unduh gambar (bytes). ValueError kalau bukan gambar, terlalu besar, atau gagal diunduh."""
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("Alamat gambar tidak valid.")
    try:
        with urlopen(urllib.request.Request(url, headers=USER_AGENT), timeout=15) as response:
            kind = response.headers.get("Content-Type", "") if hasattr(response, "headers") else ""
            if kind and not kind.lower().startswith("image/"):
                raise ValueError(f"Gambar ditolak: jenis konten '{kind.split(';')[0]}' bukan gambar.")
            data = response.read(MAX_IMAGE_BYTES + 1)
    except urllib.error.HTTPError as error:
        raise ValueError(f"Gambar tidak ditemukan (kode {error.code}).") from None
    except (urllib.error.URLError, TimeoutError):
        raise ValueError("Gambar tidak bisa diunduh. Periksa koneksi internet.") from None
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Gambar terlalu besar (lebih dari 5 MB).")
    if not data:
        raise ValueError("Gambar kosong.")
    return data


def format_meal(meal):
    lines = [meal.name, "=" * len(meal.name)]
    info = " · ".join(part for part in (meal.category, meal.area) if part)
    if info:
        lines.append(info)
    lines += ["", "Bahan:"]
    lines += [f"  - {measure + ' ' if measure else ''}{ingredient}" for ingredient, measure in meal.ingredients]
    lines += ["", "Instruksi:", meal.instructions or "(tidak ada instruksi)"]
    lines += ["", f"Gambar: {meal.thumbnail or '(tidak ada)'}"]
    if meal.youtube:
        lines.append(f"Video : {meal.youtube}")
    return "\n".join(lines)


def save_picture(meal, folder=".", urlopen=urllib.request.urlopen):
    """Simpan gambar makanan sebagai meal.jpg di `folder`; mengembalikan path-nya."""
    data = fetch_image(meal.thumbnail, urlopen)
    path = os.path.join(folder, "meal.jpg")
    with open(path, "wb") as file:
        file.write(data)
    return path


class MealWindow:
    """Jendela Tkinter: tombol "Meal acak" mengambil resep baru tiap diklik."""

    def __init__(self, root, get_meal=random_meal, get_image=fetch_image, open_url=None, threaded=True):
        import tkinter as tk
        from tkinter import scrolledtext

        self.tk, self.root = tk, root
        self.get_meal, self.get_image, self.threaded = get_meal, get_image, threaded
        self.open_url = open_url or webbrowser.open
        self.photo = None
        self.meal = None
        root.title("Random Meal Generator")
        top = tk.Frame(root, padx=10, pady=8)
        top.pack(fill="x")
        self.button = tk.Button(top, text="Meal acak!", command=self.new_meal, font=("Segoe UI", 11, "bold"))
        self.button.pack(side="left")
        self.status = tk.Label(top, text="Klik tombol untuk mendapat resep.", anchor="w")
        self.status.pack(side="left", padx=10)
        self.title_label = tk.Label(root, text="", font=("Segoe UI", 16, "bold"))
        self.title_label.pack()
        self.info_label = tk.Label(root, text="")
        self.info_label.pack()
        self.image_label = tk.Label(root)
        self.image_label.pack(pady=6)
        self.video_button = tk.Button(root, text="Buka video YouTube", command=self.open_video)
        self.text = scrolledtext.ScrolledText(root, width=70, height=16, wrap="word")
        self.text.pack(padx=10, pady=8, fill="both", expand=True)
        self.text.configure(state="disabled")

    def new_meal(self):
        self.button.configure(state="disabled")
        self.status.configure(text="Mengambil resep...")
        if self.threaded:
            import threading
            threading.Thread(target=self._load, daemon=True).start()
        else:
            self._load()

    def _load(self):
        try:
            meal = self.get_meal()
            try:
                image = self.get_image(meal.thumbnail)
            except ValueError:
                image = None  # resep tetap tampil tanpa gambar
            result = (meal, image, None)
        except ValueError as error:
            result = (None, None, str(error))
        if self.threaded:
            self.root.after(0, lambda: self.show(*result))
        else:
            self.show(*result)

    def show(self, meal, image, error):
        self.button.configure(state="normal")
        if error:
            self.status.configure(text=f"Gagal: {error}")
            return
        self.meal = meal
        self.status.configure(text="Klik lagi untuk resep lain.")
        self.title_label.configure(text=meal.name)
        self.info_label.configure(text=" · ".join(p for p in (meal.category, meal.area) if p))
        self.photo = None
        if image:
            try:
                from PIL import Image, ImageTk
                picture = Image.open(io.BytesIO(image)).convert("RGB")
                picture.thumbnail((320, 320))
                self.photo = ImageTk.PhotoImage(picture)
            except Exception:  # gambar rusak atau Pillow tidak ada: tampilkan tanpa gambar
                self.photo = None
        self.image_label.configure(image=self.photo or "", text="" if self.photo else "(gambar tidak tersedia)")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", "Bahan:\n" + "\n".join(
            f"  - {m + ' ' if m else ''}{i}" for i, m in meal.ingredients) + "\n\nInstruksi:\n" + meal.instructions)
        self.text.configure(state="disabled")
        if meal.youtube:
            self.video_button.pack(before=self.text)
        else:
            self.video_button.pack_forget()

    def open_video(self):
        if self.meal and self.meal.youtube:
            self.open_url(self.meal.youtube)


def main(argv=None, urlopen=urllib.request.urlopen):
    parser = argparse.ArgumentParser(description="Resep makanan acak dari TheMealDB.")
    parser.add_argument("--picture", action="store_true", help="simpan gambarnya sebagai meal.jpg lalu buka")
    parser.add_argument("--gui", action="store_true", help="buka jendela dengan tombol dan gambar")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if args.gui:
        import tkinter as tk
        root = tk.Tk()
        MealWindow(root, lambda: random_meal(urlopen), lambda url: fetch_image(url, urlopen))
        root.mainloop()
        return 0
    try:
        meal = random_meal(urlopen)
        print(format_meal(meal))
        if args.picture:
            path = save_picture(meal, ".", urlopen)
            print(f"\nGambar disimpan: {path}")
            if hasattr(os, "startfile"):
                os.startfile(path)
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
