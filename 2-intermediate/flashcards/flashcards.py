"""Flashcards: kartu soal pilihan ganda, jawaban salahnya diambil dari kartu lain.

Basis pengetahuan berupa dict Python (spesifikasi menyebut objek JavaScript).
Deck bawaan: ibu kota provinsi di Indonesia. Deck lain bisa dimuat dari JSON
dengan bentuk yang sama: [{"question": ..., "answer": ..., "info": ...}, ...].

Jalankan:
    python flashcards.py
    python flashcards.py --deck deck-saya.json
"""

import argparse
import json
import random
import sys

LETTERS = "ABCD"

# Basis pengetahuan: provinsi -> (ibu kota, info tambahan untuk sisi belakang kartu).
# DKI Jakarta tidak dimasukkan karena tidak punya ibu kota provinsi seperti provinsi lain.
PROVINCES = {
    "Aceh": ("Banda Aceh", "Ujung utara Pulau Sumatra."),
    "Sumatera Utara": ("Medan", "Pulau Sumatra. Medan adalah kota terbesar di luar Pulau Jawa."),
    "Sumatera Barat": ("Padang", "Pantai barat Pulau Sumatra, tanah asal suku Minangkabau."),
    "Riau": ("Pekanbaru", "Bagian tengah-timur Pulau Sumatra."),
    "Kepulauan Riau": ("Tanjungpinang", "Gugusan pulau di dekat Singapura. Tanjungpinang ada di Pulau Bintan."),
    "Jambi": ("Jambi", "Pulau Sumatra. Nama ibu kotanya sama dengan nama provinsinya."),
    "Sumatera Selatan": ("Palembang", "Pulau Sumatra. Palembang dilalui Sungai Musi."),
    "Kepulauan Bangka Belitung": ("Pangkalpinang", "Pulau Bangka dan Belitung, timur Sumatra."),
    "Bengkulu": ("Bengkulu", "Pantai barat daya Pulau Sumatra."),
    "Lampung": ("Bandar Lampung", "Ujung selatan Pulau Sumatra, di seberang Selat Sunda."),
    "Banten": ("Serang", "Ujung barat Pulau Jawa."),
    "Jawa Barat": ("Bandung", "Pulau Jawa. Bandung berada di dataran tinggi."),
    "Jawa Tengah": ("Semarang", "Pulau Jawa, di pantai utara."),
    "Daerah Istimewa Yogyakarta": ("Yogyakarta", "Pulau Jawa. Dipimpin oleh Sultan Hamengkubuwono sebagai gubernur."),
    "Jawa Timur": ("Surabaya", "Pulau Jawa bagian timur. Surabaya dijuluki Kota Pahlawan."),
    "Bali": ("Denpasar", "Pulau Bali, di timur Pulau Jawa."),
    "Nusa Tenggara Barat": ("Mataram", "Pulau Lombok dan Sumbawa. Mataram ada di Pulau Lombok."),
    "Nusa Tenggara Timur": ("Kupang", "Pulau Flores, Sumba, Timor, dan lainnya. Kupang ada di Pulau Timor."),
    "Kalimantan Barat": ("Pontianak", "Pulau Kalimantan. Pontianak dilalui garis khatulistiwa."),
    "Kalimantan Tengah": ("Palangka Raya", "Pulau Kalimantan, bagian tengah."),
    "Kalimantan Selatan": ("Banjarbaru", "Pulau Kalimantan. Ibu kota pindah dari Banjarmasin ke Banjarbaru pada 2022."),
    "Kalimantan Timur": ("Samarinda", "Pulau Kalimantan. Lokasi Ibu Kota Nusantara (IKN)."),
    "Kalimantan Utara": ("Tanjung Selor", "Pulau Kalimantan, berbatasan dengan Malaysia. Provinsi termuda di Kalimantan."),
    "Sulawesi Utara": ("Manado", "Ujung utara Pulau Sulawesi."),
    "Gorontalo": ("Gorontalo", "Pulau Sulawesi bagian utara. Nama ibu kotanya sama dengan nama provinsinya."),
    "Sulawesi Tengah": ("Palu", "Pulau Sulawesi bagian tengah."),
    "Sulawesi Barat": ("Mamuju", "Pantai barat Pulau Sulawesi."),
    "Sulawesi Selatan": ("Makassar", "Pulau Sulawesi bagian selatan."),
    "Sulawesi Tenggara": ("Kendari", "Pulau Sulawesi bagian tenggara."),
    "Maluku": ("Ambon", "Kepulauan Maluku. Ambon ada di Pulau Ambon."),
    "Maluku Utara": ("Sofifi", "Kepulauan Maluku. Sofifi ada di Pulau Halmahera; Ternate dulu pusat pemerintahan sementara."),
    "Papua": ("Jayapura", "Pulau Papua bagian utara, dekat perbatasan dengan Papua Nugini."),
    "Papua Barat": ("Manokwari", "Pulau Papua bagian barat (Kepala Burung)."),
    "Papua Barat Daya": ("Sorong", "Pulau Papua. Dibentuk pada 2022 dari sebagian wilayah Papua Barat."),
    "Papua Selatan": ("Merauke", "Pulau Papua. Dibentuk pada 2022 dari sebagian wilayah Papua."),
    "Papua Tengah": ("Nabire", "Pulau Papua. Dibentuk pada 2022 dari sebagian wilayah Papua."),
    "Papua Pegunungan": ("Wamena", "Pulau Papua. Dibentuk pada 2022; satu-satunya provinsi yang tidak punya laut."),
}

DEFAULT_DECK = [
    {"question": f"Apa ibu kota provinsi {province}?", "answer": capital, "info": f"{province}: {info}"}
    for province, (capital, info) in PROVINCES.items()
]


def load_deck(path):
    """Muat deck JSON. Setiap kartu butuh 'question' dan 'answer'; 'info' boleh kosong."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("Deck harus berupa daftar kartu.")
    deck = []
    for number, card in enumerate(data, start=1):
        if not isinstance(card, dict) or not str(card.get("question", "")).strip() or \
                not str(card.get("answer", "")).strip():
            raise ValueError(f"Kartu ke-{number} butuh 'question' dan 'answer'.")
        deck.append({"question": str(card["question"]).strip(), "answer": str(card["answer"]).strip(),
                     "info": str(card.get("info", "")).strip()})
    if len({card["answer"] for card in deck}) < len(LETTERS):
        raise ValueError(f"Deck butuh setidaknya {len(LETTERS)} jawaban berbeda.")
    return deck


class FlashcardSession:
    """Urutan kartu, pilihan jawaban, dan hitungan benar/salah. Tanpa Tkinter supaya mudah diuji."""

    def __init__(self, deck, rng=None):
        if len({card["answer"] for card in deck}) < len(LETTERS):
            raise ValueError(f"Deck butuh setidaknya {len(LETTERS)} jawaban berbeda.")
        self.deck = list(deck)
        self.rng = rng or random.Random()
        self.correct = 0
        self.incorrect = 0
        self.order = []
        self.card = None
        self.choices = []
        self.answered = False  # sudah dijawab benar
        self.attempted = False  # sudah pernah dijawab (benar/salah) -> hitungan sudah dicatat
        self.shuffle()

    def shuffle(self):
        """Kocok ulang deck dan tampilkan kartu pertama."""
        self.order = list(range(len(self.deck)))
        self.rng.shuffle(self.order)
        self.next_card()

    def next_card(self):
        if not self.order:  # deck habis: kocok lagi
            self.order = list(range(len(self.deck)))
            self.rng.shuffle(self.order)
            if self.card is not None and len(self.order) > 1 and self.deck[self.order[-1]] is self.card:
                self.order.insert(0, self.order.pop())  # jangan tampilkan kartu yang sama dua kali berturut
        self.card = self.deck[self.order.pop()]
        self.choices = self._make_choices(self.card)
        self.answered = False
        self.attempted = False
        return self.card

    def _make_choices(self, card):
        wrong = sorted({other["answer"] for other in self.deck if other["answer"] != card["answer"]})
        options = self.rng.sample(wrong, len(LETTERS) - 1) + [card["answer"]]
        self.rng.shuffle(options)
        return list(zip(LETTERS, options))

    @property
    def correct_letter(self):
        return next(letter for letter, text in self.choices if text == self.card["answer"])

    def answer(self, letter):
        """Pilih jawaban. Hitungan dicatat sekali per kartu, dari pilihan pertama."""
        if self.answered:
            return None
        if letter not in dict(self.choices):
            raise ValueError(f"Pilihan '{letter}' tidak ada.")
        is_correct = letter == self.correct_letter
        if not self.attempted:
            self.attempted = True
            if is_correct:
                self.correct += 1
            else:
                self.incorrect += 1
        if is_correct:
            self.answered = True
        return is_correct

    def reset_tallies(self):
        self.correct = self.incorrect = 0

    def results(self):
        total = self.correct + self.incorrect
        percent = f" ({self.correct * 100 // total}% benar)" if total else ""
        return f"Benar {self.correct} | Salah {self.incorrect}{percent}"


# --- tampilan Tkinter -----------------------------------------------------------

CARD_BG, CARD_BACK_BG = "#fffdf7", "#eef4fb"
GOOD, BAD = "#2a7d46", "#b3261e"


class FlashcardApp:
    def __init__(self, root, session):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.root = root
        self.session = session
        self.showing_info = False
        root.title("Flashcards")
        root.resizable(False, False)
        self.card = tk.Frame(root, background=CARD_BG, highlightthickness=1, highlightbackground="#c9c4b8",
                             padx=24, pady=20)
        self.card.pack(padx=18, pady=(18, 8), fill="x")
        tk.Label(self.card, text="Pertanyaan", background=CARD_BG, foreground="#777",
                 font=("Segoe UI", 9)).pack(anchor="w")
        # Tinggi 2 baris tetap, supaya jendela tidak naik-turun untuk soal yang panjang/pendek.
        self.question = tk.Label(self.card, background=CARD_BG, font=("Segoe UI", 15, "bold"), wraplength=540,
                                 justify="left", anchor="w", height=2)
        self.question.pack(fill="x", pady=(4, 12))
        self.choice_buttons = []
        for _ in LETTERS:
            button = tk.Button(self.card, anchor="w", relief="groove", font=("Segoe UI", 12), padx=12, pady=6,
                               cursor="hand2", background="#ffffff", activebackground="#f1efe8")
            button.pack(fill="x", pady=3)
            self.choice_buttons.append(button)
        self.feedback = tk.Label(self.card, background=CARD_BG, font=("Segoe UI", 11, "bold"), anchor="w")
        self.feedback.pack(fill="x", pady=(10, 0))

        # Sisi belakang kartu menutupi sisi depan (place), jadi ukuran kartu tidak berubah saat dibalik.
        self.back = tk.Frame(self.card, background=CARD_BACK_BG, padx=24, pady=20)
        tk.Label(self.back, text="Info", background=CARD_BACK_BG, foreground="#777",
                 font=("Segoe UI", 9)).pack(anchor="w")
        self.info = tk.Label(self.back, background=CARD_BACK_BG, font=("Segoe UI", 13), wraplength=540,
                             justify="left", anchor="nw")
        self.info.pack(fill="both", expand=True, pady=(4, 0))

        bar = ttk.Frame(root, padding=(18, 0, 18, 6))
        bar.pack(fill="x")
        ttk.Button(bar, text="Next Question", command=self.next_question).pack(side="left")
        self.info_button = ttk.Button(bar, text="More Info", width=16, command=self.flip)
        self.info_button.pack(side="left", padx=6)
        ttk.Button(bar, text="Shuffle", command=self.shuffle).pack(side="right")
        ttk.Button(bar, text="Reset", command=self.reset).pack(side="right", padx=6)
        ttk.Button(bar, text="Results", command=self.show_results).pack(side="right")
        self.results = tk.StringVar()
        ttk.Label(root, textvariable=self.results, padding=(18, 0, 18, 14)).pack(anchor="w")
        for index, letter in enumerate(LETTERS):
            root.bind(letter.lower(), lambda _e, i=index: self.choose(i))
        root.bind("<Return>", lambda _e: self.next_question())
        self.render()

    def render(self):
        s = self.session
        self.show_front()
        self.question.configure(text=s.card["question"])
        for index, ((letter, text), button) in enumerate(zip(s.choices, self.choice_buttons)):
            button.configure(text=f"{letter}.  {text}", command=lambda i=index: self.choose(i),
                             background="#ffffff", foreground="#1d1d1b", state="normal")
        self.feedback.configure(text="")
        self.info_button.configure(state="normal" if s.card.get("info") else "disabled")

    def choose(self, index):
        if self.showing_info:
            return
        letter, text = self.session.choices[index]
        result = self.session.answer(letter)
        if result is None:
            return
        button = self.choice_buttons[index]
        if result:
            button.configure(background="#dcefe2", foreground=GOOD)
            self.feedback.configure(text=f"Selamat, benar! Jawabannya {text}.", foreground=GOOD)
            for other in self.choice_buttons:
                if other is not button:
                    other.configure(state="disabled")
        else:
            button.configure(background="#f7dedb", foreground=BAD, state="disabled")
            self.feedback.configure(text=f"Salah, {text} bukan jawabannya. Coba lagi.", foreground=BAD)
        if self.results.get():
            self.show_results()

    def flip(self):
        """Balik kartu: sisi belakang berisi info tambahan."""
        if self.showing_info:
            self.show_front()
            return
        self.showing_info = True
        self.info.configure(text=self.session.card.get("info") or "Tidak ada info tambahan.")
        # place() dihitung dari dalam padding kartu (24, 20), jadi geser keluar sebesar padding itu.
        self.back.place(x=-24, y=-20, relwidth=1, relheight=1, width=48, height=40)
        self.back.lift()
        self.info_button.configure(text="Kembali ke soal")

    def show_front(self):
        self.showing_info = False
        self.back.place_forget()
        self.info_button.configure(text="More Info")

    def next_question(self):
        self.session.next_card()
        self.render()

    def shuffle(self):
        self.session.shuffle()
        self.render()
        self.results.set(self.results.get() and self.session.results())

    def show_results(self):
        self.results.set(self.session.results())

    def reset(self):
        self.session.reset_tallies()
        self.results.set(self.session.results())


def main(argv=None):
    parser = argparse.ArgumentParser(description="Flashcards pilihan ganda.")
    parser.add_argument("--deck", help="berkas JSON berisi kartu (bawaan: ibu kota provinsi Indonesia)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        deck = load_deck(args.deck) if args.deck else DEFAULT_DECK
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    import tkinter as tk

    root = tk.Tk()
    FlashcardApp(root, FlashcardSession(deck))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
