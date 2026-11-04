"""Typing Practice: ketik kata yang muncul sebelum waktunya habis. Makin sering benar, makin singkat waktunya.

- Satu huruf salah: huruf yang sudah diketik berkedip merah, kotak isian dikosongkan,
  muncul pesan "coba lagi", dan jumlah percobaan bertambah. Katanya tetap sama.
- Kata benar: ucapan selamat, jumlah berhasil dan percobaan bertambah, waktu per
  kata berkurang 0,25 detik (minimal 1,5 detik), lalu kata baru muncul.
- Waktu habis: dihitung sebagai percobaan gagal, lalu kata baru muncul.

Bunyi berbeda untuk kata baru, kata benar, dan huruf salah (berkas WAV buatan sendiri, winsound).

Jalankan:
    python typing_practice.py
"""

import math
import os
import random
import struct
import tempfile
import time
import wave

START_INTERVAL = 6.0
STEP = 0.25
MIN_INTERVAL = 1.5

WORDS = """
rumah sekolah pasar sungai gunung pantai jalan kereta sepeda motor mobil kapal pesawat
buku pensil meja kursi jendela pintu lampu kipas kunci tas sepatu baju celana topi
makan minum tidur bangun mandi belajar bermain menulis membaca berlari berenang memasak
nasi roti teh kopi susu air buah apel jeruk pisang mangga semangka durian kelapa
merah biru hijau kuning putih hitam ungu oranye coklat abu
senang sedih marah takut lelah lapar haus bahagia tenang ramah
pagi siang sore malam hari minggu bulan tahun kemarin besok sekarang nanti
kucing anjing burung ikan ayam sapi kambing kuda gajah harimau kelinci kupu
komputer laptop ponsel internet program kode python fungsi variabel daftar kamus kelas
indonesia jakarta bandung surabaya medan makassar yogyakarta semarang denpasar
pelangi hujan angin awan matahari bintang petir salju embun kabut
keluarga teman sahabat guru murid dokter petani nelayan pedagang tetangga
""".split()


def pick_word(rng, previous=None):
    """Kata acak, tidak sama dengan kata sebelumnya."""
    while True:
        word = rng.choice(WORDS)
        if word != previous:
            return word


class Session:
    """Satu sesi latihan. Jam bisa diganti di tes (clock), jadi tidak perlu menunggu sungguhan."""

    def __init__(self, rng=None, clock=time.monotonic):
        self.rng = rng or random.Random()
        self.clock = clock
        self.running = False
        self.reset()

    def reset(self):
        self.interval = START_INTERVAL
        self.successes = 0
        self.attempts = 0
        self.word = None
        self.deadline = None

    def start(self):
        self.reset()
        self.running = True
        return self.next_word()

    def stop(self):
        self.running = False
        self.deadline = None

    def next_word(self):
        self.word = pick_word(self.rng, self.word)
        self.deadline = self.clock() + self.interval
        return self.word

    def remaining(self):
        if not self.running or self.deadline is None:
            return 0.0
        return max(0.0, self.deadline - self.clock())

    def type(self, text):
        """Periksa teks di kotak isian. Hasil: 'idle', 'typing', 'wrong', 'correct', atau 'timeout'."""
        if not self.running:
            return "idle"
        if self.remaining() <= 0:
            return self.timeout()
        if not self.word.startswith(text.lower()):
            self.attempts += 1
            return "wrong"
        if text.lower() == self.word:
            self.attempts += 1
            self.successes += 1
            self.interval = max(MIN_INTERVAL, round(self.interval - STEP, 2))
            self.next_word()
            return "correct"
        return "typing"

    def timeout(self):
        if not self.running:
            return "idle"
        self.attempts += 1
        self.next_word()
        return "timeout"

    def check_time(self):
        """Dipanggil berkala: 'timeout' kalau waktu kata sekarang sudah habis."""
        if self.running and self.remaining() <= 0:
            return self.timeout()
        return None


# --- bunyi -----------------------------------------------------------------------

RATE = 22050


def tone(freqs, duration, volume=0.4):
    count = int(RATE * duration)
    samples = []
    for n in range(count):
        t = n / RATE
        envelope = min(1.0, n / 200) * math.exp(-5 * t / duration)
        samples.append(volume * envelope * sum(math.sin(2 * math.pi * f * t) for f in freqs) / len(freqs))
    return samples


def write_wav(path, samples):
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(b"".join(struct.pack("<h", int(s * 32000)) for s in samples))
    return path


SOUNDS = {
    "new": ([660], 0.12),  # bip pendek: kata baru
    "correct": ([784, 988, 1319], 0.35),  # akor naik: benar
    "wrong": ([196, 185], 0.3),  # nada rendah sumbang: salah
}


class SoundPlayer:
    def __init__(self):
        self.folder = tempfile.mkdtemp(prefix="typing-")
        self.paths = {name: write_wav(os.path.join(self.folder, f"{name}.wav"), tone(*spec))
                      for name, spec in SOUNDS.items()}
        try:
            import winsound
            self.winsound = winsound
        except ImportError:
            self.winsound = None

    def play(self, name):
        if self.winsound:
            self.winsound.PlaySound(self.paths[name], self.winsound.SND_FILENAME | self.winsound.SND_ASYNC)


# --- tampilan Tkinter -------------------------------------------------------------------

class TypingApp:
    def __init__(self, root, session=None, sound=None):
        import tkinter as tk
        from tkinter import ttk

        self.root = root
        self.session = session or Session()
        self.sound = sound if sound is not None else SoundPlayer()
        self.timer_job = None
        self.flash_job = None
        root.title("Typing Practice")
        root.resizable(False, False)
        frame = ttk.Frame(root, padding=18)
        frame.pack()
        top = ttk.Frame(frame)
        top.pack(fill="x")
        self.interval_text = tk.StringVar()
        ttk.Label(top, textvariable=self.interval_text, font=("Segoe UI", 11)).pack(side="left")
        score = ttk.LabelFrame(top, text="Skor", padding=(10, 2))
        score.pack(side="right")
        self.score_text = tk.StringVar()
        ttk.Label(score, textvariable=self.score_text, font=("Segoe UI", 12, "bold")).pack()

        self.prompt = tk.Entry(frame, font=("Consolas", 30, "bold"), justify="center", width=16,
                               readonlybackground="#f1efe8", relief="flat", state="readonly")
        self.prompt.pack(pady=(16, 6), ipady=6)
        self.prompt_var = tk.StringVar()
        self.prompt.configure(textvariable=self.prompt_var)
        self.bar = tk.Canvas(frame, height=8, width=440, highlightthickness=0, background="#e4e2da")
        self.bar.pack(fill="x")

        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(14, 0))
        self.typed = tk.StringVar()
        self.entry = tk.Entry(row, textvariable=self.typed, font=("Consolas", 20), width=16, relief="solid",
                              borderwidth=1, state="disabled")
        self.entry.pack(side="left", ipady=4)
        self.typed.trace_add("write", lambda *_: self.on_type())
        self.message = tk.StringVar()
        self.message_label = ttk.Label(row, textvariable=self.message, font=("Segoe UI", 11, "bold"), width=18)
        self.message_label.pack(side="left", padx=12)
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(16, 0))
        self.start_button = ttk.Button(buttons, text="Start Practice", command=self.start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(buttons, text="Stop Practice", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=8)
        self.normal_bg = self.entry.cget("background")
        self.update_labels()

    def update_labels(self):
        s = self.session
        self.interval_text.set(f"Waktu per kata: {s.interval:.2f} detik".replace(".", ","))
        self.score_text.set(f"{s.successes} berhasil / {s.attempts} percobaan")

    def show_word(self):
        self.prompt_var.set(self.session.word)
        self.sound.play("new")

    def start(self):
        self.session.start()
        self.entry.configure(state="normal")
        self.entry.focus_set()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.message.set("")
        self.show_word()
        self.update_labels()
        self.tick()

    def stop(self):
        self.session.stop()
        for job in (self.timer_job, self.flash_job):
            if job:
                self.root.after_cancel(job)
        self.timer_job = self.flash_job = None
        self.entry.configure(state="normal", background=self.normal_bg)
        self.typed.set("")
        self.entry.configure(state="disabled")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.prompt_var.set("")
        s = self.session
        rate = f" ({s.successes * 100 // s.attempts}% benar)" if s.attempts else ""
        self.message.set(f"Selesai{rate}")
        self.message_label.configure(foreground="#1d1d1b")
        self.draw_bar()

    def tick(self):
        if self.session.check_time() == "timeout":
            self.feedback("Waktu habis!", "#b3261e")
            self.typed.set("")
            self.show_word()
            self.update_labels()
        self.draw_bar()
        if self.session.running:
            self.timer_job = self.root.after(50, self.tick)

    def draw_bar(self):
        self.bar.delete("all")
        width = int(self.bar.cget("width"))
        fraction = self.session.remaining() / self.session.interval if self.session.running else 0
        color = "#2a9d55" if fraction > 0.5 else "#d9900f" if fraction > 0.25 else "#c0392b"
        self.bar.create_rectangle(0, 0, width * fraction, 8, fill=color, outline="")

    def feedback(self, text, color):
        self.message.set(text)
        self.message_label.configure(foreground=color)

    def on_type(self):
        text = self.typed.get()
        if not text or self.flash_job:
            return
        result = self.session.type(text)
        if result == "wrong":
            self.sound.play("wrong")
            self.feedback("Salah, coba lagi!", "#b3261e")
            self.flash(6)
        elif result == "correct":
            self.sound.play("correct")
            self.feedback("Selamat, benar!", "#2a7d46")
            self.typed.set("")
            self.show_word()
        elif result == "timeout":
            self.feedback("Waktu habis!", "#b3261e")
            self.typed.set("")
            self.show_word()
        self.update_labels()

    def flash(self, times):
        """Kedipkan huruf yang sudah diketik, lalu kosongkan kotak isian."""
        if times <= 0:
            self.flash_job = None
            self.entry.configure(background=self.normal_bg)
            self.typed.set("")
            return
        self.entry.configure(background="#f7c5c0" if times % 2 == 0 else self.normal_bg)
        self.flash_job = self.root.after(70, lambda: self.flash(times - 1))


def main():
    import tkinter as tk

    root = tk.Tk()
    TypingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
