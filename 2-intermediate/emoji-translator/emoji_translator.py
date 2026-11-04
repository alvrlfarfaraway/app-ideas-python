"""Emoji Translator: ubah kata-kata dalam kalimat menjadi emoji.

Kamus ditulis sendiri untuk bahasa Indonesia dan Inggris, termasuk sinonim
(misalnya 'kucing', 'meong', dan 'kitten' semuanya menjadi 🐱). Frasa dua-tiga
kata ('es krim', 'hot dog') dicocokkan lebih dulu. Kata tanpa emoji dibiarkan.

Jalankan:
    python emoji_translator.py                                # jendela Tkinter
    python emoji_translator.py "saya suka kucing dan kopi"    # terminal
    python emoji_translator.py "i love pizza" --lang en
"""

import argparse
import re
import sys

# (emoji, kata Indonesia, kata Inggris). Kata pertama adalah kata utama, sisanya sinonim.
EMOJI_TABLE = (
    # perasaan dan wajah
    ("😀", "senang, gembira, bahagia, ceria", "happy, glad, joy, cheerful"),
    ("😂", "tertawa, ketawa, ngakak, lucu", "laugh, laughing, lol, funny"),
    ("😢", "sedih, menangis, nangis", "sad, cry, crying, unhappy"),
    ("😡", "marah, kesal, geram", "angry, mad, furious"),
    ("😱", "takut, kaget, ngeri", "scared, afraid, shocked"),
    ("😴", "tidur, ngantuk, mengantuk, lelah, capek", "sleep, sleepy, tired"),
    ("😎", "keren, mantap", "cool, awesome"),
    ("🤔", "berpikir, mikir, bingung, hmm", "think, thinking, confused, hmm"),
    ("😍", "naksir, terpesona", "crush, adore"),
    ("🤒", "sakit, demam", "sick, ill, fever"),
    ("❤️", "cinta, sayang, suka, love", "love, like, heart"),
    ("💔", "patah hati", "heartbreak, heartbroken"),
    ("👍", "oke, ok, setuju, bagus, sip", "ok, okay, agree, good, yes"),
    ("👎", "jelek, buruk", "bad, dislike"),
    ("👋", "halo, hai, dadah", "hello, hi, hey, bye"),
    ("🙏", "terima kasih, makasih, tolong, mohon", "thanks, thank you, please"),
    ("👏", "tepuk tangan, selamat", "applause, congrats, congratulations"),
    ("💪", "kuat, semangat", "strong, strength"),
    ("🎉", "pesta, perayaan, hore", "party, celebrate, celebration, hooray"),
    ("🎂", "ulang tahun, kue ulang tahun", "birthday, birthday cake"),
    ("🎁", "hadiah, kado", "gift, present"),
    # orang
    ("👨", "pria, laki-laki, bapak, ayah", "man, father, dad"),
    ("👩", "wanita, perempuan, ibu", "woman, mother, mom"),
    ("👶", "bayi", "baby"),
    ("👦", "anak laki-laki", "boy"),
    ("👧", "anak perempuan", "girl"),
    ("👪", "keluarga", "family"),
    ("🧑‍🏫", "guru, dosen", "teacher, lecturer"),
    ("🧑‍🎓", "murid, siswa, mahasiswa, pelajar", "student, pupil"),
    ("👮", "polisi", "police, cop"),
    ("🧑‍⚕️", "dokter, perawat", "doctor, nurse"),
    ("🧑‍💻", "programmer, koder", "programmer, coder, developer"),
    # hewan
    ("🐱", "kucing, meong, kitten", "cat, kitten, kitty"),
    ("🐶", "anjing, guguk", "dog, puppy, doggy"),
    ("🐭", "tikus", "mouse, rat"),
    ("🐰", "kelinci", "rabbit, bunny"),
    ("🐻", "beruang", "bear"),
    ("🐼", "panda", "panda"),
    ("🐯", "harimau, macan", "tiger"),
    ("🦁", "singa", "lion"),
    ("🐮", "sapi", "cow"),
    ("🐷", "babi", "pig"),
    ("🐸", "katak, kodok", "frog"),
    ("🐵", "monyet, kera", "monkey"),
    ("🐔", "ayam", "chicken, hen"),
    ("🐦", "burung", "bird"),
    ("🐟", "ikan", "fish"),
    ("🐍", "ular", "snake"),
    ("🐢", "kura-kura, penyu", "turtle, tortoise"),
    ("🦋", "kupu-kupu", "butterfly"),
    ("🐝", "lebah", "bee"),
    ("🐜", "semut", "ant"),
    ("🐘", "gajah", "elephant"),
    ("🐴", "kuda", "horse"),
    ("🦆", "bebek, itik", "duck"),
    ("🐊", "buaya", "crocodile"),
    # makanan dan minuman
    ("🍎", "apel", "apple"),
    ("🍌", "pisang", "banana"),
    ("🍇", "anggur", "grape, grapes"),
    ("🍉", "semangka", "watermelon"),
    ("🍊", "jeruk", "orange"),
    ("🍓", "stroberi", "strawberry"),
    ("🥭", "mangga", "mango"),
    ("🍍", "nanas", "pineapple"),
    ("🥥", "kelapa", "coconut"),
    ("🥕", "wortel", "carrot"),
    ("🌶️", "cabai, cabe, pedas", "chili, chilli, pepper, spicy"),
    ("🍚", "nasi", "rice"),
    ("🍜", "mi, mie, bakmi, ramen", "noodle, noodles, ramen"),
    ("🍞", "roti", "bread"),
    ("🍕", "pizza", "pizza"),
    ("🍔", "burger, hamburger", "burger, hamburger"),
    ("🍟", "kentang goreng", "fries, french fries"),
    ("🌭", "hot dog, sosis", "hot dog, sausage"),
    ("🍳", "telur, telor, masak, memasak", "egg, eggs, cook, cooking"),
    ("🍦", "es krim", "ice cream"),
    ("🍰", "kue", "cake"),
    ("🍫", "cokelat, coklat", "chocolate"),
    ("🍬", "permen", "candy, sweets"),
    ("☕", "kopi", "coffee"),
    ("🍵", "teh", "tea"),
    ("🥛", "susu", "milk"),
    ("💧", "air", "water"),
    ("🍽️", "makan, makanan", "eat, eating, food, meal"),
    ("🥤", "minum, minuman", "drink, drinking, beverage"),
    # alam dan cuaca
    ("☀️", "matahari, cerah, panas", "sun, sunny, hot"),
    ("🌙", "bulan, malam", "moon, night"),
    ("⭐", "bintang", "star"),
    ("☁️", "awan, mendung", "cloud, cloudy"),
    ("🌧️", "hujan", "rain, rainy"),
    ("⛈️", "badai, petir", "storm, thunder"),
    ("❄️", "salju, dingin", "snow, cold"),
    ("🌈", "pelangi", "rainbow"),
    ("🔥", "api, kebakaran", "fire, flame"),
    ("🌊", "ombak, gelombang, laut", "wave, sea, ocean"),
    ("🌳", "pohon", "tree"),
    ("🌸", "bunga", "flower, blossom"),
    ("🌹", "mawar", "rose"),
    ("⛰️", "gunung", "mountain"),
    ("🏖️", "pantai", "beach"),
    ("🌍", "bumi, dunia", "earth, world, globe"),
    # tempat dan benda
    ("🏠", "rumah", "house, home"),
    ("🏫", "sekolah", "school"),
    ("🏥", "rumah sakit", "hospital"),
    ("🏢", "kantor", "office"),
    ("🕌", "masjid", "mosque"),
    ("⛪", "gereja", "church"),
    ("🏪", "toko, warung", "shop, store"),
    ("🏙️", "kota", "city"),
    ("🚗", "mobil", "car"),
    ("🏍️", "motor, sepeda motor", "motorcycle, motorbike"),
    ("🚲", "sepeda", "bicycle, bike"),
    ("🚌", "bus, bis", "bus"),
    ("🚆", "kereta, kereta api", "train"),
    ("✈️", "pesawat, terbang", "plane, airplane, fly"),
    ("🚢", "kapal", "ship, boat"),
    ("📱", "hp, ponsel, handphone, telepon", "phone, mobile, smartphone"),
    ("💻", "laptop, komputer", "laptop, computer"),
    ("📚", "buku", "book, books"),
    ("✏️", "pensil, menulis, tulis", "pencil, write, writing"),
    ("📝", "catatan", "note, notes, memo"),
    ("💡", "ide, lampu", "idea, light, bulb"),
    ("⏰", "jam, waktu, alarm", "clock, time, alarm"),
    ("📅", "tanggal, kalender, jadwal", "date, calendar, schedule"),
    ("💰", "uang, duit", "money, cash"),
    ("🔑", "kunci", "key"),
    ("🎵", "musik, lagu", "music, song"),
    ("🎮", "game, gim, main", "game, games, gaming, play"),
    ("⚽", "bola, sepak bola", "ball, soccer, football"),
    ("🏀", "basket", "basketball"),
    ("🎬", "film", "movie, film"),
    ("📷", "kamera, foto", "camera, photo"),
    ("✉️", "surat, email", "letter, mail, email"),
    ("🎒", "tas", "bag, backpack"),
    ("👕", "baju, kaos", "shirt, tshirt, clothes"),
    ("👟", "sepatu", "shoe, shoes, sneakers"),
    # kegiatan dan konsep
    ("🏃", "lari, berlari", "run, running"),
    ("🏊", "berenang, renang", "swim, swimming"),
    ("💼", "kerja, bekerja, pekerjaan", "work, working, job"),
    ("📖", "baca, membaca, belajar", "read, reading, study"),
    ("🗣️", "bicara, berbicara, ngomong", "talk, speak, say"),
    ("👀", "lihat, melihat", "look, see, watch"),
    ("🚀", "roket, cepat", "rocket, fast"),
    ("✅", "benar, betul, selesai", "correct, right, done"),
    ("❌", "salah, tidak, bukan", "wrong, no, not"),
    ("❓", "apa, kenapa, mengapa, bagaimana", "what, why, how"),
    ("⚠️", "awas, hati-hati, peringatan", "warning, careful, caution"),
    ("🆕", "baru", "new"),
    ("🔝", "atas", "top"),
    ("💯", "sempurna, seratus", "perfect, hundred"),
    ("🇮🇩", "indonesia", "indonesia"),
)

LANGUAGES = {"id": "Bahasa Indonesia", "en": "English"}
KEYCAPS = {str(d): f"{d}️⃣" for d in range(10)}
MAX_PHRASE = 3
TOKEN_RE = re.compile(r"[^\W_]+(?:-[^\W_]+)*|[\W_]+")  # kata (boleh berstrip: kupu-kupu) atau bukan kata
SUFFIXES = {"id": ("nya", "ku", "mu"), "en": ()}


def build_lexicon(language):
    """Kamus 'kata/frasa' -> emoji untuk satu bahasa. Frasa disimpan dengan satu spasi."""
    if language not in LANGUAGES:
        raise ValueError(f"Bahasa '{language}' tidak tersedia. Pilih: {', '.join(LANGUAGES)}.")
    column = 1 if language == "id" else 2
    lexicon = {}
    for row in EMOJI_TABLE:
        for word in row[column].split(","):
            key = " ".join(word.lower().split())
            if key:
                lexicon.setdefault(key, row[0])  # entri pertama menang kalau ada kata ganda
    return lexicon


LEXICONS = {code: build_lexicon(code) for code in LANGUAGES}


def lookup(word, language):
    """Emoji untuk satu kata, dengan aturan sinonim sederhana. None kalau tidak ada."""
    lexicon = LEXICONS[language]
    lower = word.lower()
    if lower in lexicon:
        return lexicon[lower]
    if language == "en":
        for ending in ("es", "s"):  # cats -> cat, boxes -> box
            if lower.endswith(ending) and lower[: -len(ending)] in lexicon:
                return lexicon[lower[: -len(ending)]]
    if language == "id" and "-" in lower:
        left, _, right = lower.partition("-")
        if left == right and left in lexicon:  # kucing-kucing (bentuk jamak)
            return lexicon[left] * 2
    for suffix in SUFFIXES[language]:  # rumahnya -> 🏠nya
        if lower.endswith(suffix) and lower[: -len(suffix)] in lexicon:
            return lexicon[lower[: -len(suffix)]] + word[-len(suffix):]
    if lower.isdigit() and lower.isascii():
        return "".join(KEYCAPS[d] for d in lower)
    return None


def tokenize(text):
    return TOKEN_RE.findall(text)


def is_word(token):
    return bool(token) and (token[0].isalnum())


def translate(text, language="id"):
    """Ganti kata dan frasa yang punya emoji. Spasi, tanda baca, dan kata lain dibiarkan."""
    if language not in LEXICONS:
        raise ValueError(f"Bahasa '{language}' tidak tersedia.")
    tokens = tokenize(text)
    lexicon = LEXICONS[language]
    out = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if not is_word(token):
            out.append(token)
            i += 1
            continue
        matched = False
        for size in range(MAX_PHRASE, 1, -1):  # frasa terpanjang dulu: "rumah sakit" sebelum "rumah"
            end = i + size * 2 - 1
            if end > len(tokens):
                continue
            parts = tokens[i:end]
            if all(t.isspace() for t in parts[1::2]) and all(is_word(t) for t in parts[0::2]):
                phrase = " ".join(t.lower() for t in parts[0::2])
                emoji = lexicon.get(phrase)
                if emoji is None and language == "en":  # hot dogs -> hot dog
                    emoji = next((lexicon[phrase[:-len(e)]] for e in ("es", "s")
                                  if phrase.endswith(e) and phrase[:-len(e)] in lexicon), None)
                if emoji is not None:
                    out.append(emoji)
                    i = end
                    matched = True
                    break
        if matched:
            continue
        emoji = lookup(token, language)
        out.append(emoji if emoji is not None else token)
        i += 1
    return "".join(out)


class Translator:
    """Logika tombol Translate/Clear, terpisah dari Tkinter supaya mudah diuji."""

    def __init__(self):
        self.last = None  # (teks, bahasa) yang terakhir diterjemahkan

    def translate(self, text, language):
        """Mengembalikan (hasil, peringatan). Salah satunya None."""
        if not text.strip():
            return None, "Kotak teks masih kosong. Tulis kalimat dulu."
        if self.last == (text, language):
            return None, "Teks belum berubah sejak terjemahan terakhir."
        self.last = (text, language)
        return translate(text, language), None

    def clear(self):
        self.last = None


# --- tampilan Tkinter -------------------------------------------------------------

class TranslatorApp:
    def __init__(self, root):
        import tkinter as tk
        from tkinter import ttk

        self.root = root
        self.logic = Translator()
        root.title("Emoji Translator")
        frame = ttk.Frame(root, padding=14)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)

        top = ttk.Frame(frame)
        top.grid(row=0, column=0, sticky="we")
        ttk.Label(top, text="Teks").pack(side="left")
        self.language = tk.StringVar(value=LANGUAGES["id"])
        ttk.Combobox(top, textvariable=self.language, values=list(LANGUAGES.values()), state="readonly",
                     width=18).pack(side="right")
        ttk.Label(top, text="Bahasa:").pack(side="right", padx=6)

        font = ("Segoe UI Emoji", 13)
        self.input = tk.Text(frame, height=5, width=60, wrap="word", font=font, undo=True)
        self.input.grid(row=1, column=0, sticky="nsew", pady=(4, 8))
        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, sticky="we")
        ttk.Button(buttons, text="Translate", command=self.on_translate).pack(side="left")
        ttk.Button(buttons, text="Clear", command=self.on_clear).pack(side="left", padx=6)
        self.warning = tk.StringVar()
        ttk.Label(buttons, textvariable=self.warning, foreground="#b3261e").pack(side="left", padx=8)

        ttk.Label(frame, text="Hasil").grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.output = tk.Text(frame, height=5, width=60, wrap="word", font=font, state="disabled",
                              background="#f6f5f1")
        self.output.grid(row=4, column=0, sticky="nsew", pady=(4, 0))
        root.bind("<Control-Return>", lambda _e: self.on_translate())
        self.input.focus_set()

    @property
    def language_code(self):
        return next(code for code, name in LANGUAGES.items() if name == self.language.get())

    def set_output(self, text):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def on_translate(self):
        text = self.input.get("1.0", "end-1c")
        result, warning = self.logic.translate(text, self.language_code)
        if warning:
            self.warning.set(warning)
            self.root.bell()
            return
        self.warning.set("")
        self.set_output(result)

    def on_clear(self):
        self.input.delete("1.0", "end")
        self.set_output("")
        self.warning.set("")
        self.logic.clear()


def main(argv=None, gui=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Terjemahkan kata menjadi emoji.")
    parser.add_argument("text", nargs="*", help="kalimat yang diterjemahkan (kosong: buka jendela)")
    parser.add_argument("--lang", choices=sorted(LANGUAGES), default="id", help="bahasa kalimat (bawaan: id)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.text:
        print(translate(" ".join(args.text), args.lang))
        return 0
    (gui or run_gui)()
    return 0


def run_gui():
    import tkinter as tk

    root = tk.Tk()
    TranslatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    raise SystemExit(main())
