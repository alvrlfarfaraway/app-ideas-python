"""Recipe App: buku resep dengan daftar judul, kartu resep, pencarian ke TheMealDB, dan simpan.

Data resep berupa berkas JSON (sample-recipes.json disalin ke ~/.app-ideas-python/recipes.json saat
pertama dipakai). Hanya pustaka bawaan Python.

Jalankan:
    python recipes.py        # panel interaktif
Perintah: list, show <nomor|judul>, search <kata>, open <nomor>, save, photo, quit
"""

import argparse
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE_FILE = os.path.join(HERE, "sample-recipes.json")
DEFAULT_FILE = os.path.join(os.path.expanduser("~"), ".app-ideas-python", "recipes.json")
API = "https://www.themealdb.com/api/json/v1/1"

MEAL_TYPES = {"breakfast": "sarapan", "lunch": "makan siang", "supper": "makan malam", "snack": "camilan"}
DIFFICULTIES = {"beginner": "pemula", "intermediate": "menengah", "advanced": "mahir"}
# Kategori TheMealDB -> jenis hidangan di buku ini (perkiraan; yang tidak tercantum dianggap makan siang)
CATEGORY_TO_MEAL_TYPE = {"breakfast": "breakfast", "dessert": "snack", "starter": "snack", "side": "snack"}


def validate_recipe(recipe):
    """Pastikan resep punya semua bagian wajib dengan nilai yang sah; ValueError menyebut yang salah."""
    if not isinstance(recipe, dict):
        raise ValueError("Resep harus berupa objek.")
    title = recipe.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Resep harus punya judul.")
    where = f"Resep '{title}'"
    if recipe.get("meal_type") not in MEAL_TYPES:
        raise ValueError(f"{where}: jenis hidangan harus salah satu dari {', '.join(MEAL_TYPES)}.")
    serves = recipe.get("serves")
    if serves is not None and (isinstance(serves, bool) or not isinstance(serves, int) or serves < 1):
        raise ValueError(f"{where}: jumlah porsi harus bilangan bulat positif (atau kosong).")
    if recipe.get("difficulty") is not None and recipe["difficulty"] not in DIFFICULTIES:
        raise ValueError(f"{where}: tingkat kesulitan harus salah satu dari {', '.join(DIFFICULTIES)} (atau kosong).")
    ingredients = recipe.get("ingredients")
    if not isinstance(ingredients, list) or not ingredients or not all(
            isinstance(i, dict) and isinstance(i.get("item"), str) and i["item"].strip()
            and isinstance(i.get("amount", ""), str) for i in ingredients):
        raise ValueError(f"{where}: bahan harus daftar berisi {{item, amount}}.")
    steps = recipe.get("steps")
    if not isinstance(steps, list) or not steps or not all(isinstance(s, str) and s.strip() for s in steps):
        raise ValueError(f"{where}: langkah persiapan harus daftar teks yang tidak kosong.")
    if recipe.get("photo") is not None and not isinstance(recipe["photo"], str):
        raise ValueError(f"{where}: foto harus berupa alamat teks.")
    return recipe


def format_card(recipe):
    """Kartu resep: judul, jenis hidangan, porsi, tingkat kesulitan, bahan dengan takaran, dan langkah."""
    serves = f"{recipe['serves']} orang" if recipe.get("serves") else "tidak diketahui"
    difficulty = DIFFICULTIES.get(recipe.get("difficulty"), "tidak diketahui")
    lines = ["┌" + "─" * 58, f"│ {recipe['title'].upper()}", "└" + "─" * 58,
             f"Jenis hidangan : {MEAL_TYPES[recipe['meal_type']]} ({recipe['meal_type']})",
             f"Untuk          : {serves}", f"Kesulitan      : {difficulty}"]
    if recipe.get("source"):
        lines.append(f"Sumber         : {recipe['source']}")
    lines += ["", "Bahan:"]
    lines += [f"  - {i['amount'] + ' ' if i.get('amount') else ''}{i['item']}" for i in recipe["ingredients"]]
    lines += ["", "Langkah:"] + [f"  {n}. {step}" for n, step in enumerate(recipe["steps"], start=1)]
    if recipe.get("photo"):
        lines += ["", f"Foto: {recipe['photo']}  (ketik 'photo' untuk membuka)"]
    return "\n".join(lines)


class RecipeBook:
    def __init__(self, path=DEFAULT_FILE, sample=SAMPLE_FILE):
        self.path = path
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            shutil.copyfile(sample, path)  # buku pribadi dimulai dari resep bawaan
        self.recipes = self._load()

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError:
            raise ValueError(f"Berkas resep '{self.path}' rusak dan tidak dibaca agar tidak tertimpa.") from None
        if not isinstance(data, list):
            raise ValueError(f"Format berkas resep '{self.path}' tidak dikenali.")
        return [validate_recipe(r) for r in data]

    def _save(self):
        temp = self.path + ".tmp"
        with open(temp, "w", encoding="utf-8") as file:
            json.dump(self.recipes, file, ensure_ascii=False, indent=2)
        os.replace(temp, self.path)

    def titles(self):
        return [r["title"] for r in self.recipes]

    def find(self, query):
        """Resep menurut nomor (1, 2, ...) atau judul (tidak peduli huruf besar-kecil; potongan judul boleh bila unik)."""
        query = str(query).strip()
        if query.isdigit():
            number = int(query)
            if not 1 <= number <= len(self.recipes):
                raise ValueError(f"Nomor resep harus 1 sampai {len(self.recipes)}.")
            return self.recipes[number - 1]
        exact = [r for r in self.recipes if r["title"].lower() == query.lower()]
        partial = [r for r in self.recipes if query.lower() in r["title"].lower()]
        found = exact or partial
        if not query or not found:
            raise ValueError(f"Resep '{query}' tidak ada di daftar.")
        if len(found) > 1:
            raise ValueError(f"'{query}' cocok dengan {len(found)} resep: " + ", ".join(r["title"] for r in found))
        return found[0]

    def add(self, recipe):
        validate_recipe(recipe)
        if recipe["title"].lower() in (t.lower() for t in self.titles()):
            raise ValueError(f"Resep '{recipe['title']}' sudah ada di buku resep.")
        self.recipes.append(recipe)
        self._save()


# --- TheMealDB (bonus) --------------------------------------------------------

def fetch_json(url, urlopen=urllib.request.urlopen):
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "app-ideas-python/1.0"})
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise ValueError(f"TheMealDB menjawab kode {error.code}.") from None
    except (urllib.error.URLError, TimeoutError):
        raise ValueError("Tidak bisa menjangkau TheMealDB. Periksa koneksi internet.") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("Jawaban TheMealDB bukan JSON yang valid.") from None


def split_steps(instructions):
    """Pecah teks instruksi menjadi langkah: per paragraf; satu paragraf panjang dipecah per kalimat."""
    text = instructions.replace("\r\n", "\n").replace("\r", "\n")
    parts = [p.strip() for p in re.split(r"\n+", text)]
    parts = [p for p in parts if p and not re.fullmatch(r"(?i)(step\s*)?\d+[.:)]?", p)]  # buang baris "1" atau "STEP 2"
    parts = [re.sub(r"(?i)^(step\s*)?\d+[.:)]\s+", "", p) for p in parts]
    if len(parts) == 1:
        parts = [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", parts[0]) if s]
    return parts


def meal_to_recipe(raw):
    """Ubah objek meal TheMealDB menjadi resep buku ini. Porsi dan kesulitan tidak ada di API, jadi dikosongkan."""
    try:
        ingredients = []
        for number in range(1, 21):
            item = (raw.get(f"strIngredient{number}") or "").strip()
            if item:
                ingredients.append({"item": item, "amount": (raw.get(f"strMeasure{number}") or "").strip()})
        category = (raw.get("strCategory") or "").strip()
        recipe = {"title": raw["strMeal"].strip(), "meal_type": CATEGORY_TO_MEAL_TYPE.get(category.lower(), "lunch"),
                  "serves": None, "difficulty": None, "ingredients": ingredients,
                  "steps": split_steps(raw.get("strInstructions") or ""),
                  "photo": raw.get("strMealThumb") or None, "source": f"TheMealDB ({category or 'tanpa kategori'})"}
        return validate_recipe(recipe)
    except (KeyError, AttributeError, TypeError):
        raise ValueError("Data resep dari TheMealDB tidak lengkap.") from None


def search_meals(name, urlopen=urllib.request.urlopen):
    """Daftar resep yang cocok dengan nama makanan. ValueError berisi peringatan kalau tidak ada yang cocok."""
    name = name.strip()
    if not name:
        raise ValueError("Ketik nama makanan yang dicari.")
    data = fetch_json(f"{API}/search.php?{urllib.parse.urlencode({'s': name})}", urlopen)
    meals = data.get("meals") if isinstance(data, dict) else None
    if not meals:
        raise ValueError(f"Tidak ada resep yang cocok dengan '{name}'.")
    results = []
    for raw in meals:
        try:
            results.append(meal_to_recipe(raw))
        except ValueError:
            continue  # lewati data rusak, tampilkan sisanya
    if not results:
        raise ValueError(f"Tidak ada resep yang cocok dengan '{name}'.")
    return results


class App:
    """Logika panel: kartu yang sedang tampil, hasil pencarian terakhir, dan tombol Save. Terpisah dari input/output."""

    def __init__(self, book, urlopen=urllib.request.urlopen, open_url=webbrowser.open):
        self.book, self.urlopen, self.open_url = book, urlopen, open_url
        self.card = None
        self.from_api = False  # kartu yang tampil berasal dari pencarian API (boleh disimpan)
        self.results = []

    def show(self, query):
        self.card, self.from_api = self.book.find(query), False  # kartu baru menggantikan yang lama
        return format_card(self.card)

    def search(self, name):
        self.results = search_meals(name, self.urlopen)
        return "\n".join(f"  {n}. {r['title']}  ({r['source']})" for n, r in enumerate(self.results, start=1))

    def open_result(self, number):
        if not self.results:
            raise ValueError("Belum ada hasil pencarian. Cari dulu dengan: search <kata>")
        if not number.strip().isdigit() or not 1 <= int(number) <= len(self.results):
            raise ValueError(f"Nomor hasil harus 1 sampai {len(self.results)}.")
        self.card, self.from_api = self.results[int(number) - 1], True
        return format_card(self.card)

    @property
    def save_enabled(self):
        """Tombol Save hanya ada untuk resep hasil API yang belum tersimpan."""
        return self.from_api and self.card["title"].lower() not in (t.lower() for t in self.book.titles())

    def save(self):
        if not self.from_api:
            raise ValueError("Hanya resep hasil pencarian yang bisa disimpan; buka satu dengan: open <nomor>")
        self.book.add(self.card)
        self.from_api = False
        return f"Tersimpan: {self.card['title']}"

    def photo(self):
        if not self.card or not self.card.get("photo"):
            raise ValueError("Kartu ini tidak punya foto.")
        self.open_url(self.card["photo"])
        return "Membuka foto di browser."


def interactive(app):
    print("Buku resep. Perintah: list, show <nomor|judul>, search <kata>, open <nomor>, save, photo, quit\n")
    print(list_text(app.book))
    while True:
        try:
            line = input("\n> ").strip()
        except EOFError:
            return 0
        command, _, argument = line.partition(" ")
        try:
            if command in ("quit", "q", "exit"):
                return 0
            elif command == "list":
                print(list_text(app.book))
            elif command == "show":
                print(app.show(argument))
            elif command == "search":
                print(app.search(argument) + "\nBuka salah satunya dengan: open <nomor>")
            elif command == "open":
                print(app.open_result(argument))
                print("\nSimpan ke buku resep dengan perintah: save" if app.save_enabled else "")
            elif command == "save":
                print(app.save())
            elif command == "photo":
                print(app.photo())
            elif command:
                print("Perintah tidak dikenal.")
        except ValueError as error:
            print(f"Peringatan: {error}")


def list_text(book):
    return "Daftar resep:\n" + "\n".join(f"  {n}. {t}" for n, t in enumerate(book.titles(), start=1))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Buku resep.")
    parser.add_argument("-f", "--file", default=DEFAULT_FILE, help="berkas buku resep")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        return interactive(App(RecipeBook(args.file)))
    except (ValueError, OSError) as error:
        print(f"Error: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
